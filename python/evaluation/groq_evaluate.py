"""
Groq Vision Model Evaluation Script

Tests Llama 4 Maverick (multimodal) via Groq API.
Known for extremely fast inference on LPU chips.

Usage:
    export GROQ_API_KEY=your_key
    python evaluation/groq_evaluate.py
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

from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Groq vision models
GROQ_MODELS = {
    "llama4-maverick": {
        "id": "meta-llama/llama-4-maverick-17b-128e-instruct",
        "name": "Llama 4 Maverick (17B, 128 experts)",
        "input_cost_per_m": 0.20,
        "output_cost_per_m": 0.60,
    },
    "llama4-scout": {
        "id": "meta-llama/llama-4-scout-17b-16e-instruct",
        "name": "Llama 4 Scout (17B, 16 experts)",
        "input_cost_per_m": 0.11,
        "output_cost_per_m": 0.34,
    },
}

# Test documents
TEST_DOCS = {
    "cs": {
        "path": Path(__file__).parent.parent / "cs.pdf",
        "description": "Computer Science",
        "test_pages": [1, 3, 5],
    },
    "physics": {
        "path": Path(__file__).parent.parent / "physics-chapter 3.pdf",
        "description": "Physics",
        "test_pages": [1, 5, 10],
    },
    "chemistry": {
        "path": Path(__file__).parent.parent / "lech103.pdf",
        "description": "Chemistry",
        "test_pages": [1, 5, 10],
    },
    "biology": {
        "path": Path(__file__).parent.parent / "chapter1.pdf",
        "description": "Biology",
        "test_pages": [1, 3, 5],
    },
}

OCR_PROMPT = """Extract ALL text from this document image in clean markdown format.

Requirements:
1. Preserve the exact layout and structure
2. Convert mathematical equations to LaTeX (use $ for inline, $$ for display)
3. Preserve tables as markdown tables
4. For diagrams/figures, provide a brief [description]
5. Include ALL text including captions and footnotes

