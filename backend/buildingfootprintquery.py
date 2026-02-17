"""
Google Solar API integration for building roof data.

Replaces the previous Microsoft Building Footprints approach with Google's
Solar API buildingInsights endpoint, which provides roof segments with
pitch, azimuth, surface area, and height data.
"""

import os
import math
import time
import requests

from geopy.geocoders import Nominatim, ArcGIS
from geopy.location import Location
from geopy.exc import GeocoderServiceError
from geopy.distance import geodesic

from backend.database import PRICING


def _geocode_address(address: str) -> tuple[float, float]:
    """Geocode an address to (latitude, longitude) using Nominatim with ArcGIS fallback."""
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
    return location.latitude, location.longitude


def get_building_insights(address: str) -> dict:
    """
    Query Google Solar API for building roof data at the given address.

    Returns a dict with:
      - latitude, longitude
      - whole_roof_area_m2, ground_area_m2
      - roof_segments: list of dicts with pitch, azimuth, area, ground_area,
        height, center, bounding_box
      - imagery_quality
    """
    api_key = os.environ.get("GOOGLE_SOLAR_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_SOLAR_API_KEY not set. Add it to your .env file. "
            "Get a key at https://console.cloud.google.com/apis/library/solar.googleapis.com"
        )

    lat, lng = _geocode_address(address)

    url = "https://solar.googleapis.com/v1/buildingInsights:findClosest"
    params = {
        "location.latitude": lat,
        "location.longitude": lng,
        "requiredQuality": "HIGH",
        "key": api_key,
    }

    resp = requests.get(url, params=params, timeout=30)

    if resp.status_code == 404:
        raise ValueError(
            f"No building found near ({lat:.6f}, {lng:.6f}). "
            "Google Solar API may not have coverage for this location."
        )
    if resp.status_code == 403:
        raise ValueError(
            "Google Solar API access denied. Check that your API key is valid "
            "and the Solar API is enabled in your Google Cloud project."
        )
    if resp.status_code != 200:
        raise ValueError(f"Google Solar API error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    solar = data.get("solarPotential", {})
    whole_roof = solar.get("wholeRoofStats", {})

    segments = []
    for seg in solar.get("roofSegmentStats", []):
        stats = seg.get("stats", {})
        bbox = seg.get("boundingBox", {})
        segments.append({
            "pitch_degrees": seg.get("pitchDegrees", 0),
            "azimuth_degrees": seg.get("azimuthDegrees", 0),
            "area_m2": stats.get("areaMeters2", 0),
            "ground_area_m2": stats.get("groundAreaMeters2", 0),
            "height_m": seg.get("planeHeightAtCenterMeters", 0),
            "center": seg.get("center", {}),
            "bounding_box": bbox,
        })

    return {
        "latitude": lat,
        "longitude": lng,
        "whole_roof_area_m2": whole_roof.get("areaMeters2", 0),
        "ground_area_m2": whole_roof.get("groundAreaMeters2", 0),
        "roof_segments": segments,
        "imagery_quality": data.get("imageryQuality", "UNKNOWN"),
    }


def _estimate_perimeter_from_bbox(insights: dict) -> float:
    """
    Estimate building perimeter in feet from the bounding boxes of all roof segments.

    Computes the outer bounding box of all segments, then uses geodesic distances
    to convert lat/lng extents to linear feet.
    """
    M_TO_FT = 3.28084
    segments = insights.get("roof_segments", [])

    # Collect all bounding box corners
    all_sw_lats = []
    all_sw_lngs = []
    all_ne_lats = []
    all_ne_lngs = []

    for seg in segments:
        bbox = seg.get("bounding_box", {})
        sw = bbox.get("sw", {})
        ne = bbox.get("ne", {})
        if sw.get("latitude") is not None and ne.get("latitude") is not None:
            all_sw_lats.append(sw["latitude"])
            all_sw_lngs.append(sw["longitude"])
            all_ne_lats.append(ne["latitude"])
            all_ne_lngs.append(ne["longitude"])

    if not all_sw_lats:
        # Fallback: square assumption from ground area
        ground_area_sqft = insights["ground_area_m2"] * 10.7639
        side = math.sqrt(ground_area_sqft)
        return 4 * side

    sw_lat = min(all_sw_lats)
    sw_lng = min(all_sw_lngs)
    ne_lat = max(all_ne_lats)
    ne_lng = max(all_ne_lngs)

    # Use geodesic distance to compute width and height in feet
    width_ft = geodesic((sw_lat, sw_lng), (sw_lat, ne_lng)).meters * M_TO_FT
    height_ft = geodesic((sw_lat, sw_lng), (ne_lat, sw_lng)).meters * M_TO_FT

    return 2 * (width_ft + height_ft)


def estimate_flat_roof(insights: dict, system_type: str = "TPO",
                       parapet_height_ft: float = 2.0,
                       hvac_count_est: int = None) -> dict:
    """
    Generate a cost estimate from Google Solar API building insights.

    Args:
        insights: dict from get_building_insights()
        system_type: "TPO" or "EPDM"
        parapet_height_ft: parapet wall height in feet
        hvac_count_est: override HVAC unit count (auto-estimated if None)

    Returns:
        dict with metrics, costs, and roof_segments for display
    """
    SQ_M_TO_SQ_FT = 10.7639

    # Ground footprint area (plan-view projection)
    field_area_sqft = insights["ground_area_m2"] * SQ_M_TO_SQ_FT

    # Whole roof surface area (accounts for pitch)
    whole_roof_area_sqft = insights["whole_roof_area_m2"] * SQ_M_TO_SQ_FT

    # Perimeter from bounding box
    perimeter_lf = _estimate_perimeter_from_bbox(insights)

    # HVAC estimate
    if hvac_count_est is None:
        hvac_count_est = math.ceil(field_area_sqft / 2500)

    # Parapet vertical area
    parapet_vertical_area = perimeter_lf * parapet_height_ft

    # Total membrane (field + parapet + 10% waste)
    total_membrane_sqft = (field_area_sqft + parapet_vertical_area) * 1.10

    # Costs
    price_per_sqft = (PRICING["TPO_60mil_Mechanically_Attached"]
                      if system_type == "TPO"
                      else PRICING["EPDM_60mil_Fully_Adhered"])

    cost_membrane = total_membrane_sqft * price_per_sqft
    cost_insulation = field_area_sqft * PRICING["ISO_Insulation_2_Layer"]
    cost_flashing = perimeter_lf * PRICING["Parapet_Flashing_Detail"]
    cost_hvac = hvac_count_est * PRICING["HVAC_Curb_Detail"]

    total_project_cost = cost_membrane + cost_insulation + cost_flashing + cost_hvac

    # Build roof segment display data
    segment_details = []
    for i, seg in enumerate(insights.get("roof_segments", []), 1):
        seg_area_sqft = seg["area_m2"] * SQ_M_TO_SQ_FT
        seg_ground_sqft = seg["ground_area_m2"] * SQ_M_TO_SQ_FT

        # Convert azimuth to compass direction
        azimuth = seg["azimuth_degrees"]
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        dir_index = round(azimuth / 45) % 8
        compass = directions[dir_index]

        segment_details.append({
            "segment_number": i,
            "pitch_degrees": round(seg["pitch_degrees"], 1),
            "azimuth_degrees": round(azimuth, 1),
            "compass_direction": compass,
            "surface_area_sqft": round(seg_area_sqft, 0),
            "ground_area_sqft": round(seg_ground_sqft, 0),
            "height_ft": round(seg["height_m"] * 3.28084, 1),
        })

    return {
        "metrics": {
            "footprint_area_sqft": round(field_area_sqft, 0),
            "roof_surface_area_sqft": round(whole_roof_area_sqft, 0),
            "perimeter_linear_ft": round(perimeter_lf, 0),
            "est_hvac_units": hvac_count_est,
            "num_roof_segments": len(segment_details),
            "imagery_quality": insights.get("imagery_quality", "UNKNOWN"),
        },
        "costs": {
            "TOTAL_ESTIMATE": round(total_project_cost, 2),
        },
        "roof_segments": segment_details,
    }


# --- CLI entry point ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    import json
    load_dotenv()

    addr = input("Enter Commercial Address: ")
    try:
        insights = get_building_insights(addr)
        est = estimate_flat_roof(insights)
        print(json.dumps(est, indent=2))
    except Exception as e:
        print(f"Error: {e}")
