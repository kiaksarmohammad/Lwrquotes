"""
Roof Estimator - Drawing-based quantity takeoff and cost estimation.

Takes manual measurements from scaled architectural drawings and calculates
material quantities based on specification requirements (Div 07).

Replaces satellite/footprint-based estimation with spec-driven calculations.

Usage:
    python roof_estimator.py
    python roof_estimator.py --json output.json
"""

import math
import json
import sys
from dataclasses import dataclass, field

from backend.database import (
    PRICING,
    EPDM_SPECIFIC_MATERIALS,
    TPO_SPECIFIC_MATERIALS,
    COMMON_ROOF_MATERIALS,
    ROOF_SYSTEM_CONFIGS,
)


# ---------------------------------------------------------------------------
# Coverage rates - how much area/length one purchase unit covers
# Used by AI-driven detail calculations to convert area -> unit count
# ---------------------------------------------------------------------------

COVERAGE_RATES = {
    "Primer":                          {"sqft_per_unit": 250, "unit": "pail"},
    "Base_Membrane":                   {"sqft_per_unit": 100, "unit": "roll"},
    "Cap_Membrane":                    {"sqft_per_unit": 86,  "unit": "roll"},
    "SBS_Membrane":                    {"sqft_per_unit": 100, "unit": "roll"},
    "EPDM_Membrane":                   {"sqft_per_unit": 100, "unit": "roll"},
    "TPO_Membrane":                    {"sqft_per_unit": 100, "unit": "roll"},
    "PVC_Membrane":                    {"sqft_per_unit": 100, "unit": "roll"},
    "Vapour_Barrier_Membrane":         {"sqft_per_unit": 200, "unit": "roll"},
    "EPDM_Accessory":                  {"sqft_per_unit": 50,  "unit": "roll"},
    "TPO_Accessory":                   {"sqft_per_unit": 50,  "unit": "piece"},
    "Polyisocyanurate_ISO_Insulation": {"sqft_per_unit": 16,  "unit": "sheet (4'x4')"},
    "XPS_Insulation":                  {"sqft_per_unit": 16,  "unit": "sheet (2'x8')"},
    "Fiberboard_Insulation":           {"sqft_per_unit": 8,   "unit": "sheet (2'x4')"},
    "Batt_Insulation":                 {"sqft_per_unit": 40,  "unit": "bundle"},
    "DensDeck_Coverboard":             {"sqft_per_unit": 32,  "unit": "sheet (4'x8')"},
    "Gypsum_Fiber_Coverboard":         {"sqft_per_unit": 32,  "unit": "sheet (4'x8')"},
    "Drainage_Board":                  {"sqft_per_unit": 300, "unit": "roll (6'x50')"},
    "Fleece_Reinforcement_Fabric":     {"sqft_per_unit": 300, "unit": "roll"},
    "Flashing_General":                {"lf_per_unit": 10,    "unit": "10ft piece"},
    "Coated_Metal_Sheet":              {"sqft_per_unit": 40,  "unit": "sheet (4'x10')"},
    "Metal_Panel":                     {"lf_per_unit": 1,     "unit": "lin ft"},
    "Standing_Seam_Metal":             {"lf_per_unit": 1,     "unit": "lin ft"},
    "Drip_Edge":                       {"lf_per_unit": 10,    "unit": "10ft piece"},
    "Wood_Blocking_Lumber":            {"lf_per_unit": 8,     "unit": "8ft piece"},
    "Plywood_Sheathing":              {"lf_per_unit": 8,     "unit": "4'x8' sheet"},
    "Mastic":                          {"sqft_per_unit": 500, "unit": "pail"},
    "Adhesive":                        {"sqft_per_unit": 200, "unit": "pail"},
    "Adhesive_Elastocol":              {"sqft_per_unit": 333, "unit": "pail (19L)"},
    "Sealant_General":                 {"lf_per_unit": 20,    "unit": "tube"},
    "Coating_Paint":                   {"sqft_per_unit": 200, "unit": "pail"},
    "Tape":                            {"lf_per_unit": 150,   "unit": "roll"},
    "Walkway_Pads":                    {"sqft_per_unit": 12,  "unit": "pad"},
    "Roof_Drain":                      {"per_each": 1, "unit": "EA"},
    "Scupper":                         {"per_each": 1, "unit": "EA"},
    "Gooseneck_Vent":                  {"per_each": 1, "unit": "EA"},
    "Pipe_Boot_Seal":                  {"per_each": 1, "unit": "EA"},
    "Plumbing_Vent":                   {"per_each": 1, "unit": "EA"},
    "Vent_Cap":                        {"per_each": 1, "unit": "EA"},
    "Roof_Hatch":                      {"per_each": 1, "unit": "EA"},
    "Roof_Anchor":                     {"per_each": 1, "unit": "EA"},
    "Gutter_Downpipe":                 {"per_each": 1, "unit": "EA"},
    "Clips":                           {"per_each": 1, "unit": "piece"},
    "Fasteners":                       {"sqft_per_unit": 100, "unit": "box (1M)"},
    "Insulation_Plates":               {"sqft_per_unit": 100, "unit": "box (1M)"},
    "Nails_Staples":                   {"sqft_per_unit": 200, "unit": "box"},
    "Screws":                          {"sqft_per_unit": 100, "unit": "box"},
    "Equipment_Torch":                 {"sqft_per_unit": 100, "unit": "roll"},
}

# Map AI detail_type -> (measurement_type, RoofMeasurements attribute)
DETAIL_TYPE_MAP = {
    "field_assembly":          ("sqft",      "total_roof_area_sqft"),
    "parapet":                 ("linear_ft", "parapet_length_lf"),
    "curtain_wall":            ("linear_ft", "parapet_length_lf"),
    "drain":                   ("each",      "roof_drain_count"),
    "mechanical_curb":         ("each",      "mechanical_unit_count"),
    "sleeper_curb":            ("each",      "sleeper_curb_count"),
    "penetration_gas":         ("each",      "gas_penetration_count"),
    "penetration_electrical":  ("each",      "electrical_penetration_count"),
    "penetration_plumbing":    ("each",      "plumbing_vent_count"),
    "vent_hood":               ("each",      "vent_hood_count"),
    "scupper":                 ("each",      "scupper_count"),
    "expansion_joint":         ("linear_ft", "perimeter_lf"),
    "pipe_support":            ("each",      "plumbing_vent_count"),
    "opening_cover":           ("each",      "mechanical_unit_count"),
}


