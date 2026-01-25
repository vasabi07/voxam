"""
Local VLM/OCR Model Evaluation Script

Tests models that can run locally (CPU or Apple Silicon):
- Granite-Docling (IBM) - 258M params, runs on CPU
- SmolDocling - 256M params, runs on CPU

Usage:
    python evaluation/local_evaluate.py --model granite-docling
    python evaluation/local_evaluate.py --model all
"""

import argparse
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

# Test documents
TEST_DOCS = {
    "cs": {
        "path": Path(__file__).parent.parent / "cs.pdf",
        "description": "Computer Science - code blocks, algorithms, flowcharts",
        "key_features": ["code_blocks", "algorithms", "pseudocode", "flowcharts"],
    },
    "physics": {
        "path": Path(__file__).parent.parent / "physics-chapter 3.pdf",
        "description": "Physics - equations, diagrams, formulas, units",
        "key_features": ["equations", "diagrams", "formulas", "units"],
    },
    "chemistry": {
        "path": Path(__file__).parent.parent / "lech103.pdf",
        "description": "Chemistry - chemical formulas, molecular structures, tables",
        "key_features": ["chemical_formulas", "molecular_structures", "tables"],
    },
    "biology": {
        "path": Path(__file__).parent.parent / "chapter1.pdf",
        "description": "Biology - diagrams, terminology, figures, dense text",
        "key_features": ["diagrams", "terminology", "figures", "dense_text"],
    },
}


@dataclass
class ExtractionResult:
    """Result from extracting a single document."""
    doc_name: str
    model_name: str
    total_pages: int
    total_chars: int
    total_time_seconds: float
    chars_per_page: float
    seconds_per_page: float
    markdown_preview: str  # First 3000 chars
    has_tables: bool
    has_equations: bool
    has_code_blocks: bool
    error: Optional[str] = None


@dataclass
class EvaluationSummary:
    """Summary of evaluation across all documents."""
    model_name: str
    total_docs: int
    total_pages: int
    total_chars: int
    total_time_seconds: float
    avg_chars_per_page: float
    avg_seconds_per_page: float
    results: list[dict]


def evaluate_granite_docling(doc_path: Path, doc_name: str) -> ExtractionResult:
    """Evaluate Granite-Docling on a document."""
    from docling.document_converter import DocumentConverter

    print(f"  Processing {doc_name} with Granite-Docling...")

    start_time = time.time()

    try:
        converter = DocumentConverter()
        result = converter.convert(str(doc_path))

        elapsed = time.time() - start_time

        # Export to markdown
        markdown = result.document.export_to_markdown()

        # Count pages
        total_pages = len(result.document.pages) if hasattr(result.document, 'pages') else 1

        # Detect features
        has_tables = "|" in markdown and "---" in markdown
        has_equations = "$" in markdown or "\\(" in markdown or "\\[" in markdown
        has_code_blocks = "```" in markdown or "    " in markdown[:5000]

        return ExtractionResult(
            doc_name=doc_name,
            model_name="granite-docling",
            total_pages=total_pages,
            total_chars=len(markdown),
            total_time_seconds=elapsed,
            chars_per_page=len(markdown) / max(total_pages, 1),
            seconds_per_page=elapsed / max(total_pages, 1),
            markdown_preview=markdown[:3000],
            has_tables=has_tables,
            has_equations=has_equations,
            has_code_blocks=has_code_blocks,
        )

    except Exception as e:
        elapsed = time.time() - start_time
        return ExtractionResult(
            doc_name=doc_name,
            model_name="granite-docling",
            total_pages=0,
            total_chars=0,
            total_time_seconds=elapsed,
            chars_per_page=0,
            seconds_per_page=0,
            markdown_preview="",
            has_tables=False,
            has_equations=False,
            has_code_blocks=False,
            error=str(e),
        )


