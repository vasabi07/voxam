"""
Test script for Llama-4-Scout image extraction and matching.

This script tests:
1. PDF extraction with Llama-4-Scout (with page markers)
2. Image extraction with PyMuPDF
3. Parsing of [IMAGE_N page=X: description] markers
4. Matching accuracy between Llama markers and PyMuPDF images

Usage:
    uv run python test_llama_ingestion.py <pdf_path>
"""

import sys
import json
from pathlib import Path

# Import from llama_ingestion
from llama_ingestion import (
    LlamaIngestionPipeline,
    extract_images_from_pdf,
    parse_image_markers,
    pdf_to_images,
)


def test_extraction(pdf_path: str):
    """Test the full extraction pipeline and show results."""
    
    print(f"\n{'='*70}")
    print(f"🧪 TESTING LLAMA INGESTION PIPELINE")
    print(f"📄 File: {pdf_path}")
    print(f"{'='*70}\n")
    
    # Step 1: Extract images with PyMuPDF
    print("📸 Step 1: Extracting images with PyMuPDF...")
    images_by_page = extract_images_from_pdf(pdf_path)
    
    print(f"\n   📊 Images by page:")
    for page_num, images in sorted(images_by_page.items()):
        print(f"      Page {page_num}: {len(images)} image(s)")
        for img in images:
            bbox = img.get("bbox")
            y_pos = img.get("y_pos", "N/A")
            print(f"         - Index {img['index']}, y_pos={y_pos:.0f}, ext={img['ext']}")
    
    # Step 2: Count total pages
    print(f"\n📄 Step 2: Converting PDF to page images...")
    page_images = pdf_to_images(pdf_path)
    total_pages = len(page_images)
    print(f"   Total pages: {total_pages}")
    
    # Step 3: Run Llama extraction
    print(f"\n🦙 Step 3: Running Llama-4-Scout extraction...")
    pipeline = LlamaIngestionPipeline({"question_model": "gpt-4.1"})
    
    try:
        extracted = pipeline.extract_document(pdf_path)
        
        print(f"\n   📖 Document Title: {extracted.document_title}")
        print(f"   📚 Sections: {len(extracted.sections)}")
        print(f"   📐 Equations: {len(extracted.equations)}")
        
        # Step 4: Analyze image markers in each section
        print(f"\n🔍 Step 4: Analyzing image markers in sections...")
        
        all_markers = []
        for i, section in enumerate(extracted.sections):
            markers = parse_image_markers(section.content)
            if markers:
                print(f"\n   📖 Section {i+1}: {section.title[:50]}...")
                for marker in markers:
                    print(f"      🖼️  {marker['full_match']}")
                    print(f"         → Page: {marker['page']}, Index: {marker['index']}")
                    print(f"         → Description: {marker['description'][:80]}...")
                    all_markers.append(marker)
        
        # Step 5: Cross-reference with PyMuPDF
        print(f"\n🔗 Step 5: Cross-referencing markers with extracted images...")
        
        matched = 0
        unmatched = 0
        
        for marker in all_markers:
            page = marker['page']
            index = marker['index']
            
            if page and index:
                # Convert to 0-indexed
                img_order = index - 1
                
                if page in images_by_page and img_order < len(images_by_page[page]):
                    matched += 1
                    print(f"   ✅ [IMAGE_{index} page={page}] → Found image at page {page}, position {img_order}")
                else:
                    unmatched += 1
                    print(f"   ❌ [IMAGE_{index} page={page}] → No matching image found!")
                    if page in images_by_page:
                        print(f"      (Page {page} has {len(images_by_page[page])} images, requested index {img_order})")
                    else:
                        print(f"      (No images extracted from page {page})")
            else:
                unmatched += 1
                print(f"   ⚠️  {marker['full_match']} → Missing page or index info")
        
        # Summary
        print(f"\n{'='*70}")
        print(f"📊 SUMMARY")
        print(f"{'='*70}")
        print(f"   Total sections: {len(extracted.sections)}")
        print(f"   Total image markers found: {len(all_markers)}")
        print(f"   ✅ Successfully matched: {matched}")
        print(f"   ❌ Unmatched: {unmatched}")
        
        if all_markers:
            accuracy = (matched / len(all_markers)) * 100
            print(f"   📈 Matching accuracy: {accuracy:.1f}%")
        
        # Show sample content
        print(f"\n📝 Sample section content (first section with images):")
        for section in extracted.sections:
            if "[IMAGE" in section.content:
                print(f"   Title: {section.title}")
                print(f"   Content preview:")
                # Show first 500 chars
                preview = section.content[:500].replace('\n', '\n      ')
                print(f"      {preview}...")
                break
        
        return extracted
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python test_llama_ingestion.py <pdf_path>")
        print("\nExample:")
        print("  uv run python test_llama_ingestion.py chapter1.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    result = test_extraction(pdf_path)
    
    if result:
        print(f"\n✅ Test complete! You can now inspect the extraction quality.")
