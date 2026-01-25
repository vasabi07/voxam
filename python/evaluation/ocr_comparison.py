"""
OCR Model Comparison Script

Compares multiple OCR models on problem pages detected by encoding check.
Tests Gemini and DeepInfra models side-by-side on the same pages.

Usage:
    export GOOGLE_API_KEY=your_key
    export DEEPINFRA_API_KEY=your_key

    # Compare all models on detected problem pages
    python evaluation/ocr_comparison.py

    # Compare specific models
    python evaluation/ocr_comparison.py --models gemini,olmocr2,gemma-12b

    # Test specific document
    python evaluation/ocr_comparison.py --doc cs

    # Test specific page
    python evaluation/ocr_comparison.py --doc physics --page 5
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict, field
from io import BytesIO
from pathlib import Path
from typing import Optional

import httpx
from pdf2image import convert_from_path
from PIL import Image

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.encoding_check import check_pdf_encoding, DEEPINFRA_OCR_MODELS, DEEPINFRA_OCR_PROMPT


# =============================================================================
# Configuration
# =============================================================================

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

# All models to compare
OCR_MODELS = {
    "gemini": {
        "provider": "gemini",
        "name": "Gemini 2.0 Flash",
        "input_cost_per_m": 0.10,
        "output_cost_per_m": 0.40,
    },
    "olmocr2": {
        "provider": "deepinfra",
        "model_key": "olmocr2",
        "name": "olmOCR-2 (7B)",
        "input_cost_per_m": 0.09,
        "output_cost_per_m": 0.19,
    },
    "gemma-12b": {
        "provider": "deepinfra",
        "model_key": "gemma-12b",
        "name": "Gemma-3-12B-IT",
        "input_cost_per_m": 0.04,
        "output_cost_per_m": 0.13,
    },
    "mistral-small": {
        "provider": "deepinfra",
        "model_key": "mistral-small",
        "name": "Mistral-Small-3.1-24B",
        "input_cost_per_m": 0.075,
        "output_cost_per_m": 0.20,
    },
    "deepseek-ocr": {
        "provider": "deepinfra",
        "model_key": "deepseek-ocr",
        "name": "DeepSeek-OCR",
        "input_cost_per_m": 0.03,
        "output_cost_per_m": 0.10,
    },
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PageOCRResult:
    """Result from OCR'ing a single page with one model."""
    page_num: int
    model_name: str
    text: str
    char_count: int
    latency_ms: int
    tokens_input: int = 0
    tokens_output: int = 0
    error: Optional[str] = None

    # Quality metrics (computed after extraction)
    has_latex: bool = False
    latex_count: int = 0
    has_tables: bool = False
    table_count: int = 0
    has_code_blocks: bool = False


@dataclass
class ModelComparison:
    """Comparison results for a single model across all test pages."""
    model_key: str
    model_name: str
    provider: str
    total_pages: int
    total_chars: int
    total_latency_ms: int
    avg_chars_per_page: float
    avg_latency_per_page_ms: float
    total_tokens_input: int
    total_tokens_output: int
    cost_estimate: float
    cost_per_1000_pages: float

    # Quality metrics
    pages_with_latex: int = 0
    total_latex_count: int = 0
    pages_with_tables: int = 0
    pages_with_code: int = 0

    page_results: list = field(default_factory=list)


# =============================================================================
# OCR Functions
# =============================================================================

