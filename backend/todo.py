"""
================================================================================
  PER-UNIT DETAIL PERIMETERS & UNIT-TO-DETAIL MAPPING
================================================================================

GOAL
----
Currently, detail calculations use the ENTIRE roof perimeter (or total area) as
the quantity basis for every detail. In reality, each detail applies to a SPECIFIC
unit on the plan (e.g., a hot stack penetration "HS" has its own small perimeter,
not the full 750 LF roof perimeter). We need:

  1. Gemini to identify labelled units on the plan view (HS, P, D, V, M, etc.)
  2. Gemini to read the legend and map each label → its detail reference
  3. Gemini to calculate the specific perimeter/dimensions of each unit instance
  4. Pass this per-unit data to roof_estimator.py so details are costed correctly


================================================================================
  PHASE 1 — AI EXTRACTION (drawing_analyzer.py)
================================================================================

# STEP 1.1: Update PLAN_PROMPT to extract unit labels + legend mapping
# ----------------------------------------------------------------------
# File: backend/drawing_analyzer.py, PLAN_PROMPT (line ~251)

# What to add to the prompt:
#   - Instruct Gemini to find ALL labelled units/symbols on the plan view
#     (letters like "HS", "P", "D", "V", "M", "PW", "GG", "JJ", "HH", etc.)
#   - For EACH label, record:
#       * The label text (e.g., "HS")
#       * How many instances of that label appear on the plan
#       * The coordinates/location description of each instance
#   - Instruct Gemini to read the LEGEND on the plan page and map each label
#     to its detail reference. Example legend entries:
#       "P  — PIPE PENETRATION, SEE DETAIL 1/R3.2"
#       "HS — HOT STACK PENETRATION, SEE DETAIL 3/R3.1"
#       "D  — TWIN DUCT PENETRATION, SEE DETAIL 4/R3.1"
#       "V  — VENT PENETRATION, SEE 1/R3.1"
#       "M  — MECHANICAL VENT PENETRATION, SEE DETAIL 2/R3.1"
#   - For each labelled unit, Gemini should determine the unit's physical size
#     by measuring from the drawing scale:
#       * For rectangular units: width and height → perimeter = 2*(W+H)
#       * For circular units: diameter → perimeter = π * D
#       * For irregular shapes: estimate the outer perimeter in LF
#       * Report dimensions in feet and the calculated perimeter in LF

# Add to the JSON output schema a new key "unit_labels":
#   "unit_labels": [
#     {
#       "label": "HS",
#       "description": "Hot Stack Penetration",
#       "detail_ref": "Detail 3/R3.1",
#       "detail_page": "R3.1",
#       "instances": [
#         {
#           "instance_id": "HS-1",
#           "location": "center-left area near grid line 4",
#           "shape": "rectangular",
#           "width_ft": 2.5,
#           "height_ft": 3.0,
#           "perimeter_lf": 11.0,
#           "area_sqft": 7.5
#         },
#         {
#           "instance_id": "HS-2",
#           "location": "center-right area near grid line 5",
#           "shape": "rectangular",
#           "width_ft": 2.5,
#           "height_ft": 3.0,
#           "perimeter_lf": 11.0,
#           "area_sqft": 7.5
#         }
#       ],
#       "total_count": 2,
#       "total_perimeter_lf": 22.0,
#       "total_area_sqft": 15.0
#     }
#   ]

# How to do it:
#   - Add a new section to the PLAN_PROMPT string (after the existing sections)
#     numbered as section 7 or similar
#   - Add "unit_labels" to the example JSON output in the prompt
#   - The prompt should emphasize:
#       * Read the legend FIRST to understand what each letter means
#       * Then scan the plan to count and measure each labelled unit
#       * Use the drawing scale to convert drawn dimensions to real-world feet
#       * Calculate perimeter for each individual unit instance
#   - Keep the existing sections (counts, zones, detail_quantities, etc.) intact


# STEP 1.2: Update DETAIL_PROMPT to capture detail reference numbers precisely
# ------------------------------------------------------------------------------
# File: backend/drawing_analyzer.py, DETAIL_PROMPT (line ~194)

# What to change:
#   - Add instruction to capture the exact detail reference ID as shown on the
#     drawing (e.g., "3/R3.1", "1/R3.2", "4/R3.1") in a new field "detail_ref_id"
#   - This must match the format used in the plan legend so we can join them
#   - Currently detail_name captures this loosely (e.g., "Detail 3 - Hot Stack
#     Penetration") but we need a clean machine-readable reference

# Add to the detail JSON schema:
#   "detail_ref_id": "3/R3.1"

# This is the key that links a detail's material layers to the plan-view units.


STEP 1.3: Link unit labels to detail analysis in analyze_drawing()
-------------------------------------------------------------------
File: backend/drawing_analyzer.py, analyze_drawing() (line ~590)

What to add:
  - After both plan and detail analyses complete, create a new key in the
    result dict called "unit_detail_map" that joins unit_labels with details
  - For each unit_label entry, find the matching detail from detail_analysis
    by comparing detail_ref (e.g., "Detail 3/R3.1") against detail_ref_id
  - The map should look like:
    "unit_detail_map": [
      {
        "label": "HS",
        "description": "Hot Stack Penetration",
        "detail_ref": "Detail 3/R3.1",
        "matched_detail_index": 5,
        "instances": [...],           // from plan
        "total_perimeter_lf": 22.0,
        "total_area_sqft": 15.0,
        "layers": [...]               // from detail analysis
      }
    ]
  - If a unit label can't be matched to any detail, flag it with
    "match_status": "unmatched" so the estimator knows


================================================================================
  PHASE 2 — ESTIMATOR INTEGRATION (roof_estimator.py)
================================================================================

STEP 2.1: Add unit_detail_map parsing in calculate_detail_takeoff()
--------------------------------------------------------------------
File: backend/roof_estimator.py, calculate_detail_takeoff() (line ~2487)

What to change:
  - After building plan_detail_qtys, also extract the "unit_detail_map" from
    the analysis dict
  - Build a lookup: detail_ref → { total_perimeter_lf, total_area_sqft,
    total_count, instances[] }
  - This lookup will be used in the quantity resolution step

How it fits in the existing priority system:
  The current priority order is:
    1. Plan-view detail_quantities
    2. Detail-view scope_quantity
    3. DETAIL_TYPE_MAP fallback

  Insert the new unit-based data as PRIORITY 0 (highest):
    0. Unit-specific perimeter from unit_detail_map (NEW — most accurate)
    1. Plan-view detail_quantities
    2. Detail-view scope_quantity
    3. DETAIL_TYPE_MAP fallback

  When a detail's detail_ref_id matches a unit_detail_map entry:
    - Use total_perimeter_lf as the base_value for linear details
    - Use total_area_sqft as the base_value for area details
    - Use total_count as the base_value for discrete (each) details
    - Set quantity_source = "unit_perimeter"

  This means a hot stack penetration with perimeter 11 LF × 2 instances = 22 LF
  will use 22 LF instead of the full 750 LF roof perimeter.


STEP 2.2: Store per-instance data in detail_result for reporting
-----------------------------------------------------------------
File: backend/roof_estimator.py, calculate_detail_takeoff()

What to add:
  - When a detail is resolved via unit_detail_map, include the instance
    breakdown in the detail_result dict:
    detail_result["unit_instances"] = [
      {"instance_id": "HS-1", "perimeter_lf": 11.0, "location": "..."},
      {"instance_id": "HS-2", "perimeter_lf": 11.0, "location": "..."}
    ]
    detail_result["unit_label"] = "HS"
  - This allows the UI/report to show per-unit breakdowns


STEP 2.3: Update detail_cost_calculation in material_registry
--------------------------------------------------------------
File: backend/roof_estimator.py, material_registry loop (line ~2557)

What to change:
  - Currently, material_registry[pkey]["detail_cost_calculation"] is set to
    m.total_roof_area_sqft for area scope and m.perimeter_lf for linear scope
  - This is the global value — it should ONLY be used as the fallback
  - When unit_detail_map provides a specific perimeter for a detail, that
    detail's layers should use the unit-specific value, NOT the global one
  - The per-detail override happens in the layer loop (step 2.1 already
    handles this via the priority system), so no change needed here IF the
    quantity_basis resolution correctly uses unit data before falling back
    to material_registry


================================================================================
  PHASE 3 — FRONTEND DISPLAY
================================================================================

STEP 3.1: Update drawing_result.html to show unit-level data
--------------------------------------------------------------
File: templates/drawing_result.html

What to add:
  - In the detail breakdown section, when a detail has "unit_instances",
    show a sub-table or expandable section listing each unit instance:
      HS-1: 11.0 LF perimeter (center-left near grid 4)
      HS-2: 11.0 LF perimeter (center-right near grid 5)
      Total: 22.0 LF
  - Show the unit_label badge next to the detail name
  - Show quantity_source = "unit_perimeter" differently from other sources
    (e.g., green badge) so user can see which details got accurate per-unit
    measurements vs fallback global measurements


================================================================================
  REFERENCE: PDF DRAWING STRUCTURE (from Roxboro House example)
================================================================================

Plan page (R2.0) contains:
  - Labelled units: P (×3), HS (×2), M (×1), D (×1), V (×1), PW (×1)
  - Legend mapping:
      P   → Pipe Penetration, Detail 1/R3.2
      PW  → Pipe Penetration w/ Electrical Conduit, Detail 2/R3.2
      M   → Mechanical Vent Penetration, Detail 2/R3.1
      HS  → Hot Stack Penetration, Detail 3/R3.1
      D   → Twin Duct Penetration, Detail 4/R3.1
      V   → Vent Penetration, Detail 1/R3.1
  - Each unit has a visible physical footprint on the plan that can be
    measured using the drawing scale
  - Scupper symbols (existing overflow scupper, existing scupper drain)
  - Parapet cap flashing callout (separate price item)

Detail pages (R3.0, R3.1, R3.2) contain:
  - Each detail referenced by the legend, with full material layer assemblies
  - Cross-section views showing all materials from bottom to top
  - Dimensions for curb heights, flashing widths, insulation thicknesses

The JOIN between plan and detail pages happens via the detail reference:
  Plan label "HS" → legend says "Detail 3/R3.1" → Detail page R3.1 has
  "Detail 3 - Hot Stack Penetration" with layers → those layers get costed
  using the HS unit's measured perimeter (not the full roof perimeter)


================================================================================
  TESTING & VERIFICATION
================================================================================

1. Upload the Roxboro House PDF and verify:
   - unit_labels in plan analysis contains HS(×2), P(×3), M(×1), D(×1), V(×1), PW(×1)
   - Each unit has a measured perimeter (should be small, 5-30 LF range)
   - Legend mapping correctly links to detail references
   - detail_ref_id in detail analysis matches the legend references

2. Verify cost calculation uses unit perimeters:
   - HS detail should use ~22 LF (2 units × ~11 LF each), NOT 750 LF
   - P detail should use ~15 LF (3 small pipe penetrations), NOT 750 LF
   - Parapet/wall details should still use full perimeter (they aren't "units")

3. Verify the UI shows per-unit breakdowns with instance IDs and locations

4. Run: python -c "from backend.roof_estimator import *; print('OK')"
   to confirm no import errors after changes
"""
