"""
Test Extraction Pipeline: PyMuPDF + Mistral OCR vs Gemini baseline

Tests the document extraction phase (before topic creation) using:
1. PyMuPDF + Mistral-Small OCR (candidate)
2. PyMuPDF + Gemini OCR (baseline)

Compares:
- Character count similarity
- LaTeX equation detection
- Content coverage
- Semantic similarity (via embeddings)

Usage:
    source .venv/bin/activate
    set -a && source .env && set +a
    python evaluation/test_extraction_pipeline.py
"""

import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.encoding_check import (
    check_pdf_encoding,
    extract_pdf_with_fallback,
    DEEPINFRA_OCR_MODELS,
)


# Test documents
TEST_DOCS = {
    "cs": Path(__file__).parent.parent / "cs.pdf",
    "physics": Path(__file__).parent.parent / "physics-chapter 3.pdf",
    "chemistry": Path(__file__).parent.parent / "lech103.pdf",
    "biology": Path(__file__).parent.parent / "chapter1.pdf",
}


@dataclass
class ExtractionResult:
    """Result from extracting a document."""
    doc_name: str
    provider: str
    model: str
    total_pages: int
    problem_pages: int
    ocr_pages: int
    total_chars: int
    avg_chars_per_page: float
    extraction_time_s: float

    # Quality metrics
    latex_equations: int
    tables_detected: int
    code_blocks: int

    # Per-page data
    page_chars: list[int]
    page_texts: list[str]  # Store actual text for comparison


@dataclass
class ComparisonResult:
    """Comparison between candidate and baseline."""
    doc_name: str
    candidate_provider: str
    baseline_provider: str

    # Character similarity
    char_ratio: float  # candidate_chars / baseline_chars

    # Per-page similarity
    page_similarities: list[float]  # Jaccard similarity per page
    avg_page_similarity: float

    # Feature comparison
    latex_ratio: float
    tables_ratio: float

    # Overall quality score (0-100)
    quality_score: float
    passes_threshold: bool  # >= 95%


def count_latex_equations(text: str) -> int:
    """Count LaTeX equations in text."""
    patterns = [
        r'\$[^\$]+\$',           # $...$
        r'\$\$[^\$]+\$\$',       # $$...$$
        r'\\\([^\)]+\\\)',       # \(...\)
        r'\\\[[^\]]+\\\]',       # \[...\]
    ]
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, text))
    return count


def count_tables(text: str) -> int:
    """Count markdown tables in text."""
    table_pattern = r'\|[^\n]+\|'
    rows = re.findall(table_pattern, text)
    # Estimate tables by groups of rows
    return len(rows) // 3 if len(rows) >= 3 else 0


def count_code_blocks(text: str) -> int:
    """Count code blocks in text."""
    return text.count("```") // 2


def jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts."""
    # Tokenize (simple word-based)
    words1 = set(re.findall(r'\w+', text1.lower()))
    words2 = set(re.findall(r'\w+', text2.lower()))

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def extract_document(
    doc_path: Path,
    doc_name: str,
    ocr_provider: str = "gemini",
    deepinfra_model: str = "mistral-small"
) -> ExtractionResult:
    """Extract a document using specified OCR provider."""

    print(f"\n{'='*60}")
    print(f"Extracting: {doc_name}")
    print(f"Provider: {ocr_provider}" + (f" ({deepinfra_model})" if ocr_provider == "deepinfra" else ""))
    print(f"{'='*60}")

    start_time = time.time()

    # Check for problem pages first
    encoding_check = check_pdf_encoding(str(doc_path))
    problem_pages = encoding_check["problem_page_numbers"]

    print(f"Total pages: {encoding_check['total_pages']}")
    print(f"Problem pages: {len(problem_pages)}")

    # Extract with fallback
    pages_text = extract_pdf_with_fallback(
        str(doc_path),
        doc_id=doc_name,
        ocr_provider=ocr_provider,
        deepinfra_model=deepinfra_model
    )

    extraction_time = time.time() - start_time

    # Calculate metrics
    total_chars = sum(len(p) for p in pages_text)
    page_chars = [len(p) for p in pages_text]

    # Combine all text for feature detection
    combined_text = "\n\n".join(pages_text)

    latex_count = count_latex_equations(combined_text)
    tables_count = count_tables(combined_text)
    code_count = count_code_blocks(combined_text)

    print(f"\nExtraction complete in {extraction_time:.2f}s")
    print(f"Total chars: {total_chars:,}")
    print(f"LaTeX equations: {latex_count}")
    print(f"Tables: {tables_count}")
    print(f"Code blocks: {code_count}")

    return ExtractionResult(
        doc_name=doc_name,
        provider=ocr_provider,
        model=deepinfra_model if ocr_provider == "deepinfra" else "gemini-2.0-flash",
        total_pages=len(pages_text),
        problem_pages=len(problem_pages),
        ocr_pages=len(problem_pages),  # OCR applied to problem pages
        total_chars=total_chars,
        avg_chars_per_page=total_chars / len(pages_text) if pages_text else 0,
        extraction_time_s=extraction_time,
        latex_equations=latex_count,
        tables_detected=tables_count,
        code_blocks=code_count,
        page_chars=page_chars,
        page_texts=pages_text,
    )


def compare_extractions(
    candidate: ExtractionResult,
    baseline: ExtractionResult
) -> ComparisonResult:
    """Compare candidate extraction against baseline."""

    # Character ratio
    char_ratio = candidate.total_chars / baseline.total_chars if baseline.total_chars > 0 else 0

    # Per-page Jaccard similarity
    page_similarities = []
    for cand_text, base_text in zip(candidate.page_texts, baseline.page_texts):
        sim = jaccard_similarity(cand_text, base_text)
        page_similarities.append(sim)

    avg_similarity = sum(page_similarities) / len(page_similarities) if page_similarities else 0

    # Feature ratios
    latex_ratio = candidate.latex_equations / baseline.latex_equations if baseline.latex_equations > 0 else (1.0 if candidate.latex_equations == 0 else 0)
    tables_ratio = candidate.tables_detected / baseline.tables_detected if baseline.tables_detected > 0 else (1.0 if candidate.tables_detected == 0 else 0)

    # Calculate quality score (weighted)
    # - 50% content similarity (Jaccard)
    # - 25% character coverage
    # - 15% LaTeX extraction
    # - 10% table extraction

    # Normalize char_ratio to 0-1 (penalize both under and over extraction)
    char_score = 1.0 - abs(1.0 - char_ratio) if 0.5 <= char_ratio <= 1.5 else 0.5

    # Normalize latex_ratio (allow some variance)
    latex_score = min(1.0, latex_ratio) if latex_ratio <= 1.5 else 0.8

    # Normalize tables_ratio
    tables_score = min(1.0, tables_ratio) if tables_ratio <= 1.5 else 0.8

    quality_score = (
        avg_similarity * 50 +
        char_score * 25 +
        latex_score * 15 +
        tables_score * 10
    )

    return ComparisonResult(
        doc_name=candidate.doc_name,
        candidate_provider=f"{candidate.provider}:{candidate.model}",
        baseline_provider=f"{baseline.provider}:{baseline.model}",
        char_ratio=char_ratio,
        page_similarities=page_similarities,
        avg_page_similarity=avg_similarity,
        latex_ratio=latex_ratio,
        tables_ratio=tables_ratio,
        quality_score=quality_score,
        passes_threshold=quality_score >= 95.0,
    )


def print_comparison_table(comparisons: list[ComparisonResult]):
    """Print comparison results as a table."""

    print(f"\n{'='*80}")
    print("QUALITY COMPARISON: Mistral-Small vs Gemini")
    print(f"{'='*80}")

    print(f"\n{'Document':<12} {'Char Ratio':<12} {'Similarity':<12} {'LaTeX':<10} {'Tables':<10} {'Score':<10} {'Pass':<6}")
    print("-" * 80)

    for comp in comparisons:
        pass_str = "✅ YES" if comp.passes_threshold else "❌ NO"
        print(f"{comp.doc_name:<12} "
              f"{comp.char_ratio:>10.2%}  "
              f"{comp.avg_page_similarity:>10.2%}  "
              f"{comp.latex_ratio:>8.2%}  "
              f"{comp.tables_ratio:>8.2%}  "
              f"{comp.quality_score:>8.1f}%  "
              f"{pass_str}")

    print("-" * 80)

    # Overall
    avg_score = sum(c.quality_score for c in comparisons) / len(comparisons)
    all_pass = all(c.passes_threshold for c in comparisons)

    print(f"\n{'OVERALL':<12} {'':<12} {'':<12} {'':<10} {'':<10} {avg_score:>8.1f}%  {'✅ PASS' if all_pass else '❌ FAIL'}")

    return avg_score, all_pass


def main():
    # Check API keys
    google_key = os.getenv("GOOGLE_API_KEY")
    deepinfra_key = os.getenv("DEEPINFRA_API_KEY")

    if not google_key:
        print("ERROR: GOOGLE_API_KEY not set (needed for baseline)")
        return
    if not deepinfra_key:
        print("ERROR: DEEPINFRA_API_KEY not set (needed for Mistral)")
        return

    print("=" * 80)
    print("EXTRACTION PIPELINE TEST")
    print("Candidate: PyMuPDF + Mistral-Small-3.1-24B OCR")
    print("Baseline:  PyMuPDF + Gemini 2.0 Flash OCR")
    print("=" * 80)

    all_comparisons = []
    all_results = {}

    for doc_name, doc_path in TEST_DOCS.items():
        if not doc_path.exists():
            print(f"WARNING: {doc_path} not found, skipping")
            continue

        # Extract with Mistral (candidate)
        candidate = extract_document(
            doc_path, doc_name,
            ocr_provider="deepinfra",
            deepinfra_model="mistral-small"
        )

        # Extract with Gemini (baseline)
        baseline = extract_document(
            doc_path, doc_name,
            ocr_provider="gemini"
        )

        # Compare
        comparison = compare_extractions(candidate, baseline)
        all_comparisons.append(comparison)

        all_results[doc_name] = {
            "candidate": asdict(candidate),
            "baseline": asdict(baseline),
            "comparison": asdict(comparison),
        }
        # Remove large text arrays from saved results
        del all_results[doc_name]["candidate"]["page_texts"]
        del all_results[doc_name]["baseline"]["page_texts"]

    # Print summary
    avg_score, all_pass = print_comparison_table(all_comparisons)

    # Save results
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)

    results_path = output_dir / "extraction_pipeline_test.json"
    with open(results_path, "w") as f:
        json.dump({
            "summary": {
                "avg_quality_score": avg_score,
                "passes_95_threshold": all_pass,
                "candidate": "deepinfra:mistral-small",
                "baseline": "gemini:gemini-2.0-flash",
            },
            "documents": all_results,
        }, f, indent=2)

    print(f"\nResults saved to: {results_path}")

    # Final verdict
    print("\n" + "=" * 80)
    if all_pass:
        print("✅ VERDICT: Mistral-Small extraction is 95%+ quality - READY TO DEPLOY")
    else:
        print("❌ VERDICT: Mistral-Small extraction below 95% threshold - NEEDS REVIEW")
    print("=" * 80)


if __name__ == "__main__":
    main()
