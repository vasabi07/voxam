"""
Current Approach Evaluation Script

Tests the existing VOXAM ingestion pipeline:
1. PyMuPDF text extraction (fast, free)
2. Gemini 2.0 Flash OCR (for problem pages)
3. Combined hybrid approach

Usage:
    python evaluation/current_approach_evaluate.py --method pymupdf
    python evaluation/current_approach_evaluate.py --method gemini
    python evaluation/current_approach_evaluate.py --method all
"""

import argparse
import asyncio
import base64
import json
import os
import time
from dataclasses import dataclass, asdict
from io import BytesIO
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import httpx
from pdf2image import convert_from_path

# Load env vars
from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
DEEPINFRA_API_KEY = os.environ.get("DEEPINFRA_API_KEY")

# Test documents
TEST_DOCS = {
    "cs": {
        "path": Path(__file__).parent.parent / "cs.pdf",
        "description": "Computer Science - code blocks, algorithms, flowcharts",
    },
    "physics": {
        "path": Path(__file__).parent.parent / "physics-chapter 3.pdf",
        "description": "Physics - equations, diagrams, formulas, units",
    },
    "chemistry": {
        "path": Path(__file__).parent.parent / "lech103.pdf",
        "description": "Chemistry - chemical formulas, molecular structures, tables",
    },
    "biology": {
        "path": Path(__file__).parent.parent / "chapter1.pdf",
        "description": "Biology - diagrams, terminology, figures, dense text",
    },
}


@dataclass
class ExtractionResult:
    """Result from extracting a document."""
    doc_name: str
    method: str
    total_pages: int
    total_chars: int
    total_time_seconds: float
    chars_per_page: float
    seconds_per_page: float
    cost_estimate: float
    markdown_preview: str
    has_tables: bool
    has_equations: bool
    has_code_blocks: bool
    error: Optional[str] = None


def extract_with_pymupdf(pdf_path: Path) -> tuple[str, int, float]:
    """Extract text using PyMuPDF (current fast approach)."""
    start_time = time.time()

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    all_text = []
    for page_num, page in enumerate(doc, 1):
        page_text = page.get_text("text")
        all_text.append(f"[PAGE {page_num}]\n{page_text}")

    doc.close()

    combined_text = "\n\n".join(all_text)
    elapsed = time.time() - start_time

    return combined_text, total_pages, elapsed