def ocr_page_gemini(image_b64: str, page_num: int, api_key: str) -> PageOCRResult:
    """OCR a page using Gemini API."""
    start_time = time.time()

    prompt = "Extract ALL text from this image. Preserve formatting, line breaks, and structure. Include all equations, formulas, and symbols. Convert mathematical equations to LaTeX format (wrapped in $ or $$). Output only the extracted text."

    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/png", "data": image_b64}}
                    ]
                }]
            },
            timeout=120.0
        )

        latency_ms = int((time.time() - start_time) * 1000)

        if response.status_code == 200:
            result = response.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"]

            # Estimate tokens (Gemini doesn't always return usage)
            usage = result.get("usageMetadata", {})
            tokens_input = usage.get("promptTokenCount", len(prompt) // 4 + 1600)  # ~1600 for image
            tokens_output = usage.get("candidatesTokenCount", len(text) // 4)

            return PageOCRResult(
                page_num=page_num,
                model_name="Gemini 2.0 Flash",
                text=text,
                char_count=len(text),
                latency_ms=latency_ms,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
            )
        else:
            return PageOCRResult(
                page_num=page_num,
                model_name="Gemini 2.0 Flash",
                text="",
                char_count=0,
                latency_ms=latency_ms,
                error=f"HTTP {response.status_code}: {response.text[:200]}",
            )
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return PageOCRResult(
            page_num=page_num,
            model_name="Gemini 2.0 Flash",
            text="",
            char_count=0,
            latency_ms=latency_ms,
            error=str(e),
        )


def ocr_page_deepinfra(
    image_b64: str,
    page_num: int,
    api_key: str,
    model_key: str
) -> PageOCRResult:
    """OCR a page using DeepInfra API."""
    start_time = time.time()

    model_info = DEEPINFRA_OCR_MODELS.get(model_key)
    if not model_info:
        return PageOCRResult(
            page_num=page_num,
            model_name=model_key,
            text="",
            char_count=0,
            latency_ms=0,
            error=f"Unknown model: {model_key}",
        )

    model_id = model_info["id"]
    model_name = model_info["name"]

    try:
        response = httpx.post(
            "https://api.deepinfra.com/v1/openai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": DEEPINFRA_OCR_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}"
                                },
                            },
                        ],
                    }
                ],
                "max_tokens": 4096,
            },
            timeout=120.0,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        if response.status_code == 200:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return PageOCRResult(
                page_num=page_num,
                model_name=model_name,
                text=text,
                char_count=len(text),
                latency_ms=latency_ms,
                tokens_input=usage.get("prompt_tokens", 0),
                tokens_output=usage.get("completion_tokens", 0),
            )
        else:
            return PageOCRResult(
                page_num=page_num,
                model_name=model_name,
                text="",
                char_count=0,
                latency_ms=latency_ms,
                error=f"HTTP {response.status_code}: {response.text[:200]}",
            )
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return PageOCRResult(
            page_num=page_num,
            model_name=model_name,
            text="",
            char_count=0,
            latency_ms=latency_ms,
            error=str(e),
        )


def analyze_ocr_quality(result: PageOCRResult) -> PageOCRResult:
    """Analyze extracted text for quality metrics."""
    text = result.text

    # Detect LaTeX equations
    # $...$ or $$...$$ or \(...\) or \[...\]
    latex_patterns = [
        r'\$[^\$]+\$',           # Single $...$
        r'\$\$[^\$]+\$\$',       # Double $$...$$
        r'\\\([^\)]+\\\)',       # \(...\)
        r'\\\[[^\]]+\\\]',       # \[...\]
    ]
    latex_count = 0
    for pattern in latex_patterns:
        matches = re.findall(pattern, text)
        latex_count += len(matches)

    result.has_latex = latex_count > 0
    result.latex_count = latex_count

    # Detect tables (markdown style)
    table_pattern = r'\|[^\n]+\|'
    table_rows = re.findall(table_pattern, text)
    result.has_tables = len(table_rows) >= 2
    result.table_count = len(table_rows) // 2 if result.has_tables else 0

    # Detect code blocks
    result.has_code_blocks = "```" in text

    return result


# =============================================================================
# Main Comparison Logic
# =============================================================================

