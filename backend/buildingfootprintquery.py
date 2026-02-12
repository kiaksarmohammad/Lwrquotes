from pystac_client import Client
import planetary_computer as pc
from geopy.geocoders import Nominatim, ArcGIS
from geopy.location import Location
from geopy.exc import GeocoderServiceError
from shapely.geometry import box, mapping, Point
from shapely import wkb
from shapely.ops import transform
from pyproj import Transformer
import pyarrow.parquet as pq
import adlfs
import math
import time

from backend.database import PRICING
    
def get_commercial_footprint(address: str):
    # FIX 1: Ensure we use the standard synchronous Geolocator
    # We do NOT pass an 'adapter_factory' here, ensuring it blocks and returns data, not a coroutine.
    geolocator = Nominatim(user_agent=f"lwrquotes_roofing_estimator_{int(time.time())}")
    
    location = None
    max_retries = 5
    for attempt in range(max_retries):
        try:
            location = geolocator.geocode(address)
            break
        except GeocoderServiceError as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"Geocoder error (attempt {attempt + 1}/{max_retries}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"Nominatim failed after {max_retries} attempts, falling back to ArcGIS...")
                try:
                    arcgis = ArcGIS()
                    location = arcgis.geocode(address)
                except Exception as fallback_err:
                    raise ValueError(f"All geocoders failed. Nominatim: {e} | ArcGIS: {fallback_err}")

    if not isinstance(location, Location):
        raise ValueError(f"Could not find coordinates for address: {address}")
        
    print(f"Locate: {address} ({location.latitude}, {location.longitude})")
    
    # Find the region-level STAC item to get the parquet file path
    bbox = box(location.longitude - 0.001, location.latitude - 0.001,
               location.longitude + 0.001, location.latitude + 0.001)

    catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace)
    search = catalog.search(
        filter_lang="cql2-json",
        filter={
            "op": "and",
            "args": [
                {"op": "s_intersects", "args": [{"property": "geometry"}, mapping(bbox)]},
                {"op": "=", "args": [{"property": "collection"}, "ms-buildings"]}
            ]
        }
    )

    items = list(search.items()) 
    if not items:
        raise ValueError("No building footprint data found for this region.")

    # Compute quadkey (level 9) for the target location to filter the parquet file
    quadkey = _lat_lon_to_quadkey(location.latitude, location.longitude, 9)
    print(f"Searching buildings in quadkey {quadkey}...")

    sas_token = pc.sas.get_token("bingmlbuildings", "footprints").token
    fs = adlfs.AzureBlobFileSystem(account_name="bingmlbuildings", sas_token=sas_token)

    # Try each regional parquet file until we find buildings
    table = None
    for item in items:
        asset_href = item.assets["data"].href
        parquet_path = asset_href.replace("abfs://", "")
        print(f"Checking {item.id}...")
        t = pq.read_table(parquet_path, filesystem=fs,
                          filters=[("quadkey", "=", int(quadkey))],
                          columns=["geometry"])
        if len(t) > 0:
            table = t
            break

    if table is None or len(table) == 0:
        raise ValueError("No building footprint found at this location.")

    # Parse WKB geometries and find the building closest to the address
    target = Point(location.longitude, location.latitude)
    geoms = [wkb.loads(g.as_py()) for g in table.column("geometry")]
    dists = [g.distance(target) for g in geoms]
    closest = geoms[dists.index(min(dists))]
    print(f"Found building footprint ({len(geoms)} candidates in tile)")

    return closest


def _lat_lon_to_quadkey(lat: float, lon: float, level: int) -> str:
    x = int((lon + 180) / 360 * (2 ** level))
    sin_lat = math.sin(lat * math.pi / 180)
    y = int((0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * (2 ** level))
    quadkey = ""
    for i in range(level, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if x & mask:
            digit += 1
        if y & mask:
            digit += 2
        quadkey += str(digit)
    return quadkey

def estimate_flat_roof(polygon, system_type="TPO", parapet_height_ft=2.0, hvac_count_est=None):
    # 1. Base Geometry — project from WGS84 (lat/lon) to UTM (meters), then convert to feet
    centroid = polygon.centroid
    utm_zone = int((centroid.x + 180) / 6) + 1
    hemisphere = "north" if centroid.y >= 0 else "south"
    utm_crs = f"+proj=utm +zone={utm_zone} +{hemisphere} +datum=WGS84"

    projector = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
    polygon_m = transform(projector.transform, polygon)

    SQ_M_TO_SQ_FT = 10.7639
    M_TO_FT = 3.28084
    field_area_sqft = polygon_m.area * SQ_M_TO_SQ_FT
    perimeter_lf = polygon_m.length * M_TO_FT
    
    # 2. Heuristics
    if hvac_count_est is None:
        hvac_count_est = math.ceil(field_area_sqft / 2500)
    
    # 3. Vertical Area (Parapet)
    parapet_vertical_area = perimeter_lf * parapet_height_ft
    
    # 4. Total Membrane
    total_membrane_sqft = (field_area_sqft + parapet_vertical_area) * 1.10
    
    # 5. Cost
    price_per_sqft = PRICING["TPO_60mil_Mechanically_Attached"] if system_type == "TPO" else PRICING["EPDM_60mil_Fully_Adhered"]
    
    cost_membrane = total_membrane_sqft * price_per_sqft
    cost_insulation = field_area_sqft * PRICING["ISO_Insulation_2_Layer"]
    cost_flashing = perimeter_lf * PRICING["Parapet_Flashing_Detail"]
    cost_hvac = hvac_count_est * PRICING["HVAC_Curb_Detail"]
    
    total_project_cost = cost_membrane + cost_insulation + cost_flashing + cost_hvac
    
    return {
        "metrics": {
            "footprint_area_sqft": round(field_area_sqft, 0),
            "perimeter_linear_ft": round(perimeter_lf, 0),
            "est_hvac_units": hvac_count_est
        },
        "costs": {
            "TOTAL_ESTIMATE": round(total_project_cost, 2)
        }
    }

# --- Execution ---
if __name__ == "__main__":
    addr = input("Enter Commercial Address: ")
    try:
        poly = get_commercial_footprint(addr)
        est = estimate_flat_roof(poly)
        print(est)
    except Exception as e:
        print(f"Error: {e}")