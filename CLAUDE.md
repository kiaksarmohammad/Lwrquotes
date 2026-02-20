# Project Instructions

## Code Changes Policy
- **Backend (Python):** Do NOT directly edit or write code. Instead, provide detailed explanations of what needs to be changed and why, so the developer can implement it themselves.
- **Frontend (HTML/CSS/JS/Jinja templates):** You may directly edit and write frontend code without detailed explanations.
- When identifying bugs or issues, explain the root cause, the fix, and where exactly it should be applied.
- When explaining backend code changes, describe the logic, which existing variables/functions to use, and the reasoning — do NOT write out the code. The developer will implement it.

---

## Layer Cost Loop — Implementation Guide

### Location
Inside `calculate_ai_takeoff()` in `backend/roof_estimator.py`, between the `detail_result` dict initialization and the sanity cap check. Currently there's a `for layer in detail.get("layers", []):` loop with only Step 1 implemented.

### What already exists (Step 1)
The loop iterates over each layer dict from the AI output. Each layer has a `pricing_key` string (e.g. `"Base_Membrane"`). You extract it, skip `"custom"`/`"CUSTOM"` keys, and look up the registry entry via `material_registry.get(pkey)`. This part is done.

### Step 2 — Decide the quantity basis

**Goal:** Determine "how much" of this material is needed — a raw number in sqft, linear feet, or count.

**Variables involved:**
- `reg["detail_cost_calculation"]` — pre-resolved at lines 2557-2569. For area-scope materials it holds `m.total_roof_area_sqft`, for linear-scope it holds `m.perimeter_lf`, for discrete-scope it holds the relevant count attribute from `RoofMeasurements` (looked up via `DETAIL_TYPE_MAP`). Can be `None` if unresolved.
- `base_value` — already calculated earlier in the same loop iteration (lines 2587-2626) using the 3-priority system: plan quantities > AI scope_quantity > DETAIL_TYPE_MAP fallback.

**Logic:** If the registry entry exists and its `detail_cost_calculation` is not None, use that. It's the more accurate number because it's scope-aware (area materials use roof area, linear materials use perimeter). If it's None, fall back to `base_value` which is the detail-level measurement.

### Step 3 — Calculate purchasable units using COVERAGE_RATES

**Goal:** Convert the raw quantity basis into a number of purchasable units (rolls, pieces, pails, etc.).

**Variables involved:**
- `COVERAGE_RATES` — dict at line 41 mapping pricing keys to their coverage info. Each entry tells you how much one purchasable unit covers.
- `reg["scope"]` — from the registry, tells you whether the material is `"area"`, `"linear"`, or `"discrete"`.

**Logic — three branches based on what keys exist in the coverage entry:**

1. **If `per_each` key exists** → discrete item (drains, boots, vents). One item = one unit. Just round up the quantity_basis. Example: 4 drains = 4 units.

2. **If `lf_per_unit` key exists AND scope is `"linear"`** → linear material. Divide quantity_basis by `lf_per_unit` and round up. Example: `Cant_Strip_4x4` covers 8 LF/piece; 500 LF ÷ 8 = 63 pieces.

3. **If `sqft_per_unit` key exists** → area material. Divide quantity_basis by `sqft_per_unit` and round up. Example: `Base_Membrane` covers 100 sqft/roll; 10,000 sqft ÷ 100 = 100 rolls.

4. **Else (no matching key)** → fallback, just round up quantity_basis as-is.

**Why check scope for linear:** Some entries like `Plywood_Sheathing` and `Fasteners` have BOTH `sqft_per_unit` and `lf_per_unit`. The scope from the registry disambiguates which coverage rate to use.

**Rounding:** Always round up (`math.ceil`) because you can't buy partial rolls/pieces.

### Step 4 — Price and accumulate

**Goal:** Get the dollar cost for this layer and add it to the detail's running total.

**Functions/variables involved:**
- `_get_price(pkey)` — existing function at line 1231. Pass the pricing key string, it returns a float (the avg_price from the material dictionaries, or 0.0 if not found).
- `detail_result["layers"]` — the list to append each layer's breakdown to (for output/display).
- `detail_result["detail_cost"]` — the running total for this detail, initialized to 0.0.

**Logic:** Multiply `units_needed` by the unit price to get `layer_cost`. Append a dict with all the computed values (pricing_key, material name, scope, quantity_basis, units_needed, unit label from COVERAGE_RATES, unit_price, layer_cost) to `detail_result["layers"]`. Add `layer_cost` to `detail_result["detail_cost"]`.

### After the loop

Round `detail_result["detail_cost"]` to 2 decimal places. This must happen after the layer loop closes but before the sanity cap check that follows.