# ---------------------------------------------------------------------------
# System-Specific Material Definitions
# Coverage rates sourced from database.py descriptions
# ---------------------------------------------------------------------------

# Aggregated material sources for price lookup
_ALL_MATERIALS = [PRICING, EPDM_SPECIFIC_MATERIALS, TPO_SPECIFIC_MATERIALS, COMMON_ROOF_MATERIALS]

# Price overrides for materials with non-standard pricing models
_PRICE_OVERRIDES = {
    # EPS: $0.31/sqft/inch × 16 sqft (4'×4' sheet) × 2.5" thick = $12.40/sheet
    "EPS_Insulation_EPDM": 12.40,
}

# Area-based material layers per roof system type
# Format: (name, pricing_key, unit, sqft_per_unit, area_source, waste_pct, bid_group)
_SYSTEM_AREA_LAYERS = {
    "SBS": [
        ("Asphaltic Primer",
         "Primer", "pail (5 gal)", 250, "roof_area", 0.05, "roofing"),
        ("SBS Base Sheet (Sopraply Base 520)",
         "Base_Membrane", "roll", 100, "roof_area", 0.15, "roofing"),
        ("SBS Cap Sheet (Sopraply Traffic Cap)",
         "Cap_Membrane", "roll", 86, "roof_area", 0.15, "roofing"),
        ("Tapered ISO Insulation (Soprasmart Board 2:1)",
         "Polyisocyanurate_ISO_Insulation", "sheet (4'x4')", 16, "tapered_area", 0.10, "roofing"),
        ("XPS Insulation (Sopra-XPS 40 Type 4)",
         "XPS_Insulation", "sheet (2'x8')", 16, "roof_area", 0.10, "roofing"),
        ("Drainage Board (Sopradrain EcoVent)",
         "Drainage_Board", "roll (6'x50')", 300, "roof_area", 0.10, "roofing"),
        ("Filter Fabric",
         "Fleece_Reinforcement_Fabric", "roll", 300, "roof_area", 0.10, "roofing"),
    ],
    "EPDM_Fully_Adhered": [
        ("Vapour Barrier (Sopravap'r WG 45\")",
         "Vapour_Barrier_Sopravapor", "roll (45\" x 5Sq)", 500, "roof_area", 0.10, "roofing"),
        ("ISO Insulation 2.5\" (Sopra-ISO)",
         "ISO_2_5_inch", "sheet (4'x4')", 16, "roof_area", 0.10, "roofing"),
        ("Tapered ISO Insulation (drainage slope)",
         "Tapered_ISO", "sqft", 1, "tapered_area", 0.10, "roofing"),
        ("Densdeck Coverboard 1/2\"",
         "Densdeck_Half_Inch", "sheet (4'x8')", 32, "roof_area", 0.10, "roofing"),
        ("EPDM Membrane 60 mil (Carlisle Sure-Seal)",
         "EPDM_Membrane_60mil", "roll (10'x100')", 1000, "roof_area", 0.10, "roofing"),
        ("EPDM Bonding Adhesive 90-8-30A",
         "EPDM_Bonding_Adhesive", "pail (5 gal)", 300, "roof_area", 0.05, "roofing"),
        ("EPDM Primer HP-250",
         "EPDM_Primer_HP250", "gallon", 50, "roof_area", 0.05, "roofing"),
        ("EPDM Seam Tape 3\"x100'",
         "EPDM_Seam_Tape", "roll (100 lf)", 1000, "roof_area", 0.10, "roofing"),
    ],
    "EPDM_Ballasted": [
        ("Vapour Barrier (Sopravap'r WG 45\")",
         "Vapour_Barrier_Sopravapor", "roll (45\" x 5Sq)", 500, "roof_area", 0.10, "roofing"),
        ("EPDM Membrane 60 mil (Carlisle Sure-Seal, loose laid)",
         "EPDM_Membrane_60mil", "roll (10'x100')", 1000, "roof_area", 0.10, "roofing"),
        ("EPS Insulation Type II (2 layers x 2.5\")",
         "EPS_Insulation_EPDM", "sheet (4'x4')", 8, "roof_area", 0.10, "roofing"),
        ("Filter Fabric (Soprafilter)",
         "EPDM_Filter_Fabric", "roll", 300, "roof_area", 0.10, "roofing"),
        ("Drainage Mat (Sopradrain 15G 6'x50')",
         "EPDM_Drainage_Mat", "roll (6'x50')", 300, "roof_area", 0.10, "roofing"),
        ("EPDM Seam Tape 3\"x100'",
         "EPDM_Seam_Tape", "roll (100 lf)", 1000, "roof_area", 0.10, "roofing"),
    ],
    "TPO_Mechanically_Attached": [
        ("Vapour Barrier (Sopravap'r WG 45\")",
         "Vapour_Barrier_Sopravapor", "roll (45\" x 5Sq)", 500, "roof_area", 0.10, "roofing"),
        ("ISO Insulation 2.5\" (Sopra-ISO)",
         "ISO_2_5_inch", "sheet (4'x4')", 16, "roof_area", 0.10, "roofing"),
        ("Tapered ISO Insulation (drainage slope)",
         "Tapered_ISO", "sqft", 1, "tapered_area", 0.10, "roofing"),
        ("Densdeck Coverboard 1/2\"",
         "Densdeck_Half_Inch", "sheet (4'x8')", 32, "roof_area", 0.10, "roofing"),
        ("TPO Membrane 60 mil (Sure-Weld)",
         "TPO_Membrane", "roll (10'x100')", 1000, "roof_area", 0.10, "roofing"),
        ("Rhinobond Induction Weld Plates",
         "TPO_Rhinobond_Plate", "pallet", 4000, "roof_area", 0.05, "roofing"),
        ("TPO Fastening Screws",
         "TPO_Screws", "box", 4000, "roof_area", 0.05, "roofing"),
    ],
    "TPO_Fully_Adhered": [
        ("Vapour Barrier (Sopravap'r WG 45\")",
         "Vapour_Barrier_Sopravapor", "roll (45\" x 5Sq)", 500, "roof_area", 0.10, "roofing"),
        ("ISO Insulation 2.5\" (Sopra-ISO)",
         "ISO_2_5_inch", "sheet (4'x4')", 16, "roof_area", 0.10, "roofing"),
        ("Tapered ISO Insulation (drainage slope)",
         "Tapered_ISO", "sqft", 1, "tapered_area", 0.10, "roofing"),
        ("Soprasmart ISO HD 1/2\" (factory laminated coverboard)",
         "Soprasmart_ISO_HD", "sheet (4'x8')", 32, "roof_area", 0.10, "roofing"),
        ("TPO Membrane 60 mil (Sure-Weld)",
         "TPO_Membrane", "roll (10'x100')", 1000, "roof_area", 0.10, "roofing"),
        ("TPO Bonding Adhesive (SureWeld)",
         "TPO_Bonding_Adhesive_SureWeld", "pail (5 gal)", 300, "roof_area", 0.05, "roofing"),
        ("TPO Primer",
         "TPO_Primer", "gallon", 100, "roof_area", 0.05, "roofing"),
    ],
}

