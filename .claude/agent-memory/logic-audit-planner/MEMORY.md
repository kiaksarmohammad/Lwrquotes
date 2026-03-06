# Logic Audit Planner - Memory

## Project Architecture
- FastAPI app (app.py) with two estimate paths: manual form and drawing analysis pipeline
- Drawing pipeline: drawing_analyzer.py (Gemini Vision) -> roof_estimator.py (calculate_detail_takeoff + join_takeoff_data)
- Spec pipeline: file_extractor.py (regex) -> spec_materials dict -> join_takeoff_data()
- Pricing: database.py PRICING dict, looked up via _get_price() in roof_estimator.py

## Key Functions for Detail-Based Estimates
- `calculate_detail_takeoff(m, analysis)` - Uses synthetic field + AI details, deduplicates via costed_pkeys
- `join_takeoff_data(spatial, spec, measurements)` - Merges spec-confirmed materials with AI details
- `_build_synthetic_field_section(m)` - Builds SBS/EPDM/TPO field layers from _SYSTEM_AREA_LAYERS
- `_get_price(key)` - Checks _PRICE_OVERRIDES then _ALL_MATERIALS dicts

## Common Failure Patterns (from 333 5th Ave audit, March 2026)
- AI misclassifies demolition/planter details as field_assembly -> wrong products at full area cost
- No filter for "temporarily remove and reinstate" layer notes -> demo items priced as new
- Cap_Membrane avg_price was $150, actual Sopraply Traffic Cap GR is ~$105.80
- Spec-confirmed materials (PMMA, Alsan RS, Fleece, Duotack) not in _DETAIL_TYPE_TO_SPEC_KEYS -> omitted
- AI drain counting unreliable (4 vs 6 actual); metric scale conversion errors cause area overestimate

## Effective Audit Methodologies
- Reference Parity (Excel comparison) most effective for pricing/formula bugs
- Control Flow Analysis effective for filtering logic gaps (missing exclusion branches)
- Boundary Value Analysis useful for scale conversion edge cases

## File Locations
- PRICING dict: database.py line ~11
- Cap_Membrane entry: database.py line ~197
- _DETAIL_TYPE_TO_SPEC_KEYS: roof_estimator.py line ~3243
- calculate_detail_takeoff: roof_estimator.py line ~2766
- join_takeoff_data: roof_estimator.py line ~3319
- DETAIL_PROMPT: drawing_analyzer.py line ~242
- PLAN_PROMPT: drawing_analyzer.py line ~306
- MEASUREMENT_PROMPT_BASE: drawing_analyzer.py line ~126
