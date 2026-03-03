# Post-D1-D5 Fix Parity Audit (2026-03-03)

## Test: calculate_detail_takeoff() vs Excel $55,543.33

### Project: The Ampersand 2026 (231260)
- Total roof area: 4,438.26 sqft (45 squares)
- Perimeter: 328.5 LF
- Parapets: A(12in,134LF), B(10in,132LF), C(10in,22LF), D(20in,40.5LF)
- Weighted avg parapet height: 12.05in (1.0 ft)
- Excel strip sqft (girth-based): 891.66 sqft
- Drains: 3 (Excel) vs 4 (AI plan view)
- System: SBS with inverted roof assembly

### Results
| Scenario | parapet_h | Code Total | vs Excel | Within 5%? |
|---|---|---|---|---|
| Default AI path | 2.0 ft | $63,556.25 | +14.4% | NO |
| User-provided height | 1.0 ft | $55,433.94 | -0.2% | YES (error cancellation) |

### Error Cancellation Analysis (h=1.0)
Total overestimation: +$30,769
Total underestimation: -$30,879
Net: -$109 (appears accurate but individual items wildly off)

### Overestimates (code charges, Excel does not)
- XPS_Insulation: +$13,372 (Excel has $0 -- not used in SBS system)
- Coated_Metal_Sheet: +$5,831 (parapet strip, Excel handles via metal flashing)
- Gravel_Ballast: +$3,662 (Excel $0 -- EPDM ballasted not active)
- SBS_2Ply_Modified_Bitumen: +$2,534 (parapet strip material, not in Excel)
- Base_Membrane: +$2,036 (code uses full area; Excel splits field=20 rolls, wall=13 rolls)
- Cap_Membrane: +$1,102 (code $150/roll vs Excel $98/roll)
- Sealant: +$369 (code $29.86/tube vs Excel $9/tube Mulco Supra)

### Underestimates (Excel charges, code does not)
- Tapered Insulation: -$8,376 (not in AI detail layers at all)
- Soprasmart Board: -$6,816 (not in AI detail layers)
- Batt Insulation: -$4,368 (code 41sqft vs Excel 54 bundles)
- Delivery/Disposal/Rental: -$4,279 (logistics, never in material calc)
- Duotack Adhesive: -$4,060 (not in AI detail layers)
- Flashing: -$920 (code $75 generic vs Excel $65/$85 specific)
- Elastocol: -$750 (not in AI detail layers)
- Sopralap: -$546 (not in AI detail layers)

### Root Causes

1. **AI detail layers missing SBS-specific products**: The AI drawing analysis
   identifies generic material names (Base_Membrane, Cap_Membrane) but misses
   SBS-specific accessories: Tapered ISO, Soprasmart coverboard, Duotack adhesive,
   Elastocol primer, Sopralap cover strip. These total $20,548 in the Excel.

2. **AI includes EPDM ballasted components at full area**: The roof assembly detail
   shows XPS, Gravel, Filter Fabric as layers. The AI applies these at full roof area
   even though the Excel has qty=0 for XPS and Gravel (they are in the EPDM section
   which is not active). This adds $17,034 in phantom costs.

3. **Price mismatches**: Cap_Membrane ($150 vs $98), Sealant ($29.86 vs $9),
   Drainage Board ($410 vs $535.75). The database avg_price does not match
   project-specific vendor pricing.

4. **Quantity scope mismatches**: Batt insulation gets expansion_joint fallback
   (41 sqft) instead of the Excel's 54 bundles covering parapet cavity.
   Plywood gets 41 sqft instead of 11 sheets (440 sqft).

### Verdict
The D1-D5 fixes are structurally correct -- the code no longer produces $579
or other nonsensical totals. But the apparent 0.2% accuracy is pure coincidence
from error cancellation. No individual line item is within 5% of its Excel
counterpart except Drainage Board (+0.2%).

### Fixes needed to achieve genuine 5% parity
1. System-aware material filtering (do not apply EPDM materials to SBS projects)
2. SBS-specific material injection (Tapered ISO, Soprasmart, Duotack, Elastocol, Sopralap)
3. Project-specific pricing (use spec_json vendor prices, not database averages)
4. Batt/Wood/Plywood scope needs to use parapet cavity dimensions, not expansion_joint fallback
5. Logistics items (delivery, disposal, rental) need separate estimation path