def compare_models_on_page(
    image_b64: str,
    page_num: int,
    models: list[str],
    google_api_key: Optional[str],
    deepinfra_api_key: Optional[str],
) -> dict[str, PageOCRResult]:
    """Run all models on a single page and return results."""
    results = {}

    for model_key in models:
        model_info = OCR_MODELS[model_key]

        if model_info["provider"] == "gemini":
            if not google_api_key:
                print(f"    Skipping {model_key} (no GOOGLE_API_KEY)")
                continue
            result = ocr_page_gemini(image_b64, page_num, google_api_key)
        else:  # deepinfra
            if not deepinfra_api_key:
                print(f"    Skipping {model_key} (no DEEPINFRA_API_KEY)")
                continue
            result = ocr_page_deepinfra(
                image_b64, page_num, deepinfra_api_key, model_info["model_key"]
            )

        # Analyze quality
        result = analyze_ocr_quality(result)
        results[model_key] = result

        # Print progress
        if result.error:
            print(f"    {model_key}: ERROR - {result.error[:50]}")
        else:
            latex_info = f", {result.latex_count} LaTeX" if result.has_latex else ""
            print(f"    {model_key}: {result.char_count} chars, {result.latency_ms}ms{latex_info}")

    return results


def run_comparison(
    doc_name: str,
    doc_path: Path,
    page_numbers: list[int],
    models: list[str],
    google_api_key: Optional[str],
    deepinfra_api_key: Optional[str],
) -> dict[str, ModelComparison]:
    """Run comparison for a document on specified pages."""

    print(f"\n{'='*60}")
    print(f"Document: {doc_name.upper()}")
    print(f"Path: {doc_path}")
    print(f"Testing pages: {page_numbers}")
    print(f"Models: {', '.join(models)}")
    print(f"{'='*60}")

    # Initialize results
    model_results = {
        model: {
            "pages": [],
            "total_chars": 0,
            "total_latency": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "pages_with_latex": 0,
            "total_latex_count": 0,
            "pages_with_tables": 0,
            "pages_with_code": 0,
        }
        for model in models
    }

    # Convert pages to images once
    print("\nConverting pages to images...")
    all_images = convert_from_path(str(doc_path), dpi=150)

    for page_num in page_numbers:
        if page_num > len(all_images):
            print(f"  Page {page_num} out of range, skipping")
            continue

        print(f"\n  Page {page_num}:")

        # Convert to base64
        img = all_images[page_num - 1]
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        image_b64 = base64.b64encode(buffer.getvalue()).decode()

        # Run all models
        page_results = compare_models_on_page(
            image_b64, page_num, models, google_api_key, deepinfra_api_key
        )

        # Aggregate results
        for model_key, result in page_results.items():
            model_results[model_key]["pages"].append(asdict(result))
            if not result.error:
                model_results[model_key]["total_chars"] += result.char_count
                model_results[model_key]["total_latency"] += result.latency_ms
                model_results[model_key]["total_input_tokens"] += result.tokens_input
                model_results[model_key]["total_output_tokens"] += result.tokens_output
                if result.has_latex:
                    model_results[model_key]["pages_with_latex"] += 1
                    model_results[model_key]["total_latex_count"] += result.latex_count
                if result.has_tables:
                    model_results[model_key]["pages_with_tables"] += 1
                if result.has_code_blocks:
                    model_results[model_key]["pages_with_code"] += 1

    # Build comparison objects
    comparisons = {}
    for model_key, data in model_results.items():
        valid_pages = len([p for p in data["pages"] if not p.get("error")])
        if valid_pages == 0:
            continue

        model_info = OCR_MODELS[model_key]

        # Calculate cost
        input_cost = (data["total_input_tokens"] / 1_000_000) * model_info["input_cost_per_m"]
        output_cost = (data["total_output_tokens"] / 1_000_000) * model_info["output_cost_per_m"]
        total_cost = input_cost + output_cost

        # Estimate cost per 1000 pages
        cost_per_1000 = (total_cost / valid_pages) * 1000 if valid_pages > 0 else 0

        comparisons[model_key] = ModelComparison(
            model_key=model_key,
            model_name=model_info["name"],
            provider=model_info["provider"],
            total_pages=valid_pages,
            total_chars=data["total_chars"],
            total_latency_ms=data["total_latency"],
            avg_chars_per_page=data["total_chars"] / valid_pages,
            avg_latency_per_page_ms=data["total_latency"] / valid_pages,
            total_tokens_input=data["total_input_tokens"],
            total_tokens_output=data["total_output_tokens"],
            cost_estimate=total_cost,
            cost_per_1000_pages=cost_per_1000,
            pages_with_latex=data["pages_with_latex"],
            total_latex_count=data["total_latex_count"],
            pages_with_tables=data["pages_with_tables"],
            pages_with_code=data["pages_with_code"],
            page_results=data["pages"],
        )

    return comparisons


