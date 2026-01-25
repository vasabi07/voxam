"""
Replicate VLM/OCR Model Evaluation Script

Tests models via Replicate API:
- dots.ocr (sljeff/dots.ocr) - Best multilingual OCR
- Marker (cuuupid/marker) - PDF to markdown converter

Usage:
    export REPLICATE_API_TOKEN=your_token
    python evaluation/replicate_evaluate.py --model dots-ocr
    python evaluation/replicate_evaluate.py --model marker
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

import httpx
from pdf2image import convert_from_path
from PIL import Image

# Replicate models
REPLICATE_MODELS = {
    "dots-ocr": {
        "version": "sljeff/dots.ocr:latest",
        "name": "dots.ocr (1.7B)",
        "cost_per_run": 0.018,  # ~19s on L40S
        "input_type": "image",
    },
    "marker": {
        "version": "cuuupid/marker:latest",
        "name": "Marker (PDF→MD)",
        "cost_per_run": 0.02,
        "input_type": "pdf",
    },
}

# Test documents
TEST_DOCS = {
    "cs": {
        "path": Path(__file__).parent.parent / "cs.pdf",
        "description": "Computer Science - code blocks, algorithms, flowcharts",
        "test_pages": [1, 3, 5],
    },
    "physics": {
        "path": Path(__file__).parent.parent / "physics-chapter 3.pdf",
        "description": "Physics - equations, diagrams, formulas, units",
        "test_pages": [1, 5, 10],
    },
    "chemistry": {
        "path": Path(__file__).parent.parent / "lech103.pdf",
        "description": "Chemistry - chemical formulas, molecular structures, tables",
        "test_pages": [1, 5, 10],
    },
    "biology": {
        "path": Path(__file__).parent.parent / "chapter1.pdf",
        "description": "Biology - diagrams, terminology, figures, dense text",
        "test_pages": [1, 3, 5],
    },
}


@dataclass
class PageResult:
    """Result from extracting a single page."""
    page_num: int
    text: str
    latency_ms: int
    error: Optional[str] = None


@dataclass
class DocumentResult:
    """Result from extracting a document."""
    doc_name: str
    model_name: str
    pages_tested: int
    total_chars: int
    total_latency_ms: int
    avg_chars_per_page: float
    avg_latency_per_page_ms: float
    cost_estimate: float
    page_results: list[dict]
    markdown_preview: str
    has_tables: bool
    has_equations: bool
    has_code_blocks: bool


async def run_replicate_prediction(
    client: httpx.AsyncClient,
    model_version: str,
    input_data: dict,
    api_token: str,
) -> dict:
    """Run a Replicate prediction and wait for completion."""

    # Create prediction
    response = await client.post(
        "https://api.replicate.com/v1/predictions",
        headers={
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
        },
        json={
            "version": model_version,
            "input": input_data,
        },
        timeout=30.0,
    )

    if response.status_code != 201:
        raise Exception(f"Failed to create prediction: {response.text}")

    prediction = response.json()
    prediction_id = prediction["id"]

    # Poll for completion
    while True:
        response = await client.get(
            f"https://api.replicate.com/v1/predictions/{prediction_id}",
            headers={"Authorization": f"Token {api_token}"},
            timeout=30.0,
        )

        prediction = response.json()
        status = prediction["status"]

        if status == "succeeded":
            return prediction
        elif status in ["failed", "canceled"]:
            raise Exception(f"Prediction {status}: {prediction.get('error', 'Unknown error')}")

        await asyncio.sleep(2)


async def extract_page_dots_ocr(
    client: httpx.AsyncClient,
    model_info: dict,
    image: Image.Image,
    page_num: int,
    api_token: str,
) -> PageResult:
    """Extract text from a page using dots.ocr."""

    # Convert image to base64 data URI
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    image_b64 = base64.b64encode(buffer.getvalue()).decode()
    data_uri = f"data:image/png;base64,{image_b64}"

    start_time = time.time()

    try:
        # Get the actual model version
        response = await client.get(
            "https://api.replicate.com/v1/models/sljeff/dots.ocr",
            headers={"Authorization": f"Token {api_token}"},
            timeout=30.0,
        )
        model_data = response.json()
        version = model_data["latest_version"]["id"]

        prediction = await run_replicate_prediction(
            client,
            version,
            {"image": data_uri},
            api_token,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract text from output
        output = prediction.get("output", "")
        if isinstance(output, list):
            text = "\n".join(output)
        else:
            text = str(output)

        return PageResult(
            page_num=page_num,
            text=text,
            latency_ms=latency_ms,
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return PageResult(
            page_num=page_num,
            text="",
            latency_ms=latency_ms,
            error=str(e),
        )


async def extract_with_marker(
    client: httpx.AsyncClient,
    model_info: dict,
    pdf_path: Path,
    api_token: str,
) -> tuple[str, int]:
    """Extract full PDF using Marker."""

    # Read PDF as base64
    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode()
    data_uri = f"data:application/pdf;base64,{pdf_b64}"

    start_time = time.time()

    try:
        # Get the actual model version
        response = await client.get(
            "https://api.replicate.com/v1/models/cuuupid/marker",
            headers={"Authorization": f"Token {api_token}"},
            timeout=30.0,
        )
        model_data = response.json()
        version = model_data["latest_version"]["id"]

        prediction = await run_replicate_prediction(
            client,
            version,
            {"document": data_uri},
            api_token,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract text from output
        output = prediction.get("output", "")
        if isinstance(output, dict):
            text = output.get("markdown", str(output))
        elif isinstance(output, list):
            text = "\n".join(str(o) for o in output)
        else:
            text = str(output)

        return text, latency_ms

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return f"ERROR: {e}", latency_ms


async def evaluate_document_dots_ocr(
    model_info: dict,
    doc_name: str,
    doc_path: Path,
    test_pages: list[int],
    api_token: str,
) -> DocumentResult:
    """Evaluate dots.ocr on a document."""

    print(f"  Processing {doc_name} with {model_info['name']}...")

    # Convert PDF pages to images
    images = convert_from_path(str(doc_path), dpi=150)
    total_pages = len(images)

    # Filter test pages to valid range
    valid_pages = [p for p in test_pages if p <= total_pages]

    page_results = []

    async with httpx.AsyncClient() as client:
        for page_num in valid_pages:
            image = images[page_num - 1]  # 0-indexed
            result = await extract_page_dots_ocr(
                client, model_info, image, page_num, api_token
            )
            page_results.append(result)

            if result.error:
                print(f"    Page {page_num}: ERROR - {result.error[:50]}")
            else:
                print(f"    Page {page_num}: {len(result.text)} chars, {result.latency_ms}ms")

    # Calculate aggregates
    valid_results = [r for r in page_results if not r.error]
    total_chars = sum(len(r.text) for r in valid_results)
    total_latency = sum(r.latency_ms for r in valid_results)

    # Combine text for preview
    combined_text = "\n\n---\n\n".join(
        f"## Page {r.page_num}\n\n{r.text}"
        for r in valid_results
    )

    # Detect features
    has_tables = "|" in combined_text and "---" in combined_text
    has_equations = "$" in combined_text or "\\(" in combined_text
    has_code_blocks = "```" in combined_text

    # Cost estimate
    cost_estimate = len(valid_results) * model_info["cost_per_run"]

    return DocumentResult(
        doc_name=doc_name,
        model_name=model_info["name"],
        pages_tested=len(valid_results),
        total_chars=total_chars,
        total_latency_ms=total_latency,
        avg_chars_per_page=total_chars / len(valid_results) if valid_results else 0,
        avg_latency_per_page_ms=total_latency / len(valid_results) if valid_results else 0,
        cost_estimate=cost_estimate,
        page_results=[asdict(r) for r in page_results],
        markdown_preview=combined_text[:5000],
        has_tables=has_tables,
        has_equations=has_equations,
        has_code_blocks=has_code_blocks,
    )


async def evaluate_document_marker(
    model_info: dict,
    doc_name: str,
    doc_path: Path,
    api_token: str,
) -> DocumentResult:
    """Evaluate Marker on a document (processes full PDF)."""

    print(f"  Processing {doc_name} with {model_info['name']}...")

    async with httpx.AsyncClient() as client:
        text, latency_ms = await extract_with_marker(
            client, model_info, doc_path, api_token
        )

    # Estimate pages from PDF
    images = convert_from_path(str(doc_path), dpi=72)  # Low DPI just for count
    total_pages = len(images)

    # Detect features
    has_tables = "|" in text and "---" in text
    has_equations = "$" in text or "\\(" in text
    has_code_blocks = "```" in text

    error = None
    if text.startswith("ERROR:"):
        error = text
        text = ""

    return DocumentResult(
        doc_name=doc_name,
        model_name=model_info["name"],
        pages_tested=total_pages if not error else 0,
        total_chars=len(text),
        total_latency_ms=latency_ms,
        avg_chars_per_page=len(text) / total_pages if total_pages and not error else 0,
        avg_latency_per_page_ms=latency_ms / total_pages if total_pages and not error else 0,
        cost_estimate=model_info["cost_per_run"],
        page_results=[{"page_num": 0, "text": text[:1000], "latency_ms": latency_ms, "error": error}],
        markdown_preview=text[:5000],
        has_tables=has_tables,
        has_equations=has_equations,
        has_code_blocks=has_code_blocks,
    )


async def run_evaluation(model_key: str, api_token: str) -> list[DocumentResult]:
    """Run evaluation for a specific model."""

    model_info = REPLICATE_MODELS[model_key]

    print(f"\n{'='*60}")
    print(f"EVALUATING: {model_info['name']}")
    print(f"{'='*60}\n")

    results = []

    for doc_name, doc_info in TEST_DOCS.items():
        doc_path = doc_info["path"]

        if not doc_path.exists():
            print(f"  WARNING: {doc_path} not found, skipping")
            continue

        if model_key == "dots-ocr":
            result = await evaluate_document_dots_ocr(
                model_info, doc_name, doc_path, doc_info["test_pages"], api_token
            )
        elif model_key == "marker":
            result = await evaluate_document_marker(
                model_info, doc_name, doc_path, api_token
            )
        else:
            raise ValueError(f"Unknown model: {model_key}")

        results.append(result)

        # Print summary
        print(f"  Summary: {result.total_chars:,} chars")
        print(f"           {result.avg_latency_per_page_ms:.0f}ms/page, ${result.cost_estimate:.4f}")
        print(f"           Tables: {'Yes' if result.has_tables else 'No'}, "
              f"Equations: {'Yes' if result.has_equations else 'No'}")
        print()

    return results


def print_summary(model_key: str, results: list[DocumentResult]):
    """Print evaluation summary."""
    model_info = REPLICATE_MODELS[model_key]

    total_chars = sum(r.total_chars for r in results)
    total_latency = sum(r.total_latency_ms for r in results)
    total_pages = sum(r.pages_tested for r in results)
    total_cost = sum(r.cost_estimate for r in results)

    print(f"\n{'='*60}")
    print(f"SUMMARY: {model_info['name']}")
    print(f"{'='*60}")
    print(f"Documents processed: {len(results)}")
    print(f"Pages tested: {total_pages}")
    print(f"Total characters: {total_chars:,}")
    print(f"Total latency: {total_latency:,}ms ({total_latency/1000:.1f}s)")
    if total_pages:
        print(f"Avg latency/page: {total_latency/total_pages:.0f}ms")
    print(f"Total cost: ${total_cost:.4f}")
    print()


def save_results(model_key: str, results: list[DocumentResult], output_dir: Path):
    """Save evaluation results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_data = {
        "model": REPLICATE_MODELS[model_key],
        "results": [asdict(r) for r in results],
    }
    summary_path = output_dir / f"replicate_{model_key}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Summary saved to: {summary_path}")

    for result in results:
        preview_path = output_dir / f"replicate_{model_key}_{result.doc_name}_preview.md"
        with open(preview_path, "w") as f:
            f.write(f"# {result.doc_name.upper()} - {result.model_name}\n\n")
            f.write(f"**Pages tested:** {result.pages_tested}\n")
            f.write(f"**Characters:** {result.total_chars:,}\n")
            f.write(f"**Latency:** {result.total_latency_ms:,}ms\n")
            f.write(f"**Cost:** ${result.cost_estimate:.4f}\n\n")
            f.write("---\n\n")
            f.write(result.markdown_preview)
        print(f"Preview saved to: {preview_path}")


async def main():
    parser = argparse.ArgumentParser(description="Evaluate VLM models via Replicate API")
    parser.add_argument(
        "--model",
        choices=list(REPLICATE_MODELS.keys()) + ["all"],
        default="dots-ocr",
        help="Model to evaluate",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--api-token",
        default=os.environ.get("REPLICATE_API_TOKEN"),
        help="Replicate API token (or set REPLICATE_API_TOKEN env var)",
    )

    args = parser.parse_args()

    if not args.api_token:
        print("ERROR: REPLICATE_API_TOKEN environment variable not set")
        print("Set it with: export REPLICATE_API_TOKEN=your_token")
        return

    models = list(REPLICATE_MODELS.keys()) if args.model == "all" else [args.model]

    for model_key in models:
        results = await run_evaluation(model_key, args.api_token)
        print_summary(model_key, results)
        save_results(model_key, results, args.output_dir)


if __name__ == "__main__":
    asyncio.run(main())
