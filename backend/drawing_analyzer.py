"""
Drawing Analyzer - Uses Gemini Vision to extract spatial data from
architectural roofing drawings.

Sends PDF drawing pages as images to Google Gemini API to identify:
  1. Detail types and their material layer assemblies (from section/detail views)
  2. Item counts and zones (from plan views)

Output JSON feeds into roof_estimator.py for quantity takeoff calculations.

NOTE: Specification PDF analysis has been removed from this module.
      Use file_extractor.py (deterministic regex engine) for all
      Specification PDF processing.

Usage:
    python drawing_analyzer.py <drawing.pdf> --plan-pages 2,3 --detail-pages 4,5,6
    python drawing_analyzer.py <drawing.pdf> --all-pages

Environment:
    GEMINI_API_KEY  -  Your Google Gemini API key (or use --api-key)
"""

import json
import sys
import os
import io
import time
import re
import logging
import concurrent.futures
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
import pypdfium2 as pdfium
from PIL import Image

from backend.database import PRICING, PRODUCT_KEYWORDS

# Load .env file (GEMINI_API_KEY, etc.)
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "gemini-3.1-pro-preview"
RENDER_SCALE = 2  # 2x = ~144 DPI for drawing pages
MAX_GEMINI_WORKERS = 2  # Limit concurrent Gemini API calls to avoid rate limits


# ---------------------------------------------------------------------------
# PDF page rendering
# ---------------------------------------------------------------------------

def render_pdf_pages(pdf_path: str,
                     pages: list[int] | None = None,
                     scale: int = RENDER_SCALE) -> list[tuple[int, Image.Image]]:
    """
    Render PDF pages to PIL Images.

    Args:
        pdf_path: Path to PDF file.
        pages: 1-indexed page numbers to render. None = all pages.
        scale: Render scale (2.0 = ~144 DPI).

    Returns:
        List of (page_number, PIL.Image) tuples.
    """
    pdf_path = os.path.normpath(pdf_path)
    doc = pdfium.PdfDocument(pdf_path)
    total = len(doc)
    indices = [p - 1 for p in pages] if pages else list(range(total))

    results = []
    for idx in indices:
        if idx < 0 or idx >= total:
            sys.stderr.write(f"  WARNING: Page {idx + 1} out of range (PDF has {total} pages), skipping.\n")
            continue
        page = doc[idx]
        bitmap = page.render(scale=scale)
        pil_img = bitmap.to_pil()
        results.append((idx + 1, pil_img))

    doc.close()
    return results


def _image_to_part(img: Image.Image) -> types.Part:
    """Convert a PIL Image to a Gemini Part."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png")


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

def _pricing_keys_list() -> str:
    """Format available pricing keys for the prompt."""
    lines = []
    for key, val in PRICING.items():
        if isinstance(val, dict):
            name = val.get("canonical_name", key)
            unit = val.get("unit", "?")
            lines.append(f"  {key}  ({name}, per {unit})")
        else:
            lines.append(f"  {key}")
    return "\n".join(lines)


def _product_names_list() -> str:
    """Format known product names for context."""
    names = []
    for cat, patterns in PRODUCT_KEYWORDS.items():
        for _, name in patterns.items():
            names.append(f"  [{cat}] {name}")
    return "\n".join(names)


MEASUREMENT_PROMPT_BASE = """You are a roofing quantity surveyor analyzing a roof plan view drawing.

Follow these steps in order:

STEP 1 — FIND THE DRAWING SCALE (PRIMARY SOURCE):
   - Look for a printed scale notation such as "1/8\" = 1'-0\"", "Scale: 1:100",
     "1:200", or a graphical scale bar with labeled lengths.
   - Record exactly what it says and where you found it.
   - If a graphical scale bar is present, use the labeled segment (e.g. "50 ft")
     to establish the pixel-to-foot ratio.
   - If the scale is metric (e.g. 1:100 with mm dimensions), convert all measurements
     to feet before reporting (1 ft = 304.8 mm).
   - METRIC REPRESENTATIVE FRACTION SCALES (e.g. 1:70, 1:100, 1:200): These mean
     1 unit on paper = N units in reality. Use dimension annotations (in mm) directly:
     dimension_ft = dimension_mm / 304.8. Do NOT scale from pixels unless no annotations
     exist — pixel-based scaling with metric RFs is error-prone.
   - SANITY CHECK: A typical small commercial roof is 500–5,000 sqft. If your calculated
     area exceeds 5,000 sqft for what appears to be a small building, recheck the scale
     factor before reporting.

