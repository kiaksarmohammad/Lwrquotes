# Drawing Analysis Pricing Audit (2026-03-03)

## Reference: The Ampersand 2026 Roof Replacement
- Excel Total Materials: $55,543.33 (FRS Row 127)
- Spec-driven estimate (join_takeoff_data): $578.78
- Ratio: 96x underestimate

## Excel Material Breakdown (non-zero items)
- Tapered Insulation: 287 units @ $3.10 = $8,376
- Soprasmart Board: 128 sheets @ $53.25 = $6,816
- Cap Membrane (field): 66 rolls @ $98 = $6,468
- Cap Membrane (wall): 10 rolls @ $98 = $980
- Base Membrane (wall): 13 rolls @ $127.25 = $1,654
- Base Membrane (field): 20 rolls @ $127.25 = $2,545
- Duotack adhesive: 70 @ $58 = $4,060
- Elastocol (wall): 1 @ $125.05 = $125
- Elastocol (field): 5 @ $125.05 = $625
- Sealant: 22 tubes @ $9 = $198
- Sopralap: 13 @ $42 = $546
- Filter Fabric: 1 roll @ $1,076 = $1,076
- Drainage Board: 13 rolls @ $535.75 = $6,965
- Drains: 3 @ $325 = $975
- Scuppers: 1 @ $185 = $185
- Metal Galv (clips): 6 @ $85 = $510
- Metal Prepainted: 49 @ $65 = $3,185
- Wood 2x6: 100 @ $10 = $1,000
- Plywood: 11 @ $40 = $440
- Comfortbatt R22: 54 @ $83.99 = $4,535
- Delivery: 3 @ $250 = $750
- Disposal: 45 @ $70 = $3,150
- Toilet/Fencing: $379

## Confirmed Bugs

### D1 - CRITICAL: join_takeoff_data fallback base_value=1.0
- File: backend/roof_estimator.py, line 3265
- Code: `base_value = 1.0  # conservative -- no spatial data available`
- Expected: Use DETAIL_TYPE_MAP attr to get real measurement (like calculate_detail_takeoff does)
- But: join_takeoff_data has no RoofMeasurements object, so it CAN'T read m.total_roof_area_sqft
- Impact: field_assembly gets qty=1 roll instead of ~200 rolls
- The `_` discard on line 3263 shows the attr was intentionally ignored

### D2 - CRITICAL: join_takeoff_data resolves only ONE material per detail
- File: backend/roof_estimator.py, lines 3282-3286
- The function iterates candidate_keys and picks the FIRST match in confirmed_spec
- A field_assembly detail with 6 materials (Base, Cap, XPS, Drainage, Filter, Gravel) -> only 1 priced
- calculate_detail_takeoff processes ALL layers per detail; join_takeoff_data does not
- Impact: 5 of 6 field materials are completely ignored

### D3 - CRITICAL: material_registry first-registration bias in calculate_detail_takeoff
- File: backend/roof_estimator.py, lines 2679-2694
- Materials registered with FIRST detail they appear in; later details get "already_costed"
- Base_Membrane first appears in penetration_gas (detail_cost_calc=None) -> qty=1
- Should be assigned to field_assembly (detail_cost_calc=total_roof_area_sqft) -> qty=~200
- Similarly affected: Flashing_General, Batt_Insulation, Gravel_Ballast, Sealant_General,
  Coated_Metal_Sheet, Wood_Blocking_Lumber
- Root cause: all_details iterates page-by-page; drain/penetration details precede field_assembly

### D4 - MODERATE: Spec extractor fails to resolve Polyisocyanurate
- File: backend/file_extractor.py, _resolve_pricing_key()
- Product name "Polyisocyanurate Insulation" -> None (missing "ISO" in name)
- "Polyisocyanurate ISO Insulation" -> Polyisocyanurate_ISO_Insulation (works)
- Impact: spec_materials never contains Polyisocyanurate_ISO_Insulation
- Fix: Add "polyisocyanurate" as substring match to Polyisocyanurate_ISO_Insulation

### D5 - MODERATE: "2-Ply SBS Membrane System" maps to wrong pricing key
- File: backend/file_extractor.py, _resolve_pricing_key()
- "2-Ply SBS Membrane System" resolves to SBS_Membrane ($298/roll per-unit price)
- Should resolve to SBS_2Ply_Modified_Bitumen ($7.00/sqft composite rate)
- But SBS_2Ply_Modified_Bitumen is a scalar in PRICING (not a dict with canonical_name)
- So _build_pricing_key_index maps "sbs 2ply modified bitumen" -> SBS_2Ply_Modified_Bitumen
- And "2 ply sbs membrane system" normalizes to match "sbs membrane" via substring

### D6 - DESIGN FLAW: join_takeoff_data has no area/length data for fallback
- join_takeoff_data() receives only spatial_json and spec_json, no RoofMeasurements
- When AI doesn't provide measurements, base_value defaults to 1.0
- calculate_detail_takeoff() has RoofMeasurements and uses DETAIL_TYPE_MAP attrs
- Fix options:
  1. Pass RoofMeasurements to join_takeoff_data (API change)
  2. Extract area/perimeter from spatial_json plan_analysis
  3. Add a measurements dict parameter alongside spec_json
