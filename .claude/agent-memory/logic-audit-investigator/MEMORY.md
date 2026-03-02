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
- Discrete item overcount (Roof_Drain etc): FIXED via DISCRETE_COUNT_ATTR/DISCRETE_AI_COUNT_KEY
- Asphalt EasyMelt layer_count: FIXED (hardcoded mopped_layers=2)

### Active Bugs (found 2026-03-02 Excel Parity Audit)

**CRITICAL: PerimeterSection missing width_in field (lines 377-425)**
- Excel has Height(C) AND Width(D); Python only has height_in
- load_takeoff_excel line 648 never reads column D for perimeters
- ALL strip_girth_in and metal_girth_in formulas produce wrong results

**CRITICAL: Vent labour base hours all wrong (lines 252-261)**
- pipe_boot: Python=1.0, Excel=0.5; hood_vent: Python=4, Excel=5
- scupper: Python=2, Excel=4; drain: Python=2, Excel=3; etc.
- plumb_vent adjustments use wrong categories entirely

**CRITICAL: install_hours ignores per-section difficulty (line 462-467)**
- Excel divides by R37/R38/R39 (Normal=1.0, Hard=0.9, Easy=1.5)
- Python only uses settings.effective_rate, install_difficulty field unused

**MODERATE: ProjectSettings modifiers additive(Excel) vs multiplicative(Python)**
**MODERATE: BattInsulation 2x4=59.4, 2x6=39.8 sqft/bundle (Excel) vs flat 40 (Python)**
**MODERATE: WoodWork formulas differ (fence-post, board optimization, waste)**
**MINOR: Soprasmart 24 vs 32 sqft/sheet; Vapour barrier 5% vs 10% waste**
**Low: sbs_base_type defined but never used in calculate_takeoff**

### Detail Takeoff Overestimation Bugs (2026-03-02)

**CRITICAL: Substring match in plan_detail_qtys (lines 2783-2788, 3161-3167)**
- "Detail 1" in "Detail 10/R3.0" = TRUE; small details inherit large quantities
- Same bug in both calculate_detail_takeoff() and join_takeoff_data()
- Fix: exact match on detail number, not substring `in`

**MODERATE: parapet_height_ft applied to all linear-to-area conversions (line 2886-2887)**
- Curbs/expansion joints use parapet height instead of own height
- 1.5x-3x overestimation for curb area-scope materials

**MODERATE: join_takeoff_data() lacks costed_pkeys dedup (lines 3148-3282)**
- Same material priced N times for N details; no consolidation

**VERIFIED: CURB_TYPICAL_PERIMETER_LF multiplier (line 2817-2818) is dead code**
- DETAIL_TYPE_MAP sets mtype="each" for curbs, guard requires "linear_ft"

### Pricing/Coverage Audit (2026-03-02) - see pricing-audit.md

## Verified Correct (2026-03-02)
- CurbDetail 3-tier labour thresholds and formula MATCH Excel SUMPRODUCT
- CurbDetail perimeter formula MATCHES
- ISO layer formula MATCHES
- B-vent hours MATCH; Drain adjustments MATCH
- DISCRETE_COUNT_ATTR/DISCRETE_AI_COUNT_KEY keyspaces
- EPS tiered pricing, Bid summary formula, Fire board scope
- Firetape COVERAGE_RATES lf_per_unit=75
- EPDM/TPO detail sections, Corner defaults, Division-by-zero guards

## Architecture Notes
- Excel ref: 231260__THE AMPERSAND 2026.xlsm (Takeoff, FRS, Project, Dropdown)
- Excel perimeter cols: B(name) C(height) D(width) E(type) F(LF) G(strip) H(metal)
- Project rates: R37=1.0(Normal) R38=0.9(Hard) R39=1.5(Easy)
- Project modifiers: T41-T46 are ADDITIVE (-0.1 to -0.2), not multiplicative
- `_get_price()`: _PRICE_OVERRIDES -> PRICING -> EPDM_SPECIFIC -> TPO_SPECIFIC -> COMMON
- `calculate_takeoff()`: 4 cost buckets (roofing, flashing, mechanical, other)
