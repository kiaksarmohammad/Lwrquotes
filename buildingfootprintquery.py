from pystac_client import Client
import planetary_computer as pc
from geopy.geocoders import Nominatim, ArcGIS
from geopy.location import Location
from geopy.exc import GeocoderServiceError
from shapely.geometry import shape, box, mapping
import math
import time

# --- CONFIGURATION ---
PRICING = {
    "TPO_60mil_Mechanically_Attached": 8.50,
    "EPDM_60mil_Fully_Adhered": 9.75,
    "ISO_Insulation_2_Layer": 3.50,
    "Parapet_Flashing_Detail": 18.00,
    "HVAC_Curb_Detail": 350.00
}

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
    
    # Create search box
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
        raise ValueError("No building footprint found at this location.")

    # FIX 2: Handle the 'None' type error for geometry
    first_item = items[0]
    
    # We explicitly check if geometry exists. If it's None, we stop.
    # This satisfies Pylance that we aren't passing None to shape().
    if first_item.geometry is None:
        raise ValueError("Building footprint found, but geometry data is missing (None).")

    return shape(first_item.geometry)

def estimate_flat_roof(polygon, system_type="TPO", parapet_height_ft=2.0, hvac_count_est=None):
    # 1. Base Geometry
    # Approx conversion: 1 degree latitude ~ 364,000 ft (rough estimation for estimator logic)
    # For high precision, use pyproj.
    field_area_sqft = polygon.area * 11630000000  # Adjusted scalar for lat/lon -> sq ft roughly
    
    perimeter_lf = polygon.length * 340000 # Rough deg -> ft conversion
    
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