STEP 2 — READ DIMENSION ANNOTATIONS ON THE DRAWING:
   - Scan for all dimension lines (arrows with numbers).
   - Identify any that represent the OVERALL building width and depth end-to-end.
   - Note whether dimensions are in feet-inches or millimetres.
   - Partial/internal dimensions (e.g. bay spacings, room widths) do NOT count as
     overall building dimensions unless they clearly sum to the full building span.
   - If you cannot determine overall width AND overall depth from annotations alone,
     record annotated_width_ft and annotated_depth_ft as 0 and proceed to Step 3b.

STEP 3 — CALCULATE AREA AND PERIMETER:
   - If Step 2 gave reliable overall annotated dimensions, use them directly.
   - Otherwise see Step 3b (reference calibration) below.
   - For L-shapes or irregular outlines, break into rectangles and sum.
   - MULTI-SECTION ROOFS: If the roof has two or more disconnected or clearly separate
     sections, measure each as its own rectangle (length × width) and SUM the areas.
     Do NOT use a single bounding box across all sections — this overcounts significantly.
     Example: two sections (90ft × 13ft) + (40ft × 5ft) = 1,170 + 200 = 1,370 sqft,
     NOT 90ft × 18ft = 1,620 sqft.
   - Total Roof Area (sqft): flat plan-view footprint of the roof.
   - Perimeter (LF): total length of the roof edge.
   - Parapet Length (LF): edges with a parapet wall (vs. open edges or gutters).
{reference_section}
STEP 4 — CONFIDENCE:
   Rate high/medium/low based on scale legibility and dimension annotation clarity.
   Use "medium" whenever you relied on reference calibration (Step 3b Case B).

Return ONLY valid JSON (no markdown, no explanation):
{{
  "scale": "1/8\\" = 1'-0\\"",
  "scale_source": "title block bottom right",
  "annotated_width_ft": 0.0,
  "annotated_depth_ft": 0.0,
  "reference_measurement_used": false,
  "reference_discrepancy_pct": null,
  "total_roof_area_sqft": 0.0,
  "perimeter_lf": 0.0,
  "parapet_length_lf": 0.0,
  "confidence": "high",
  "notes": "Scale found in title block. Annotated dims: 66'-0\\" x 67'-6\\"."
}}"""

REFERENCE_SECTION_WITH_DATA = """
STEP 3b — REFERENCE CALIBRATION:
   Google Maps data provides these building dimensions (approximate bounding box):
     East-West:  {width_ft} ft
     North-South: {height_ft} ft

   CASE A — Overall annotated dimensions were found in Step 2:
   - Compare your drawing-based width and depth against the reference above.
   - A discrepancy under 20% is acceptable; set reference_measurement_used: true
     and record the percentage difference in reference_discrepancy_pct.
   - If discrepancy exceeds 20%, keep your drawing-based answer, note it in "notes",
     and set confidence to "medium".

   CASE B — Overall building dimensions could NOT be determined from annotations:
   - You MUST use the reference dimensions to calibrate the drawing. Do not give up.
   - Identify which axis is longer: East-West ({width_ft} ft) or North-South ({height_ft} ft).
   - Locate the corresponding wall span in the plan view image (the longest horizontal
     edge for E-W, or longest vertical edge for N-S).
   - Measure the pixel length of that wall edge in the image.
   - Compute: scale_ratio = reference_ft / pixel_length  (ft per pixel).
   - Use this scale_ratio to measure ALL other edges of the building outline.
   - Sum those edges to get perimeter_lf and calculate total_roof_area_sqft.
   - Set reference_measurement_used: true, confidence: "medium", and describe
     the wall you matched and the computed ratio in "notes".
   - If only a partial plan view is shown (e.g. one wing), apply the same ratio
     to the visible portion and note it is partial in "notes".
"""

REFERENCE_SECTION_NO_DATA = """
STEP 3b — No reference data available:
   Rely entirely on the drawing scale (Step 1) and any annotations (Step 2).
   If neither overall dimensions nor a usable scale can be found, return
   total_roof_area_sqft: 0, perimeter_lf: 0, confidence: "low", and explain
   in "notes" what was missing.
"""


def _build_measurement_prompt(reference_measurement: dict | None = None) -> str:
    """Build the measurement prompt, injecting reference data if provided."""
    if reference_measurement:
        ref_section = REFERENCE_SECTION_WITH_DATA.format(
            width_ft=reference_measurement.get("width_ft", reference_measurement.get("value", 0)),
            height_ft=reference_measurement.get("height_ft", reference_measurement.get("value", 0)),
        )
    else:
        ref_section = REFERENCE_SECTION_NO_DATA

    return MEASUREMENT_PROMPT_BASE.format(reference_section=ref_section)


PARAPET_HEIGHT_PROMPT = """You are a roofing quantity surveyor analyzing a detail/section drawing.

Your goal is to find the Parapet Height.

1. Look for a cross-section detail of a parapet wall.
2. Read the vertical dimension from the roof deck level to the top of the coping cap.
3. If multiple parapet details exist, pick the most common or tallest one.
4. If no parapet detail is found, return 0.

