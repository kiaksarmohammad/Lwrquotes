# Logic Audit Investigator - Memory

## Confirmed Bugs (2026-03-01 Audit)
See `audit-2026-03-01.md` for full details.

### Critical: Double/Triple-Counted Materials
- EPDM Seam Tape: area_materials + epdm_tpo_details (both EPDM systems)
- TPO Tuck Tape: consumables + epdm_tpo_details (both TPO systems)
- EPDM HP-250 Primer: area_materials + wall_consumables + epdm_tpo_details
- TPO Rhinobond Plates: area_materials + epdm_tpo_details (TPO_Mech_Attached)

### Critical: Firetape Name Match Bug
- Line 1802: searches area_materials for 'Soprasmart' but matches Tapered ISO (not coverboard)
- SBS system has no Densdeck coverboard, so formula picks up wrong material
- Produces 11,416 LF of firetape instead of ~408 LF (28x overshoot)

### High: Ballast Qty Uses Wrong Area
- Line 1386 uses `roof_area` but should use `m.effective_ballast_area`

### High: PMMA Primer Uses Section Count Instead of LF
- Line 1860: `perim_section_count / 200` always yields 1 pail (max 5 sections)

### Medium: Empty String Detail Matching
- drawing_analyzer.py line 721: `"" in "any_string"` is always True

### Medium: calculate_detail_takeoff Over-Aggressive Dedup
- Lines 2626-2633 mark all same-type details as alternatives (too broad)

### Low: Template Division by Zero
- manual_result.html line 390: no guard against zero roof area

### Low: Garland Gar-Mesh Identity Formula
- `(parapet_lf/3)*3` = `parapet_lf` (no-op, likely copy error from Excel)

## Verified Correct
- CurbDetail 3-tier labour formula (< 25", 25-69", > 69")
- PerimeterSection girth calculations (5 types)
- EPS tiered pricing (0.31/sqft/inch x 16 sqft x thickness)
- ProjectSettings effective_rate cascading multipliers
- VentItem hours_per_unit (base + difficulty adjustment)
- Fire board scope logic (Wall/Field/Both)
- ISO 2nd/3rd layer logic

## Architecture Notes
- `_get_price()` checks _PRICE_OVERRIDES first, then PRICING, EPDM_SPECIFIC, TPO_SPECIFIC, COMMON
- `calculate_takeoff()` builds 4 cost buckets: roofing, flashing, mechanical, other
- `calculate_detail_takeoff()` is the AI-driven path; `calculate_takeoff()` is manual
- database.py has 3 extra dicts beyond PRICING: EPDM_SPECIFIC, TPO_SPECIFIC, COMMON
