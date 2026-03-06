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

### Detail Takeoff Bugs (2026-03-02)

**FIXED: Substring match in plan_detail_qtys** - now uses token-exact regex
**FIXED: join_takeoff_data() costed_pkeys dedup** - costed_pkeys_j added

**MODERATE: parapet_height_ft applied to all linear-to-area conversions (line 2886-2887)**
- Curbs/expansion joints use parapet height instead of own height
- 1.5x-3x overestimation for curb area-scope materials

**VERIFIED: CURB_TYPICAL_PERIMETER_LF multiplier (line 2817-2818) is dead code**

### Drawing Analysis Pricing Bugs (2026-03-03) - see drawing-analysis-audit.md

**D1-CRITICAL: join_takeoff_data fallback base_value=1.0 (line 3265)**
**D2-CRITICAL: join_takeoff_data 1 material per detail (lines 3282-3286)**
**D3-CRITICAL: material_registry first-registration bias (lines 2679-2694)**
**D4-MODERATE: Spec extractor missing "ISO" -> Polyiso never resolves**
**D5-MODERATE: "2-Ply SBS" maps to SBS_Membrane ($298/roll) not composite**
**D6-DESIGN: join_takeoff_data has no RoofMeasurements -> no area/LF fallback**
Excel reference: $55,543 material cost; spec-driven estimate: $579 (96x under)

### 333 5th Ave Overestimation Audit (2026-03-06) - see 333-5th-ave-audit.md
**Root cause: same SBS superset bug as Ampersand (below)**
- Excel total materials: $20,117.35 (area=1370, perim=215, height=8in)
- App field assembly: $23,967.14 (area=1534, perim=230, parapet=139x0.66ft)
- Phantom materials: XPS($4,632), Soprasmart($3,781), Drainage Board($2,463) = $11,476
- Wrong primer: Asphaltic($1,980) vs Elastocol($535) = +$1,445
- Missing from app: ISO Glass($1,948), Densdeck($1,642), Vapour Barrier($860), Duotack($2,870)
- Strip area 2.7x too low: app 91.7sqft vs Excel 250.8sqft (girth=14in not just height)

### Post-D1-D5 Fix Parity Audit (2026-03-03) - see post-fix-parity-audit.md
**calculate_detail_takeoff() with Ampersand project data:**
- With default parapet_h=2.0: $63,556 (+14.4% vs Excel) -> OUTSIDE 5%
- With parapet_h=1.0: $55,434 (-0.2% vs Excel) -> WITHIN 5% but ERROR CANCELLATION
- $30,769 overestimation cancels $30,879 underestimation
- Key overestimates: XPS $13,372 (Excel $0), Coated_Metal $5,831 (Excel $0), Gravel $3,662 (Excel $0)
- Key underestimates: Tapered ISO missing ($8,376), Soprasmart missing ($6,816), Batt $168 vs $4,535
- Root cause: AI detail layers drive material list, but miss SBS-specific products (Tapered ISO, Soprasmart, Duotack, Elastocol, Sopralap) while including EPDM-ballasted components at full area

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