# Consumables per system type
# Format: (name, pricing_key, unit, rate_per_1000sqft, bid_group)
_SYSTEM_CONSUMABLES = {
    "SBS": [
        ("Mastic (Sopramastic)", "Mastic", "pail", 2, "roofing"),
        ("Elastocol Adhesive", "Adhesive_Elastocol", "pail (19L)", 3, "roofing"),
        ("Polyurethane Sealant (Dymonic 100 / NP1)", "Sealant_General", "tube", 6, "flashing"),
    ],
    "EPDM_Fully_Adhered": [
        ("EPDM Lap Sealant", "EPDM_Lap_Sealant", "tube", 4, "roofing"),
        ("Duotack Foamable Adhesive (insulation bonding)", "Duotack_Adhesive", "case", 2, "roofing"),
        ("Polyurethane Sealant (Dymonic 100 / NP1)", "Sealant_General", "tube", 4, "flashing"),
    ],
    "EPDM_Ballasted": [
        ("EPDM Lap Sealant", "EPDM_Lap_Sealant", "tube", 4, "roofing"),
        ("Polyurethane Sealant (Dymonic 100 / NP1)", "Sealant_General", "tube", 4, "flashing"),
    ],
    "TPO_Mechanically_Attached": [
        ("TPO Lap Sealant", "TPO_Lap_Sealant", "tube", 3, "roofing"),
        ("Polyurethane Sealant (Dymonic 100 / NP1)", "Sealant_General", "tube", 4, "flashing"),
    ],
    "TPO_Fully_Adhered": [
        ("TPO Lap Sealant", "TPO_Lap_Sealant", "tube", 3, "roofing"),
        ("Polyurethane Sealant (Dymonic 100 / NP1)", "Sealant_General", "tube", 4, "flashing"),
    ],
}

# System metadata for display and bid multipliers
_SYSTEM_META = {
    "SBS": {
        "display_name": "Inverted Modified Bitumen (2-Ply SBS) - Soprema System",
        "spec": "Div 07 52 01 / 07 62 00 / 07 92 00",
        "labour_multiplier": 1.65,
        "labour_note": "Labour typically 1.5-1.8x material for SBS torch-applied",
        "mechanical_multiplier": 1.80,
        "include_ballast_note": True,
    },
    "EPDM_Fully_Adhered": {
        "display_name": "EPDM 60 mil Fully Adhered System",
        "spec": "Div 07 53 23",
        "labour_multiplier": 1.55,
        "labour_note": "Labour typically 1.4-1.6x material for EPDM fully adhered",
        "mechanical_multiplier": 1.80,
        "include_ballast_note": False,
    },
    "EPDM_Ballasted": {
        "display_name": "EPDM 60 mil Ballasted / Inverted System",
        "spec": "Div 07 53 23",
        "labour_multiplier": 1.40,
        "labour_note": "Labour typically 1.3-1.5x material for EPDM ballasted",
        "mechanical_multiplier": 1.70,
        "include_ballast_note": True,
    },
    "TPO_Mechanically_Attached": {
        "display_name": "TPO 60 mil Mechanically Attached System",
        "spec": "Div 07 54 23",
        "labour_multiplier": 1.50,
        "labour_note": "Labour typically 1.4-1.6x material for TPO mechanically attached",
        "mechanical_multiplier": 1.80,
        "include_ballast_note": False,
    },
    "TPO_Fully_Adhered": {
        "display_name": "TPO 60 mil Fully Adhered System",
        "spec": "Div 07 54 23",
        "labour_multiplier": 1.65,
        "labour_note": "Labour typically 1.5-1.8x material for TPO fully adhered",
        "mechanical_multiplier": 1.80,
        "include_ballast_note": False,
    },
}

# System-specific pipe seal product keys
_PIPE_SEAL_KEY = {
    "SBS": ("Pipe_Boot_Seal", "Penetration Seal"),
    "EPDM_Fully_Adhered": ("EPDM_Pipe_Flashing", "EPDM Pipe Flashing (1\"-6\")"),
    "EPDM_Ballasted": ("EPDM_Pipe_Flashing", "EPDM Pipe Flashing (1\"-6\")"),
    "TPO_Mechanically_Attached": ("TPO_Pipe_Boot", "TPO Universal Pipe Boot"),
    "TPO_Fully_Adhered": ("TPO_Pipe_Boot", "TPO Universal Pipe Boot"),
}


# ---------------------------------------------------------------------------
# Project Measurements (input from scaled drawings)
# ---------------------------------------------------------------------------

