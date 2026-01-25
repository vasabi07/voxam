"""
Gemini 2.5 Flash - PDF Extraction Test Script

Usage:
    python test_gemini_extraction.py <pdf_path>

Output:
    - extracted_output.md (the markdown result)
    - Console: token usage, estimated cost
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from pdf2image import convert_from_path
from google import genai
from google.genai import types
import base64
from io import BytesIO

load_dotenv()

# Configure Gemini client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Pricing (per 1M tokens) - Gemini 2.5 Flash
GEMINI_INPUT_PRICE = 0.15  # $0.15 per 1M input tokens
GEMINI_OUTPUT_PRICE = 0.60  # $0.60 per 1M output tokens


def pdf_to_images(pdf_path: str):
    """Convert PDF pages to PIL images."""
    print(f"📄 Converting PDF to images...")
    images = convert_from_path(pdf_path, dpi=150)
    print(f"   ✅ Converted {len(images)} pages")
    return images


def image_to_part(pil_image) -> types.Part:
    """Convert PIL image to Gemini Part."""
    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    
    return types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/png"
    )


def extract_with_gemini(images: list) -> tuple:
    """
    Send all pages to Gemini in one call.
    Returns: (markdown_text, usage_metadata)
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

    print(f"🚀 Sending {len(images)} pages to Gemini 2.5 Flash...")
    start_time = time.time()
    
    # Convert images to parts
    parts = [prompt]
    for img in images:
        parts.append(image_to_part(img))
    
    # Send all images in one request
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=parts
    )
    
    elapsed = time.time() - start_time
    print(f"   ✅ Response received in {elapsed:.2f}s")
    
    # Extract text from response (handle different structures)
    text = None
    if hasattr(response, 'text') and response.text:
        text = response.text
    elif hasattr(response, 'candidates') and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, 'content') and candidate.content:
            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                text = candidate.content.parts[0].text
    
    if not text:
        print(f"   ⚠️ Response structure: {response}")
        text = str(response)  # Fallback
    
    return text, response.usage_metadata


def calculate_cost(usage_metadata) -> dict:
    """Calculate estimated cost from usage metadata."""
    # Handle different attribute names in new SDK
    input_tokens = getattr(usage_metadata, 'prompt_token_count', None) or \
                   getattr(usage_metadata, 'input_tokens', None) or \
                   getattr(usage_metadata, 'prompt_tokens', None) or 0
    
    output_tokens = getattr(usage_metadata, 'candidates_token_count', None) or \
                    getattr(usage_metadata, 'output_tokens', None) or \
                    getattr(usage_metadata, 'completion_tokens', None) or 0
    
    input_cost = (input_tokens / 1_000_000) * GEMINI_INPUT_PRICE
    output_cost = (output_tokens / 1_000_000) * GEMINI_OUTPUT_PRICE
    total_cost = input_cost + output_cost
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "raw_metadata": str(usage_metadata)  # Debug: show what we actually got
    }


def analyze_output(markdown: str) -> dict:
    """Analyze the extracted markdown for key metrics."""
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
        print("Usage: python test_gemini_extraction.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"🧪 Gemini 2.5 Flash - PDF Extraction Test")
    print(f"{'='*60}")
    print(f"📁 File: {pdf_path}")
    print()
    
    # Step 1: Convert PDF to images
    images = pdf_to_images(pdf_path)
    
    # Step 2: Extract with Gemini
    markdown, usage = extract_with_gemini(images)
    
    # Step 3: Calculate cost
    cost = calculate_cost(usage)
    
    # Step 4: Analyze output
    analysis = analyze_output(markdown)
    
    # Step 5: Save output
    output_path = Path(pdf_path).stem + "_extracted.md"
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
