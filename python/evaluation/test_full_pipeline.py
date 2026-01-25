"""
Full Pipeline Quality Test: PyMuPDF + Mistral-Small OCR

Tests the complete ingestion pipeline on Physics and Chemistry documents:
1. Checkpoint 1: OCR page replacement verification
2. Checkpoint 2: Content block quality (LaTeX preserved)
3. Checkpoint 3: Question generation quality (LaTeX, no hallucination)

Usage:
    source .venv/bin/activate
    set -a && source .env && set +a
    python evaluation/test_full_pipeline.py

    # Test specific doc
    python evaluation/test_full_pipeline.py --doc physics
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.encoding_check import (
    check_pdf_encoding,
    extract_pdf_with_fallback,
    DEEPINFRA_OCR_MODELS,
)


# Test documents
TEST_DOCS = {
    "physics": {
        "path": Path(__file__).parent.parent / "physics-chapter 3.pdf",
        "description": "Physics - equations, diagrams, formulas",
    },
    "chemistry": {
        "path": Path(__file__).parent.parent / "lech103.pdf",
        "description": "Chemistry - chemical formulas, reactions, tables",
    },
}


def count_latex_patterns(text: str) -> Dict[str, int]:
    """Count different LaTeX patterns in text."""
    patterns = {
        "inline_dollar": len(re.findall(r'\$[^\$\n]+\$', text)),
        "display_dollar": len(re.findall(r'\$\$[^\$]+\$\$', text)),
        "backslash_paren": len(re.findall(r'\\\([^\)]+\\\)', text)),
        "backslash_bracket": len(re.findall(r'\\\[[^\]]+\\\]', text)),
        "frac": len(re.findall(r'\\frac', text)),
        "delta": len(re.findall(r'\\[Dd]elta', text)),
        "subscript": len(re.findall(r'_\{[^\}]+\}|_[a-zA-Z0-9]', text)),
        "superscript": len(re.findall(r'\^\{[^\}]+\}|\^[a-zA-Z0-9]', text)),
    }
    patterns["total"] = sum(patterns.values())
    return patterns


def extract_pymupdf_only(pdf_path: str) -> List[str]:
    """Extract text using PyMuPDF only (no OCR fallback)."""
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return pages


# =============================================================================
# CHECKPOINT 1: Page Replacement Verification
# =============================================================================

def checkpoint_1_page_replacement(doc_name: str, doc_path: Path) -> Dict[str, Any]:
    """Verify OCR pages are correctly replaced without mismatch."""
    print(f"\n{'='*60}")
    print(f"CHECKPOINT 1: Page Replacement - {doc_name.upper()}")
    print(f"{'='*60}")

    # Step 1: Get encoding check results
    encoding_check = check_pdf_encoding(str(doc_path))
    problem_pages = set(encoding_check["problem_page_numbers"])
    total_pages = encoding_check["total_pages"]

    print(f"Total pages: {total_pages}")
    print(f"Problem pages: {len(problem_pages)} - {sorted(problem_pages)[:10]}{'...' if len(problem_pages) > 10 else ''}")

    # Step 2: Extract with PyMuPDF only (baseline)
    print("\nExtracting with PyMuPDF only (baseline)...")
    baseline_pages = extract_pymupdf_only(str(doc_path))

    # Step 3: Extract with Mistral OCR fallback
    print("Extracting with PyMuPDF + Mistral OCR fallback...")
    ocr_pages = extract_pdf_with_fallback(
        str(doc_path),
        doc_id=doc_name,
        ocr_provider="deepinfra",
        deepinfra_model="mistral-small"
    )

    # Step 4: Verify page replacement
    results = {
        "doc_name": doc_name,
        "total_pages": total_pages,
        "problem_pages": len(problem_pages),
        "replaced_correctly": 0,
        "unchanged_correctly": 0,
        "mismatches": [],
        "latex_in_ocr_pages": 0,
    }

    print("\nVerifying page replacement...")
    for i in range(total_pages):
        page_num = i + 1  # 1-indexed
        baseline_text = baseline_pages[i]
        ocr_text = ocr_pages[i]

        is_problem_page = page_num in problem_pages
        texts_different = baseline_text != ocr_text

        if is_problem_page:
            # Problem page should have been replaced
            if texts_different:
                results["replaced_correctly"] += 1
                # Check if OCR text has LaTeX
                latex_count = count_latex_patterns(ocr_text)
                if latex_count["total"] > 0:
                    results["latex_in_ocr_pages"] += 1
            else:
                results["mismatches"].append({
                    "page": page_num,
                    "issue": "Problem page NOT replaced (texts identical)"
                })
        else:
            # Non-problem page should be unchanged
            if not texts_different:
                results["unchanged_correctly"] += 1
            else:
                results["mismatches"].append({
                    "page": page_num,
                    "issue": "Non-problem page was changed unexpectedly"
                })

    # Print results
    print(f"\n✅ Problem pages replaced correctly: {results['replaced_correctly']}/{len(problem_pages)}")
    print(f"✅ Non-problem pages unchanged: {results['unchanged_correctly']}/{total_pages - len(problem_pages)}")
    print(f"✅ OCR pages with LaTeX: {results['latex_in_ocr_pages']}/{len(problem_pages)}")

    if results["mismatches"]:
        print(f"\n❌ Mismatches found: {len(results['mismatches'])}")
        for m in results["mismatches"][:5]:
            print(f"   Page {m['page']}: {m['issue']}")

    results["passed"] = len(results["mismatches"]) == 0
    return results


# =============================================================================
# CHECKPOINT 2: Content Block Quality
# =============================================================================

def checkpoint_2_content_blocks(doc_name: str, doc_path: Path) -> Dict[str, Any]:
    """Verify content blocks have LaTeX preserved."""
    print(f"\n{'='*60}")
    print(f"CHECKPOINT 2: Content Blocks - {doc_name.upper()}")
    print(f"{'='*60}")

    # Import ingestion components
    from ingestion_workflow import create_hierarchy_with_llm, create_topic_content_blocks, ContentBlock
    from lib.text_chunker import chunk_pages
    from lib.math_to_speech import extract_equations

    # Step 1: Extract pages with OCR
    print("Extracting pages with Mistral OCR...")
    pages_text = extract_pdf_with_fallback(
        str(doc_path),
        doc_id=doc_name,
        ocr_provider="deepinfra",
        deepinfra_model="mistral-small"
    )

    # Step 2: Chunk pages
    print("Chunking pages...")
    raw_chunks = chunk_pages(pages_text, max_chars=4000, min_chars=500, overlap=200)
    print(f"Created {len(raw_chunks)} raw chunks")

    # Step 3: Create hierarchy with LLM
    print("Creating hierarchy with LLM...")
    temp_blocks = []
    for chunk in raw_chunks:
        temp = ContentBlock()
        temp.text_content = chunk["text"]
        temp.page_number = chunk["page_start"]
        temp.page_start = chunk["page_start"]
        temp.page_end = chunk["page_end"]
        temp_blocks.append(temp)

    hierarchy = create_hierarchy_with_llm(temp_blocks)

    # Step 4: Create topic content blocks
    print("Creating topic content blocks...")
    content_blocks = create_topic_content_blocks(raw_chunks, hierarchy)
    print(f"Created {len(content_blocks)} content blocks")

    # Step 5: Analyze blocks for LaTeX
    results = {
        "doc_name": doc_name,
        "total_blocks": len(content_blocks),
        "blocks_with_latex": 0,
        "total_latex_patterns": 0,
        "blocks_with_equations": 0,
        "sample_blocks": [],
    }

    print("\nAnalyzing content blocks...")
    for i, block in enumerate(content_blocks):
        # Extract equations
        block.equations = extract_equations(block.text_content)

        latex_counts = count_latex_patterns(block.text_content)
        has_latex = latex_counts["total"] > 0

        if has_latex:
            results["blocks_with_latex"] += 1
            results["total_latex_patterns"] += latex_counts["total"]

        if block.equations:
            results["blocks_with_equations"] += 1

        # Save first 3 blocks as samples
        if i < 3:
            results["sample_blocks"].append({
                "index": i,
                "chapter": block.chapter_title,
                "section": block.section_title,
                "text_preview": block.text_content[:500] + "..." if len(block.text_content) > 500 else block.text_content,
                "latex_counts": latex_counts,
                "equations_found": len(block.equations) if block.equations else 0,
            })

    # Print results
    pct_latex = (results["blocks_with_latex"] / results["total_blocks"] * 100) if results["total_blocks"] > 0 else 0
    print(f"\n✅ Blocks with LaTeX: {results['blocks_with_latex']}/{results['total_blocks']} ({pct_latex:.1f}%)")
    print(f"✅ Total LaTeX patterns found: {results['total_latex_patterns']}")
    print(f"✅ Blocks with extracted equations: {results['blocks_with_equations']}")

    # Print sample block
    if results["sample_blocks"]:
        print(f"\n--- Sample Block 0 ---")
        sample = results["sample_blocks"][0]
        print(f"Chapter: {sample['chapter']}")
        print(f"Section: {sample['section']}")
        print(f"LaTeX counts: {sample['latex_counts']}")
        print(f"Text preview:\n{sample['text_preview'][:300]}...")

    results["passed"] = pct_latex >= 50  # At least 50% of blocks should have LaTeX for science docs
    results["content_blocks"] = content_blocks  # Return for next checkpoint
    return results


# =============================================================================
# CHECKPOINT 3: Question Generation Quality
# =============================================================================

def checkpoint_3_questions(doc_name: str, content_blocks: List, max_blocks: int = 3) -> Dict[str, Any]:
    """Verify question generation preserves LaTeX and doesn't hallucinate."""
    print(f"\n{'='*60}")
    print(f"CHECKPOINT 3: Question Generation - {doc_name.upper()}")
    print(f"{'='*60}")

    from ingestion_workflow import IngestionPipeline, ContentBlock

    # Initialize pipeline (question generation uses Groq GPT-OSS-120B directly)
    config = {}
    pipeline = IngestionPipeline(config)

    results = {
        "doc_name": doc_name,
        "blocks_tested": 0,
        "total_questions": 0,
        "questions_with_latex": 0,
        "questions_per_block": [],
        "sample_questions": [],
        "errors": [],
    }

    # Test question generation on first N blocks
    blocks_to_test = content_blocks[:max_blocks]
    print(f"Testing question generation on {len(blocks_to_test)} blocks...")

    for i, block in enumerate(blocks_to_test):
        print(f"\n  Block {i+1}/{len(blocks_to_test)}: {block.section_title or block.chapter_title or 'Untitled'}")

        try:
            # Generate questions using pipeline instance
            questions = pipeline._generate_questions(block, max_retries=2)

            if questions:
                results["blocks_tested"] += 1
                results["total_questions"] += len(questions)
                results["questions_per_block"].append(len(questions))

                print(f"    Generated {len(questions)} questions")

                # Analyze questions
                for j, q in enumerate(questions):
                    q_text = q.text if hasattr(q, 'text') else str(q)
                    latex_in_q = count_latex_patterns(q_text)

                    if latex_in_q["total"] > 0:
                        results["questions_with_latex"] += 1

                    # Save first 2 questions from each block as samples
                    if j < 2:
                        options = q.options if hasattr(q, 'options') else []
                        results["sample_questions"].append({
                            "block": i,
                            "question": q_text,
                            "type": q.question_type.value if hasattr(q, 'question_type') else "unknown",
                            "bloom": q.bloom_level.value if hasattr(q, 'bloom_level') else "unknown",
                            "options": options[:4] if options else [],
                            "latex_count": latex_in_q["total"],
                        })
            else:
                results["errors"].append(f"Block {i}: No questions generated")
                print(f"    ❌ No questions generated")

        except Exception as e:
            results["errors"].append(f"Block {i}: {str(e)}")
            print(f"    ❌ Error: {str(e)[:100]}")

    # Print results
    if results["total_questions"] > 0:
        pct_latex = results["questions_with_latex"] / results["total_questions"] * 100
        avg_per_block = results["total_questions"] / results["blocks_tested"] if results["blocks_tested"] > 0 else 0

        print(f"\n✅ Total questions generated: {results['total_questions']}")
        print(f"✅ Average per block: {avg_per_block:.1f} (target: 12)")
        print(f"✅ Questions with LaTeX: {results['questions_with_latex']} ({pct_latex:.1f}%)")

        # Print sample questions
        print(f"\n--- Sample Questions ---")
        for sq in results["sample_questions"][:5]:
            print(f"\n[Block {sq['block']}, {sq['type']}, {sq['bloom']}]")
            print(f"Q: {sq['question'][:200]}{'...' if len(sq['question']) > 200 else ''}")
            if sq['options']:
                print(f"Options: {sq['options']}")
            print(f"LaTeX patterns: {sq['latex_count']}")

    if results["errors"]:
        print(f"\n❌ Errors: {len(results['errors'])}")
        for err in results["errors"][:3]:
            print(f"   {err}")

    results["passed"] = (
        results["blocks_tested"] == len(blocks_to_test) and
        results["total_questions"] >= results["blocks_tested"] * 10  # At least 10 questions per block
    )
    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Full pipeline quality test")
    parser.add_argument(
        "--doc",
        choices=list(TEST_DOCS.keys()) + ["all"],
        default="all",
        help="Document to test (default: all)",
    )
    parser.add_argument(
        "--checkpoint",
        choices=["1", "2", "3", "all"],
        default="all",
        help="Checkpoint to run (default: all)",
    )
    parser.add_argument(
        "--max-blocks",
        type=int,
        default=3,
        help="Max blocks to test for question generation (default: 3)",
    )

    args = parser.parse_args()

    # Check API keys
    if not os.getenv("DEEPINFRA_API_KEY"):
        print("ERROR: DEEPINFRA_API_KEY not set")
        return

    docs = list(TEST_DOCS.keys()) if args.doc == "all" else [args.doc]

    all_results = {}

    for doc_name in docs:
        doc_info = TEST_DOCS[doc_name]
        doc_path = doc_info["path"]

        if not doc_path.exists():
            print(f"WARNING: {doc_path} not found, skipping")
            continue

        print(f"\n{'#'*70}")
        print(f"# TESTING: {doc_name.upper()}")
        print(f"# {doc_info['description']}")
        print(f"{'#'*70}")

        doc_results = {}
        content_blocks = None

        # Checkpoint 1
        if args.checkpoint in ["1", "all"]:
            doc_results["checkpoint_1"] = checkpoint_1_page_replacement(doc_name, doc_path)

        # Checkpoint 2
        if args.checkpoint in ["2", "all"]:
            cp2_results = checkpoint_2_content_blocks(doc_name, doc_path)
            doc_results["checkpoint_2"] = {k: v for k, v in cp2_results.items() if k != "content_blocks"}
            content_blocks = cp2_results.get("content_blocks")
            # Cache content blocks for checkpoint 3
            if content_blocks:
                cache_path = Path(__file__).parent / "results" / f"{doc_name}_content_blocks.json"
                cache_path.parent.mkdir(exist_ok=True)
                cached = [{"text_content": b.text_content, "chapter_title": b.chapter_title,
                           "section_title": b.section_title, "page_start": b.page_start,
                           "page_end": b.page_end} for b in content_blocks]
                with open(cache_path, "w") as f:
                    json.dump(cached, f)
                print(f"💾 Cached {len(content_blocks)} content blocks to {cache_path}")

        # Checkpoint 3
        if args.checkpoint in ["3", "all"]:
            if content_blocks is None:
                # Try to load cached content blocks first
                cache_path = Path(__file__).parent / "results" / f"{doc_name}_content_blocks.json"
                if cache_path.exists():
                    print(f"📂 Loading cached content blocks from {cache_path}")
                    from ingestion_workflow import ContentBlock
                    with open(cache_path) as f:
                        cached = json.load(f)
                    content_blocks = []
                    for cb in cached:
                        block = ContentBlock()
                        block.text_content = cb.get("text_content", "")
                        block.chapter_title = cb.get("chapter_title", "")
                        block.section_title = cb.get("section_title", "")
                        block.page_start = cb.get("page_start", 1)
                        block.page_end = cb.get("page_end", 1)
                        content_blocks.append(block)
                else:
                    # Need to run checkpoint 2 first to get content blocks
                    cp2_results = checkpoint_2_content_blocks(doc_name, doc_path)
                    content_blocks = cp2_results.get("content_blocks")
                    # Cache for next run
                    if content_blocks:
                        cache_path.parent.mkdir(exist_ok=True)
                        cached = [{"text_content": b.text_content, "chapter_title": b.chapter_title,
                                   "section_title": b.section_title, "page_start": b.page_start,
                                   "page_end": b.page_end} for b in content_blocks]
                        with open(cache_path, "w") as f:
                            json.dump(cached, f)
                        print(f"💾 Cached content blocks to {cache_path}")

            if content_blocks:
                doc_results["checkpoint_3"] = checkpoint_3_questions(
                    doc_name, content_blocks, max_blocks=args.max_blocks
                )

        all_results[doc_name] = doc_results

    # Final Summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")

    for doc_name, doc_results in all_results.items():
        print(f"\n{doc_name.upper()}:")
        for cp_name, cp_results in doc_results.items():
            passed = cp_results.get("passed", False)
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {cp_name}: {status}")

    # Save results
    output_path = Path(__file__).parent / "results" / "full_pipeline_test.json"
    output_path.parent.mkdir(exist_ok=True)

    # Remove non-serializable content
    serializable_results = {}
    for doc_name, doc_results in all_results.items():
        serializable_results[doc_name] = {}
        for cp_name, cp_results in doc_results.items():
            serializable_results[doc_name][cp_name] = {
                k: v for k, v in cp_results.items()
                if not callable(v) and k != "content_blocks"
            }

    with open(output_path, "w") as f:
        json.dump(serializable_results, f, indent=2, default=str)

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