Return ONLY valid JSON (no markdown, no explanation) in this format:
{
  "parapet_height_ft": 0.0,
  "confidence": "high",
  "notes": "Found detail 3/A5.0 showing 2'-6\" height."
}"""


DETAIL_PROMPT = """You are a roofing quantity-takeoff specialist analyzing architectural detail/section drawings.

For EACH detail or section shown on this drawing page, identify:
1. The detail name and reference number (e.g. "Detail 1", "Section A-A")
2. The EXACT detail reference ID as printed on the drawing sheet. This is typically
   shown as a number/sheet format like "3/R3.1" or "1/R3.2" in a circle or label
   near the detail. Extract ONLY the reference (e.g. "3/R3.1"), not the full name.
   This ID is used to match this detail to unit labels on the plan view.
3. The detail type - classify as one of:
   parapet, drain, mechanical_curb, sleeper_curb, penetration_gas,
   penetration_electrical, penetration_plumbing, vent_hood, scupper,
   expansion_joint, curtain_wall, field_assembly, pipe_support, opening_cover,
   slope_plan
4. All materials/products shown, listed from BOTTOM to TOP (or inside to outside)
5. For each material, map it to the closest pricing_key from our database
6. Whether this detail is measured in: sqft, linear_ft, or each
7. SCOPE & QUANTITY: Read any dimensions, annotations, or notes on the detail to determine:
   - The physical size of the detail (e.g., opening dimensions, curb size, etc.)
   - Any "typical of N" or "N locations" callouts
   - For openings/infills: calculate the area from shown dimensions (e.g., 4'x6' = 24 sqft)
   - For linear details: note the length if dimensioned
   - For penetrations/curbs: note the size (e.g., "6 inch pipe", "48x48 curb")
   If no quantity can be determined from the drawing, set scope_quantity to null.
8. MATERIAL DIMENSIONS: For each material in a detail, estimate its cross-sectional width, height, or girth (in inches) if it is shown or can be visually estimated from the scale. For example, a parapet plywood face might be 24 inches tall, or a flashing strip might have an 18-inch girth. If unmeasurable, return null.

IMPORTANT classification rules:
- "field_assembly" is ONLY for the main roof membrane system cross-section detail (layers from deck to top of membrane)
- "slope_plan" is for roof slope or drainage plan views embedded on a detail sheet (e.g. "Roof Slope Plan", "Drainage Plan", tapered insulation layout plans). These are NOT cross-sections and should NOT be classified as field_assembly.
- Slab openings, infills, patches, and localized repairs are NOT field_assembly - classify as "opening_cover"
- Structural repairs (concrete patching, grouting) are NOT field_assembly - classify as "opening_cover"
- Each penetration, curb, or opening is measured as "each" with a small count
- DEMOLITION / PLANTER DETAILS: Any detail titled "DEMOLITION", "DEMO", "PLANTER WALL", "PLANTER WALL DEMO", or any detail that describes removal/stripping of existing materials (not new installation) must be classified as "opening_cover" — do NOT classify it as "field_assembly". Planter wall and green roof teardown details containing XPS insulation, drainage boards, and filter fabric are existing assembly removals, NOT the new roof field assembly.
- REINSTALL / EXISTING ITEMS: For each material layer, if the drawing annotation says "temporarily remove and reinstate", "existing to remain", "remove and dispose", "salvage and reinstall", or similar, you MUST copy that exact phrase into the layer's "notes" field. These are NOT new material purchases — they are existing items being handled during construction and must be flagged so they can be excluded from material costing.

Our pricing database keys:
{pricing_keys}

Known product names in our system:
{product_names}

Return ONLY valid JSON (no markdown, no explanation) in this format:
{{
  "drawing_ref": "the drawing sheet number shown on the page",
  "details": [
    {{
      "detail_name": "Detail 1 - Typical Parapet",
      "detail_ref_id": "1/R3.0",
      "detail_type": "parapet",
      "measurement_type": "linear_ft",
      "scope_quantity": 200,
      "scope_unit": "linear_ft",
      "scope_notes": "Noted as typical parapet, dimension shows 200 LF total",
      "layers": [
        {{
          "position": 1,
          "material": "exact material name from drawing",
          "pricing_key": "closest match from our database",
          "dimension_in": 24.0,
          "notes": "thickness, size, or spec info visible"
        }}
      ]
    }}
  ]
}}"""


PLAN_PROMPT = """You are a roofing quantity-takeoff specialist analyzing a roof plan view drawing.

Count and identify everything visible on this plan view:

