# Logic Audit Investigator - Memory

## Confirmed Bugs (2026-03-01 Re-Audit)

### Previously Critical Bugs - ALL FIXED
- EPDM Seam Tape double-counting: FIXED
- TPO Tuck Tape double-counting: FIXED
- EPDM HP-250 Primer double-counting: FIXED
- TPO Rhinobond Plates double-counting: FIXED
- Firetape name match bug (Soprasmart matching Tapered ISO): FIXED
- Ballast qty using wrong area: FIXED (now uses effective_ballast_area)
- PMMA Primer using section count: FIXED (now uses parapet_lf / 200)
- calculate_detail_takeoff over-aggressive dedup: FIXED

### Active Bugs (found 2026-03-01)

**CRITICAL: Discrete materials in non-discrete detail types get wrong quantity basis**
- Lines 2627-2630 in calculate_detail_takeoff
- Discrete items (per_each) inside field_assembly details get total_roof_area_sqft as count
- Example: Roof_Drain gets 18,450 EA instead of 4 EA ($5.99M overcount)
- Same pattern affects Clips in parapet details (503 instead of ~50)
- Root cause: DETAIL_TYPE_MAP lookup uses enclosing detail_type, not item's own count attr

**Medium: Asphalt EasyMelt layer_count = 7 instead of ~2**
- Line 1865: uses ALL area layers (7) instead of mopped layers (~2)
- 3.5x overcounting of asphalt quantity

**Medium: Firetape roll size 60 vs 75 LF mismatch**
- Line 1800 uses 60; COVERAGE_RATES says 75 LF/roll
- ~17% overcount

**Low: EPS price override ignores thickness in AI path**
- _PRICE_OVERRIDES fixed at $12.40 (2.5"), AI path uses this regardless

**Low: sbs_base_type defined but never used in calculate_takeoff**

**Low: Fabrication hours never totaled in calculate_takeoff**

**Low: Garland products added with zero parapet/curbs (min 1 unit)**

### Possibly Not in roof_estimator.py
- drawing_analyzer.py empty string detail matching
- manual_result.html template division by zero

## Verified Correct (2026-03-01)
- CurbDetail 3-tier labour, PerimeterSection 5-type girth, ProjectSettings
- VentItem, WoodWorkSection, BattInsulationSection
- EPS tiered pricing, Bid summary formula, Fire board scope, ISO layers
- Firetape conditional logic, EPDM/TPO detail sections, Corner defaults
- Division-by-zero guards, TPO wall primer separation

## Architecture Notes
- `_get_price()`: _PRICE_OVERRIDES -> PRICING -> EPDM_SPECIFIC -> TPO_SPECIFIC -> COMMON
- `calculate_takeoff()`: 4 cost buckets (roofing, flashing, mechanical, other)
- `calculate_detail_takeoff()`: AI-driven path with material dedup by pricing_key
- `join_takeoff_data()`: spec-joined path, base_value=1.0 in fallback (conservative)
- COVERAGE_RATES (AI path) vs _SYSTEM_AREA_LAYERS (manual path) may conflict
- DETAIL_TYPE_MAP maps detail_type -> (mtype, attr); DANGEROUS for discrete items in area/linear details
