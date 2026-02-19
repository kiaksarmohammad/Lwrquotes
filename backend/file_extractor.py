"""
file_extractor.py — Deterministic Specification PDF Analyzer
=============================================================

Processes Specification / IFT PDF documents using regex matching against the
PRODUCT_KEYWORDS dictionary in database.py.  No LLM calls are made; all
material identification is 100% deterministic.

Pipeline role
-------------
  Drawing PDFs  →  drawing_analyzer.py  (Gemini Vision, spatial data only)
  Spec PDFs     →  THIS MODULE          (regex, material identification)
  Integration   →  roof_estimator.py    (join_takeoff_data, deterministic join)

Output JSON schema
------------------
  {
    "project_info": { ... },
    "products": {                        # verbose per-product detail
      "<Category>": {
        "<Product Name>": {
          "pricing_key": str | None,     # canonical key from PRICING dict
          "pages": [int, ...],
          "mention_count": int,
          "context_snippets": [str, ...],
          "dimensions": [str, ...]
        }
      }
    },
    "spec_materials": {                  # MACHINE-READABLE flat dict for integration
      "<pricing_key>": {
        "product_name": str,
        "category": str,
        "pages": [int, ...],
        "dimensions": [str, ...]
      }
    },
    "summary": {
      "total_categories": int,
      "total_unique_products": int,
      "total_confirmed_pricing_keys": int,
      "categories": { "<Category>": int }
    }
  }

Usage
-----
    python file_extractor.py <path_to_spec.pdf> [--json output.json]
"""

from __future__ import annotations

import re
import sys
import json
import logging
from typing import Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore[assignment]

try:
    from PyPDF2 import PdfReader  # type: ignore[import-not-found]
except ImportError:
    PdfReader = None  # type: ignore[assignment]

from backend.database import PRODUCT_KEYWORDS, PRICING

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# Pattern: capture dimensions / thicknesses tied to a product mention
# ---------------------------------------------------------------------------
DIMENSION_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mm|cm|m|inch|in|ft|mil)\b", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Build a reverse lookup: product_name → pricing_key
# Scans PRICING dict for canonical_name matches; falls back to key-derived name.
# Pre-computed once at import time for O(1) lookups during analysis.
# ---------------------------------------------------------------------------

def _build_pricing_key_index() -> dict[str, str]:
    """
    Return a dict mapping normalised product names → PRICING dict key.

    Normalisation: lower-case, collapse whitespace, strip punctuation so that
    minor formatting differences don't break the match.
    """
    index: dict[str, str] = {}
    for key, val in PRICING.items():
        if isinstance(val, dict):
            canonical = val.get("canonical_name", "")
            if canonical:
                index[_normalise(canonical)] = key
            # Also index the raw key itself (spaces → underscores already canonical)
            index[_normalise(key.replace("_", " "))] = key
        # Scalar entries (composite per-sqft rates) — index the key as a name
        else:
            index[_normalise(key.replace("_", " "))] = key
    return index


