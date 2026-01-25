"""
DeepInfra VLM/OCR Model Evaluation Script

Tests VLM models via DeepInfra API:
- olmOCR-2 (allenai/olmOCR-2)
- Qwen2.5-VL-7B (Qwen/Qwen2.5-VL-7B-Instruct)
- MiniCPM-Llama3-V-2_5 (openbmb/MiniCPM-Llama3-V-2_5)

Usage:
    export DEEPINFRA_API_KEY=your_key
    python evaluation/deepinfra_evaluate.py --model olmocr2
    python evaluation/deepinfra_evaluate.py --model qwen-vl
    python evaluation/deepinfra_evaluate.py --model all
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

# DeepInfra models
DEEPINFRA_MODELS = {
    "olmocr2": {
        "id": "allenai/olmOCR-2",
        "name": "olmOCR-2 (7B)",
        "cost_per_m_tokens": 0.09,
    },
    "qwen-vl-7b": {
        "id": "Qwen/Qwen2.5-VL-7B-Instruct",
        "name": "Qwen2.5-VL-7B",
        "cost_per_m_tokens": 0.05,
    },
    "qwen-vl-72b": {
        "id": "Qwen/Qwen2.5-VL-72B-Instruct",
        "name": "Qwen2.5-VL-72B",
        "cost_per_m_tokens": 0.18,
    },
    "minicpm": {
        "id": "openbmb/MiniCPM-Llama3-V-2_5",
        "name": "MiniCPM-V 2.5",
        "cost_per_m_tokens": 0.08,
    },
}

# Test documents
TEST_DOCS = {
    "cs": {
        "path": Path(__file__).parent.parent / "cs.pdf",
        "description": "Computer Science - code blocks, algorithms, flowcharts",
        "test_pages": [1, 3, 5],  # Sample pages for quick testing
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

# OCR prompt
OCR_PROMPT = """You are an expert document OCR system. Extract ALL text content from this document page.

Requirements:
1. Preserve the exact layout and structure of the text
2. Convert any mathematical equations to LaTeX format (wrapped in $ or $$)
3. Preserve tables using markdown table syntax
4. For diagrams/figures, provide a brief description in [brackets]
5. Preserve code blocks with proper formatting using triple backticks
6. Include ALL text, even small captions and footnotes