1. ITEM COUNTS - count each type you can see:
   - roof_drains: circular drain symbols — includes circles with cross-hairs, concentric circles, circles labelled "D", "RD", "FD", or drain grate symbols. Scan the ENTIRE plan systematically left-to-right, top-to-bottom. Count ALL drain symbols including any partially obscured by dimension lines or annotations. Double-check your total before reporting.
   - scuppers: rectangular openings in parapet/wall edges
   - mechanical_units: large rooftop equipment (RTUs, AHUs)
   - sleeper_curbs: linear support structures (often shown as parallel lines)
   - vent_hoods: small rectangular/circular vents
   - gas_penetrations: gas pipe penetrations (may be labeled)
   - electrical_penetrations: electrical conduit penetrations
   - plumbing_vents: plumbing vent pipes

2. ZONES - identify any distinct roof zones with different assemblies

3. DIMENSIONS - note any dimensions, areas, or the drawing scale

4. PARAPET - identify which edges have parapets vs other edge conditions

5. DETAIL REFERENCES - note which detail drawings are referenced (e.g., "see Detail 3/R3.1")

6. DETAIL QUANTITIES - For each detail reference visible on the plan, determine:
   - How many times/locations it applies
   - The total measurement (LF of parapet it applies to, sqft of area, count of openings, etc.)
   - Use the drawing scale and visible dimensions to calculate actual quantities
   This is CRITICAL for accurate pricing - each detail needs a real-world quantity.

7. UNIT LABELS & LEGEND — This is CRITICAL for accurate per-unit costing:
   a) Find the LEGEND on the plan page. It maps letter labels to detail references.
      Example legend entries:
        "P  — PIPE PENETRATION, SEE DETAIL 1/R3.2"
        "HS — HOT STACK PENETRATION, SEE DETAIL 3/R3.1"
        "D  — TWIN DUCT PENETRATION, SEE DETAIL 4/R3.1"
        "V  — VENT PENETRATION, SEE 1/R3.1"
        "M  — MECHANICAL VENT PENETRATION, SEE DETAIL 2/R3.1"
   b) Scan the plan for EVERY labelled unit symbol. These are typically single or
      multi-letter codes placed next to or inside units on the plan (e.g., P, HS, D,
      V, M, PW, GG, JJ, HH). They may appear circled, boxed, or as plain text.
   c) For EACH labelled unit found:
      - Count how many instances of that label appear on the plan
      - Measure each instance's physical footprint using the drawing scale:
        * Rectangular units: measure width_ft and height_ft → perimeter_lf = 2*(W+H)
        * Circular units: measure diameter_ft → perimeter_lf = π * diameter
        * Irregular shapes: estimate the outer perimeter in LF
      - Note the location of each instance on the plan (e.g., "near grid line 4")
   d) Use the legend to determine which detail drawing page each label refers to.
      The detail_ref format should be "Detail N/RX.X" (e.g., "Detail 3/R3.1").

