"""
PaddleOCR-VL - PDF Extraction Test Script via DeepInfra

Usage:
    python test_paddleocr.py <pdf_path>

Output:
    - extracted_output.md (the markdown result)
    - Console: token usage, estimated cost
"""

import os
import sys
import time
import base64
from pathlib import Path
from io import BytesIO
from dotenv import load_dotenv
from pdf2image import convert_from_path
import httpx

load_dotenv()

# DeepInfra API
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

# Pricing (per 1M tokens)
PADDLE_INPUT_PRICE = 0.14
PADDLE_OUTPUT_PRICE = 0.80


def pdf_to_images(pdf_path: str):
    """Convert PDF pages to PIL images."""
    print(f"📄 Converting PDF to images...")
    images = convert_from_path(pdf_path, dpi=150)
    print(f"   ✅ Converted {len(images)} pages")
    return images


def image_to_base64(pil_image) -> str:
    """Convert PIL image to base64 string."""
    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def extract_with_paddleocr(images: list) -> tuple:
    """
    Send all pages to PaddleOCR-VL via DeepInfra.
    Returns: (markdown_text, usage_dict)
    """
    prompt = """Analyze this educational document and create a comprehensive study guide in markdown format.

YOUR TASK: Create an original study guide that captures ALL the educational content.

STRUCTURE YOUR OUTPUT AS:
1. Use ## for main topics/chapters
2. Use ### for subtopics
3. Use #### for detailed sections

FOR TEXT CONTENT:
- Paraphrase and explain all concepts in your own words
- Keep all key facts, definitions, and formulas
- Use bullet points for lists
- Use LaTeX notation for math (like $E=mc^2$)

FOR IMAGES/DIAGRAMS:
- Where you see an image, diagram, graph, or figure, insert:
  [IMAGE: Detailed description of what the visual shows, including labels and data points]
- Be specific (e.g., "Diagram showing human digestive system with labeled organs")

FOR TABLES:
- Recreate tables in markdown format

PAGE TRACKING:
- Add <!-- PAGE X --> before each page's content

OUTPUT: Return ONLY the markdown study guide, no other text."""

    print(f"🚀 Sending {len(images)} pages to PaddleOCR-VL...")
    start_time = time.time()
    
    # Build content array with images
    content = [{"type": "text", "text": prompt}]
    for i, img in enumerate(images):
        b64 = image_to_base64(img)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}"
            }
        })
    
    # Call DeepInfra API
    response = httpx.post(
        DEEPINFRA_URL,
        headers={
            "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "PaddlePaddle/PaddleOCR-VL-0.9B",
            "messages": [
                {"role": "user", "content": content}
            ],
            "max_tokens": 16000
        },
        timeout=300.0
    )
    
    elapsed = time.time() - start_time
    print(f"   ✅ Response received in {elapsed:.2f}s")
    
    if response.status_code != 200:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   {response.text}")
        return None, None
    
    result = response.json()
    text = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})
    
    return text, usage


def calculate_cost(usage: dict) -> dict:
    """Calculate estimated cost from usage."""
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    
    input_cost = (input_tokens / 1_000_000) * PADDLE_INPUT_PRICE
    output_cost = (output_tokens / 1_000_000) * PADDLE_OUTPUT_PRICE
    total_cost = input_cost + output_cost
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost
    }


def analyze_output(markdown: str) -> dict:
    """Analyze the extracted markdown for key metrics."""
    if not markdown:
        return {"error": "No markdown output"}
    
    lines = markdown.split("\n")
    
    return {
        "total_lines": len(lines),
        "total_chars": len(markdown),
        "chapters": markdown.count("## "),
        "sections": markdown.count("### "),
        "subsections": markdown.count("#### "),
        "images": markdown.count("[IMAGE:"),
        "tables": markdown.count("|"),
        "equations": markdown.count("$"),
        "page_markers": markdown.count("<!-- PAGE"),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_paddleocr.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    if not DEEPINFRA_API_KEY:
        print("❌ DEEPINFRA_API_KEY not set in environment")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"🧪 PaddleOCR-VL - PDF Extraction Test")
    print(f"{'='*60}")
    print(f"📁 File: {pdf_path}")
    print()
    
    # Step 1: Convert PDF to images
    images = pdf_to_images(pdf_path)
    
    # Step 2: Extract with PaddleOCR-VL
    markdown, usage = extract_with_paddleocr(images)
    
    if not markdown:
        print("❌ Extraction failed")
        sys.exit(1)
    
    # Step 3: Calculate cost
    cost = calculate_cost(usage)
    
    # Step 4: Analyze output
    analysis = analyze_output(markdown)
    
    # Step 5: Save output
    output_path = Path(pdf_path).stem + "_paddleocr_extracted.md"
    with open(output_path, "w") as f:
        f.write(markdown)
    print(f"\n📝 Saved to: {output_path}")
    
    # Print results
    print(f"\n{'='*60}")
    print(f"📊 RESULTS")
    print(f"{'='*60}")
    
    print(f"\n💰 Cost Breakdown:")
    print(f"   Input tokens:  {cost['input_tokens']:,}")
    print(f"   Output tokens: {cost['output_tokens']:,}")
    print(f"   Input cost:    ${cost['input_cost']:.4f}")
    print(f"   Output cost:   ${cost['output_cost']:.4f}")
    print(f"   TOTAL COST:    ${cost['total_cost']:.4f}")
    
    print(f"\n📈 Extraction Analysis:")
    print(f"   Total lines:    {analysis['total_lines']}")
    print(f"   Total chars:    {analysis['total_chars']:,}")
    print(f"   Chapters (##):  {analysis['chapters']}")
    print(f"   Sections (###): {analysis['sections']}")
    print(f"   Subsections:    {analysis['subsections']}")
    print(f"   Images found:   {analysis['images']}")
    print(f"   Tables (|):     {analysis['tables']}")
    print(f"   Equations ($):  {analysis['equations']}")
    print(f"   Page markers:   {analysis['page_markers']}")
    
    print(f"\n{'='*60}")
    print(f"✅ Test complete! Check {output_path} for the extracted markdown.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