def run_evaluation(model: str) -> EvaluationSummary:
    """Run evaluation for a specific model."""

    print(f"\n{'='*60}")
    print(f"EVALUATING: {model.upper()}")
    print(f"{'='*60}\n")

    results = []

    for doc_name, doc_info in TEST_DOCS.items():
        doc_path = doc_info["path"]

        if not doc_path.exists():
            print(f"  WARNING: {doc_path} not found, skipping")
            continue

        if model == "granite-docling":
            result = evaluate_granite_docling(doc_path, doc_name)
        else:
            raise ValueError(f"Unknown model: {model}")

        results.append(result)

        # Print result
        if result.error:
            print(f"  ERROR: {result.error}")
        else:
            print(f"  {doc_name}: {result.total_chars:,} chars, {result.total_pages} pages, {result.total_time_seconds:.2f}s")
            print(f"    Tables: {'Yes' if result.has_tables else 'No'}")
            print(f"    Equations: {'Yes' if result.has_equations else 'No'}")
            print(f"    Code blocks: {'Yes' if result.has_code_blocks else 'No'}")

    # Calculate summary
    valid_results = [r for r in results if not r.error]

    summary = EvaluationSummary(
        model_name=model,
        total_docs=len(valid_results),
        total_pages=sum(r.total_pages for r in valid_results),
        total_chars=sum(r.total_chars for r in valid_results),
        total_time_seconds=sum(r.total_time_seconds for r in valid_results),
        avg_chars_per_page=sum(r.chars_per_page for r in valid_results) / len(valid_results) if valid_results else 0,
        avg_seconds_per_page=sum(r.seconds_per_page for r in valid_results) / len(valid_results) if valid_results else 0,
        results=[asdict(r) for r in results],
    )

    return summary


def print_summary(summary: EvaluationSummary):
    """Print evaluation summary."""
    print(f"\n{'='*60}")
    print(f"SUMMARY: {summary.model_name.upper()}")
    print(f"{'='*60}")
    print(f"Documents processed: {summary.total_docs}")
    print(f"Total pages: {summary.total_pages}")
    print(f"Total characters: {summary.total_chars:,}")
    print(f"Total time: {summary.total_time_seconds:.2f}s")
    print(f"Avg chars/page: {summary.avg_chars_per_page:,.0f}")
    print(f"Avg time/page: {summary.avg_seconds_per_page:.3f}s")
    print()


def save_results(summary: EvaluationSummary, output_dir: Path):
    """Save evaluation results to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save summary as JSON
    summary_path = output_dir / f"{summary.model_name}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(asdict(summary), f, indent=2)
    print(f"Summary saved to: {summary_path}")

    # Save markdown previews for each document
    for result in summary.results:
        if result.get("error"):
            continue

        preview_path = output_dir / f"{summary.model_name}_{result['doc_name']}_preview.md"
        with open(preview_path, "w") as f:
            f.write(f"# {result['doc_name'].upper()} - {summary.model_name}\n\n")
            f.write(f"**Pages:** {result['total_pages']}\n")
            f.write(f"**Characters:** {result['total_chars']:,}\n")
            f.write(f"**Time:** {result['total_time_seconds']:.2f}s\n")
            f.write(f"**Tables detected:** {'Yes' if result['has_tables'] else 'No'}\n")
            f.write(f"**Equations detected:** {'Yes' if result['has_equations'] else 'No'}\n")
            f.write(f"**Code blocks detected:** {'Yes' if result['has_code_blocks'] else 'No'}\n\n")
            f.write("---\n\n")
            f.write("## Preview (first 3000 chars)\n\n")
            f.write(result['markdown_preview'])
        print(f"Preview saved to: {preview_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate local VLM/OCR models")
    parser.add_argument(
        "--model",
        choices=["granite-docling", "all"],
        default="granite-docling",
        help="Model to evaluate",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Output directory for results",
    )

    args = parser.parse_args()

    models = ["granite-docling"] if args.model != "all" else ["granite-docling"]

    all_summaries = []

    for model in models:
        summary = run_evaluation(model)
        print_summary(summary)
        save_results(summary, args.output_dir)
        all_summaries.append(summary)

    # Print comparison if multiple models
    if len(all_summaries) > 1:
        print(f"\n{'='*60}")
        print("MODEL COMPARISON")
        print(f"{'='*60}")
        print(f"{'Model':<20} {'Chars/page':<12} {'Time/page':<12} {'Total time':<12}")
        print("-" * 60)
        for s in all_summaries:
            print(f"{s.model_name:<20} {s.avg_chars_per_page:<12,.0f} {s.avg_seconds_per_page:<12.3f}s {s.total_time_seconds:<12.2f}s")


if __name__ == "__main__":
    main()