Return ONLY valid JSON (no markdown, no explanation) in this format:
{{
  "drawing_ref": "the drawing sheet number",
  "scale": "the drawing scale if shown",
  "counts": {{
    "roof_drains": 0,
    "scuppers": 0,
    "mechanical_units": 0,
    "sleeper_curbs": 0,
    "vent_hoods": 0,
    "gas_penetrations": 0,
    "electrical_penetrations": 0,
    "plumbing_vents": 0
  }},
  "detail_quantities": {{
    "Detail 1/R3.0": {{"count": 1, "measurement": 636, "unit": "linear_ft", "notes": "applies to full parapet perimeter"}},
    "Detail 5/R3.1": {{"count": 3, "measurement": 72, "unit": "sqft", "notes": "3 slab openings, each ~24 sqft"}}
  }},
  "unit_labels": [
    {{
      "label": "HS",
      "description": "Hot Stack Penetration",
      "detail_ref": "Detail 3/R3.1",
      "instances": [
        {{
          "instance_id": "HS-1",
          "location": "center-left area near grid line 4",
          "shape": "rectangular",
          "width_ft": 2.5,
          "height_ft": 3.0,
          "perimeter_lf": 11.0,
          "area_sqft": 7.5
        }},
        {{
          "instance_id": "HS-2",
          "location": "center-right area near grid line 5",
          "shape": "rectangular",
          "width_ft": 2.5,
          "height_ft": 3.0,
          "perimeter_lf": 11.0,
          "area_sqft": 7.5
        }}
      ],
      "total_count": 2,
      "total_perimeter_lf": 22.0,
      "total_area_sqft": 15.0
    }},
    {{
      "label": "P",
      "description": "Pipe Penetration",
      "detail_ref": "Detail 1/R3.2",
      "instances": [
        {{
          "instance_id": "P-1",
          "location": "north side near grid line 6",
          "shape": "circular",
          "width_ft": 0.5,
          "height_ft": 0.5,
          "perimeter_lf": 1.57,
          "area_sqft": 0.2
        }}
      ],
      "total_count": 1,
      "total_perimeter_lf": 1.57,
      "total_area_sqft": 0.2
    }}
  ],
  "zones": [
    {{
      "name": "zone description",
      "assembly_type": "field_assembly or detail type",
      "detail_refs": ["Detail 1/R3.0"],
      "notes": "any relevant observations"
    }}
  ],
  "parapet": {{
    "edges_with_parapet": "describe which edges",
    "other_edges": "describe other edge conditions (curtain wall, etc.)"
  }},
  "dimensions_noted": ["list any dimensions or areas visible"],
  "detail_references": ["list all detail callouts visible on the plan"]
}}"""



# ---------------------------------------------------------------------------
# Gemini API calls
# ---------------------------------------------------------------------------

def _call_gemini(client: genai.Client, model: str, image: Image.Image,
                 prompt: str, retries: int = 3) -> str:
    """Send an image + prompt to Gemini and return the response text."""
    img_part = _image_to_part(image)

    for attempt in range(retries):
        t0 = time.time()
        try:
            logger.info(f"  Gemini API call attempt {attempt + 1}/{retries} (model={model})...")
            response = client.models.generate_content(
                model=model,
                contents=[img_part, prompt],
                config={"temperature": 0, "seed": 42},
            )
            elapsed = time.time() - t0
            logger.info(f"  Gemini API responded in {elapsed:.1f}s ({len(response.text or '')} chars)")
            return response.text or ""
        except Exception as e:
            elapsed = time.time() - t0
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                logger.warning(f"  Gemini API error after {elapsed:.1f}s (attempt {attempt + 1}): {type(e).__name__}: {e}")
                logger.info(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"  Gemini API failed after {retries} attempts: {type(e).__name__}: {e}")
                raise
    raise RuntimeError("Gemini API failed")


def _extract_json(text: str) -> str:
    """Extract JSON from AI response, handling markdown code blocks."""
    if "```json" in text:
        start = text.index("```json") + 7
        closing = text.find("```", start)
        end = closing if closing != -1 else len(text)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        closing = text.find("```", start)
        end = closing if closing != -1 else len(text)
        return text[start:end].strip()
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1:
        return text[first:last + 1]
    return text


def _analyze_single_page(page_num: int, img: Image.Image, client: genai.Client,
                         model: str, prompt: str) -> dict:
    """Helper to analyze a single page in a thread."""
    logger.info(f"Page {page_num}: starting analysis...")
    t0 = time.time()
    raw = ""
    try:
        raw = _call_gemini(client, model, img, prompt)
        json_str = _extract_json(raw)
        data = json.loads(json_str)
        data["source_page"] = page_num
        elapsed = time.time() - t0
        logger.info(f"Page {page_num}: completed successfully in {elapsed:.1f}s")
        return data
    except json.JSONDecodeError as e:
        elapsed = time.time() - t0
        logger.warning(f"Page {page_num}: JSON parse error after {elapsed:.1f}s: {e}")
        logger.debug(f"Page {page_num}: raw response was: {raw[:500]}")
        return {"source_page": page_num, "raw_response": raw, "parse_error": True}
    except Exception as e:
        elapsed = time.time() - t0
        logger.error(f"Page {page_num}: failed after {elapsed:.1f}s: {type(e).__name__}: {e}")
        return {"source_page": page_num, "error": str(e)}


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def analyze_details(pdf_path: str, detail_pages: list[int],
                    client: genai.Client, model: str = DEFAULT_MODEL) -> list[dict]:
    """Analyze detail/section drawing pages to extract material assemblies."""
    images = render_pdf_pages(pdf_path, detail_pages)
    prompt = DETAIL_PROMPT.format(
        pricing_keys=_pricing_keys_list(),
        product_names=_product_names_list(),
    )

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_GEMINI_WORKERS) as executor:
        futures = [
            executor.submit(_analyze_single_page, p, i, client, model, prompt)
            for p, i in images
        ]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    return sorted(results, key=lambda x: x.get("source_page", 0))


def analyze_plan(pdf_path: str, plan_pages: list[int],
                 client: genai.Client, model: str = DEFAULT_MODEL) -> list[dict]:
    """Analyze plan view drawing pages to extract counts and zones."""
    images = render_pdf_pages(pdf_path, plan_pages)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_GEMINI_WORKERS) as executor:
        futures = [
            executor.submit(_analyze_single_page, p, i, client, model, PLAN_PROMPT)
            for p, i in images
        ]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    return sorted(results, key=lambda x: x.get("source_page", 0))



def analyze_measurements(pdf_path: str, plan_pages: list[int],
                         client: genai.Client, model: str = DEFAULT_MODEL,
                         reference_measurement: dict | None = None) -> dict:
    """
    Analyze plan pages to extract roof measurements (Area, Perimeter, Parapet Length).

    Args:
        reference_measurement: Optional dict with keys 'description', 'value', 'unit'
            providing a known dimension for calibration.

    Returns the result from the highest-confidence page.
    """
    logger.info(f"[MEASUREMENTS] Starting analysis of plan pages {plan_pages}...")
    if reference_measurement:
        logger.info(f"[MEASUREMENTS] Reference: {reference_measurement}")
    t0 = time.time()
    images = render_pdf_pages(pdf_path, plan_pages)
    logger.info(f"[MEASUREMENTS] Rendered {len(images)} page(s) in {time.time() - t0:.1f}s")

    # Build the prompt, injecting reference measurement if provided
    prompt = _build_measurement_prompt(reference_measurement)

    candidates = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_GEMINI_WORKERS) as executor:
        futures = [
            executor.submit(_analyze_single_page, p, i, client, model, prompt)
            for p, i in images
        ]
        for future in concurrent.futures.as_completed(futures):
            candidates.append(future.result())

    elapsed = time.time() - t0
    logger.info(f"[MEASUREMENTS] Completed in {elapsed:.1f}s ({len(candidates)} result(s))")
    return _aggregate_measurements(candidates)


def _aggregate_measurements(candidates: list[dict]) -> dict:
    """Select the best measurement result based on confidence."""
    default = {
        "scale": "Unknown",
        "total_roof_area_sqft": 0.0,
        "perimeter_lf": 0.0,
        "parapet_length_lf": 0.0,
        "confidence": "low",
        "notes": "No measurements extracted."
    }

    if not candidates:
        return default

    # Only consider successfully parsed results (no error/parse_error keys)
    successful = [c for c in candidates if not c.get("error") and not c.get("parse_error")]
    if not successful:
        return default

    # Sort by confidence: high > medium > low
    priority = {"high": 3, "medium": 2, "low": 1}
    successful.sort(key=lambda x: priority.get(x.get("confidence", "low").lower(), 0), reverse=True)

    best = successful[0]
    # Ensure all numeric keys exist and are floats
    for key in ["total_roof_area_sqft", "perimeter_lf", "parapet_length_lf"]:
        try:
            best[key] = float(best.get(key, 0.0))
        except (ValueError, TypeError):
            best[key] = 0.0

    # Geometric sanity check: area vs perimeter plausibility.
    # A square with side = perimeter/4 has the MAXIMUM area for that perimeter.
    # If the reported area exceeds 1.5× that maximum, the scale is likely wrong.
    area = best.get("total_roof_area_sqft", 0.0)
    perim = best.get("perimeter_lf", 0.0)
    if area > 0 and perim > 0:
        max_square_area = (perim / 4.0) ** 2
        if area > max_square_area * 1.5:
            logger.warning(
                "[MEASUREMENTS] Area (%.0f sqft) exceeds 1.5× the theoretical maximum "
                "for perimeter %.0f LF (max square = %.0f sqft). Possible scale error — "
                "verify measurement manually.",
                area, perim, max_square_area,
            )
            best["_area_perimeter_warning"] = (
                f"Area {area:.0f} sqft may be overestimated for perimeter {perim:.0f} LF "
                f"(max square = {max_square_area:.0f} sqft). Check scale."
            )

    return best


def analyze_parapet_height(pdf_path: str, detail_pages: list[int],
                           client: genai.Client, model: str = DEFAULT_MODEL) -> dict:
    """
    Analyze detail pages to find parapet height.
    Returns the result from the highest-confidence page.
    """
    logger.info(f"[PARAPET HEIGHT] Starting analysis of detail pages {detail_pages}...")
    t0 = time.time()
    images = render_pdf_pages(pdf_path, detail_pages)
    logger.info(f"[PARAPET HEIGHT] Rendered {len(images)} page(s) in {time.time() - t0:.1f}s")

    candidates = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_GEMINI_WORKERS) as executor:
        futures = [
            executor.submit(_analyze_single_page, p, i, client, model, PARAPET_HEIGHT_PROMPT)
            for p, i in images
        ]
        for future in concurrent.futures.as_completed(futures):
            candidates.append(future.result())

    elapsed = time.time() - t0
    logger.info(f"[PARAPET HEIGHT] Completed in {elapsed:.1f}s ({len(candidates)} result(s))")
    return _select_best_parapet_height(candidates)


def _select_best_parapet_height(candidates: list[dict]) -> dict:
    """Select the best parapet height result."""
    default = {
        "parapet_height_ft": 1.0,
        "confidence": "low",
        "notes": "No parapet details found, using default."
    }

    if not candidates:
        return default

    # Only consider successfully parsed results
    successful = [c for c in candidates if not c.get("error") and not c.get("parse_error")]
    if not successful:
        return default

    # Filter out zero heights unless all are zero
    non_zero = [c for c in successful if c.get("parapet_height_ft", 0) > 0]
    pool = non_zero if non_zero else successful

    # Sort by confidence
    priority = {"high": 3, "medium": 2, "low": 1}
    pool.sort(key=lambda x: priority.get(x.get("confidence", "low").lower(), 0), reverse=True)
    
    best = pool[0]
    try:
        best["parapet_height_ft"] = float(best.get("parapet_height_ft", 1.0))
    except (ValueError, TypeError):
        best["parapet_height_ft"] = 1.0
        
    return best


def suggest_page_ranges(pdf_path: str) -> dict:
    """
    Scan PDF text to suggest plan and detail page ranges.
    Returns dict with 'plan_pages' and 'detail_pages' as comma-separated strings.
    """
    doc = pdfium.PdfDocument(pdf_path)
    plan_pages = []
    detail_pages = []
    
    for i, page in enumerate(doc):
        page_num = i + 1
        try:
            text_page = page.get_textpage()
            text = text_page.get_text_range().lower()
            text_page.close()
        except Exception:
            continue
            
        # Heuristics for page classification
        if "roof plan" in text:
            plan_pages.append(page_num)
        elif "detail" in text or "section" in text or "elevation" in text:
            detail_pages.append(page_num)
            
    doc.close()
    
    def _format_pages(pages):
        if not pages:
            return ""
        # Simple comma separation for now
        return ",".join(map(str, pages))

    return {
        "plan_pages": _format_pages(plan_pages),
        "detail_pages": _format_pages(detail_pages)
    }


# ---------------------------------------------------------------------------
# Full analysis pipeline
# ---------------------------------------------------------------------------

def analyze_drawing(pdf_path: str, client: genai.Client,
                    model: str = DEFAULT_MODEL,
                    plan_pages: list[int] | None = None,
                    detail_pages: list[int] | None = None) -> dict:
    """
    Full spatial analysis of architectural drawing PDFs.

    Processes plan views (for item counts / zones) and detail/section views
    (for material layer assemblies).  Specification PDF processing has been
    moved to the deterministic file_extractor.py module.

    Returns:
        dict with keys:
          drawing_pdf  – source PDF path
          model_used   – Gemini model name
          plan_analysis   – list of per-page plan results
          detail_analysis – list of per-page detail results
    """
    result: dict = {
        "drawing_pdf": pdf_path,
        "model_used": model,
        "plan_analysis": [],
        "detail_analysis": [],
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_GEMINI_WORKERS) as executor:
        futures: dict = {}
        if plan_pages:
            print(f"\n[PLAN VIEWS] Analyzing pages {plan_pages}...")
            futures[executor.submit(analyze_plan, pdf_path, plan_pages, client, model)] = "plan_analysis"

        if detail_pages:
            print(f"\n[DETAIL VIEWS] Analyzing pages {detail_pages}...")
            futures[executor.submit(analyze_details, pdf_path, detail_pages, client, model)] = "detail_analysis"

        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                result[key] = future.result()
            except Exception as e:
                sys.stderr.write(f"Error in {key}: {e}\n")

    # --- Build unit_detail_map by joining plan unit_labels with detail_analysis ---
    dref: list[dict] = []
    drefid: list[dict] = []
    unit_detail_map: list[dict] = []
    for plan_page in result["plan_analysis"]:
        for unit_label in plan_page.get("unit_labels", []):
            dref.append(unit_label)

    for detail_page in result["detail_analysis"]:
        for detail in detail_page.get("details", []):
            drefid.append(detail)

    for unit_label in dref:
        for detail in drefid:
            ref_id = detail.get("detail_ref_id", "")
            if ref_id and ref_id in unit_label.get("detail_ref", ""):
                unit_detail = detail | unit_label | {"match_status": "matched"}
                unit_detail_map.append(unit_detail)
                break
        else:
            unit_detail_map.append(unit_label | {"match_status": "unmatched"})

    result["unit_detail_map"] = unit_detail_map

    return result


def save_analysis(analysis: dict, output_path: str) -> None:
    """Save analysis results to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"\nAnalysis saved to: {output_path}")