@dataclass
class RoofMeasurements:
    """Measurements taken from architectural drawings (plan + section views)."""

    # --- Field area (from plan view, e.g. R2.0 at given scale) ---
    total_roof_area_sqft: float
    perimeter_lf: float  # total roof edge perimeter

    # --- Parapet ---
    parapet_length_lf: float  # may differ from perimeter if partial parapet
    parapet_height_ft: float = 2.0

    # --- Drains & Drainage ---
    roof_drain_count: int = 0
    scupper_count: int = 0

    # --- Penetrations & Equipment ---
    mechanical_unit_count: int = 0  # RTUs / rooftop units
    sleeper_curb_count: int = 0
    vent_hood_count: int = 0
    gas_penetration_count: int = 0
    electrical_penetration_count: int = 0
    plumbing_vent_count: int = 0

    # --- Optional area overrides ---
    tapered_area_sqft: float | None = None   # area needing tapered ISO (default: full roof)
    ballast_area_sqft: float | None = None   # area getting gravel ballast (default: full roof)

    # --- System type ---
    roof_system_type: str = "SBS"

    @property
    def effective_tapered_area(self) -> float:
        return self.tapered_area_sqft if self.tapered_area_sqft is not None else self.total_roof_area_sqft

    @property
    def effective_ballast_area(self) -> float:
        return self.ballast_area_sqft if self.ballast_area_sqft is not None else self.total_roof_area_sqft

    @property
    def total_penetrations(self) -> int:
        return (self.mechanical_unit_count + self.sleeper_curb_count +
                self.vent_hood_count + self.gas_penetration_count +
                self.electrical_penetration_count + self.plumbing_vent_count)


def validate_measurements(m: RoofMeasurements) -> list[str]:
    """
    Validate measurements and return a list of warning messages.
    Does not block execution, just flags suspicious values.
    """
    warnings = []
    
    if m.total_roof_area_sqft <= 0:
        warnings.append("Total roof area is zero or negative.")
    
    if m.perimeter_lf <= 0:
        warnings.append("Roof perimeter is zero or negative.")
        
    if m.total_roof_area_sqft > 0 and m.perimeter_lf > 0:
        # Check for unreasonable area/perimeter ratio (e.g. extremely long/thin or error)
        # A square has P = 4 * sqrt(A). If P is vastly smaller, it's physically impossible.
        min_perimeter = 4 * math.sqrt(m.total_roof_area_sqft)
        if m.perimeter_lf < min_perimeter * 0.5: # Allow some margin for error/shape
            warnings.append(f"Perimeter ({m.perimeter_lf:.0f}') seems too small for the area ({m.total_roof_area_sqft:.0f} sqft).")

    if m.parapet_length_lf > m.perimeter_lf * 1.5:
        warnings.append("Parapet length is significantly longer than roof perimeter.")
        
    if m.parapet_height_ft > 6.0:
        warnings.append(f"Parapet height ({m.parapet_height_ft} ft) is unusually high.")
        
    return warnings


# ---------------------------------------------------------------------------
# Assembly Definition - Inverted Modified Bitumen (2-Ply SBS, Soprema)
# Spec: Div 07 52 01 / 07 62 00 / 07 92 00
# ---------------------------------------------------------------------------

def _get_price(pricing_key: str) -> float:
    """Look up avg_price from any material dictionary. Returns 0 if key missing."""
    if pricing_key in _PRICE_OVERRIDES:
        return _PRICE_OVERRIDES[pricing_key]
    for source in _ALL_MATERIALS:
        entry = source.get(pricing_key)
        if entry is not None:
            if isinstance(entry, dict):
                return entry.get("avg_price", 0.0)
            return float(entry)
    return 0.0


