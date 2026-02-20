"""Fix Detail Takeoff Overestimation - Match Excel Formulas
Context
The calculate_detail_takeoff() function in backend/roof_estimator.py massively overestimates costs because it prices every AI-detected detail independently, applying the full roof area or perimeter to each. The reference Excel (231260__THE AMPERSAND 2026.xlsm) uses a single consolidated material list where each material appears once. This causes costs to be 3-5x what they should be.
line 2487 in roof_estimator
Example from the PDF output (26,500 sqft roof, 750 LF perimeter):

"NO TAPERED PACKAGE" field_assembly: $237,011 (full 26,500 sqft)
"WITH TAPERED INSULATION" field_assembly: $334,744 (full 26,500 sqft again!)
Parapet detail R3.0: $23,522 (full 750 LF)
Parapet detail R3.2: $13,301 (full 750 LF again!)
Curtain wall detail R3.2: $23,299 (full 750 LF again!)
Mech curb Type 1 + Type 2 + Typical: all 3 get full count of 3 units each
Total detail-based: $726,727 vs standard: $730,194 — but the detail estimate double/triple counts most items.

Root Causes
1. Same-type details not deduplicated (CRITICAL)
calculate_detail_takeoff (line 2546) iterates ALL details independently. Two field_assembly details each get 26,500 sqft. Three mechanical_curb details each get count=3. Multiple parapet details each get 750 LF. The alternative detection (line 2539-2544) only marks details as alternatives if they share the SAME _drawing_ref page, but alternatives often appear on the same page with different detail numbers.

2. Perimeter girth formulas wrong (line 337-374)
Excel uses Height + Width + 10 for strip girth. Python uses Height + 16 (missing width dimension entirely). PerimeterSection doesn't even have a width_in field.

Excel formulas (Takeoff G53):

Parapet w/o facing: C53 + D53 + 10 (Height + Width + 10)
Parapet w/ facing: C53 + D53 + 10 (same)
Interior Walls: C53 + 6 (Height + 6)
Cant: 8 + 6 (fixed 14")
Divider w/ facing: 2*(C53 + D53 + 10) (both sides)
Python (PerimeterSection.strip_girth_in):

parapet_no_facing: h + 16
parapet_w_facing: h + 20
interior_wall: h + 16
cant: sqrt(2) * h + 12
divider_w_facing: 2 * h + 12
3. Metal girth formulas wrong (line 357-374)
Excel: Parapet w/o facing = Width + 14. Python: Height + 6.

Excel (Takeoff H53):

Parapet w/o facing: D53 + 14 (Width + 14)
Parapet w/ facing: D53 + C53 + 14 (Width + Height + 14)
Interior Walls: 6 (fixed)
Cant: 8 + 4 (fixed 12")
Divider w/ facing: D53 + 2*C53 + 14
4. Top-of-parapet formula wrong
Excel (Takeoff K53):

Parapet w/o facing: D53 + 4 (Width + 4)
Parapet w/ facing: D53 + 4 (Width + 4)
Divider w/ facing: D53 + 4
Cant: 0
Interior Walls: 0
Python doesn't use this; it just checks boolean top_of_parapet.

5. Metal flashing qty formula wrong
Excel (FRS R111): F111 = ROUNDUP(perimeter_lf / 8 / 8, 0) for Galvanized w/ Clips (÷64)
Excel (FRS R112): F112 = ROUNDUP((metal_sqft / 30) * 1.5, 0) for Prepainted
Python: qty = ceil(LF * 1.1 / lf_per_unit) — completely different formula.

6. Fabrication hours formula (Takeoff Q53)
Excel: Q53 = ROUNDUP((F53/8/8) + ((P53/30)*1.5), 0) — combines LF/64 + metal_sqft/30*1.5
Python: uses fabrication_hours_per_sheet difficulty rates — different approach.

Implementation Plan
Step 1: Fix calculate_detail_takeoff — Deduplicate same-type details
File: backend/roof_estimator.py lines 2537-2612

Change: Before iterating details, group by detail_type. For each type, only ONE detail (the first/primary) gets the full base measurement. All others of the same type are marked as alternatives.


# Group details by detail_type
from collections import defaultdict
details_by_type = defaultdict(list)
for detail in all_details:
    dtype = detail.get("detail_type", "unknown")
    details_by_type[dtype].append(detail)

# Mark all but the first of each type as alternatives
for dtype, detail_list in details_by_type.items():
    if len(detail_list) > 1:
        for alt in detail_list[1:]:
            alt["_is_alternative"] = True
This replaces the current same-page-only alternative detection that misses cross-page alternatives.

Step 2: Fix PerimeterSection — Add width_in dimension
File: backend/roof_estimator.py lines 325-397

Change: Add width_in field to PerimeterSection dataclass and update all girth formulas to match Excel exactly.

Add: width_in: float = 0.0 field
Fix strip_girth_in: Use h + w + 10 for parapet types
Fix metal_girth_in: Use w + 14 for parapet_no_facing, w + h + 14 for parapet_w_facing
Add top_of_parapet_in property for cap-only girth
Fix wood_face_sqft to use correct formula: IF((strip_girth - 6 - top_of_parapet) / 12 * LF < 0, 0, ...)
Step 3: Fix metal flashing quantity formulas
File: backend/roof_estimator.py lines 1498-1547

Change: Match Excel FRS R111-R112 formulas:

Galvanized: qty = ceil(perimeter_lf / 8 / 8) (each sheet is 8" wide × 8ft long → covers 64 LF equivalent)
Prepainted: qty = ceil((total_metal_sqft / 30) * 1.5)
Step 4: Fix fabrication hours formula
File: backend/roof_estimator.py PerimeterSection class

Change: Match Excel Takeoff Q53: ROUNDUP((LF/8/8) + ((metal_sqft/30)*1.5), 0)

Step 5: Fix cap stripping girth (N column)
File: Excel uses N53 = F53 * ((G53 - K53) / 12) for cap stripping area.
This means: cap_strip_sqft = LF * ((strip_girth - top_of_parapet) / 12)

Add this as a computed property on PerimeterSection.

Step 6: Update measurements_from_analysis and form handling
File: backend/roof_estimator.py line 2453 and app.py

If the user's form provides perimeter section width, pass it through. Otherwise default width_in=0 for backward compatibility.

Files to Modify
backend/roof_estimator.py — Main changes (Steps 1-5)
Verification
Run the app, upload the same drawings, verify the detail takeoff total is no longer 3-5x inflated
Check that alternative details show "Alternative assembly — not included in total"
Verify perimeter girth calculations match Excel for test values (e.g., Height=12, Width=14.5, Parapet w/ facing → strip girth = 12+14.5+10 = 36.5")
Run python -c "from backend.roof_estimator import *; print('OK')" to verify no import errors
"""