Output the extracted text in clean markdown format."""


@dataclass
class PageResult:
    """Result from extracting a single page."""
    page_num: int
    text: str
    tokens_used: int
    latency_ms: int
    error: Optional[str] = None


@dataclass
class DocumentResult:
    """Result from extracting a document."""
    doc_name: str
    model_name: str
    model_id: str
    pages_tested: int
    total_chars: int
    total_tokens: int
    total_latency_ms: int
    avg_chars_per_page: float
    avg_latency_per_page_ms: float
    cost_estimate: float
    page_results: list[dict]
    markdown_preview: str
    has_tables: bool
    has_equations: bool
    has_code_blocks: bool


async def extract_page_deepinfra(
    client: httpx.AsyncClient,
    model_id: str,
    image: Image.Image,
    page_num: int,
    api_key: str,
) -> PageResult:
    """Extract text from a single page using DeepInfra API."""

    # Convert image to base64
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    image_b64 = base64.b64encode(buffer.getvalue()).decode()

    start_time = time.time()

    try:
        response = await client.post(
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
                            {"type": "text", "text": OCR_PROMPT},
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

        if response.status_code != 200:
            return PageResult(
                page_num=page_num,
                text="",
                tokens_used=0,
                latency_ms=latency_ms,
                error=f"HTTP {response.status_code}: {response.text[:200]}",
            )

        data = response.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)

        return PageResult(
            page_num=page_num,
            text=text,
            tokens_used=tokens,
            latency_ms=latency_ms,
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return PageResult(
            page_num=page_num,
            text="",
            tokens_used=0,
            latency_ms=latency_ms,
            error=str(e),
        )


async def evaluate_document(
    model_key: str,
    doc_name: str,
    doc_path: Path,
    test_pages: list[int],
    api_key: str,
) -> DocumentResult:
    """Evaluate a model on a document."""

    model_info = DEEPINFRA_MODELS[model_key]
    model_id = model_info["id"]
    model_name = model_info["name"]

    print(f"  Processing {doc_name} with {model_name}...")

    # Convert PDF pages to images
    images = convert_from_path(str(doc_path), dpi=150)
    total_pages = len(images)

    # Filter test pages to valid range
    valid_pages = [p for p in test_pages if p <= total_pages]

    page_results = []

    async with httpx.AsyncClient() as client:
        for page_num in valid_pages:
            image = images[page_num - 1]  # 0-indexed
            result = await extract_page_deepinfra(
                client, model_id, image, page_num, api_key
            )
            page_results.append(result)

            if result.error:
                print(f"    Page {page_num}: ERROR - {result.error[:50]}")
            else:
                print(f"    Page {page_num}: {len(result.text)} chars, {result.latency_ms}ms")

    # Calculate aggregates
    valid_results = [r for r in page_results if not r.error]
    total_chars = sum(len(r.text) for r in valid_results)
    total_tokens = sum(r.tokens_used for r in valid_results)
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

    # Estimate cost
    cost_per_token = model_info["cost_per_m_tokens"] / 1_000_000
    cost_estimate = total_tokens * cost_per_token

    return DocumentResult(
        doc_name=doc_name,
        model_name=model_name,
        model_id=model_id,
        pages_tested=len(valid_results),
        total_chars=total_chars,
        total_tokens=total_tokens,
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


async def run_evaluation(model_key: str, api_key: str) -> list[DocumentResult]:
    """Run evaluation for a specific model."""

    model_info = DEEPINFRA_MODELS[model_key]

    print(f"\n{'='*60}")
    print(f"EVALUATING: {model_info['name']}")
    print(f"Model ID: {model_info['id']}")
    print(f"{'='*60}\n")

    results = []

    for doc_name, doc_info in TEST_DOCS.items():
        doc_path = doc_info["path"]

        if not doc_path.exists():
            print(f"  WARNING: {doc_path} not found, skipping")
            continue

        result = await evaluate_document(
            model_key, doc_name, doc_path, doc_info["test_pages"], api_key
        )
        results.append(result)

        # Print summary
        print(f"  Summary: {result.total_chars:,} chars, {result.total_tokens:,} tokens")
        print(f"           {result.avg_latency_per_page_ms:.0f}ms/page, ${result.cost_estimate:.4f}")
        print(f"           Tables: {'Yes' if result.has_tables else 'No'}, "
              f"Equations: {'Yes' if result.has_equations else 'No'}, "
              f"Code: {'Yes' if result.has_code_blocks else 'No'}")
        print()

    return results


def print_summary(model_key: str, results: list[DocumentResult]):
    """Print evaluation summary."""
    model_info = DEEPINFRA_MODELS[model_key]

    total_chars = sum(r.total_chars for r in results)
    total_tokens = sum(r.total_tokens for r in results)
    total_latency = sum(r.total_latency_ms for r in results)
    total_pages = sum(r.pages_tested for r in results)
    total_cost = sum(r.cost_estimate for r in results)

    print(f"\n{'='*60}")
    print(f"SUMMARY: {model_info['name']}")
    print(f"{'='*60}")
    print(f"Documents processed: {len(results)}")
    print(f"Pages tested: {total_pages}")
    print(f"Total characters: {total_chars:,}")
    print(f"Total tokens: {total_tokens:,}")
    print(f"Total latency: {total_latency:,}ms ({total_latency/1000:.1f}s)")
    print(f"Avg latency/page: {total_latency/total_pages:.0f}ms")
    print(f"Total cost: ${total_cost:.4f}")
    print()


def save_results(model_key: str, results: list[DocumentResult], output_dir: Path):
    """Save evaluation results to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save summary as JSON
    summary_data = {
        "model": DEEPINFRA_MODELS[model_key],
        "results": [asdict(r) for r in results],
    }
    summary_path = output_dir / f"deepinfra_{model_key}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Summary saved to: {summary_path}")

    # Save markdown previews
    for result in results:
        preview_path = output_dir / f"deepinfra_{model_key}_{result.doc_name}_preview.md"
        with open(preview_path, "w") as f:
            f.write(f"# {result.doc_name.upper()} - {result.model_name}\n\n")
            f.write(f"**Pages tested:** {result.pages_tested}\n")
            f.write(f"**Characters:** {result.total_chars:,}\n")
            f.write(f"**Tokens:** {result.total_tokens:,}\n")
            f.write(f"**Latency:** {result.total_latency_ms:,}ms\n")
            f.write(f"**Cost:** ${result.cost_estimate:.4f}\n")
            f.write(f"**Tables detected:** {'Yes' if result.has_tables else 'No'}\n")
            f.write(f"**Equations detected:** {'Yes' if result.has_equations else 'No'}\n")
            f.write(f"**Code blocks detected:** {'Yes' if result.has_code_blocks else 'No'}\n\n")
            f.write("---\n\n")
            f.write("## Extraction Preview\n\n")
            f.write(result.markdown_preview)
        print(f"Preview saved to: {preview_path}")


async def main():
    parser = argparse.ArgumentParser(description="Evaluate VLM models via DeepInfra API")
    parser.add_argument(
        "--model",
        choices=list(DEEPINFRA_MODELS.keys()) + ["all"],
        default="olmocr2",
        help="Model to evaluate",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("DEEPINFRA_API_KEY"),
        help="DeepInfra API key (or set DEEPINFRA_API_KEY env var)",
    )

    args = parser.parse_args()

    if not args.api_key:
        print("ERROR: DEEPINFRA_API_KEY environment variable not set")
        print("Set it with: export DEEPINFRA_API_KEY=your_key")
        return

    models = list(DEEPINFRA_MODELS.keys()) if args.model == "all" else [args.model]

    for model_key in models:
        results = await run_evaluation(model_key, args.api_key)
        print_summary(model_key, results)
        save_results(model_key, results, args.output_dir)


if __name__ == "__main__":
    asyncio.run(main())