def calculate_takeoff(m: RoofMeasurements) -> dict:
    """
    Calculate full material quantity takeoff and cost estimate.

    Returns a structured dict with:
      - project_measurements: echo of input measurements
      - area_materials: membrane, insulation, drainage, ballast (sqft-driven)
      - linear_materials: flashings, blocking, sheathing (lf-driven)
      - unit_items: drains, penetration flashings (count-driven)
      - consumables: primer, mastic, sealant, adhesive
      - bid_summary: costs grouped by bid form line items
    """

    system = m.roof_system_type
    meta = _SYSTEM_META.get(system, _SYSTEM_META["SBS"])

    results = {
        "project_measurements": {
            "total_roof_area_sqft": m.total_roof_area_sqft,
            "perimeter_lf": m.perimeter_lf,
            "parapet_length_lf": m.parapet_length_lf,
            "parapet_height_ft": m.parapet_height_ft,
            "tapered_area_sqft": m.effective_tapered_area,
            "ballast_area_sqft": m.effective_ballast_area,
            "total_penetrations": m.total_penetrations,
            "roof_system_type": system,
            "roof_system_name": meta["display_name"],
            "spec": meta["spec"],
        },
        "area_materials": [],
        "linear_materials": [],
        "unit_items": [],
        "consumables": [],
    }

    total_roofing_cost = 0.0
    total_flashing_cost = 0.0
    total_mechanical_cost = 0.0

    # ===================================================================
    # AREA-BASED MATERIALS (membrane, insulation, drainage)
    # ===================================================================
    area_layers = _SYSTEM_AREA_LAYERS.get(system, _SYSTEM_AREA_LAYERS["SBS"])

    for name, pkey, unit, sqft_per_unit, area_src, waste_pct, bid_grp in area_layers:
        if area_src == "roof_area":
            base_area = m.total_roof_area_sqft
        elif area_src == "tapered_area":
            base_area = m.effective_tapered_area
        elif area_src == "ballast_area":
            base_area = m.effective_ballast_area
        else:
            base_area = m.total_roof_area_sqft

        area_with_waste = base_area * (1 + waste_pct)
        qty = math.ceil(area_with_waste / sqft_per_unit)
        unit_price = _get_price(pkey)
        line_cost = qty * unit_price

        results["area_materials"].append({
            "name": name,
            "base_area_sqft": round(base_area, 0),
            "waste_pct": f"{waste_pct:.0%}",
            "quantity": qty,
            "unit": unit,
            "unit_price": round(unit_price, 2),
            "line_cost": round(line_cost, 2),
            "bid_group": bid_grp,
        })

        if bid_grp == "roofing":
            total_roofing_cost += line_cost

    # Gravel ballast note (only for systems that use ballast)
    if meta["include_ballast_note"]:
        results["area_materials"].append({
            "name": "Gravel Ballast (100mm max / 15 lb/sqft) - existing, redistribute",
            "base_area_sqft": round(m.effective_ballast_area, 0),
            "waste_pct": "0%",
            "quantity": round(m.effective_ballast_area, 0),
            "unit": "sqft",
            "unit_price": 0.0,
            "line_cost": 0.0,
            "bid_group": "roofing",
            "note": "Existing ballast. Reduce depth to 100mm max. Disposal/redistribution cost by contractor.",
        })

    # ===================================================================
    # LINEAR-FOOT MATERIALS (flashings, blocking, sheathing)
    # ===================================================================
    linear_items = [
        # (name, pricing_key, unit, lf_per_unit, length_source, waste%, bid_group)
        ("Metal Cap Flashing (24ga prefinished galv.)",
         "Flashing_General", "10ft piece", 10, "parapet", 0.10, "flashing"),
        ("Metal Counter Flashing (24ga prefinished galv.)",
         "Flashing_General", "10ft piece", 10, "parapet", 0.10, "flashing"),
        ("Wood Blocking (SPF 2x)",
         "Wood_Blocking_Lumber", "8ft piece", 8, "parapet", 0.15, "flashing"),
        ("Plywood Sheathing (12.5mm Douglas Fir)",
         "Plywood_Sheathing", "4'x8' sheet", 8, "parapet", 0.15, "flashing"),
    ]

    for name, pkey, unit, lf_per_unit, src, waste_pct, bid_grp in linear_items:
        if src == "parapet":
            base_lf = m.parapet_length_lf
        else:
            base_lf = m.perimeter_lf

        lf_with_waste = base_lf * (1 + waste_pct)
        qty = math.ceil(lf_with_waste / lf_per_unit)
        unit_price = _get_price(pkey)
        line_cost = qty * unit_price

        results["linear_materials"].append({
            "name": name,
            "base_lf": round(base_lf, 0),
            "waste_pct": f"{waste_pct:.0%}",
            "quantity": qty,
            "unit": unit,
            "unit_price": round(unit_price, 2),
            "line_cost": round(line_cost, 2),
            "bid_group": bid_grp,
        })

        if bid_grp == "flashing":
            total_flashing_cost += line_cost

    # ===================================================================
    # UNIT ITEMS (drains, penetration flashings, equipment)
    # ===================================================================
    pipe_key, pipe_name = _PIPE_SEAL_KEY.get(system, ("Pipe_Boot_Seal", "Penetration Seal"))
    unit_defs = [
        # (name, pricing_key, unit, count_attr, multiplier, bid_group)
        ("Roof Drain Insert (spun aluminum, OMG/Thaler)",
         "Roof_Drain", "EA", "roof_drain_count", 1, "roofing"),
        ("Overflow Scupper",
         "Scupper", "EA", "scupper_count", 1, "roofing"),
        ("Mechanical Unit Curb Flashing",
         "Flashing_General", "EA", "mechanical_unit_count", 4, "mechanical"),
        ("Sleeper Curb Flashing",
         "Flashing_General", "EA", "sleeper_curb_count", 2, "mechanical"),
        ("Vent Hood Flashing",
         "Gooseneck_Vent", "EA", "vent_hood_count", 1, "roofing"),
        (f"Gas {pipe_name}",
         pipe_key, "EA", "gas_penetration_count", 1, "roofing"),
        (f"Electrical {pipe_name}",
         pipe_key, "EA", "electrical_penetration_count", 1, "roofing"),
        ("Plumbing Vent Flashing",
         "Plumbing_Vent", "EA", "plumbing_vent_count", 1, "roofing"),
    ]

    for name, pkey, unit, count_attr, multiplier, bid_grp in unit_defs:
        base_count = getattr(m, count_attr, 0)
        qty = base_count * multiplier
        if qty == 0:
            continue
        unit_price = _get_price(pkey)
        line_cost = qty * unit_price

        results["unit_items"].append({
            "name": name,
            "base_count": base_count,
            "multiplier": multiplier,
            "quantity": qty,
            "unit": unit,
            "unit_price": round(unit_price, 2),
            "line_cost": round(line_cost, 2),
            "bid_group": bid_grp,
        })

        if bid_grp == "roofing":
            total_roofing_cost += line_cost
        elif bid_grp == "mechanical":
            total_mechanical_cost += line_cost

    # ===================================================================
    # CONSUMABLES (primer already above, mastic, sealant, adhesive)
    # ===================================================================
    consumable_defs = _SYSTEM_CONSUMABLES.get(system, _SYSTEM_CONSUMABLES["SBS"])

    for name, pkey, unit, rate_per_1000, bid_grp in consumable_defs:
        qty = math.ceil(m.total_roof_area_sqft / 1000 * rate_per_1000)
        unit_price = _get_price(pkey)
        line_cost = qty * unit_price

        results["consumables"].append({
            "name": name,
            "quantity": qty,
            "unit": unit,
            "unit_price": round(unit_price, 2),
            "line_cost": round(line_cost, 2),
            "bid_group": bid_grp,
        })

        if bid_grp == "roofing":
            total_roofing_cost += line_cost
        elif bid_grp == "flashing":
            total_flashing_cost += line_cost

    # ===================================================================
    # BID SUMMARY (matches Div 00 41 00 bid form structure)
    # ===================================================================
    total_roofing_plus_flashing = total_roofing_cost + total_flashing_cost
    labour_mult = meta["labour_multiplier"]
    mech_mult = meta["mechanical_multiplier"]

    results["bid_summary"] = {
        "item_1_general_requirements": {
            "description": "General Requirements (Div 01)",
            "note": "Mobilization, site protection, cleanup - typically 8-12% of roofing",
            "estimated_pct": 0.10,
            "estimated_cost": round(total_roofing_plus_flashing * 0.10, 2),
        },
        "item_2_roofing_assembly_and_flashing": {
            "description": f"Roofing Assembly + Metal Flashing ({meta['spec']})",
            "material_cost": round(total_roofing_plus_flashing, 2),
            "labour_multiplier": labour_mult,
            "note": meta["labour_note"],
            "estimated_cost": round(total_roofing_plus_flashing * labour_mult, 2),
        },
        "item_3_mechanical_support": {
            "description": "Mechanical Support (sleeper curbs, RTU flashings)",
            "material_cost": round(total_mechanical_cost, 2),
            "labour_multiplier": mech_mult,
            "note": "Higher labour ratio for detail work",
            "estimated_cost": round(total_mechanical_cost * mech_mult, 2),
        },
        "total_estimate": round(
            total_roofing_plus_flashing * 0.10 +      # general req
            total_roofing_plus_flashing * labour_mult + # roofing + flashing
            total_mechanical_cost * mech_mult,          # mechanical
            2
        ),
    }

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_estimate(est: dict) -> None:
    """Pretty-print the quantity takeoff and cost estimate."""
    meas = est["project_measurements"]

    system_name = meas.get("roof_system_name", "Inverted Modified Bitumen (2-Ply SBS) - Soprema System")
    spec = meas.get("spec", "Div 07 52 01 / 07 62 00 / 07 92 00")
    print("=" * 72)
    print("  ROOFING QUANTITY TAKEOFF & COST ESTIMATE")
    print(f"  {system_name}")
    print(f"  Spec: {spec}")
    print("=" * 72)

    print(f"\n  Roof Area     : {meas['total_roof_area_sqft']:,.0f} sqft")
    print(f"  Perimeter     : {meas['perimeter_lf']:,.0f} LF")
    print(f"  Parapet       : {meas['parapet_length_lf']:,.0f} LF x {meas['parapet_height_ft']:.1f} ft")
    print(f"  Tapered Area  : {meas['tapered_area_sqft']:,.0f} sqft")
    print(f"  Ballast Area  : {meas['ballast_area_sqft']:,.0f} sqft")
    print(f"  Penetrations  : {meas['total_penetrations']} total")

    # Area materials
    print(f"\n  {'-' * 68}")
    print("  AREA-BASED MATERIALS (membrane, insulation, drainage)")
    print(f"  {'-' * 68}")
    for item in est["area_materials"]:
        cost_str = f"${item['line_cost']:,.2f}" if item["line_cost"] > 0 else "TBD"
        print(f"    {item['name']}")
        print(f"      {item['quantity']:,} {item['unit']}  @  ${item['unit_price']:,.2f}  =  {cost_str}")
        if item.get("note"):
            print(f"      ** {item['note']}")

    # Linear materials
    print(f"\n  {'-' * 68}")
    print("  LINEAR-FOOT MATERIALS (flashings, blocking, sheathing)")
    print(f"  {'-' * 68}")
    for item in est["linear_materials"]:
        print(f"    {item['name']}")
        print(f"      {item['quantity']:,} {item['unit']}  ({item['base_lf']:,.0f} LF + {item['waste_pct']} waste)")
        print(f"      @  ${item['unit_price']:,.2f}  =  ${item['line_cost']:,.2f}")

    # Unit items
    if est["unit_items"]:
        print(f"\n  {'-' * 68}")
        print("  UNIT ITEMS (drains, penetrations, equipment)")
        print(f"  {'-' * 68}")
        for item in est["unit_items"]:
            mult_str = f" x{item['multiplier']}" if item["multiplier"] > 1 else ""
            print(f"    {item['name']}")
            print(f"      {item['base_count']}{mult_str}  =  {item['quantity']} {item['unit']}")
            print(f"      @  ${item['unit_price']:,.2f}  =  ${item['line_cost']:,.2f}")

    # Consumables
    print(f"\n  {'-' * 68}")
    print("  CONSUMABLES (mastic, adhesive, sealant)")
    print(f"  {'-' * 68}")
    for item in est["consumables"]:
        print(f"    {item['name']}")
        print(f"      {item['quantity']} {item['unit']}  @  ${item['unit_price']:,.2f}  =  ${item['line_cost']:,.2f}")

    # Bid summary
    bid = est["bid_summary"]
    print(f"\n{'=' * 72}")
    print("  BID FORM SUMMARY (Div 00 41 00)")
    print(f"{'=' * 72}")

    item1 = bid["item_1_general_requirements"]
    print(f"\n  1. {item1['description']}")
    print(f"     ({item1['note']})")
    print(f"     Estimated: ${item1['estimated_cost']:>12,.2f}")

    item2 = bid["item_2_roofing_assembly_and_flashing"]
    print(f"\n  2. {item2['description']}")
    print(f"     Material: ${item2['material_cost']:>12,.2f}")
    print(f"     x {item2['labour_multiplier']}  ({item2['note']})")
    print(f"     Estimated: ${item2['estimated_cost']:>12,.2f}")

    item3 = bid["item_3_mechanical_support"]
    print(f"\n  3. {item3['description']}")
    print(f"     Material: ${item3['material_cost']:>12,.2f}")
    print(f"     x {item3['labour_multiplier']}  ({item3['note']})")
    print(f"     Estimated: ${item3['estimated_cost']:>12,.2f}")

    print(f"\n  {'-' * 50}")
    print(f"  TOTAL PROJECT ESTIMATE:  ${bid['total_estimate']:>12,.2f}")
    print(f"  {'-' * 50}")
    print(f"  Per sqft:  ${bid['total_estimate'] / est['project_measurements']['total_roof_area_sqft']:>8,.2f} / sqft")
    print("=" * 72)