def print_comparison_summary(doc_name: str, comparisons: dict[str, ModelComparison]):
    """Print comparison summary table."""
    print(f"\n{'='*80}")
    print(f"COMPARISON SUMMARY: {doc_name.upper()}")
    print(f"{'='*80}")

    # Header
    print(f"\n{'Model':<25} {'Chars':<10} {'Latency':<12} {'LaTeX':<10} {'Cost/1K':<12} {'Provider':<12}")
    print("-" * 80)

    # Sort by cost
    sorted_models = sorted(comparisons.values(), key=lambda x: x.cost_per_1000_pages)

    for comp in sorted_models:
        print(f"{comp.model_name:<25} "
              f"{comp.avg_chars_per_page:>8.0f}  "
              f"{comp.avg_latency_per_page_ms:>8.0f}ms  "
              f"{comp.total_latex_count:>8}  "
              f"${comp.cost_per_1000_pages:>8.2f}  "
              f"{comp.provider:<12}")

    print("-" * 80)

    # Best for each metric
    if sorted_models:
        cheapest = sorted_models[0]
        fastest = min(comparisons.values(), key=lambda x: x.avg_latency_per_page_ms)
        most_latex = max(comparisons.values(), key=lambda x: x.total_latex_count)

        print(f"\nBest cost:   {cheapest.model_name} (${cheapest.cost_per_1000_pages:.2f}/1K pages)")
        print(f"Best speed:  {fastest.model_name} ({fastest.avg_latency_per_page_ms:.0f}ms/page)")
        print(f"Most LaTeX:  {most_latex.model_name} ({most_latex.total_latex_count} equations found)")


