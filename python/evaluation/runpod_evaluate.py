"""
RunPod Serverless VLM/OCR Model Evaluation Script

Deploy and test models on RunPod serverless:
- MiniCPM-V 4.5 (best overall accuracy)
- OCRFlux-3B (best for cross-page tables)
- DeepSeek-OCR (best compression/throughput)

Usage:
    export RUNPOD_API_KEY=your_key

    # First deploy endpoints (one-time)
    python evaluation/runpod_evaluate.py --deploy minicpm-v4.5

    # Then run evaluation
    python evaluation/runpod_evaluate.py --endpoint ENDPOINT_ID --model minicpm-v4.5

Cost Estimates (per 1000 documents, 20 pages each):
- MiniCPM-V 4.5 (A40): ~$4.00
- OCRFlux-3B (L4): ~$2.20
- DeepSeek-OCR (L4): ~$1.30
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

# RunPod serverless configurations
RUNPOD_MODELS = {
    "minicpm-v4.5": {
        "name": "MiniCPM-V 4.5",
        "hf_model": "openbmb/MiniCPM-V-4_5",
        "gpu": "A40",  # 48GB VRAM
        "docker_image": "runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04",
        "vram_gb": 16,
        "cost_per_hour": 0.35,
        "estimated_seconds_per_page": 2.0,
    },
    "ocrflux-3b": {
        "name": "OCRFlux-3B",
        "hf_model": "ChatDOC/OCRFlux-3B",
        "gpu": "L4",  # 24GB VRAM
        "docker_image": "runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04",
        "vram_gb": 6,
        "cost_per_hour": 0.44,
        "estimated_seconds_per_page": 0.5,
    },
    "deepseek-ocr": {
        "name": "DeepSeek-OCR",
        "hf_model": "deepseek-ai/DeepSeek-OCR",
        "gpu": "L4",
        "docker_image": "runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04",
        "vram_gb": 6,
        "cost_per_hour": 0.44,
        "estimated_seconds_per_page": 0.3,
    },
}

# Test documents
TEST_DOCS = {
    "cs": {
        "path": Path(__file__).parent.parent / "cs.pdf",
        "description": "Computer Science",
        "test_pages": [1, 3, 5, 8, 10],
    },
    "physics": {
        "path": Path(__file__).parent.parent / "physics-chapter 3.pdf",
        "description": "Physics",
        "test_pages": [1, 5, 10, 15, 20],
    },
    "chemistry": {
        "path": Path(__file__).parent.parent / "lech103.pdf",
        "description": "Chemistry",
        "test_pages": [1, 5, 10, 15, 20],
    },
    "biology": {
        "path": Path(__file__).parent.parent / "chapter1.pdf",
        "description": "Biology",
        "test_pages": [1, 3, 5, 8, 10],
    },
}


# RunPod handler template
HANDLER_TEMPLATE = '''
"""RunPod serverless handler for {model_name}."""
import base64
import io
import runpod
from PIL import Image

# Initialize model on cold start
MODEL = None

def load_model():
    """Load the VLM model."""
    global MODEL
    if MODEL is None:
        from transformers import AutoModel, AutoTokenizer
        import torch

        MODEL = {{
            "model": AutoModel.from_pretrained(
                "{hf_model}",
                trust_remote_code=True,
                torch_dtype=torch.float16,
                device_map="auto",
            ),
            "tokenizer": AutoTokenizer.from_pretrained(
                "{hf_model}",
                trust_remote_code=True,
            ),
        }}
    return MODEL

def handler(event):
    """Handle inference request."""
    model_data = load_model()
    model = model_data["model"]
    tokenizer = model_data["tokenizer"]

    # Get input
    input_data = event.get("input", {{}})
    image_b64 = input_data.get("image_base64", "")
    prompt = input_data.get("prompt", "Extract all text from this image in markdown format.")

    # Decode image
    image_bytes = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Run inference
    messages = [
        {{"role": "user", "content": [
            {{"type": "image", "image": image}},
            {{"type": "text", "text": prompt}},
        ]}}
    ]

    response = model.chat(
        image=image,
        msgs=messages,
        tokenizer=tokenizer,
        max_new_tokens=4096,
    )

    return {{"output": {{"text": response, "status": "success"}}}}

runpod.serverless.start({{"handler": handler}})
'''


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


async def run_runpod_inference(
    client: httpx.AsyncClient,
    endpoint_id: str,
    image: Image.Image,
    api_key: str,
) -> tuple[str, int]:
    """Run inference on RunPod endpoint."""

    # Convert image to base64
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    image_b64 = base64.b64encode(buffer.getvalue()).decode()

    start_time = time.time()

    try:
        # Submit job
        response = await client.post(
            f"https://api.runpod.ai/v2/{endpoint_id}/runsync",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": {
                    "image_base64": image_b64,
                    "prompt": "Extract ALL text from this document page in clean markdown format. "
                             "Convert equations to LaTeX, preserve tables as markdown, "
                             "and describe any diagrams briefly.",
                }
            },
            timeout=120.0,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            return f"ERROR: HTTP {response.status_code}", latency_ms

        data = response.json()

        if data.get("status") == "FAILED":
            return f"ERROR: {data.get('error', 'Unknown error')}", latency_ms

        text = data.get("output", {}).get("text", "")
        return text, latency_ms

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return f"ERROR: {e}", latency_ms


async def evaluate_document(
    model_key: str,
    endpoint_id: str,
    doc_name: str,
    doc_path: Path,
    test_pages: list[int],
    api_key: str,
) -> DocumentResult:
    """Evaluate a model on a document."""

    model_info = RUNPOD_MODELS[model_key]

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
            text, latency_ms = await run_runpod_inference(
                client, endpoint_id, image, api_key
            )

            error = None
            if text.startswith("ERROR:"):
                error = text
                text = ""

            result = PageResult(
                page_num=page_num,
                text=text,
                latency_ms=latency_ms,
                error=error,
            )
            page_results.append(result)

            if error:
                print(f"    Page {page_num}: {error[:50]}")
            else:
                print(f"    Page {page_num}: {len(text)} chars, {latency_ms}ms")

    # Calculate aggregates
    valid_results = [r for r in page_results if not r.error]
    total_chars = sum(len(r.text) for r in valid_results)
    total_latency = sum(r.latency_ms for r in valid_results)

    combined_text = "\n\n---\n\n".join(
        f"## Page {r.page_num}\n\n{r.text}"
        for r in valid_results
    )

    has_tables = "|" in combined_text and "---" in combined_text
    has_equations = "$" in combined_text or "\\(" in combined_text

    # Estimate cost
    total_seconds = total_latency / 1000
    cost_estimate = (total_seconds / 3600) * model_info["cost_per_hour"]

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
    )


def generate_handler(model_key: str, output_dir: Path):
    """Generate handler.py for RunPod deployment."""
    model_info = RUNPOD_MODELS[model_key]

    handler_code = HANDLER_TEMPLATE.format(
        model_name=model_info["name"],
        hf_model=model_info["hf_model"],
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    handler_path = output_dir / f"{model_key}_handler.py"

    with open(handler_path, "w") as f:
        f.write(handler_code)

    print(f"Handler generated: {handler_path}")

    # Generate Dockerfile
    dockerfile = f'''FROM {model_info["docker_image"]}

WORKDIR /app

RUN pip install --no-cache-dir \\
    runpod \\
    transformers>=4.40.0 \\
    accelerate \\
    torch \\
    pillow \\
    sentencepiece

COPY {model_key}_handler.py /app/handler.py

# Pre-download model weights
RUN python -c "from transformers import AutoModel, AutoTokenizer; \\
    AutoModel.from_pretrained('{model_info["hf_model"]}', trust_remote_code=True); \\
    AutoTokenizer.from_pretrained('{model_info["hf_model"]}', trust_remote_code=True)"

CMD ["python", "-u", "handler.py"]
'''

    dockerfile_path = output_dir / f"{model_key}.Dockerfile"
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile)

    print(f"Dockerfile generated: {dockerfile_path}")
    print()
    print("Next steps:")
    print(f"  1. Build: docker build -f {dockerfile_path} -t {model_key}:latest .")
    print(f"  2. Push to Docker Hub: docker push youruser/{model_key}:latest")
    print(f"  3. Create RunPod serverless endpoint with the image")
    print(f"  4. Run: python evaluation/runpod_evaluate.py --endpoint ENDPOINT_ID --model {model_key}")


async def run_evaluation(
    model_key: str,
    endpoint_id: str,
    api_key: str,
) -> list[DocumentResult]:
    """Run full evaluation."""

    model_info = RUNPOD_MODELS[model_key]

    print(f"\n{'='*60}")
    print(f"EVALUATING: {model_info['name']}")
    print(f"Endpoint: {endpoint_id}")
    print(f"{'='*60}\n")

    results = []

    for doc_name, doc_info in TEST_DOCS.items():
        doc_path = doc_info["path"]

        if not doc_path.exists():
            print(f"  WARNING: {doc_path} not found, skipping")
            continue

        result = await evaluate_document(
            model_key, endpoint_id, doc_name, doc_path, doc_info["test_pages"], api_key
        )
        results.append(result)

        print(f"  Summary: {result.total_chars:,} chars, ${result.cost_estimate:.4f}")
        print()

    return results


def print_summary(model_key: str, results: list[DocumentResult]):
    """Print summary."""
    model_info = RUNPOD_MODELS[model_key]

    total_chars = sum(r.total_chars for r in results)
    total_latency = sum(r.total_latency_ms for r in results)
    total_pages = sum(r.pages_tested for r in results)
    total_cost = sum(r.cost_estimate for r in results)

    print(f"\n{'='*60}")
    print(f"SUMMARY: {model_info['name']}")
    print(f"{'='*60}")
    print(f"Documents: {len(results)}, Pages: {total_pages}")
    print(f"Characters: {total_chars:,}")
    print(f"Latency: {total_latency/1000:.1f}s ({total_latency/total_pages:.0f}ms/page)")
    print(f"Cost: ${total_cost:.4f}")
    print()


def save_results(model_key: str, results: list[DocumentResult], output_dir: Path):
    """Save results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_data = {
        "model": RUNPOD_MODELS[model_key],
        "results": [asdict(r) for r in results],
    }
    summary_path = output_dir / f"runpod_{model_key}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Summary saved: {summary_path}")

    for result in results:
        preview_path = output_dir / f"runpod_{model_key}_{result.doc_name}_preview.md"
        with open(preview_path, "w") as f:
            f.write(f"# {result.doc_name.upper()} - {result.model_name}\n\n")
            f.write(f"**Pages:** {result.pages_tested}, **Chars:** {result.total_chars:,}\n")
            f.write(f"**Cost:** ${result.cost_estimate:.4f}\n\n---\n\n")
            f.write(result.markdown_preview)
        print(f"Preview saved: {preview_path}")


async def main():
    parser = argparse.ArgumentParser(description="RunPod VLM evaluation")
    parser.add_argument(
        "--model",
        choices=list(RUNPOD_MODELS.keys()),
        required=True,
        help="Model to evaluate",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Generate deployment files instead of running evaluation",
    )
    parser.add_argument(
        "--endpoint",
        help="RunPod endpoint ID (required for evaluation)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Output directory",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("RUNPOD_API_KEY"),
        help="RunPod API key",
    )

    args = parser.parse_args()

    if args.deploy:
        generate_handler(args.model, args.output_dir / "runpod_deploy")
        return

    if not args.endpoint:
        print("ERROR: --endpoint is required for evaluation")
        print("First deploy with: --deploy")
        return

    if not args.api_key:
        print("ERROR: RUNPOD_API_KEY not set")
        return

    results = await run_evaluation(args.model, args.endpoint, args.api_key)
    print_summary(args.model, results)
    save_results(args.model, results, args.output_dir)


if __name__ == "__main__":
    asyncio.run(main())