def export_json(est: dict, output_path: str) -> None:
    """Write the estimate to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(est, f, indent=2, ensure_ascii=False)
    print(f"\nJSON estimate saved to: {output_path}")


# ---------------------------------------------------------------------------
# AI Analysis Integration (drawing_analyzer.py output)
# ---------------------------------------------------------------------------

def load_analysis(json_path: str) -> dict:
    """Load AI analysis JSON produced by drawing_analyzer.py."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def measurements_from_analysis(analysis: dict,
                                total_roof_area_sqft: float,
                                perimeter_lf: float,
                                parapet_length_lf: float | None = None,
                                parapet_height_ft: float = 2.0) -> RoofMeasurements:
    """
    Build RoofMeasurements using AI-detected item counts + user-provided areas.

    The AI provides item counts from plan views; the user still provides
    area and perimeter (these must be measured from the scaled drawings).
    """
    counts: dict[str, int] = {}
    for plan in analysis.get("plan_analysis", []):
        if plan.get("parse_error"):
            continue
        for key, val in plan.get("counts", {}).items():
            counts[key] = counts.get(key, 0) + val

    return RoofMeasurements(
        total_roof_area_sqft=total_roof_area_sqft,
        perimeter_lf=perimeter_lf,
        parapet_length_lf=parapet_length_lf or perimeter_lf,
        parapet_height_ft=parapet_height_ft,
        roof_drain_count=counts.get("roof_drains", 0),
        scupper_count=counts.get("scuppers", 0),
        mechanical_unit_count=counts.get("mechanical_units", 0),
        sleeper_curb_count=counts.get("sleeper_curbs", 0),
        vent_hood_count=counts.get("vent_hoods", 0),
        gas_penetration_count=counts.get("gas_penetrations", 0),
        electrical_penetration_count=counts.get("electrical_penetrations", 0),
        plumbing_vent_count=counts.get("plumbing_vents", 0),
    )