def _normalise(text: str) -> str:
    """Lower-case and collapse whitespace/punctuation for fuzzy key matching."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Module-level index built once
_PRICING_KEY_INDEX: dict[str, str] = _build_pricing_key_index()


def _resolve_pricing_key(product_name: str) -> Optional[str]:
    """
    Deterministically map a product_name (from PRODUCT_KEYWORDS values) to
    the corresponding key in the PRICING dictionary.

    Strategy (in order):
      1. Exact normalised match against PRICING canonical_name or key
      2. Check if any PRICING key is a substring of the normalised product_name
      3. Return None if no confident match is found (requires manual review)
    """
    normalised = _normalise(product_name)

    # 1. Exact match
    if normalised in _PRICING_KEY_INDEX:
        return _PRICING_KEY_INDEX[normalised]

    # 2. Substring scan — PRICING key words contained in product_name
    for norm_key, pricing_key in _PRICING_KEY_INDEX.items():
        # Only accept substring matches that are at least 5 chars to avoid noise
        if len(norm_key) >= 5 and norm_key in normalised:
            return pricing_key

    logger.debug(
        "No pricing key resolved for product_name=%r (normalised=%r)",
        product_name, normalised
    )
    return None


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> list[tuple[int, str]]:
    """
    Return a list of (page_number, text) tuples from the PDF.

    Tries pdfplumber first (superior text extraction), falls back to PyPDF2.
    Raises ImportError if neither library is available.
    """
    pages: list[tuple[int, str]] = []

    if pdfplumber is not None:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append((i, text))
        return pages

    if PdfReader is not None:
        reader = PdfReader(pdf_path)
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append((i, text))
        return pages

    raise ImportError(
        "No PDF library found. Install one of:\n"
        "  pip install pdfplumber\n"
        "  pip install PyPDF2"
    )


# ---------------------------------------------------------------------------
# Core analysis engine
# ---------------------------------------------------------------------------

def analyze_text(pages: list[tuple[int, str]]) -> dict:
    """
    Scan every page for product keywords defined in PRODUCT_KEYWORDS.

    Returns a predictable JSON-serialisable payload:

    {
      "project_info": { ... },
      "products": {
        "<Category>": {
          "<Product Name>": {
            "pricing_key": str | None,
            "pages": [int, ...],
            "mention_count": int,
            "context_snippets": [str, ...],
            "dimensions": [str, ...]
          }
        }
      },
      "spec_materials": {
        "<pricing_key>": {
          "product_name": str,
          "category": str,
          "pages": [int, ...],
          "dimensions": [str, ...]
        }
      },
      "summary": {
        "total_categories": int,
        "total_unique_products": int,
        "total_confirmed_pricing_keys": int,
        "categories": { "<Category>": int }
      }
    }

    Deduplication rules
    -------------------
    * Multiple regex patterns that resolve to the **same product_name** in the
      same category are merged into a single entry (mention_count accumulates).
    * Dimensions are de-duplicated per product entry.
    * A product_name that appears on multiple pages lists each page once.
    """
    verbose_products: dict[str, dict[str, dict]] = {}
    project_info = _extract_project_info(pages)

    for page_num, text in pages:
        lines = text.split("\n")
        for line in lines:
            clean = line.strip()
            if not clean:
                continue

            for category, patterns in PRODUCT_KEYWORDS.items():
                for pattern, product_name in patterns.items():
                    if not re.search(pattern, clean, re.IGNORECASE):
                        continue

                    # --- Ensure category / product entry exists ---
                    cat_dict = verbose_products.setdefault(category, {})
                    if product_name not in cat_dict:
                        pricing_key = _resolve_pricing_key(product_name)
                        cat_dict[product_name] = {
                            "pricing_key": pricing_key,
                            "pages": [],
                            "mention_count": 0,
                            "context_snippets": [],
                            "dimensions": [],
                        }

                    entry = cat_dict[product_name]
                    entry["mention_count"] += 1

                    if page_num not in entry["pages"]:
                        entry["pages"].append(page_num)

                    # Keep up to 5 unique context snippets (first 200 chars)
                    snippet = clean[:200]
                    if (snippet not in entry["context_snippets"]
                            and len(entry["context_snippets"]) < 5):
                        entry["context_snippets"].append(snippet)

                    # Capture dimensions (de-duplicated)
                    for m in DIMENSION_PATTERN.finditer(clean):
                        dim = f"{m.group(1)}{m.group(2).lower()}"
                        if dim not in entry["dimensions"]:
                            entry["dimensions"].append(dim)

    # ---------------------------------------------------------------------------
    # Build flat spec_materials dict (machine-readable, keyed by pricing_key)
    # ---------------------------------------------------------------------------
    spec_materials: dict[str, dict] = {}
    confirmed_keys: int = 0

    for category, prods in verbose_products.items():
        for product_name, info in prods.items():
            pk = info["pricing_key"]
            if pk is None:
                continue  # no pricing match — excluded from spec_materials

            confirmed_keys += 1
            if pk not in spec_materials:
                spec_materials[pk] = {
                    "product_name": product_name,
                    "category": category,
                    "pages": list(info["pages"]),
                    "dimensions": list(info["dimensions"]),
                }
            else:
                # Merge pages and dimensions if same pricing_key reached via
                # a different category/pattern path
                for pg in info["pages"]:
                    if pg not in spec_materials[pk]["pages"]:
                        spec_materials[pk]["pages"].append(pg)
                for dim in info["dimensions"]:
                    if dim not in spec_materials[pk]["dimensions"]:
                        spec_materials[pk]["dimensions"].append(dim)

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    total_products = sum(len(prods) for prods in verbose_products.values())
    summary: dict = {
        "total_categories": len(verbose_products),
        "total_unique_products": total_products,
        "total_confirmed_pricing_keys": confirmed_keys,
        "categories": {cat: len(prods) for cat, prods in verbose_products.items()},
    }

    return {
        "project_info": project_info,
        "products": verbose_products,
        "spec_materials": spec_materials,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Project metadata extraction
# ---------------------------------------------------------------------------

def _extract_project_info(pages: list[tuple[int, str]]) -> dict:
    """Try to pull project metadata from the first couple of pages."""
    info: dict[str, Optional[str]] = {
        "project_name": None,
        "address": None,
        "project_number": None,
        "date": None,
        "consultant": None,
        "client": None,
    }
    combined = "\n".join(text for _, text in pages[:2])

    m = re.search(r"Project\s*No\.?\s*:?\s*(\S+)", combined, re.IGNORECASE)
    if m:
        info["project_number"] = m.group(1)

    m = re.search(r"Date\s*:?\s*([\w\s\-,]+\d{4})", combined, re.IGNORECASE)
    if m:
        info["date"] = m.group(1).strip()

    m = re.search(r"(\d+\s+\d+\s+Street\s+\w+)", combined, re.IGNORECASE)
    if m:
        info["address"] = m.group(1)

    m = re.search(
        r"(Calgary|Edmonton|Toronto|Vancouver|Ottawa|Winnipeg)"
        r"\s*,?\s*(Alberta|Ontario|BC|Manitoba|Saskatchewan|Quebec)",
        combined, re.IGNORECASE
    )
    if m:
        city_prov = f"{m.group(1)}, {m.group(2)}"
        info["address"] = f"{info['address']}, {city_prov}" if info["address"] else city_prov

    for line in combined.split("\n")[:20]:
        if re.search(r"roofing|replacement|restoration|repair", line, re.IGNORECASE) and len(line) > 10:
            info["project_name"] = line.strip()
            break

    return info


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(analysis: dict) -> None:
    """Pretty-print the analysis to the console."""
    proj = analysis["project_info"]
    products = analysis["products"]
    summary = analysis["summary"]
    spec_materials = analysis["spec_materials"]

    print("=" * 72)
    print("  ROOFING SPECIFICATION EXTRACTION REPORT  (Deterministic Regex Engine)")
    print("=" * 72)

    if proj.get("project_name"):
        print(f"  Project : {proj['project_name']}")
    if proj.get("address"):
        print(f"  Address : {proj['address']}")
    if proj.get("project_number"):
        print(f"  Proj #  : {proj['project_number']}")
    if proj.get("date"):
        print(f"  Date    : {proj['date']}")

    print("-" * 72)
    print(
        f"  Found {summary['total_unique_products']} unique products "
        f"across {summary['total_categories']} categories  "
        f"({summary['total_confirmed_pricing_keys']} mapped to pricing keys)\n"
    )

    for category, prods in products.items():
        print(f"  [{category}]  ({len(prods)} items)")
        print(f"  {'-' * 60}")
        for name, info in prods.items():
            dims = f"  ({', '.join(info['dimensions'])})" if info["dimensions"] else ""
            pages_str = ", ".join(str(p) for p in info["pages"])
            pk_str = f"  →  {info['pricing_key']}" if info["pricing_key"] else "  →  (no pricing key)"
            print(f"    - {name}{dims}{pk_str}")
            print(f"      Mentions: {info['mention_count']}  |  Pages: {pages_str}")
            if info["context_snippets"]:
                print(f"      Example : \"{info['context_snippets'][0][:100]}\"")
        print()

    if spec_materials:
        print("=" * 72)
        print("  CONFIRMED SPEC MATERIALS  (machine-readable — used by roof_estimator.py)")
        print("=" * 72)
        for pk, info in spec_materials.items():
            dims = f"  [{', '.join(info['dimensions'])}]" if info["dimensions"] else ""
            pages_str = ", ".join(str(p) for p in info["pages"])
            print(f"  {pk:<45} {info['product_name']}{dims}  (pg {pages_str})")

    print("\n" + "=" * 72)
    print("  CATEGORY SUMMARY")
    print("=" * 72)
    for cat, count in summary["categories"].items():
        print(f"    {cat:<35} {count} products")
    print(f"\n    {'TOTAL':<35} {summary['total_unique_products']} products")
    print(f"    {'CONFIRMED PRICING KEYS':<35} {summary['total_confirmed_pricing_keys']}")
    print("=" * 72)


def export_json(analysis: dict, output_path: str) -> None:
    """Write the analysis result to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"\nJSON report saved to: {output_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python file_extractor.py <path_to_spec_pdf> [--json output.json]")
        print()
        print("Deterministic regex extraction of roofing materials from Specification PDFs.")
        print("No LLM calls — all matching is performed against the PRODUCT_KEYWORDS database.")
        sys.exit(1)

    pdf_path = sys.argv[1]
    json_output: Optional[str] = None

    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        if idx + 1 < len(sys.argv):
            json_output = sys.argv[idx + 1]

    logger.info("Analyzing: %s", pdf_path)
    pages = extract_text_from_pdf(pdf_path)
    logger.info("Extracted text from %d pages.", len(pages))

    analysis = analyze_text(pages)
    print_report(analysis)

    if json_output:
        export_json(analysis, json_output)


if __name__ == "__main__":
    main()
