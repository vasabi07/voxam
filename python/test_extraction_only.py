"""
Quick test for Llama-4-Scout extraction only.
Skips question generation and Neo4j to iterate faster on prompt.
"""

import os
import json
import time
from dotenv import load_dotenv
from llama_ingestion import pdf_to_images, image_to_base64, EXTRACTION_SCHEMA, DEEPINFRA_URL, DEEPINFRA_API_KEY
import httpx

load_dotenv()

def test_extraction(pdf_path: str, max_pages: int = 3):
    """Test just the Llama extraction phase."""
    
    print(f"\n🧪 Testing Llama extraction on first {max_pages} pages...")
    print(f"📄 File: {pdf_path}\n")
    
    # Convert PDF to images
    print("📄 Converting PDF to images...")
    images = pdf_to_images(pdf_path)
    images = images[:max_pages]  # Limit for faster testing
    print(f"   ✅ Using {len(images)} pages\n")
    
    # Build prompt - same as llama_ingestion.py
    prompt = """You are a TEXT EXTRACTION tool. Your job is to READ and COPY text from the provided document images.

=== CRITICAL: EXTRACTION ONLY ===
- You are NOT generating or creating content
- You are COPYING the exact text that exists in the document images
- Read every word from every page and output it exactly as written
- This is OCR + structuring, not summarization or generation

=== TWO REQUIREMENTS ===

**1. IMAGE MARKERS**
When you see a diagram, figure, or illustration, insert:
[IMAGE_N page=X: brief description of what the image shows]

**2. VERBATIM TEXT EXTRACTION**
- Copy ALL text exactly as it appears in each page
- Include every paragraph, every bullet point, every sentence
- Do NOT skip any text - extract EVERYTHING you can read
- Each section should contain the actual text from the pages

=== OUTPUT STRUCTURE ===
Create 5-10 sections covering ALL pages:
- Pages 1-4: Nervous system content
- Pages 4-6: Brain and reflexes  
- Pages 7-8: Plant coordination
- Pages 9-10: Hormones in animals
- Pages 11-13: Exercise questions (include ALL questions)

=== EQUATIONS ===
- Capture mathematical formulas in LaTeX
- Provide spoken form

Return valid JSON matching the schema."""

    # Build content with page markers
    content = [{"type": "text", "text": prompt}]
    for i, img in enumerate(images):
        content.append({"type": "text", "text": f"--- PAGE {i + 1} ---"})
        b64 = image_to_base64(img)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })
    
    # Add schema
    content.append({
        "type": "text", 
        "text": f"\n\nReturn JSON matching this schema:\n{json.dumps(EXTRACTION_SCHEMA, indent=2)}"
    })
    
    # Call Llama-4-Scout
    print("🚀 Calling Llama-4-Scout...")
    start = time.time()
    
    response = httpx.post(
        DEEPINFRA_URL,
        headers={
            "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 32000,
            "temperature": 0
        },
        timeout=180.0
    )
    
    elapsed = time.time() - start
    result = response.json()
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(result)
        return
    
    text = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})
    
    print(f"\n✅ Done in {elapsed:.2f}s")
    print(f"📊 Tokens: {usage.get('prompt_tokens', 0):,} in, {usage.get('completion_tokens', 0):,} out")
    
    # Parse and analyze
    try:
        data = json.loads(text)
        sections = data.get("sections", [])
        
        print(f"\n📚 Extracted {len(sections)} sections:\n")
        
        total_chars = 0
        for i, section in enumerate(sections):
            content_len = len(section.get("content", ""))
            total_chars += content_len
            
            # Count IMAGE markers
            import re
            markers = re.findall(r'\[IMAGE_\d+ page=\d+:', section.get("content", ""))
            
            print(f"  {i+1}. {section.get('title', 'Untitled')[:50]}")
            print(f"      {content_len:,} chars, {len(markers)} images")
            
            # Show first 200 chars of content
            preview = section.get("content", "")[:200]
            print(f"      Preview: {preview}...")
            print()
        
        print(f"📊 Total content: {total_chars:,} characters")
        print(f"   Estimated tokens: ~{total_chars // 4:,}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        print(f"\nRaw output:\n{text[:1000]}...")


if __name__ == "__main__":
    import sys
    
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "chapter1.pdf"
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    test_extraction(pdf_path, max_pages)