def calculate_detail_takeoff(m: RoofMeasurements, analysis: dict) -> dict:
    """
    Calculate takeoff using AI-identified detail assemblies.

    Instead of hardcoded material lists, uses the detail_analysis from
    drawing_analyzer.py to determine which materials go in each detail,
    then applies measurements to calculate quantities and costs.
    """
    results = {
        "project_measurements": {
            "total_roof_area_sqft": m.total_roof_area_sqft,
            "perimeter_lf": m.perimeter_lf,
            "parapet_length_lf": m.parapet_length_lf,
            "parapet_height_ft": m.parapet_height_ft,
            "total_penetrations": m.total_penetrations,
        },
        "details": [],
    }

    grand_total = 0.0

    # Collect all details from AI analysis
    all_details = []
    for page_data in analysis.get("detail_analysis", []):
        if page_data.get("parse_error"):
            continue
        drawing_ref = page_data.get("drawing_ref", "?")
        for detail in page_data.get("details", []):
            detail["_drawing_ref"] = drawing_ref
            all_details.append(detail)

    if not all_details:
        print("  WARNING: No AI detail analysis found. Use calculate_takeoff() instead.")
        return results

    for detail in all_details:
        dtype = detail.get("detail_type", "unknown")
        dname = detail.get("detail_name", "Unknown Detail")
        mtype = detail.get("measurement_type", "each")
        dref = detail.get("_drawing_ref", "?")

        # Look up the base measurement for this detail type
        type_info = DETAIL_TYPE_MAP.get(dtype)
        if type_info:
            _, attr = type_info
            base_value = getattr(m, attr, 0)
        else:
            base_value = 1

        detail_result = {
            "detail_name": dname,
            "detail_type": dtype,
            "drawing_ref": dref,
            "measurement_type": mtype,
            "base_measurement": base_value,
            "layers": [],
            "detail_cost": 0.0,
        }

        for layer in detail.get("layers", []):
            pkey = layer.get("pricing_key", "CUSTOM")
            material_name = layer.get("material", "?")
            notes = layer.get("notes", "")

            if pkey == "CUSTOM" or pkey not in PRICING:
                detail_result["layers"].append({
                    "material": material_name,
                    "pricing_key": pkey,
                    "quantity": "?",
                    "unit": "?",
                    "unit_price": 0.0,
                    "line_cost": 0.0,
                    "notes": notes,
                    "warning": f"No pricing for '{pkey}' - needs manual entry",
                })
                continue

            unit_price = _get_price(pkey)
            coverage = COVERAGE_RATES.get(pkey, {})
            waste = 1.10  # default 10% waste

            if mtype == "sqft" or mtype == "linear_ft" and "sqft_per_unit" in coverage and "lf_per_unit" not in coverage:
                sqft_per = coverage.get("sqft_per_unit", 1)
                qty = math.ceil(base_value * waste / sqft_per)
                unit = coverage.get("unit", "unit")
            elif mtype == "linear_ft" and "lf_per_unit" in coverage:
                lf_per = coverage.get("lf_per_unit", 1)
                qty = math.ceil(base_value * waste / lf_per)
                unit = coverage.get("unit", "unit")
            else:  # each
                per_each = coverage.get("per_each", 1)
                qty = base_value * per_each
                unit = coverage.get("unit", "EA")

            line_cost = qty * unit_price

            detail_result["layers"].append({
                "material": material_name,
                "pricing_key": pkey,
                "quantity": qty,
                "unit": unit,
                "unit_price": round(unit_price, 2),
                "line_cost": round(line_cost, 2),
                "notes": notes,
            })
            detail_result["detail_cost"] += line_cost

        detail_result["detail_cost"] = round(detail_result["detail_cost"], 2)
        grand_total += detail_result["detail_cost"]
        results["details"].append(detail_result)

    results["total_material_cost"] = round(grand_total, 2)
    results["bid_summary"] = {
        "material_cost": round(grand_total, 2),
        "general_requirements_10pct": round(grand_total * 0.10, 2),
        "labour_and_material_1_65x": round(grand_total * 1.65, 2),
        "total_estimate": round(grand_total * 0.10 + grand_total * 1.65, 2),
        "per_sqft": round(
            (grand_total * 0.10 + grand_total * 1.65) / m.total_roof_area_sqft, 2
        ) if m.total_roof_area_sqft > 0 else 0,
    }

    return results


def print_detail_estimate(est: dict) -> None:
    """Pretty-print a detail-based estimate (from AI analysis)."""
    meas = est["project_measurements"]

    print("=" * 72)
    print("  DETAIL-BASED QUANTITY TAKEOFF (AI-Analyzed)")
    print("=" * 72)

    print(f"\n  Roof Area     : {meas['total_roof_area_sqft']:,.0f} sqft")
    print(f"  Perimeter     : {meas['perimeter_lf']:,.0f} LF")
    print(f"  Parapet       : {meas['parapet_length_lf']:,.0f} LF x {meas['parapet_height_ft']:.1f} ft")
    print(f"  Penetrations  : {meas['total_penetrations']} total")

    for detail in est.get("details", []):
        dtype = detail["detail_type"]
        mtype = detail["measurement_type"]
        base = detail["base_measurement"]
        cost = detail["detail_cost"]

        print(f"\n  {'-' * 68}")
        print(f"  {detail['detail_name']}  [{dtype}]  (ref: {detail.get('drawing_ref', '?')})")
        print(f"  Measured in: {mtype}  |  Base value: {base:,}  |  Detail cost: ${cost:,.2f}")
        print(f"  {'-' * 68}")

        for layer in detail.get("layers", []):
            warning = f"  !! {layer['warning']}" if layer.get("warning") else ""
            if layer.get("line_cost", 0) > 0:
                print(f"    {layer['material']}")
                print(f"      {layer['quantity']:,} {layer['unit']}  @  ${layer['unit_price']:,.2f}  =  ${layer['line_cost']:,.2f}")
                if layer.get("notes"):
                    print(f"      ({layer['notes']})")
            else:
                print(f"    {layer['material']}  ->  {layer['pricing_key']}{warning}")
                if layer.get("notes"):
                    print(f"      ({layer['notes']})")

    bid = est.get("bid_summary", {})
    if bid:
        print(f"\n{'=' * 72}")
        print("  ESTIMATE SUMMARY")
        print(f"{'=' * 72}")
        print(f"  Total Material Cost:     ${bid.get('material_cost', 0):>12,.2f}")
        print(f"  General Req (10%):       ${bid.get('general_requirements_10pct', 0):>12,.2f}")
        print(f"  Labour + Material (1.65x): ${bid.get('labour_and_material_1_65x', 0):>12,.2f}")
        print(f"  {'-' * 50}")
        print(f"  TOTAL PROJECT ESTIMATE:  ${bid.get('total_estimate', 0):>12,.2f}")
        print(f"  Per sqft:                ${bid.get('per_sqft', 0):>12,.2f}")
    print("=" * 72)


