import sys
sys.path.insert(0, '.')
from backend.roof_estimator import RoofMeasurements, calculate_takeoff

m = RoofMeasurements(
    total_roof_area_sqft=1370.0,
    perimeter_lf=215.0,
    parapet_length_lf=215.0,
    parapet_height_ft=8/12,
    roof_drain_count=6,
    tapered_area_sqft=95.0,
)
r = calculate_takeoff(m)

# --- App outputs ---
area = {i['name']: i for i in r['area_materials']}
cons = {i['name']: i for i in r.get('consumables', [])}

def ac(d): return d['quantity'] * d['unit_price']

print()
print("=== AREA MATERIALS ===")
print(f"{'Material':<50} {'AppQty':>7} {'App$':>9}  {'ExcelQty':>9} {'Excel$':>9}  {'D%':>7}  Notes")
print("-" * 115)

rows = [
    ("Elastocol 500 (field primer)",
      area.get("Elastocol 500 (field primer)"), 3, 375.15,
      "double-counted in consumables too"),
    ("Vapour Barrier (Sopravap'r WG 45\")",
      area.get("Vapour Barrier (Sopravap'r WG 45\")"), 10, 824.50,
      "wrong product; Excel=Elastophene SP 2.2 @ $82.45/roll"),
    ("ISO Insulation 2.5\" (Sopra-ISO)",
      area.get("ISO Insulation 2.5\" (Sopra-ISO)"), 95, 1947.50,
      "qty OK; price diff app=$25.60 vs Excel=$20.50"),
    ("Tapered ISO Insulation (drainage slope)",
      area.get("Tapered ISO Insulation (drainage slope)"), 95, 2375.00,
      "qty near; price diff app=$3.10/sqft vs Excel=$25/sqft"),
    ("Densdeck Coverboard 1/2\"",
      area.get("Densdeck Coverboard 1/2\""), 48, 1641.60,
      "EXACT MATCH"),
    ("SBS Base Sheet - Field (Sopraply Base 520)",
      area.get("SBS Base Sheet - Field (Sopraply Base 520)"), 16, 2036.00,
      "EXACT MATCH"),
    ("SBS Base Sheet - Wall (Sopraply Base 520)",
      area.get("SBS Base Sheet - Wall (Sopraply Base 520)"), 3, 404.85,
      "qty OK; app=$127.25 vs Excel=Stick $134.95"),
    ("SBS Cap Sheet - Field",
      area.get("SBS Cap Sheet - Field (Sopraply Traffic Cap)"), None, None,
      "Excel combines field+wall: 24 rolls @ $105.80 = $2,539.20"),
    ("SBS Cap Sheet - Wall",
      area.get("SBS Cap Sheet - Wall (Sopraply Traffic Cap)"), None, None,
      "see above"),
]

for name, app_item, excel_qty, excel_cost, note in rows:
    if app_item:
        app_qty = app_item['quantity']
        app_cost = ac(app_item)
    else:
        app_qty = 0
        app_cost = 0.0
    if excel_cost:
        d = (app_cost - excel_cost) / excel_cost * 100
        flag = " <<<" if abs(d) > 20 else ""
        print(f"  {name:<48} {app_qty:>7}  {app_cost:>9,.2f}  {excel_qty:>9}  {excel_cost:>9,.2f}  {d:>+6.1f}%{flag}")
    else:
        print(f"  {name:<48} {app_qty:>7}  {app_cost:>9,.2f}  {'(combined)':>9}  {'':>9}")
    print(f"    -> {note}")

# Cap combo
cap_f = area.get("SBS Cap Sheet - Field (Sopraply Traffic Cap)")
cap_w = area.get("SBS Cap Sheet - Wall (Sopraply Traffic Cap)")
if cap_f and cap_w:
    app_cap_total = ac(cap_f) + ac(cap_w)
    excel_cap_total = 2539.20
    d = (app_cap_total - excel_cap_total) / excel_cap_total * 100
    print(f"  {'Cap Sheet combined (field+wall)':<48} {cap_f['quantity']+cap_w['quantity']:>7}  {app_cap_total:>9,.2f}  {'24':>9}  {excel_cap_total:>9,.2f}  {d:>+6.1f}%")

print()
print("=== CONSUMABLES (relevant) ===")
c_rows = [
    "Mastic (Sopramastic)",
    "Elastocol Adhesive - Field",
    "Elastocol Adhesive - Wall (parapet strips)",
    "Sealant (Mulco Supra)",
    "Duotack Foamable Adhesive (insulation bonding)",
]
for n in c_rows:
    item = cons.get(n)
    if item:
        print(f"  {n:<50} qty={item['quantity']:>4}  ${ac(item):>9,.2f}")

print()
print("=== TOTALS ===")
app_area_total = sum(ac(i) for i in r['area_materials'])
app_cons_total = sum(ac(i) for i in r.get('consumables', []))
excel_total = 375.15 + 824.50 + 1947.50 + 2375.00 + 1641.60 + 2036.00 + 404.85 + 2539.20
print(f"  App area materials:    ${app_area_total:>10,.2f}")
print(f"  App consumables:       ${app_cons_total:>10,.2f}")
print(f"  App combined:          ${app_area_total+app_cons_total:>10,.2f}")
print(f"  Excel key materials:   ${excel_total:>10,.2f}")
d = (app_area_total - excel_total) / excel_total * 100
print(f"  Area delta vs Excel:   ${app_area_total-excel_total:>+10,.2f}  ({d:+.1f}%)")
