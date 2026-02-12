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
def manual_estimate(
    request: Request,
    total_roof_area: float = Form(...),
    perimeter_lf: float = Form(...),
    parapet_length_lf: float = Form(0),
    parapet_height_ft: float = Form(2.0),
    roof_drain_count: int = Form(0),
    scupper_count: int = Form(0),
    mechanical_unit_count: int = Form(0),
    sleeper_curb_count: int = Form(0),
    vent_hood_count: int = Form(0),
    gas_penetration_count: int = Form(0),
    electrical_penetration_count: int = Form(0),
    plumbing_vent_count: int = Form(0),
    tapered_area_sqft: float = Form(0),
    ballast_area_sqft: float = Form(0),
):
    from backend.roof_estimator import RoofMeasurements, calculate_takeoff

    m = RoofMeasurements(
        total_roof_area_sqft=total_roof_area,
        perimeter_lf=perimeter_lf,
        parapet_length_lf=parapet_length_lf or perimeter_lf,
        parapet_height_ft=parapet_height_ft,
        roof_drain_count=roof_drain_count,
        scupper_count=scupper_count,
        mechanical_unit_count=mechanical_unit_count,
        sleeper_curb_count=sleeper_curb_count,
        vent_hood_count=vent_hood_count,
        gas_penetration_count=gas_penetration_count,
        electrical_penetration_count=electrical_penetration_count,
        plumbing_vent_count=plumbing_vent_count,
        tapered_area_sqft=tapered_area_sqft or None,
        ballast_area_sqft=ballast_area_sqft or None,
    )

    estimate = calculate_takeoff(m)
    return templates.TemplateResponse("manual_result.html", {
        "request": request,
        "estimate": estimate,
    })


# ---------------------------------------------------------------------------
# Address-Based Estimate Workflow
# ---------------------------------------------------------------------------

@app.get("/address", response_class=HTMLResponse)
def address_form(request: Request):
    return templates.TemplateResponse("address_form.html", {"request": request})


@app.post("/address", response_class=HTMLResponse)
def address_estimate(
    request: Request,
    address: str = Form(...),
    system_type: str = Form("TPO"),
    parapet_height: float = Form(2.0),
):
    try:
        from backend.buildingfootprintquery import get_commercial_footprint, estimate_flat_roof

        polygon = get_commercial_footprint(address)
        result = estimate_flat_roof(
            polygon, system_type=system_type, parapet_height_ft=parapet_height
        )
        return templates.TemplateResponse("address_result.html", {
            "request": request,
            "address": address,
            "result": result,
            "error": None,
        })
    except Exception as e:
        return templates.TemplateResponse("address_result.html", {
            "request": request,
            "address": address,
            "result": None,
            "error": str(e),
        })


# ---------------------------------------------------------------------------
# Drawing Analysis Workflow
# ---------------------------------------------------------------------------

@app.get("/drawing", response_class=HTMLResponse)
def drawing_form(request: Request):
    return templates.TemplateResponse("drawing_form.html", {
        "request": request,
        "step": 1,
    })


@app.post("/drawing/upload", response_class=HTMLResponse)
def drawing_upload(
    request: Request,
    pdf_file: UploadFile = File(...),
    spec_file: UploadFile | None = File(None),
):
    import pypdfium2 as pdfium
    from backend.drawing_analyzer import suggest_page_ranges

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

    return templates.TemplateResponse("drawing_form.html", {
        "request": request,
        "step": 2,
        "pdf_path": str(pdf_path),
        "pdf_filename": pdf_file.filename,
        "page_count": page_count,
        "spec_path": spec_path_str,
        "spec_filename": spec_filename,
        "spec_page_count": spec_page_count,
        "suggestions": suggestions,
    })


@app.post("/drawing/measure", response_class=HTMLResponse)
def drawing_measure(
    request: Request,
    pdf_path: str = Form(...),
    plan_pages: str = Form(""),
    detail_pages: str = Form(""),
    spec_path: str = Form(""),
    spec_pages: str = Form(""),
):
    # Path traversal protection
    if not pdf_path.startswith(str(UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if spec_path and not spec_path.startswith(str(UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid spec file path")

    try:
        from backend.drawing_analyzer import (
            analyze_measurements,
            analyze_parapet_height,
            _parse_page_list
        )
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in .env file")

        client = genai.Client(api_key=api_key)

        plan_pg = _parse_page_list(plan_pages) if plan_pages.strip() else []
        detail_pg = _parse_page_list(detail_pages) if detail_pages.strip() else []

        # Step 1: Measure Plan Pages (Area, Perimeter, Parapet Length)
        measurements = {
            "scale": "Unknown",
            "total_roof_area_sqft": 0.0,
            "perimeter_lf": 0.0,
            "parapet_length_lf": 0.0,
            "confidence": "low",
            "notes": "No plan pages selected."
        }
        if plan_pg:
            measurements = analyze_measurements(pdf_path, plan_pg, client)

        # Step 2: Measure Detail Pages (Parapet Height)
        parapet_height = {
            "parapet_height_ft": 2.0,
            "confidence": "low",
            "notes": "No detail pages selected."
        }
        if detail_pg:
            parapet_height = analyze_parapet_height(pdf_path, detail_pg, client)

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
def drawing_analyze(
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
    # Path traversal protection
    if not pdf_path.startswith(str(UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if spec_path and not spec_path.startswith(str(UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid spec file path")

    try:
        from backend.drawing_analyzer import analyze_drawing, _parse_page_list
        from google import genai
        from backend.roof_estimator import (
            measurements_from_analysis,
            calculate_detail_takeoff,
            calculate_takeoff,
        )

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in .env file")

        client = genai.Client(api_key=api_key)

        plan_pg = _parse_page_list(plan_pages) if plan_pages.strip() else None
        detail_pg = _parse_page_list(detail_pages) if detail_pages.strip() else None
        spec_pg = _parse_page_list(spec_pages) if spec_pages.strip() else None

        if not plan_pg and not detail_pg and not spec_pg:
            raise ValueError("Specify at least one of: plan pages, detail pages, or spec pages")

        analysis = analyze_drawing(
            pdf_path=pdf_path,
            client=client,
            plan_pages=plan_pg,
            detail_pages=detail_pg,
            spec_pdf=spec_path if spec_path else None,
            spec_pages=spec_pg,
        )

        measurements = measurements_from_analysis(
            analysis,
            total_roof_area,
            perimeter_lf,
            parapet_length_lf or perimeter_lf,
            parapet_height_ft,
        )

        detail_estimate = calculate_detail_takeoff(measurements, analysis)
        standard_estimate = calculate_takeoff(measurements)

        return templates.TemplateResponse("drawing_result.html", {
            "request": request,
            "analysis": analysis,
            "detail_estimate": detail_estimate,
            "standard_estimate": standard_estimate,
            "error": None,
        })

    except Exception as e:
        return templates.TemplateResponse("drawing_result.html", {
            "request": request,
            "analysis": None,
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