async def extract_with_gemini(pdf_path: Path) -> tuple[str, int, float, float]:
    """Extract text using Gemini 2.0 Flash OCR (current OCR approach)."""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not set")

    start_time = time.time()

    # Convert PDF to images
    images = convert_from_path(str(pdf_path), dpi=150)
    total_pages = len(images)

    all_text = []
    total_tokens = 0

    async with httpx.AsyncClient() as client:
        for page_num, img in enumerate(images, 1):
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            try:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{
                            "parts": [
                                {"text": "Extract ALL text from this image. Preserve formatting, line breaks, and structure. Convert any mathematical equations to LaTeX format. Preserve tables as markdown. Just output the text, nothing else."},
                                {"inline_data": {"mime_type": "image/png", "data": b64}}
                            ]
                        }]
                    },
                    timeout=60.0
                )

                if response.status_code == 200:
                    result = response.json()
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    # Estimate tokens from usage metadata if available
                    usage = result.get("usageMetadata", {})
                    total_tokens += usage.get("totalTokenCount", len(text) // 4)
                    all_text.append(f"[PAGE {page_num}]\n{text}")
                    print(f"    Page {page_num}: {len(text)} chars")
                else:
                    print(f"    Page {page_num}: ERROR {response.status_code}")
                    all_text.append(f"[PAGE {page_num}]\n[ERROR: {response.status_code}]")

            except Exception as e:
                print(f"    Page {page_num}: ERROR {e}")
                all_text.append(f"[PAGE {page_num}]\n[ERROR: {e}]")

    combined_text = "\n\n".join(all_text)
    elapsed = time.time() - start_time

    # Gemini 2.0 Flash pricing: $0.10 per 1M input tokens (images)
    # Estimate: ~1000 tokens per image
    cost = (total_pages * 1000 / 1_000_000) * 0.10  # Input cost
    cost += (total_tokens / 1_000_000) * 0.40  # Output cost

    return combined_text, total_pages, elapsed, cost


def evaluate_pymupdf(doc_name: str, doc_path: Path) -> ExtractionResult:
    """Evaluate PyMuPDF extraction."""
    print(f"  Processing {doc_name} with PyMuPDF...")

    try:
        text, total_pages, elapsed = extract_with_pymupdf(doc_path)

        # Detect features
        has_tables = "|" in text and "---" in text
        has_equations = "$" in text or "\\(" in text or "\\[" in text
        has_code_blocks = "```" in text or "def " in text or "function " in text

        print(f"    {len(text):,} chars, {total_pages} pages, {elapsed:.2f}s")

        return ExtractionResult(
            doc_name=doc_name,
            method="pymupdf",
            total_pages=total_pages,
            total_chars=len(text),
            total_time_seconds=elapsed,
            chars_per_page=len(text) / total_pages,
            seconds_per_page=elapsed / total_pages,
            cost_estimate=0.0,  # Free!
            markdown_preview=text[:5000],
            has_tables=has_tables,
            has_equations=has_equations,
            has_code_blocks=has_code_blocks,
        )

    except Exception as e:
        return ExtractionResult(
            doc_name=doc_name,
            method="pymupdf",
            total_pages=0,
            total_chars=0,
            total_time_seconds=0,
            chars_per_page=0,
            seconds_per_page=0,
            cost_estimate=0,
            markdown_preview="",
            has_tables=False,
            has_equations=False,
            has_code_blocks=False,
            error=str(e),
        )


async def evaluate_gemini(doc_name: str, doc_path: Path) -> ExtractionResult:
    """Evaluate Gemini 2.0 Flash OCR."""
    print(f"  Processing {doc_name} with Gemini 2.0 Flash...")

    try:
        text, total_pages, elapsed, cost = await extract_with_gemini(doc_path)

        # Detect features
        has_tables = "|" in text and "---" in text
        has_equations = "$" in text or "\\(" in text or "\\[" in text
        has_code_blocks = "```" in text

        print(f"    Total: {len(text):,} chars, {total_pages} pages, {elapsed:.2f}s, ${cost:.4f}")

        return ExtractionResult(
            doc_name=doc_name,
            method="gemini-2.0-flash",
            total_pages=total_pages,
            total_chars=len(text),
            total_time_seconds=elapsed,
            chars_per_page=len(text) / total_pages,
            seconds_per_page=elapsed / total_pages,
            cost_estimate=cost,
            markdown_preview=text[:5000],
            has_tables=has_tables,
            has_equations=has_equations,
            has_code_blocks=has_code_blocks,
        )

    except Exception as e:
        return ExtractionResult(
            doc_name=doc_name,
            method="gemini-2.0-flash",
            total_pages=0,
            total_chars=0,
            total_time_seconds=0,
            chars_per_page=0,
            seconds_per_page=0,
            cost_estimate=0,
            markdown_preview="",
            has_tables=False,
            has_equations=False,
            has_code_blocks=False,
            error=str(e),
        )


async def run_evaluation(method: str) -> list[ExtractionResult]:
    """Run evaluation for specified method."""

    results = []

    for doc_name, doc_info in TEST_DOCS.items():
        doc_path = doc_info["path"]

        if not doc_path.exists():
            print(f"  WARNING: {doc_path} not found, skipping")
            continue

        if method == "pymupdf":
            result = evaluate_pymupdf(doc_name, doc_path)
        elif method == "gemini":
            result = await evaluate_gemini(doc_name, doc_path)
        else:
            raise ValueError(f"Unknown method: {method}")

        results.append(result)

    return results


def print_summary(method: str, results: list[ExtractionResult]):
    """Print evaluation summary."""
    valid_results = [r for r in results if not r.error]

    total_chars = sum(r.total_chars for r in valid_results)
    total_pages = sum(r.total_pages for r in valid_results)
    total_time = sum(r.total_time_seconds for r in valid_results)
    total_cost = sum(r.cost_estimate for r in valid_results)

    print(f"\n{'='*60}")
    print(f"SUMMARY: {method.upper()}")
    print(f"{'='*60}")
    print(f"Documents processed: {len(valid_results)}")
    print(f"Total pages: {total_pages}")
    print(f"Total characters: {total_chars:,}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Avg time/page: {total_time/total_pages:.3f}s")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"Cost per 1000 pages: ${(total_cost/total_pages)*1000:.2f}")
    print()


def save_results(method: str, results: list[ExtractionResult], output_dir: Path):
    """Save evaluation results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save summary
    summary_data = {
        "method": method,
        "results": [asdict(r) for r in results],
    }
    summary_path = output_dir / f"current_{method}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Summary saved: {summary_path}")

    # Save previews
    for result in results:
        if result.error:
            continue

        preview_path = output_dir / f"current_{method}_{result.doc_name}_preview.md"
        with open(preview_path, "w") as f:
            f.write(f"# {result.doc_name.upper()} - {method}\n\n")
            f.write(f"**Pages:** {result.total_pages}\n")
            f.write(f"**Characters:** {result.total_chars:,}\n")
            f.write(f"**Time:** {result.total_time_seconds:.2f}s\n")
            f.write(f"**Cost:** ${result.cost_estimate:.4f}\n")
            f.write(f"**Tables detected:** {'Yes' if result.has_tables else 'No'}\n")
            f.write(f"**Equations detected:** {'Yes' if result.has_equations else 'No'}\n")
            f.write(f"**Code blocks detected:** {'Yes' if result.has_code_blocks else 'No'}\n\n")
            f.write("---\n\n")
            f.write("## Preview (first 5000 chars)\n\n")
            f.write(result.markdown_preview)
        print(f"Preview saved: {preview_path}")


async def main():
    parser = argparse.ArgumentParser(description="Evaluate current VOXAM ingestion approach")
    parser.add_argument(
        "--method",
        choices=["pymupdf", "gemini", "all"],
        default="all",
        help="Extraction method to evaluate",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Output directory for results",
    )

    args = parser.parse_args()

    methods = ["pymupdf", "gemini"] if args.method == "all" else [args.method]

    for method in methods:
        print(f"\n{'='*60}")
        print(f"EVALUATING: {method.upper()} (Current Approach)")
        print(f"{'='*60}\n")

        if method == "gemini" and not GOOGLE_API_KEY:
            print("ERROR: GOOGLE_API_KEY not set, skipping Gemini evaluation")
            continue

        results = await run_evaluation(method)
        print_summary(method, results)
        save_results(method, results, args.output_dir)


if __name__ == "__main__":
    asyncio.run(main())
