"""
Test: compare estimator output vs 333 5th Ave Excel ground truth.

Excel values (from 231178__333 5TH AVE RJC.xlsm):
  Area:        1,370 sqft
  Perimeter:   215 LF, 8" height, Interior Wall type
  Strip sqft:  250.83 (14" girth x 215 LF)
  Drains:      6
  Tapered ISO: 95 sqft
  Corners:     10

Key materials (SBS):
  Vapour Barrier:       10 roll  @ $82.45  = $824.50
  ISO Glass 2in:        95 sheet @ $20.50  = $1,947.50
  Tapered Insulation:   95 sqft  @ $25.00  = $2,375.00
  Densdeck Primed 1/2:  48 sheet @ $34.20  = $1,641.60
  Base Sheet Field:     16 roll  @ $127.25 = $2,036.00
  Cap Sheet Field+Wall: 24 roll  @ $105.80 = $2,539.20  (field & wall combined)
  Base Sheet Wall:       3 roll  @ $134.95 = $404.85  (Sopraply Stick)
  Elastocol 500 field:   3 pail  @ $125.05 = $375.15
  Elastocol Stick wall:  1 pail  @ $160.00 = $160.00
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from backend.roof_estimator import RoofMeasurements, calculate_takeoff

# --- Ground-truth values from Excel ---
EXCEL = {
    "Vapour Barrier (Elastophene SP 2.2)":        {"qty": 10,  "unit": "roll",  "unit_price": 82.45,  "total": 824.50},
    "ISO Glass 2in insulation":                    {"qty": 95,  "unit": "sheet", "unit_price": 20.50,  "total": 1947.50},
    "Tapered ISO":                                 {"qty": 95,  "unit": "sqft",  "unit_price": 25.00,  "total": 2375.00},
    "Densdeck Primed 1/2in":                       {"qty": 48,  "unit": "sheet", "unit_price": 34.20,  "total": 1641.60},
    "Sopraply Base 520 (field)":                   {"qty": 16,  "unit": "roll",  "unit_price": 127.25, "total": 2036.00},
    "Sopraply Traffic Cap (field+wall combined)":  {"qty": 24,  "unit": "roll",  "unit_price": 105.80, "total": 2539.20},
    "Sopraply Stick (base wall)":                  {"qty":  3,  "unit": "roll",  "unit_price": 134.95, "total":  404.85},
    "Elastocol 500 field":                         {"qty":  3,  "unit": "pail",  "unit_price": 125.05, "total":  375.15},
    "Elastocol Stick wall":                        {"qty":  1,  "unit": "pail",  "unit_price": 160.00, "total":  160.00},
}

# Build measurements matching the Excel exactly
m = RoofMeasurements(
    total_roof_area_sqft=1370.0,
    perimeter_lf=215.0,
    parapet_length_lf=215.0,
    parapet_height_ft=8/12,        # 8 inches = 0.667 ft
    roof_drain_count=6,
    tapered_area_sqft=95.0,        # explicitly set from Excel
)

result = calculate_takeoff(m)

# Print app output
print("=" * 72)
print("  APP ESTIMATE vs EXCEL — 333 5th Ave (SBS, 1370 sqft)")
print("=" * 72)

print(f"\n{'Material':<45} {'App Qty':>8} {'App $':>10} {'Excel Qty':>10} {'Excel $':>10} {'D%':>7}")
print("-" * 92)

# Collect app materials by name
app_materials = {item["name"]: item for item in result.get("area_materials", [])}

# Map app names → excel names for comparison
COMPARE = [
    ("Vapour Barrier (Sopravap'r WG 45\")",         "Vapour Barrier (Elastophene SP 2.2)"),
    ("ISO Insulation 2.5\" (Sopra-ISO)",             "ISO Glass 2in insulation"),
    ("Tapered ISO Insulation (drainage slope)",       "Tapered ISO"),
    ("Densdeck Coverboard 1/2\"",                    "Densdeck Primed 1/2in"),
    ("SBS Base Sheet - Field (Sopraply Base 520)",   "Sopraply Base 520 (field)"),
    ("SBS Cap Sheet - Field (Sopraply Traffic Cap)", "Sopraply Traffic Cap (field+wall combined)"),
    ("SBS Base Sheet - Wall (Sopraply Base 520)",    "Sopraply Stick (base wall)"),
    ("Elastocol 500 (field primer)",                 "Elastocol 500 field"),
]

for app_name, excel_name in COMPARE:
    app = app_materials.get(app_name)
    excel = EXCEL.get(excel_name)
    if app and excel:
        app_total = app["qty"] * app["unit_price"]
        delta = (app_total - excel["total"]) / excel["total"] * 100 if excel["total"] else 0
        flag = " <<<" if abs(delta) > 20 else ""
        print(f"{app_name:<45} {app['qty']:>8.1f} {app_total:>10.2f} {excel['qty']:>10}  {excel['total']:>9.2f} {delta:>+6.1f}%{flag}")
    elif app:
        app_total = app["qty"] * app["unit_price"]
        print(f"{app_name:<45} {app['qty']:>8.1f} {app_total:>10.2f} {'N/A':>10}  {'N/A':>9}  {'N/A':>6}")
    elif excel:
        print(f"{'[MISSING] ' + app_name:<45} {'--':>8} {'--':>10} {excel['qty']:>10}  {excel['total']:>9.2f}  {'N/A':>6}")

# Show all app materials not in compare list
print("\n--- Other app materials (no Excel counterpart in test) ---")
compared_names = {n for n, _ in COMPARE}
for name, item in app_materials.items():
    if name not in compared_names:
        total = item["qty"] * item["unit_price"]
        print(f"  {name:<45} qty={item['qty']:.1f}  total=${total:,.2f}")

# Totals
app_area_total = sum(item["qty"] * item["unit_price"] for item in result.get("area_materials", []))
excel_area_total = sum(v["total"] for v in EXCEL.values())
delta_total = (app_area_total - excel_area_total) / excel_area_total * 100

print("\n" + "=" * 72)
print(f"  App area materials total:   ${app_area_total:>10,.2f}")
print(f"  Excel area materials total: ${excel_area_total:>10,.2f}")
print(f"  Delta:                        {delta_total:>+.1f}%")
print("=" * 72)