def save_results(
    doc_name: str,
    comparisons: dict[str, ModelComparison],
    output_dir: Path
):
    """Save comparison results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON summary
    summary = {
        "document": doc_name,
        "comparisons": {k: asdict(v) for k, v in comparisons.items()},
    }
    summary_path = output_dir / f"ocr_comparison_{doc_name}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {summary_path}")

    # Save sample extractions for each model
    for model_key, comp in comparisons.items():
        if comp.page_results:
            # Get first successful page
            for page in comp.page_results:
                if not page.get("error") and page.get("text"):
                    preview_path = output_dir / f"ocr_comparison_{doc_name}_{model_key}_sample.md"
                    with open(preview_path, "w") as f:
                        f.write(f"# {doc_name.upper()} - {comp.model_name}\n\n")
                        f.write(f"**Page:** {page['page_num']}\n")
                        f.write(f"**Characters:** {page['char_count']}\n")
                        f.write(f"**Latency:** {page['latency_ms']}ms\n")
                        f.write(f"**LaTeX equations:** {page.get('latex_count', 0)}\n\n")
                        f.write("---\n\n")
                        f.write(page["text"])
                    break


def main():
    parser = argparse.ArgumentParser(description="Compare OCR models on problem pages")
    parser.add_argument(
        "--models",
        default="all",
        help="Comma-separated model keys or 'all' (default: all)",
    )
    parser.add_argument(
        "--doc",
        choices=list(TEST_DOCS.keys()) + ["all"],
        default="all",
        help="Document to test (default: all)",
    )
    parser.add_argument(
        "--page",
        type=int,
        help="Specific page to test (overrides auto-detection)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Max problem pages to test per document (default: 3)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Output directory for results",
    )

    args = parser.parse_args()

    # Get API keys
    google_api_key = os.getenv("GOOGLE_API_KEY")
    deepinfra_api_key = os.getenv("DEEPINFRA_API_KEY")

    if not google_api_key and not deepinfra_api_key:
        print("ERROR: No API keys found. Set GOOGLE_API_KEY and/or DEEPINFRA_API_KEY")
        return

    # Select models
    if args.models == "all":
        models = list(OCR_MODELS.keys())
    else:
        models = [m.strip() for m in args.models.split(",")]
        invalid = [m for m in models if m not in OCR_MODELS]
        if invalid:
            print(f"ERROR: Unknown models: {invalid}")
            print(f"Available: {list(OCR_MODELS.keys())}")
            return

    # Select documents
    if args.doc == "all":
        docs = list(TEST_DOCS.keys())
    else:
        docs = [args.doc]

    all_comparisons = {}

    for doc_name in docs:
        doc_info = TEST_DOCS[doc_name]
        doc_path = doc_info["path"]

        if not doc_path.exists():
            print(f"WARNING: {doc_path} not found, skipping {doc_name}")
            continue

        # Determine pages to test
        if args.page:
            page_numbers = [args.page]
        else:
            # Use encoding check to find problem pages
            print(f"\nAnalyzing {doc_name} for problem pages...")
            encoding_result = check_pdf_encoding(str(doc_path))

            problem_pages = encoding_result["problem_page_numbers"]
            if not problem_pages:
                # If no problem pages, test first 3 pages
                print(f"  No encoding issues detected, testing first {args.max_pages} pages")
                problem_pages = list(range(1, min(args.max_pages + 1, encoding_result["total_pages"] + 1)))
            else:
                print(f"  Found {len(problem_pages)} problem pages: {problem_pages[:10]}{'...' if len(problem_pages) > 10 else ''}")
                problem_pages = problem_pages[:args.max_pages]

            page_numbers = problem_pages

        # Run comparison
        comparisons = run_comparison(
            doc_name, doc_path, page_numbers, models,
            google_api_key, deepinfra_api_key
        )

        if comparisons:
            print_comparison_summary(doc_name, comparisons)
            save_results(doc_name, comparisons, args.output_dir)
            all_comparisons[doc_name] = comparisons

    # Print overall summary
    if len(all_comparisons) > 1:
        print(f"\n{'='*80}")
        print("OVERALL SUMMARY (All Documents)")
        print(f"{'='*80}")

        # Aggregate across documents
        model_totals = {}
        for doc_name, comparisons in all_comparisons.items():
            for model_key, comp in comparisons.items():
                if model_key not in model_totals:
                    model_totals[model_key] = {
                        "name": comp.model_name,
                        "total_chars": 0,
                        "total_latency": 0,
                        "total_latex": 0,
                        "total_pages": 0,
                        "total_cost": 0,
                    }
                model_totals[model_key]["total_chars"] += comp.total_chars
                model_totals[model_key]["total_latency"] += comp.total_latency_ms
                model_totals[model_key]["total_latex"] += comp.total_latex_count
                model_totals[model_key]["total_pages"] += comp.total_pages
                model_totals[model_key]["total_cost"] += comp.cost_estimate

        print(f"\n{'Model':<25} {'Avg Chars':<12} {'Avg Latency':<14} {'Total LaTeX':<12} {'Cost/1K':<12}")
        print("-" * 75)

        for model_key, totals in sorted(model_totals.items(), key=lambda x: (x[1]["total_cost"] / x[1]["total_pages"] * 1000) if x[1]["total_pages"] > 0 else float('inf')):
            pages = totals["total_pages"]
            if pages == 0:
                continue
            avg_chars = totals["total_chars"] / pages
            avg_latency = totals["total_latency"] / pages
            cost_per_1k = (totals["total_cost"] / pages) * 1000

            print(f"{totals['name']:<25} {avg_chars:>10.0f}  {avg_latency:>10.0f}ms  {totals['total_latex']:>10}  ${cost_per_1k:>9.2f}")


if __name__ == "__main__":
    main()
