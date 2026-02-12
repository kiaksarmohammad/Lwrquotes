"""
Roofing Drawing / Specification PDF Analyzer
Extracts products and materials needed for a roofing project from IFT-style PDFs.
"""

import re
import sys
import json
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

from backend.database import PRODUCT_KEYWORDS

# Patterns to capture dimensions / thicknesses tied to a product
DIMENSION_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mm|cm|m|inch|in|ft|mil)\b", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> list[tuple[int, str]]:
    """Return a list of (page_number, text) tuples from the PDF."""
    pages: list[tuple[int, str]] = []

    # Prefer pdfplumber – much better at extracting text from drawing PDFs
    if pdfplumber is not None:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append((i, text))
        return pages

    # Fallback to PyPDF2
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
# Analysis engine
# ---------------------------------------------------------------------------

def analyze_text(pages: list[tuple[int, str]]) -> dict:
    """
    Scan every page for product keywords.

    Returns a dict:
      {
        "project_info": { ... },
        "products": {
            "Category": {
                "Product Name": {
                    "pages": [1, 3],
                    "count": 5,
                    "context_snippets": ["...matched line..."],
                    "dimensions": ["50mm", ...]
                }
            }
        },
        "summary": { ... }
      }
    """
    results: dict[str, dict[str, dict]] = {}
    project_info = _extract_project_info(pages)

    for page_num, text in pages:
        lines = text.split("\n")
        for line in lines:
            clean = line.strip()
            if not clean:
                continue

            for category, patterns in PRODUCT_KEYWORDS.items():
                for pattern, product_name in patterns.items():
                    if re.search(pattern, clean, re.IGNORECASE):
                        if category not in results:
                            results[category] = {}
                        if product_name not in results[category]:
                            results[category][product_name] = {
                                "pages": [],
                                "count": 0,
                                "context_snippets": [],
                                "dimensions": [],
                            }

                        entry = results[category][product_name]
                        entry["count"] += 1
                        if page_num not in entry["pages"]:
                            entry["pages"].append(page_num)

                        # Keep unique context lines (cap at 5)
                        snippet = clean[:200]
                        if snippet not in entry["context_snippets"] and len(entry["context_snippets"]) < 5:
                            entry["context_snippets"].append(snippet)

                        # Extract any dimensions on that line
                        for m in DIMENSION_PATTERN.finditer(clean):
                            dim = f"{m.group(1)}{m.group(2).lower()}"
                            if dim not in entry["dimensions"]:
                                entry["dimensions"].append(dim)

    # Build summary
    total_products = sum(
        len(prods) for prods in results.values()
    )
    summary = {
        "total_categories": len(results),
        "total_unique_products": total_products,
        "categories": {cat: len(prods) for cat, prods in results.items()},
    }

    return {
        "project_info": project_info,
        "products": results,
        "summary": summary,
    }


def _extract_project_info(pages: list[tuple[int, str]]) -> dict:
    """Try to pull project metadata from the first couple of pages."""
    info: dict[str, str | None] = {
        "project_name": None,
        "address": None,
        "project_number": None,
        "date": None,
        "consultant": None,
        "client": None,
    }
    # Only look at first 2 pages for metadata
    combined = "\n".join(text for _, text in pages[:2])

    # Project number
    m = re.search(r"Project\s*No\.?\s*:?\s*(\S+)", combined, re.IGNORECASE)
    if m:
        info["project_number"] = m.group(1)

    # Date
    m = re.search(r"Date\s*:?\s*([\w\s\-,]+\d{4})", combined, re.IGNORECASE)
    if m:
        info["date"] = m.group(1).strip()

    # Address – look for a Canadian-style address pattern or street
    m = re.search(r"(\d+\s+\d+\s+Street\s+\w+)", combined, re.IGNORECASE)
    if m:
        info["address"] = m.group(1)

    # City, Province
    m = re.search(r"(Calgary|Edmonton|Toronto|Vancouver|Ottawa|Winnipeg)\s*,?\s*(Alberta|Ontario|BC|Manitoba|Saskatchewan|Quebec)", combined, re.IGNORECASE)
    if m and info["address"]:
        info["address"] += f", {m.group(1)}, {m.group(2)}"
    elif m:
        info["address"] = f"{m.group(1)}, {m.group(2)}"

    # Project name – look for lines near top that look like a title
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

    print("=" * 70)
    print("  ROOFING PRODUCT EXTRACTION REPORT")
    print("=" * 70)

    if proj.get("project_name"):
        print(f"  Project : {proj['project_name']}")
    if proj.get("address"):
        print(f"  Address : {proj['address']}")
    if proj.get("project_number"):
        print(f"  Proj #  : {proj['project_number']}")
    if proj.get("date"):
        print(f"  Date    : {proj['date']}")
    print("-" * 70)
    print(f"  Found {summary['total_unique_products']} unique products "
          f"across {summary['total_categories']} categories\n")

    for category, prods in products.items():
        print(f"  [{category}]  ({len(prods)} items)")
        print(f"  {'-' * 60}")
        for name, info in prods.items():
            dims = f"  ({', '.join(info['dimensions'])})" if info['dimensions'] else ""
            pages_str = ", ".join(str(p) for p in info["pages"])
            print(f"    - {name}{dims}")
            print(f"      Mentions: {info['count']}  |  Pages: {pages_str}")
            if info["context_snippets"]:
                print(f"      Example : \"{info['context_snippets'][0][:100]}\"")
        print()

    print("=" * 70)
    print("  CATEGORY SUMMARY")
    print("=" * 70)
    for cat, count in summary["categories"].items():
        print(f"    {cat:<35} {count} products")
    print(f"\n    {'TOTAL':<35} {summary['total_unique_products']} products")
    print("=" * 70)


def export_json(analysis: dict, output_path: str) -> None:
    """Write the analysis result to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"\nJSON report saved to: {output_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python file_extractor.py <path_to_pdf> [--json output.json]")
        print("\nExtracts roofing product keywords from IFT drawings / spec PDFs.")
        sys.exit(1)

    pdf_path = sys.argv[1]
    json_output = None
    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        if idx + 1 < len(sys.argv):
            json_output = sys.argv[idx + 1]

    print(f"Analyzing: {pdf_path}\n")
    pages = extract_text_from_pdf(pdf_path)
    print(f"Extracted text from {len(pages)} pages.\n")

    analysis = analyze_text(pages)
    print_report(analysis)

    if json_output:
        export_json(analysis, json_output)


if __name__ == "__main__":
    main()
