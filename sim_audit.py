"""
Simulation of calculate_detail_takeoff() for The Ampersand 2026 project.
Tests two scenarios: default parapet_height_ft=2.0 and realistic 1.0 ft.
"""
import math

area = 4438.26
parapet_lf = 328.5
waste = 1.10

prices = {
    "Base_Membrane": 127.25, "Cap_Membrane": 150.0, "Drainage_Board": 410.53,
    "XPS_Insulation": 43.70, "Gravel_Ballast": 0.75, "Filter_Fabric": 0.25,
    "Flashing_General": 75.0, "Sealant_General": 29.86, "SBS_2Ply_Modified_Bitumen": 7.0,
    "Batt_Insulation": 83.99, "Roof_Drain": 325.0, "Wood_Blocking_Lumber": 16.59,
    "Coated_Metal_Sheet": 583.11, "Plywood_Sheathing": 48.74,
    "Polyisocyanurate_ISO_Insulation": 43.62, "DensDeck_Coverboard": 33.52,
    "Vapour_Barrier_Membrane": 173.66, "Clips": 10.19, "Screws": 39.96,
    "Fasteners": 350.0, "Drip_Edge": 6.85, "Gypsum_Fiber_Coverboard": 29.62,
    "Fleece_Reinforcement_Fabric": 150.0,
}

def run_simulation(parapet_h, label):
    strip_sqft = parapet_lf * parapet_h

    results = []
    total = 0.0

    def add(name, qty_basis, scope, per_unit, price, note=""):
        nonlocal total
        if scope == "discrete":
            units = math.ceil(qty_basis)
        elif scope == "linear":
            units = math.ceil(qty_basis * waste / per_unit)
        else:
            units = math.ceil(qty_basis * waste / per_unit)
        cost = units * price
        total += cost
        results.append((name, qty_basis, units, price, cost, note))

    # Detail 2: drain, scope_quantity=4
    add("Roof_Drain", 4, "discrete", 1, 325.0, "drain, count=4")

    # Detail 4: field_assembly -> total_roof_area_sqft
    add("Base_Membrane", area, "area", 100, 127.25, "field_assembly, full area")
    add("Cap_Membrane", area, "area", 86, 150.0, "field_assembly, full area")
    add("Drainage_Board", area, "area", 300, 410.53, "field_assembly, full area")
    add("XPS_Insulation", area, "area", 16, 43.70, "field_assembly, full area")
    add("Filter_Fabric", area, "area", 1, 0.25, "field_assembly, full area")
    add("Gravel_Ballast", area, "area", 1, 0.75, "field_assembly, full area")

    # Detail 5: parapet -> parapet_length_lf
    add("Sealant_General", parapet_lf, "linear", 20, 29.86, "parapet, LF=328.5")
    add("Vapour_Barrier_Membrane", strip_sqft, "area", 200, 173.66, f"parapet, strip={strip_sqft}")
    add("Coated_Metal_Sheet", strip_sqft, "area", 40, 583.11, f"parapet, strip={strip_sqft}")
    add("SBS_2Ply_Modified_Bitumen", strip_sqft, "area", 1, 7.0, f"parapet, strip={strip_sqft}")
    add("Clips", 1, "discrete", 1, 10.19, "parapet, discrete")

    # Detail 6: expansion_joint -> perimeter_lf * 0.25 = 82.125
    exp_base = 328.5 * 0.25
    add("Wood_Blocking_Lumber", parapet_lf, "linear", 8, 16.59, "registry -> parapet_lf")
    add("Polyiso_ISO", exp_base * 0.5, "area", 16, 43.62, "exp_joint, 82.1*0.5=41.1")
    add("DensDeck_Coverboard", exp_base * 0.5, "area", 32, 33.52, "exp_joint, 41.1 sqft")
    add("Plywood_Sheathing", exp_base * 0.5, "area", 32, 48.74, "exp_joint fallback, 41.1")
    add("Flashing_General", parapet_lf, "linear", 10, 75.0, "registry -> parapet_lf")
    add("Batt_Insulation", exp_base * 0.5, "area", 40, 83.99, "exp_joint fallback, 41.1")

    # Detail 7: opening_cover -> mechanical_unit_count=3
    add("Screws", 3, "area", 100, 39.96, "opening_cover, count=3")

    # Detail 9: sleeper_curb -> sleeper_curb_count=3
    add("Fasteners", 3, "area", 100, 350.0, "sleeper_curb, count=3")

    # Detail 10: mechanical_curb -> mechanical_unit_count=3
    add("Gypsum_Fiber_Coverboard", 3, "area", 32, 29.62, "mech_curb, count=3")

    # Detail 11: mechanical_curb -> Fleece
    add("Fleece_Reinforcement", 3, "area", 300, 150.0, "mech_curb, count=3")

    # Detail 13: curtain_wall -> parapet_length_lf
    add("Drip_Edge", parapet_lf, "linear", 10, 6.85, "curtain_wall, LF=328.5")

    print()
    print("=" * 95)
    print(f"  SCENARIO: {label}  (parapet_height_ft = {parapet_h})")
    print("=" * 95)
    print()
    print(f"  {'Material':<35} {'Qty Basis':>10} {'Units':>6} {'Price':>10} {'Cost':>12}  Notes")
    print("  " + "-" * 93)
    for name, qb, units, price, cost, note in results:
        print(f"  {name:<35} {qb:>10.1f} {units:>6} ${price:>9.2f} ${cost:>11,.2f}  {note}")
    print("  " + "-" * 93)
    print(f"  {'TOTAL':<35} {'':>10} {'':>6} {'':>10} ${total:>11,.2f}")
    print()

    diff_full = total - 55543.33
    pct_full = (total / 55543.33 - 1) * 100
    print(f"  Excel reference:  $55,543.33")
    print(f"  Code total:       ${total:>11,.2f}")
    print(f"  Difference:       ${diff_full:>+11,.2f} ({pct_full:>+.1f}%)")
    in_range = 52766 <= total <= 58320
    print(f"  Within 5%:        {'YES' if in_range else 'NO'} (target $52,766 - $58,320)")
    return total, results

