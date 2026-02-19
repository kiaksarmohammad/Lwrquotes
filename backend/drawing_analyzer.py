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

Your goal is to extract the primary roof measurements from this drawing.

1. SCALE: Find the scale notation (e.g., 1/8" = 1'-0" or 1:100).
2. DIMENSIONS: Read the overall dimensions of the building outline.
{reference_section}
3. CALCULATE:
   - Total Roof Area (sqft): The total flat roof surface area.
   - Perimeter (LF): The total length of the roof edge.
   - Parapet Length (LF): The length of edges that have a parapet wall (vs. open edges or gutters).

4. CONFIDENCE: Rate your confidence (high/medium/low) based on image clarity and scale visibility.

Return ONLY valid JSON (no markdown, no explanation) in this format:
{{
  "scale": "1/8\\" = 1'-0\\"",
  "reference_measurement_used": true,
  "total_roof_area_sqft": 0.0,
  "perimeter_lf": 0.0,
  "parapet_length_lf": 0.0,
  "confidence": "high",
  "notes": "Scale found in bottom right. Dimensions clear."
}}"""

REFERENCE_SECTION_WITH_DATA = """
IMPORTANT - REFERENCE MEASUREMENT (use this to calibrate all other dimensions):
   The user has confirmed that "{description}" measures {value} {unit} in real life.
   Use this known dimension to:
   a) Verify or determine the drawing scale
   b) Cross-check all other measured dimensions against this reference
   c) If the scale shown on the drawing conflicts with this reference measurement, TRUST the reference measurement
   d) Calculate all areas and lengths using the scale validated by this reference"""

REFERENCE_SECTION_NO_DATA = """   Use the scale notation on the drawing along with any visible dimensions to calculate measurements."""


def _build_measurement_prompt(reference_measurement: dict | None = None) -> str:
    """Build the measurement prompt, injecting reference data if provided."""
    if reference_measurement:
        ref_section = REFERENCE_SECTION_WITH_DATA.format(
            description=reference_measurement["description"],
            value=reference_measurement["value"],
            unit=reference_measurement["unit"],
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
2. The detail type - classify as one of:
   parapet, drain, mechanical_curb, sleeper_curb, penetration_gas,
   penetration_electrical, penetration_plumbing, vent_hood, scupper,
   expansion_joint, curtain_wall, field_assembly, pipe_support, opening_cover
3. All materials/products shown, listed from BOTTOM to TOP (or inside to outside)
4. For each material, map it to the closest pricing_key from our database
5. Whether this detail is measured in: sqft, linear_ft, or each
6. SCOPE & QUANTITY: Read any dimensions, annotations, or notes on the detail to determine:
   - The physical size of the detail (e.g., opening dimensions, curb size, etc.)
   - Any "typical of N" or "N locations" callouts
   - For openings/infills: calculate the area from shown dimensions (e.g., 4'x6' = 24 sqft)
   - For linear details: note the length if dimensioned
   - For penetrations/curbs: note the size (e.g., "6 inch pipe", "48x48 curb")
   If no quantity can be determined from the drawing, set scope_quantity to null.
7. MATERIAL DIMENSIONS: For each material in a detail, estimate its cross-sectional width, height, or girth (in inches) if it is shown or can be visually estimated from the scale. For example, a parapet plywood face might be 24 inches tall, or a flashing strip might have an 18-inch girth. If unmeasurable, return null.

IMPORTANT classification rules:
- "field_assembly" is ONLY for the main roof membrane system that covers the entire roof surface
- Slab openings, infills, patches, and localized repairs are NOT field_assembly - classify as "opening_cover"
- Structural repairs (concrete patching, grouting) are NOT field_assembly - classify as "opening_cover"
- Each penetration, curb, or opening is measured as "each" with a small count

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
   - roof_drains: circular drain symbols
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
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
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
    if not candidates:
        return {
            "scale": "Unknown",
            "total_roof_area_sqft": 0.0,
            "perimeter_lf": 0.0,
            "parapet_length_lf": 0.0,
            "confidence": "low",
            "notes": "No measurements extracted."
        }
    
    # Sort by confidence: high > medium > low
    priority = {"high": 3, "medium": 2, "low": 1}
    candidates.sort(key=lambda x: priority.get(x.get("confidence", "low").lower(), 0), reverse=True)
    
    best = candidates[0]
    # Ensure numeric values are floats
    for key in ["total_roof_area_sqft", "perimeter_lf", "parapet_length_lf"]:
        if key in best:
            try:
                best[key] = float(best[key])
            except (ValueError, TypeError):
                best[key] = 0.0
                
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
    if not candidates:
        return {
            "parapet_height_ft": 2.0,
            "confidence": "low",
            "notes": "No parapet details found, using default."
        }

    # Filter out zero heights unless all are zero
    non_zero = [c for c in candidates if c.get("parapet_height_ft", 0) > 0]
    pool = non_zero if non_zero else candidates

    # Sort by confidence
    priority = {"high": 3, "medium": 2, "low": 1}
    pool.sort(key=lambda x: priority.get(x.get("confidence", "low").lower(), 0), reverse=True)
    
    best = pool[0]
    try:
        best["parapet_height_ft"] = float(best.get("parapet_height_ft", 2.0))
    except (ValueError, TypeError):
        best["parapet_height_ft"] = 2.0
        
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
