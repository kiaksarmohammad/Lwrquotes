# Pricing & Coverage Rate Audit (2026-03-02)

## Coverage Rate Disagreements (manual vs AI path)
- EPS_Insulation_EPDM: manual=8 sqft/sheet (2-layer), COVERAGE=16 (1-layer) -> AI undercounts 2x
- EPDM_Cav_Grip: consumable rate=0.5/1000sqft (manual), COVERAGE=500 sqft/cyl -> 2.0/1000sqft -> AI overcounts 3.7x
- EPDM_Primer_HP250: COVERAGE=50 sqft/gal, manual uses 400 sqft/gal on pre-reduced strip area

## Missing from COVERAGE_RATES
- Asphalt_Adhesive: $175/pail, no coverage -> units_needed=ceil(area)=18450 if used in AI
- XPS_Dow_EPDM: $52.48/sheet, no coverage -> same catastrophic risk

## Pricing Anomalies (category-wide averages)
- Coating_Paint: $1088/pail avg, max $6409, should be $50-200
- Mastic: $359/pail avg, includes $3219 items
- Tape: $425/roll avg, includes masking/caution tape to $2940
- EPDM_Accessory: $399/roll avg, range 0.62-4880
- TPO_Accessory: $499/piece avg, range 0.98-2699

## TPO_Membrane unit label
- Database says unit="SqFt" but avg_price=$2865 is clearly PER ROLL
- Code works correctly (uses sqft_per_unit=1000) but label is misleading