t1, r1 = run_simulation(2.0, "DEFAULT (AI path, no user height input)")
t2, r2 = run_simulation(1.0, "USER-PROVIDED (actual Excel avg parapet height ~12in)")

print()
print("=" * 95)
print("  ANALYSIS OF ERROR CANCELLATION (parapet_h=1.0 scenario)")
print("=" * 95)
print()

# Build cost dict for h=1.0
rc = {r[0]: r[4] for r in r2}

# Show overestimates vs underestimates
overest = 0.0
underest = 0.0

excel_map = {
    "Roof_Drain": 975.0,
    "Base_Membrane": 4199.25,
    "Cap_Membrane": 7448.0,
    "Drainage_Board": 6964.75,
    "XPS_Insulation": 0,
    "Filter_Fabric": 1076.0,
    "Gravel_Ballast": 0,
    "Sealant_General": 198.0,
    "Vapour_Barrier_Membrane": 0,
    "Coated_Metal_Sheet": 0,
    "SBS_2Ply_Modified_Bitumen": 0,
    "Clips": 0,
    "Flashing_General": 3695.0,
    "Wood_Blocking_Lumber": 1000.0,
    "Batt_Insulation": 4535.46,
    "Plywood_Sheathing": 440.0,
    "Screws": 0,
    "Fasteners": 0,
    "Drip_Edge": 0,
}

# Add missing Excel items
excel_only = {
    "Tapered_Insulation": 8376.0,
    "Soprasmart_Board": 6816.0,
    "Duotack_Adhesive": 4060.0,
    "Elastocol": 750.30,
    "Sopralap": 546.0,
    "Delivery_Disposal_Rental": 4278.57,
    "Scuppers": 185.0,
}

print(f"  {'Material':<35} {'Code':>12} {'Excel':>12} {'Diff':>12} {'Status':<8}")
print("  " + "-" * 85)

for name, qb, units, price, cost, note in r2:
    exc = excel_map.get(name, 0)
    diff = cost - exc
    if diff > 0:
        overest += diff
        status = "OVER" if diff > 100 else "~ok"
    elif diff < -100:
        underest += abs(diff)
        status = "UNDER"
    else:
        status = "~ok"
    print(f"  {name:<35} ${cost:>11,.2f} ${exc:>11,.2f} ${diff:>+11,.2f} {status:<8}")

print()
print("  Materials in Excel but NOT in code:")
for name, exc in excel_only.items():
    underest += exc
    print(f"  {name:<35} ${'0.00':>11} ${exc:>11,.2f} ${-exc:>+11,.2f} MISSING")

print()
print(f"  Total overestimation:    ${overest:>+11,.2f}")
print(f"  Total underestimation:   ${-underest:>+11,.2f}")
print(f"  Net error:               ${overest - underest:>+11,.2f}")
print(f"  (vs Excel diff of:       ${t2 - 55543.33:>+11,.2f})")