Output only the extracted text, nothing else."""


@dataclass
class PageResult:
    page_num: int
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    error: Optional[str] = None


@dataclass
class DocumentResult:
    doc_name: str
    model_name: str
    pages_tested: int
    total_chars: int
    total_input_tokens: int
    total_output_tokens: int
    total_latency_ms: int
    avg_latency_per_page_ms: float
    cost_estimate: float
    page_results: list[dict]
    markdown_preview: str
    has_tables: bool
    has_equations: bool


async def extract_page_groq(
    client: httpx.AsyncClient,
    model_id: str,
    image_b64: str,
    page_num: int,
    max_retries: int = 5,
) -> PageResult:
    """Extract text from a page using Groq API with retry logic for rate limits."""

    start_time = time.time()
    last_error = None

    for attempt in range(max_retries):
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
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
                    "temperature": 0,
                },
                timeout=120.0,
            )

            # Handle rate limiting with exponential backoff
            if response.status_code == 429:
                wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s, 40s, 80s
                print(f"      Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
                continue

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                return PageResult(
                    page_num=page_num,
                    text="",
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    error=f"HTTP {response.status_code}: {response.text[:200]}",
                )

            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            return PageResult(
                page_num=page_num,
                text=text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )

        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue

    # All retries exhausted
    latency_ms = int((time.time() - start_time) * 1000)
    return PageResult(
        page_num=page_num,
        text="",
        input_tokens=0,
        output_tokens=0,
        latency_ms=latency_ms,
        error=last_error or "Max retries exhausted",
    )


async def evaluate_document(
    model_key: str,
    doc_name: str,
    doc_path: Path,
    test_pages: list[int],
) -> DocumentResult:
    """Evaluate a model on a document."""

    model_info = GROQ_MODELS[model_key]
    model_id = model_info["id"]

    print(f"  Processing {doc_name} with {model_info['name']}...")

    # Convert PDF pages to images
    images = convert_from_path(str(doc_path), dpi=150)
    total_pages = len(images)

    # Filter test pages
    valid_pages = [p for p in test_pages if p <= total_pages]

    page_results = []

    async with httpx.AsyncClient() as client:
        for page_num in valid_pages:
            image = images[page_num - 1]

            # Convert to base64
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            image_b64 = base64.b64encode(buffer.getvalue()).decode()

            result = await extract_page_groq(client, model_id, image_b64, page_num)
            page_results.append(result)

            if result.error:
                print(f"    Page {page_num}: ERROR - {result.error[:50]}")
            else:
                print(f"    Page {page_num}: {len(result.text)} chars, {result.latency_ms}ms")

    # Calculate aggregates
    valid_results = [r for r in page_results if not r.error]
    total_chars = sum(len(r.text) for r in valid_results)
    total_input_tokens = sum(r.input_tokens for r in valid_results)
    total_output_tokens = sum(r.output_tokens for r in valid_results)
    total_latency = sum(r.latency_ms for r in valid_results)

    # Combine text
    combined_text = "\n\n---\n\n".join(
        f"## Page {r.page_num}\n\n{r.text}"
        for r in valid_results
    )

    # Detect features
    has_tables = "|" in combined_text and "---" in combined_text
    has_equations = "$" in combined_text or "\\(" in combined_text

    # Calculate cost
    cost = (total_input_tokens / 1_000_000) * model_info["input_cost_per_m"]
    cost += (total_output_tokens / 1_000_000) * model_info["output_cost_per_m"]

    return DocumentResult(
        doc_name=doc_name,
        model_name=model_info["name"],
        pages_tested=len(valid_results),
        total_chars=total_chars,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_latency_ms=total_latency,
        avg_latency_per_page_ms=total_latency / len(valid_results) if valid_results else 0,
        cost_estimate=cost,
        page_results=[asdict(r) for r in page_results],
        markdown_preview=combined_text[:5000],
        has_tables=has_tables,
        has_equations=has_equations,
    )


async def run_evaluation(model_key: str) -> list[DocumentResult]:
    """Run evaluation for a model."""

    model_info = GROQ_MODELS[model_key]

    print(f"\n{'='*60}")
    print(f"EVALUATING: {model_info['name']} (Groq)")
    print(f"{'='*60}\n")

    results = []

    for doc_name, doc_info in TEST_DOCS.items():
        doc_path = doc_info["path"]

        if not doc_path.exists():
            print(f"  WARNING: {doc_path} not found")
            continue

        result = await evaluate_document(
            model_key, doc_name, doc_path, doc_info["test_pages"]
        )
        results.append(result)

        print(f"  Summary: {result.total_chars:,} chars, {result.total_latency_ms}ms, ${result.cost_estimate:.4f}")
        print(f"           Tables: {'Yes' if result.has_tables else 'No'}, Equations: {'Yes' if result.has_equations else 'No'}")
        print()

    return results


def print_summary(model_key: str, results: list[DocumentResult]):
    """Print summary."""
    model_info = GROQ_MODELS[model_key]

    total_chars = sum(r.total_chars for r in results)
    total_latency = sum(r.total_latency_ms for r in results)
    total_pages = sum(r.pages_tested for r in results)
    total_cost = sum(r.cost_estimate for r in results)

    print(f"\n{'='*60}")
    print(f"SUMMARY: {model_info['name']} (Groq)")
    print(f"{'='*60}")
    print(f"Documents: {len(results)}, Pages: {total_pages}")
    print(f"Characters: {total_chars:,}")
    print(f"Latency: {total_latency}ms ({total_latency/1000:.1f}s)")
    print(f"Avg latency/page: {total_latency/total_pages:.0f}ms")
    print(f"Cost: ${total_cost:.4f}")
    print(f"Cost per 1000 pages: ${(total_cost/total_pages)*1000:.2f}")
    print()


def save_results(model_key: str, results: list[DocumentResult], output_dir: Path):
    """Save results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_data = {
        "model": GROQ_MODELS[model_key],
        "results": [asdict(r) for r in results],
    }
    summary_path = output_dir / f"groq_{model_key}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Summary saved: {summary_path}")

    for result in results:
        preview_path = output_dir / f"groq_{model_key}_{result.doc_name}_preview.md"
        with open(preview_path, "w") as f:
            f.write(f"# {result.doc_name.upper()} - {result.model_name} (Groq)\n\n")
            f.write(f"**Pages:** {result.pages_tested}\n")
            f.write(f"**Characters:** {result.total_chars:,}\n")
            f.write(f"**Latency:** {result.total_latency_ms}ms\n")
            f.write(f"**Cost:** ${result.cost_estimate:.4f}\n")
            f.write(f"**Tables:** {'Yes' if result.has_tables else 'No'}\n")
            f.write(f"**Equations:** {'Yes' if result.has_equations else 'No'}\n\n")
            f.write("---\n\n")
            f.write(result.markdown_preview)
        print(f"Preview saved: {preview_path}")


async def main():
    parser = argparse.ArgumentParser(description="Evaluate Groq vision models")
    parser.add_argument(
        "--model",
        choices=list(GROQ_MODELS.keys()) + ["all"],
        default="llama4-maverick",
        help="Model to evaluate",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Output directory",
    )

    args = parser.parse_args()

    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY not set")
        print("Get one at: https://console.groq.com/keys")
        return

    models = list(GROQ_MODELS.keys()) if args.model == "all" else [args.model]

    for model_key in models:
        results = await run_evaluation(model_key)
        print_summary(model_key, results)
        save_results(model_key, results, args.output_dir)


if __name__ == "__main__":
    asyncio.run(main())