# ---------------------------------------------------------------------------
# Summary printing
# ---------------------------------------------------------------------------

def print_summary(analysis: dict) -> None:
    """Print a readable summary of the analysis."""
    print("\n" + "=" * 60)
    print("  DRAWING ANALYSIS SUMMARY")
    print("=" * 60)

    # Plan views
    for plan in analysis.get("plan_analysis", []):
        if plan.get("parse_error"):
            print(f"\n  Plan page {plan['source_page']}: PARSE ERROR")
            continue
        print(f"\n  Plan: {plan.get('drawing_ref', '?')} (page {plan['source_page']})")
        if plan.get("scale"):
            print(f"  Scale: {plan['scale']}")
        counts = plan.get("counts", {})
        nonzero = {k: v for k, v in counts.items() if v > 0}
        if nonzero:
            print("  Item counts:")
            for item, count in nonzero.items():
                print(f"    {item}: {count}")
        if plan.get("detail_references"):
            print(f"  Detail refs: {', '.join(plan['detail_references'])}")

    # Detail views
    for detail_page in analysis.get("detail_analysis", []):
        if detail_page.get("parse_error"):
            print(f"\n  Detail page {detail_page['source_page']}: PARSE ERROR")
            continue
        ref = detail_page.get("drawing_ref", "?")
        print(f"\n  Details: {ref} (page {detail_page['source_page']})")
        for d in detail_page.get("details", []):
            mtype = d.get("measurement_type", "?")
            print(f"    {d['detail_name']}  [{d['detail_type']}]  measured in: {mtype}")
            for layer in d.get("layers", []):
                pkey = layer.get("pricing_key", "?")
                notes = f"  ({layer['notes']})" if layer.get("notes") else ""
                print(f"      {layer['position']}. {layer['material']}  ->  {pkey}{notes}")

    print("\n" + "=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_page_list(s: str) -> list[int]:
    """Parse '1,2,3' or '1-3' or '1,3-5' into a list of ints."""
    pages = []
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return pages


def main() -> None:
    """CLI entry point — drawing spatial analysis only.

    For Specification PDF processing use:
        python file_extractor.py <spec.pdf> [--json output.json]
    """
    if len(sys.argv) < 2:
        print("Usage: python drawing_analyzer.py <drawing.pdf> [options]")
        print()
        print("Options:")
        print("  --api-key KEY          Gemini API key (or set GEMINI_API_KEY env var)")
        print("  --model MODEL          Gemini model name (default: gemini-3.1-pro-preview)")
        print("  --plan-pages 2,3       Page numbers with plan views (1-indexed)")
        print("  --detail-pages 4,5,6   Page numbers with detail/section views")
        print("  --all-pages            Analyze all pages as details")
        print("  --json OUTPUT          Output JSON file path")
        print()
        print("NOTE: Specification PDF analysis is handled by file_extractor.py,")
        print("      not this script.  Do not pass --spec-pdf here.")
        print()
        print("Example:")
        print("  python drawing_analyzer.py drawings.pdf --plan-pages 2,3 --detail-pages 4,5,6")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Parse CLI args
    api_key: str | None = None
    model: str = DEFAULT_MODEL
    plan_pages: list[int] | None = None
    detail_pages: list[int] | None = None
    json_output: str | None = None
    all_pages: bool = False

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--api-key" and i + 1 < len(args):
            api_key = args[i + 1]
            i += 2
        elif args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        elif args[i] == "--plan-pages" and i + 1 < len(args):
            plan_pages = _parse_page_list(args[i + 1])
            i += 2
        elif args[i] == "--detail-pages" and i + 1 < len(args):
            detail_pages = _parse_page_list(args[i + 1])
            i += 2
        elif args[i] in ("--spec-pdf", "--spec-pages"):
            # Gracefully reject legacy args with a helpful message
            sys.stderr.write(
                f"ERROR: '{args[i]}' is no longer supported in drawing_analyzer.py.\n"
                f"  Use file_extractor.py for Specification PDF processing:\n"
                f"    python file_extractor.py <spec.pdf> [--json output.json]\n"
            )
            sys.exit(1)
        elif args[i] == "--json" and i + 1 < len(args):
            json_output = args[i + 1]
            i += 2
        elif args[i] == "--all-pages":
            all_pages = True
            i += 1
        else:
            print(f"Unknown argument: {args[i]}")
            i += 1

    # Resolve API key
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY")
    if api_key is None:
        sys.stderr.write("Error: Gemini API key required.\n")
        sys.stderr.write("  Use --api-key KEY or set GEMINI_API_KEY environment variable.\n")
        sys.exit(1)

    # Handle --all-pages
    if all_pages and detail_pages is None:
        doc = pdfium.PdfDocument(pdf_path)
        detail_pages = list(range(1, len(doc) + 1))
        doc.close()

    if not plan_pages and not detail_pages:
        sys.stderr.write(
            "Error: Specify at least one of --plan-pages, --detail-pages, or --all-pages\n"
        )
        sys.exit(1)

    # Initialize Gemini client
    client = genai.Client(api_key=api_key)
    print(f"Model: {model}")
    print(f"Drawing: {pdf_path}")

    # Run spatial analysis
    analysis = analyze_drawing(
        pdf_path=pdf_path,
        client=client,
        model=model,
        plan_pages=plan_pages,
        detail_pages=detail_pages,
    )

    # Print summary
    print_summary(analysis)

    # Save JSON
    if json_output is None:
        json_output = str(Path(pdf_path).stem) + "_analysis.json"
    save_analysis(analysis, json_output)


if __name__ == "__main__":
    main()
