"""
Quick test for hybrid OCR pipeline.
Tests just the extraction without question generation.
"""

import sys
from pathlib import Path
from llama_ingestion import LlamaIngestionPipeline

def test_hybrid_extraction(pdf_path: str):
    """Test the new hybrid OCR extraction pipeline."""
    
    print(f"\n{'='*60}")
    print("🧪 HYBRID OCR EXTRACTION TEST")
    print(f"{'='*60}")
    print(f"📄 File: {pdf_path}\n")
    
    pipeline = LlamaIngestionPipeline()
    
    # Just test extraction
    extracted = pipeline.extract_document(pdf_path)
    
    print(f"\n{'='*60}")
    print("📊 RESULTS")
    print(f"{'='*60}")
    
    print(f"\nSections: {len(extracted.sections)}")
    
    total_chars = 0
    for i, section in enumerate(extracted.sections):
        content_len = len(section.content)
        total_chars += content_len
        
        # Find and print IMAGE markers
        import re
        markers = re.findall(r'\[IMAGE.*?\]', section.content)
        
        print(f"\n  {i+1}. {section.title} ({content_len:,} chars)")
        if markers:
            print("     🖼️  Images:")
            for m in markers:
                print(f"         - {m}")
        else:
            print("     (No images)")
    
    print(f"\n📊 Total content: {total_chars:,} chars")
    print(f"   Estimated tokens: ~{total_chars // 4:,}")
    
    # Show token usage
    token_summary = pipeline.token_counter.get_summary()
    print(f"\n💰 Token Usage:")
    print(f"   Llama: {token_summary['llama_input_tokens']:,} in, {token_summary['llama_output_tokens']:,} out")
    print(f"   GPT OSS: {token_summary['gpt_oss_input_tokens']:,} in, {token_summary['gpt_oss_output_tokens']:,} out")
    print(f"   Total cost: ${token_summary['total_cost_usd']:.4f}")


if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "chapter1.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    test_hybrid_extraction(pdf_path)
