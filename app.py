"""
LWR Roofing Estimator - FastAPI Web Application

Run with: python app.py
Or:       uvicorn app:app --reload
Opens at: http://127.0.0.1:8000
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

# Ensure project directory is on sys.path for local module imports
_BASE_DIR = Path(__file__).resolve().parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="LWR Roofing Estimator")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Handle Chrome DevTools 404s
@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_404():
    raise HTTPException(status_code=404)

UPLOAD_DIR = Path(tempfile.gettempdir()) / "lwrquotes_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


# -- Jinja2 custom filters --

def currency_filter(value):
    try:
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return str(value)


def number_filter(value):
    try:
        return f"{value:,.0f}"
    except (ValueError, TypeError):
        return str(value)


templates.env.filters["currency"] = currency_filter
templates.env.filters["number"] = number_filter


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---------------------------------------------------------------------------
# Manual Estimate Workflow
# ---------------------------------------------------------------------------

@app.get("/manual", response_class=HTMLResponse)
def manual_form(request: Request):
    return templates.TemplateResponse("manual_form.html", {"request": request})


@app.post("/manual", response_class=HTMLResponse)
async def manual_estimate(request: Request):
    from backend.roof_estimator import (
        RoofMeasurements, RoofSection, CurbDetail, PerimeterSection,
        VentItem, WoodWorkSection, BattInsulationSection,
        ProjectSettings, calculate_takeoff,
    )

    form = await request.form()

    def fval(key, default=0.0):
        v = str(form.get(key, "") or "")
        try:
            return float(v) if v else default
        except (ValueError, TypeError):
            return default

    def ival(key, default=0):
        v = str(form.get(key, "") or "")
        try:
            return int(float(v)) if v else default
        except (ValueError, TypeError):
            return default

    def sval(key, default=""):
        return str(form.get(key, default) or default)

    def bval(key):
        return str(form.get(key, "") or "") == "on"

    # --- Basic fields ---
    roof_system_type = sval("roof_system_type", "SBS")
    total_roof_area = fval("total_roof_area")
    perimeter_lf = fval("perimeter_lf")
    parapet_length_lf = fval("parapet_length_lf")
    parapet_height_ft = fval("parapet_height_ft", 2.0)

    # --- Multi-section roof (6 sections) ---
    roof_sections = []
    for i in range(1, 7):
        l = fval(f"section_{i}_length")
        w = fval(f"section_{i}_width")
        c = ival(f"section_{i}_count", 1)
        if l > 0 and w > 0:
            roof_sections.append(RoofSection(
                name=sval(f"section_{i}_name", f"Section {i}"),
                count=max(c, 1), length_ft=l, width_ft=w,
            ))

    # --- Curbs with dimensions (4 types) ---
    curbs = []
    for ctype in ["RTU", "Roof_Hatch", "Vent_Curb", "Skylight"]:
        cnt = ival(f"curb_{ctype}_count")
        if cnt > 0:
            curbs.append(CurbDetail(
                curb_type=ctype, count=cnt,
                length_in=fval(f"curb_{ctype}_length", 48),
                width_in=fval(f"curb_{ctype}_width", 48),
                height_in=fval(f"curb_{ctype}_height", 18),
            ))

    # --- Perimeter sections (A-E) ---
    perimeter_sections = []
    for letter in "ABCDE":
        lf = fval(f"perim_{letter}_lf")
        if lf > 0:
            perimeter_sections.append(PerimeterSection(
                name=letter,
                perimeter_type=sval(f"perim_{letter}_type", "parapet_no_facing"),
                height_in=fval(f"perim_{letter}_height", 24),
                lf=lf,
                fabrication_difficulty=sval(f"perim_{letter}_fab", "Normal"),
                install_difficulty=sval(f"perim_{letter}_install", "Normal"),
            ))

    # --- Vents with type/difficulty (8 types) ---
    vents = []
    for vtype in ["pipe_boot", "b_vent", "hood_vent", "plumb_vent",
                   "gum_box", "scupper", "radon_pipe", "drain"]:
        cnt = ival(f"vent_{vtype}_count")
        if cnt > 0:
            vents.append(VentItem(
                vent_type=vtype, count=cnt,
                difficulty=sval(f"vent_{vtype}_difficulty", "Normal"),
            ))

    # --- Wood work sections (up to 3) ---
    wood_sections = []
    for i in range(1, 4):
        lf = fval(f"wood_{i}_lf")
        if lf > 0:
            wood_sections.append(WoodWorkSection(
                name=sval(f"wood_{i}_name", f"Wood Section {i}"),
                wood_type=sval(f"wood_{i}_type", "vertical"),
                height_ft=fval(f"wood_{i}_height"),
                lf=lf,
                spacing_in=fval(f"wood_{i}_spacing", 16),
                layers=ival(f"wood_{i}_layers", 1),
                lumber_size=sval(f"wood_{i}_lumber", "lumber_2x4"),
            ))

    # --- Batt insulation sections (up to 3) ---
    batt_sections = []
    for i in range(1, 4):
        lf = fval(f"batt_{i}_lf")
        if lf > 0:
            batt_sections.append(BattInsulationSection(
                name=sval(f"batt_{i}_name", f"Batt Section {i}"),
                height_ft=fval(f"batt_{i}_height"),
                lf=lf,
                insulation_type=sval(f"batt_{i}_type", "R24"),
                layers=ival(f"batt_{i}_layers", 1),
            ))

    # --- Project Settings ---
    project_settings = ProjectSettings(
        floor_count=ival("floor_count", 1),
        hot_work=bval("hot_work"),
        tear_off=bval("tear_off"),
        interior_access_only=bval("interior_access_only"),
        winter_conditions=bval("winter_conditions"),
    )

    m = RoofMeasurements(
        total_roof_area_sqft=total_roof_area,
        perimeter_lf=perimeter_lf,
        parapet_length_lf=parapet_length_lf or perimeter_lf,
        parapet_height_ft=parapet_height_ft,
        roof_sections=roof_sections,
        curbs=curbs,
        extra_mechanical_hours=fval("extra_mechanical_hours"),
        perimeter_sections=perimeter_sections,
        corner_count=ival("corner_count"),
        vents=vents,
        # Legacy counts as fallback
        roof_drain_count=ival("roof_drain_count"),
        scupper_count=ival("scupper_count"),
        mechanical_unit_count=ival("mechanical_unit_count"),
        sleeper_curb_count=ival("sleeper_curb_count"),
        vent_hood_count=ival("vent_hood_count"),
        gas_penetration_count=ival("gas_penetration_count"),
        electrical_penetration_count=ival("electrical_penetration_count"),
        plumbing_vent_count=ival("plumbing_vent_count"),
        gum_box_count=ival("gum_box_count"),
        b_vent_count=ival("b_vent_count"),
        radon_pipe_count=ival("radon_pipe_count"),
        roof_hatch_count=ival("roof_hatch_count"),
        skylight_count=ival("skylight_count"),
        tapered_area_sqft=fval("tapered_area_sqft") or None,
        ballast_area_sqft=fval("ballast_area_sqft") or None,
        roof_system_type=roof_system_type,
        wood_sections=wood_sections,
        batt_sections=batt_sections,
        delivery_count=ival("delivery_count", 1),
        disposal_roof_count=ival("disposal_roof_count", 1),
        include_toilet=bval("include_toilet"),
        include_fencing=bval("include_fencing"),
        metal_flashing_type=sval("metal_flashing_type", "galvanized"),
        include_vapour_barrier=bval("include_vapour_barrier") if "include_vapour_barrier" in form else True,
        include_insulation=bval("include_insulation") if "include_insulation" in form else True,
        include_coverboard=bval("include_coverboard") if "include_coverboard" in form else True,
        include_tapered=bval("include_tapered") if "include_tapered" in form else True,
        include_drainage=bval("include_drainage") if "include_drainage" in form else True,
        vapour_barrier_tie_in=bval("vapour_barrier_tie_in"),
        sbs_base_type=sval("sbs_base_type", "torch"),
        # New fields from audit
        project_settings=project_settings,
        fire_board_scope=sval("fire_board_scope", "None"),
        vapour_barrier_attachment=sval("vapour_barrier_attachment", "Torched"),
        vapour_barrier_product=sval("vapour_barrier_product", "Sopravapor"),
        include_asphalt_easymelt=bval("include_asphalt_easymelt"),
        include_pmma=bval("include_pmma"),
        garland_system=bval("garland_system"),
        second_iso_layer=bval("second_iso_layer"),
        third_iso_layer=bval("third_iso_layer"),
        version=sval("version", ""),
        ballast_type=sval("ballast_type", "BUR"),
        eps_thickness_in=fval("eps_thickness_in", 2.5),
        tpo_second_membrane=bval("tpo_second_membrane"),
        include_tpo_flashing_24=bval("include_tpo_flashing_24") if "include_tpo_flashing_24" in form else True,
        include_tpo_flashing_12=bval("include_tpo_flashing_12"),
    )

    estimate = calculate_takeoff(m)
    return templates.TemplateResponse("manual_result.html", {
        "request": request,
        "estimate": estimate,
    })


# ---------------------------------------------------------------------------
# Drawing Analysis Workflow (includes address-based dimension lookup)
# ---------------------------------------------------------------------------

@app.get("/drawing", response_class=HTMLResponse)
def drawing_form(request: Request):
    return templates.TemplateResponse("drawing_form.html", {
        "request": request,
        "step": 1,
    })


@app.post("/drawing/upload", response_class=HTMLResponse)
async def drawing_upload(
    request: Request,
    address: str = Form(...),
    pdf_file: UploadFile = File(...),
    spec_file: UploadFile | None = File(None),
):
    import asyncio
    import pypdfium2 as pdfium
    from backend.drawing_analyzer import suggest_page_ranges
    from backend.buildingfootprintquery import get_building_dimensions

    # Save drawing PDF
    pdf_path = UPLOAD_DIR / f"{uuid4().hex}_{pdf_file.filename}"
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(pdf_file.file, f)

    doc = pdfium.PdfDocument(str(pdf_path))
    page_count = len(doc)
    doc.close()

    # Auto-detect page ranges
    suggestions = suggest_page_ranges(str(pdf_path))

    # Save optional spec PDF
    spec_path_str = ""
    spec_filename = ""
    spec_page_count = 0
    if spec_file and spec_file.filename:
        spec_path = UPLOAD_DIR / f"{uuid4().hex}_{spec_file.filename}"
        with open(spec_path, "wb") as f:
            shutil.copyfileobj(spec_file.file, f)
        doc = pdfium.PdfDocument(str(spec_path))
        spec_page_count = len(doc)
        doc.close()
        spec_path_str = str(spec_path)
        spec_filename = spec_file.filename

    # Lookup building dimensions from Google Solar API
    dims = None
    dims_error = None
    try:
        loop = asyncio.get_running_loop()
        dims = await loop.run_in_executor(None, get_building_dimensions, address)
    except Exception as e:
        dims_error = str(e)

    return templates.TemplateResponse("drawing_form.html", {
        "request": request,
        "step": 2,
        "address": address,
        "dims": dims,
        "dims_error": dims_error,
        "pdf_path": str(pdf_path),
        "pdf_filename": pdf_file.filename,
        "page_count": page_count,
        "spec_path": spec_path_str,
        "spec_filename": spec_filename,
        "spec_page_count": spec_page_count,
        "suggestions": suggestions,
    })


@app.post("/drawing/measure", response_class=HTMLResponse)
async def drawing_measure(
    request: Request,
    pdf_path: str = Form(...),
    plan_pages: str = Form(""),
    detail_pages: str = Form(""),
    spec_path: str = Form(""),
    spec_pages: str = Form(""),
    ref_description: str = Form(""),
    ref_value: float = Form(0.0),
    ref_unit: str = Form("ft"),
    ref_page: str = Form(""),
):
    import logging
    import time as _time
    logger = logging.getLogger("drawing_measure")

    # Path traversal protection
    if not pdf_path.startswith(str(UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if spec_path and not spec_path.startswith(str(UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid spec file path")

    try:
        from backend.drawing_analyzer import (
            analyze_measurements,
            analyze_parapet_height,
            _parse_page_list,
            DEFAULT_MODEL,
        )
        from google import genai
        import asyncio
        import concurrent.futures

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in .env file")

        client = genai.Client(api_key=api_key)

        plan_pg = _parse_page_list(plan_pages) if plan_pages.strip() else []
        detail_pg = _parse_page_list(detail_pages) if detail_pages.strip() else []

        # Build reference measurement dict
        reference_measurement = None
        if ref_description.strip() and ref_value > 0:
            reference_measurement = {
                "description": ref_description.strip(),
                "value": ref_value,
                "unit": ref_unit,
            }

        logger.info(f"/drawing/measure called — plan_pages={plan_pg}, detail_pages={detail_pg}, ref={reference_measurement}")
        t0 = _time.time()

        loop = asyncio.get_running_loop()

        # Run measurements and parapet height analysis in parallel
        measurements_task = None
        parapet_height_task = None

        if plan_pg:
            measurements_task = loop.run_in_executor(
                None, analyze_measurements, pdf_path, plan_pg, client,
                DEFAULT_MODEL, reference_measurement
            )

        if detail_pg:
            parapet_height_task = loop.run_in_executor(
                None, analyze_parapet_height, pdf_path, detail_pg, client
            )

        # Wait for both tasks to complete
        measurements = await measurements_task if measurements_task else {
            "scale": "Unknown",
            "total_roof_area_sqft": 0.0,
            "perimeter_lf": 0.0,
            "parapet_length_lf": 0.0,
            "confidence": "low",
            "notes": "No plan pages selected."
        }

        parapet_height = await parapet_height_task if parapet_height_task else {
            "parapet_height_ft": 2.0,
            "confidence": "low",
            "notes": "No detail pages selected."
        }

        elapsed = _time.time() - t0
        logger.info(f"/drawing/measure completed in {elapsed:.1f}s — "
                     f"area={measurements.get('total_roof_area_sqft')}, "
                     f"parapet_ht={parapet_height.get('parapet_height_ft')}")

        return templates.TemplateResponse("drawing_form.html", {
            "request": request,
            "step": 3,
            "pdf_path": pdf_path,
            "plan_pages": plan_pages,
            "detail_pages": detail_pages,
            "spec_path": spec_path,
            "spec_pages": spec_pages,
            "measurements": measurements,
            "parapet_height": parapet_height,
        })

    except Exception as e:
        logger.error(f"/drawing/measure FAILED: {type(e).__name__}: {e}", exc_info=True)
        # Fallback to manual entry on error
        return templates.TemplateResponse("drawing_form.html", {
            "request": request,
            "step": 3,
            "pdf_path": pdf_path,
            "plan_pages": plan_pages,
            "detail_pages": detail_pages,
            "spec_path": spec_path,
            "spec_pages": spec_pages,
            "measurements": {
                "scale": "Error",
                "total_roof_area_sqft": 0.0,
                "perimeter_lf": 0.0,
                "parapet_length_lf": 0.0,
                "confidence": "low",
                "notes": f"Auto-measurement failed: {str(e)}"
            },
            "parapet_height": {
                "parapet_height_ft": 2.0,
                "confidence": "low",
                "notes": "Using default height."
            },
            "error": str(e)
        })


@app.post("/drawing/analyze", response_class=HTMLResponse)
async def drawing_analyze(
    request: Request,
    pdf_path: str = Form(...),
    plan_pages: str = Form(""),
    detail_pages: str = Form(""),
    spec_path: str = Form(""),
    spec_pages: str = Form(""),
    total_roof_area: float = Form(0.0),
    perimeter_lf: float = Form(0.0),
    parapet_length_lf: float = Form(0.0),
    parapet_height_ft: float = Form(2.0),
):
    import logging
    _logger = logging.getLogger("drawing_analyze")

    # Path traversal protection
    if not pdf_path.startswith(str(UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if spec_path and not spec_path.startswith(str(UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid spec file path")

    try:
        from backend.drawing_analyzer import analyze_drawing, _parse_page_list
        from backend.file_extractor import extract_text_from_pdf, analyze_text as spec_analyze_text
        from google import genai
        from backend.roof_estimator import (
            measurements_from_analysis,
            calculate_detail_takeoff,
            calculate_takeoff,
            join_takeoff_data,
        )
        import asyncio

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in .env file")

        client = genai.Client(api_key=api_key)

        plan_pg = _parse_page_list(plan_pages) if plan_pages.strip() else None
        detail_pg = _parse_page_list(detail_pages) if detail_pages.strip() else None

        if not plan_pg and not detail_pg:
            raise ValueError("Specify at least one of: plan pages or detail pages")

        loop = asyncio.get_running_loop()

        # -------------------------------------------------------------------
        # Step 1: Process spec PDF through file_extractor.py (deterministic).
        # This runs FIRST so spec material data is ready before pricing.
        # -------------------------------------------------------------------
        spec_result = None
        if spec_path:
            _logger.info(f"[SPEC] Extracting spec PDF: {spec_path}")
            try:
                spec_pages_data = await loop.run_in_executor(
                    None, lambda: extract_text_from_pdf(spec_path)
                )
                spec_result = await loop.run_in_executor(
                    None, lambda: spec_analyze_text(spec_pages_data)
                )
                _logger.info(
                    f"[SPEC] Extracted {spec_result['summary']['total_unique_products']} "
                    f"products, {spec_result['summary']['total_confirmed_pricing_keys']} "
                    f"pricing keys confirmed."
                )
            except Exception as spec_err:
                _logger.warning(f"[SPEC] Spec PDF extraction failed: {spec_err}")
                spec_result = None

        # -------------------------------------------------------------------
        # Step 2: Send drawing PDF to Gemini API for spatial analysis.
        # -------------------------------------------------------------------
        _logger.info(f"[DRAWING] Sending drawing to Gemini: plan={plan_pg}, detail={detail_pg}")
        analysis = await loop.run_in_executor(
            None,
            lambda: analyze_drawing(
                pdf_path=pdf_path,
                client=client,
                plan_pages=plan_pg,
                detail_pages=detail_pg,
            )
        )

        # -------------------------------------------------------------------
        # Step 3: Build measurements from AI counts + user-provided areas.
        # -------------------------------------------------------------------
        measurements = measurements_from_analysis(
            analysis,
            total_roof_area,
            perimeter_lf,
            parapet_length_lf or perimeter_lf,
            parapet_height_ft,
        )

        # -------------------------------------------------------------------
        # Step 4: Pricing.
        # If spec data is available, use join_takeoff_data() (spec-driven,
        # deterministic) as the primary estimate.
        # Always also compute the AI detail takeoff + standard estimate.
        # -------------------------------------------------------------------
        joined_estimate = None
        if spec_result and spec_result.get("spec_materials"):
            try:
                joined_estimate = join_takeoff_data(analysis, spec_result)
                _logger.info(
                    f"[PRICING] join_takeoff_data: "
                    f"{joined_estimate['bid_summary']['total_line_items']} line items, "
                    f"{joined_estimate['bid_summary']['total_failures']} failures, "
                    f"total=${joined_estimate['bid_summary']['total_material_cost']:,.2f}"
                )
            except Exception as join_err:
                _logger.warning(f"[PRICING] join_takeoff_data failed: {join_err}")
                joined_estimate = None

        detail_estimate = calculate_detail_takeoff(measurements, analysis)
        standard_estimate = calculate_takeoff(measurements)

        return templates.TemplateResponse("drawing_result.html", {
            "request": request,
            "analysis": analysis,
            "spec_result": spec_result,
            "joined_estimate": joined_estimate,
            "detail_estimate": detail_estimate,
            "standard_estimate": standard_estimate,
            "error": None,
        })

    except Exception as e:
        _logger.error(f"/drawing/analyze FAILED: {type(e).__name__}: {e}", exc_info=True)
        return templates.TemplateResponse("drawing_result.html", {
            "request": request,
            "analysis": None,
            "spec_result": None,
            "joined_estimate": None,
            "detail_estimate": None,
            "standard_estimate": None,
            "error": str(e),
        })
    finally:
        # Clean up temp files
        try:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
            if spec_path and os.path.exists(spec_path):
                os.unlink(spec_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