# ---------------------------------------------------------------------------
# CLI - interactive measurement input
# ---------------------------------------------------------------------------

def _input_float(prompt: str, default: float | None = None) -> float:
    """Prompt for a float with optional default."""
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"  {prompt}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        try:
            return float(raw)
        except ValueError:
            print("    Please enter a number.")


def _input_int(prompt: str, default: int = 0) -> int:
    """Prompt for an integer with default."""
    while True:
        raw = input(f"  {prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            print("    Please enter a whole number.")


def main():
    json_output = None
    analysis_path = None

    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        if idx + 1 < len(sys.argv):
            json_output = sys.argv[idx + 1]

    if "--analysis" in sys.argv:
        idx = sys.argv.index("--analysis")
        if idx + 1 < len(sys.argv):
            analysis_path = sys.argv[idx + 1]

    print("=" * 60)
    print("  ROOF ESTIMATOR - Drawing-Based Quantity Takeoff")
    print("=" * 60)

    # Always need area + perimeter from the user (scaled drawings)
    print("\nEnter measurements from scaled architectural drawings.\n")

    print("[AREAS]")
    area = _input_float("Total roof area (sqft)")
    perim = _input_float("Roof perimeter (LF)")

    print("\n[PARAPET]")
    par_len = _input_float("Parapet length (LF)", default=perim)
    par_ht = _input_float("Parapet height (ft)", default=2.0)

    if analysis_path:
        # --- AI-DRIVEN MODE: use Gemini analysis for details + counts ---
        print(f"\nLoading AI analysis from: {analysis_path}")
        analysis = load_analysis(analysis_path)

        # Get counts from AI, but still ask for area/perimeter
        measurements = measurements_from_analysis(
            analysis, area, perim, par_len, par_ht
        )

        print(f"\nAI-detected counts:")
        print(f"  Drains: {measurements.roof_drain_count}  |  Scuppers: {measurements.scupper_count}")
        print(f"  Mechanical: {measurements.mechanical_unit_count}  |  Sleepers: {measurements.sleeper_curb_count}")
        print(f"  Vents: {measurements.vent_hood_count}  |  Gas: {measurements.gas_penetration_count}")
        print(f"  Electrical: {measurements.electrical_penetration_count}  |  Plumbing: {measurements.plumbing_vent_count}")

        override = input("\n  Override any counts? (y/N): ").strip().lower()
        if override == "y":
            measurements.roof_drain_count = _input_int("Roof drains", measurements.roof_drain_count)
            measurements.scupper_count = _input_int("Scuppers", measurements.scupper_count)
            measurements.mechanical_unit_count = _input_int("Mechanical units", measurements.mechanical_unit_count)
            measurements.sleeper_curb_count = _input_int("Sleeper curbs", measurements.sleeper_curb_count)
            measurements.vent_hood_count = _input_int("Vent hoods", measurements.vent_hood_count)
            measurements.gas_penetration_count = _input_int("Gas penetrations", measurements.gas_penetration_count)
            measurements.electrical_penetration_count = _input_int("Electrical penetrations", measurements.electrical_penetration_count)
            measurements.plumbing_vent_count = _input_int("Plumbing vents", measurements.plumbing_vent_count)

        print(f"\nCalculating detail-based estimate...\n")
        estimate = calculate_detail_takeoff(measurements, analysis)
        print_detail_estimate(estimate)

        # Also run the standard estimate for comparison
        print("\n\n--- STANDARD ESTIMATE (for comparison) ---\n")
        std_estimate = calculate_takeoff(measurements)
        print_estimate(std_estimate)

    else:
        # --- MANUAL MODE: user enters all counts ---
        print("\n[DRAINS & SCUPPERS]")
        drains = _input_int("Number of roof drains")
        scuppers = _input_int("Number of overflow scuppers")

        print("\n[EQUIPMENT & PENETRATIONS]")
        mech = _input_int("Mechanical units (RTUs)")
        sleepers = _input_int("Sleeper curbs")
        vents = _input_int("Vent hoods")
        gas = _input_int("Gas penetrations")
        elec = _input_int("Electrical penetrations")
        plumb = _input_int("Plumbing vents")

        print("\n[OPTIONAL OVERRIDES - press Enter to use full roof area]")
        taper_raw = input("  Tapered insulation area (sqft) [full roof]: ").strip()
        taper = float(taper_raw) if taper_raw else None
        ballast_raw = input("  Ballast area (sqft) [full roof]: ").strip()
        ballast = float(ballast_raw) if ballast_raw else None

        measurements = RoofMeasurements(
            total_roof_area_sqft=area,
            perimeter_lf=perim,
            parapet_length_lf=par_len,
            parapet_height_ft=par_ht,
            roof_drain_count=drains,
            scupper_count=scuppers,
            mechanical_unit_count=mech,
            sleeper_curb_count=sleepers,
            vent_hood_count=vents,
            gas_penetration_count=gas,
            electrical_penetration_count=elec,
            plumbing_vent_count=plumb,
            tapered_area_sqft=taper,
            ballast_area_sqft=ballast,
        )

        print(f"\nCalculating estimate...\n")
        estimate = calculate_takeoff(measurements)
        print_estimate(estimate)

    if json_output:
        export_json(estimate, json_output)


if __name__ == "__main__":
    main()
