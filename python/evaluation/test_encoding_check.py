"""
Test what pages trigger OCR fallback with current encoding check.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.encoding_check import check_pdf_encoding, extract_pdf_with_fallback

TEST_DOCS = {
    "cs": Path(__file__).parent.parent / "cs.pdf",
    "physics": Path(__file__).parent.parent / "physics-chapter 3.pdf",
    "chemistry": Path(__file__).parent.parent / "lech103.pdf",
    "biology": Path(__file__).parent.parent / "chapter1.pdf",
}

print("=" * 60)
print("ENCODING CHECK ANALYSIS")
print("=" * 60)

for name, path in TEST_DOCS.items():
    print(f"\n### {name.upper()} ###")

    result = check_pdf_encoding(str(path))

    print(f"Total pages: {result['total_pages']}")
    print(f"Pages with issues: {len(result['pages_with_issues'])}")
    print(f"Problem pages: {result['problem_page_numbers']}")
    print(f"Overall score: {result['overall_score']:.1%}")
    print(f"Needs OCR fallback: {result['needs_ocr_fallback']}")

    if result['pages_with_issues']:
        print("\nSample issues:")
        for page in result['pages_with_issues'][:3]:
            print(f"  Page {page['page_num']}:")
            for line in page['problem_lines'][:2]:
                print(f"    Line {line['line_num']}: {line['issues']}")
                print(f"      '{line['text'][:60]}...'")
