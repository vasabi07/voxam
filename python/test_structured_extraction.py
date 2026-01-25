"""
Llama-4-Scout - Structured JSON Output Test

Forces the model to:
1. Use proper hierarchy (1 chapter, multiple sections)
2. Capture ALL images with descriptions
3. Extract equations with latex + spoken forms

Usage:
    python test_structured_extraction.py <pdf_path>
"""

import os
import sys
import time
import base64
import json
from pathlib import Path
from io import BytesIO
from dotenv import load_dotenv
from pdf2image import convert_from_path
import httpx

load_dotenv()

# DeepInfra API
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

# Pricing
INPUT_PRICE = 0.08
OUTPUT_PRICE = 0.30

# JSON Schema for structured output
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "document_title": {
            "type": "string",
            "description": "The main title of the document/chapter"
        },
        "sections": {
            "type": "array",
            "description": "Main sections of the document (like 6.1, 6.2, etc.)",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string", "description": "Main text content of this section"},
                    "subsections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "content": {"type": "string"}
                            },
                            "required": ["title", "content"]
                        }
                    }
                },
                "required": ["title", "content"]
            }
        },
        "images": {
            "type": "array",
            "description": "ALL images, diagrams, and figures in the document. You MUST describe every visual.",
            "items": {
                "type": "object",
                "properties": {
                    "page_number": {"type": "integer"},
                    "figure_number": {"type": "string", "description": "e.g., 'Fig 6.1' or 'Activity 6.2'"},
                    "description": {"type": "string", "description": "Detailed description of what the image shows"},
                    "related_section": {"type": "string", "description": "Which section this image relates to"}
                },
                "required": ["description", "related_section"]
            }
        },
        "tables": {
            "type": "array",
            "description": "All tables in the document",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "headers": {"type": "array", "items": {"type": "string"}},
                    "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}
                },
                "required": ["headers", "rows"]
            }
        },
        "equations": {
            "type": "array",
            "description": "All mathematical equations and formulas",
            "items": {
                "type": "object",
                "properties": {
                    "latex": {"type": "string", "description": "LaTeX notation"},
                    "spoken": {"type": "string", "description": "How to read this aloud"},
                    "context": {"type": "string", "description": "What this equation represents"}
                },
                "required": ["latex", "spoken"]
            }
        },
        "key_terms": {
            "type": "array",
            "description": "Important vocabulary/definitions",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "definition": {"type": "string"}
                },
                "required": ["term", "definition"]
            }
        },
        "questions": {
            "type": "array",
            "description": "Questions from the textbook (exercises, in-text questions)",
            "items": {
                "type": "object",
                "properties": {
                    "question_text": {"type": "string"},
                    "question_type": {"type": "string", "enum": ["mcq", "short_answer", "long_answer"]},
                    "options": {"type": "array", "items": {"type": "string"}, "description": "For MCQ only"}
                },
                "required": ["question_text", "question_type"]
            }
        }
    },
    "required": ["document_title", "sections", "images"]
}


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


def extract_structured(images: list) -> tuple:
    """
    Extract with structured JSON output.
    """
    prompt = """You are extracting content from an educational textbook. Your job is to capture ALL the text content - do NOT summarize or shorten anything.

CRITICAL: Extract COMPLETE content, not summaries!

For each section:
- Include ALL paragraphs, explanations, and details
- Include ALL bullet points and numbered lists
- Include ALL examples and activities
- Do NOT skip or shorten any content
- Each section's "content" field should be LONG (multiple paragraphs)

For images:
- Describe EVERY image, diagram, figure, and illustration you see in detail
- Include what labels/text are visible in the image
- Note the approximate position on the page

For equations:
- Capture the exact formula in LaTeX
- Provide how to read it aloud

For questions:
- Include ALL questions from exercises, activities, and "think about it" sections
- Include MCQ options if present

The "content" field for each section should be COMPREHENSIVE - typically 200-500 words per section for a textbook. If a section has 3 paragraphs, include all 3 paragraphs.

Return valid JSON matching the schema."""

    print(f"🚀 Extracting structured content from {len(images)} pages...")
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
    
    # Call DeepInfra API with JSON schema
    response = httpx.post(
        DEEPINFRA_URL,
        headers={
            "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
            "messages": [
                {"role": "user", "content": content}
            ],
            "max_tokens": 16000,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "document_extraction",
                    "schema": EXTRACTION_SCHEMA,
                    "strict": True
                }
            }
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
    
    # Parse and validate JSON
    try:
        data = json.loads(text)
        return data, usage
    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON parse error: {e}")
        return text, usage


def calculate_cost(usage: dict) -> dict:
    """Calculate estimated cost from usage."""
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": (input_tokens / 1_000_000) * INPUT_PRICE,
        "output_cost": (output_tokens / 1_000_000) * OUTPUT_PRICE,
        "total_cost": ((input_tokens / 1_000_000) * INPUT_PRICE) + ((output_tokens / 1_000_000) * OUTPUT_PRICE)
    }


def analyze_output(data: dict) -> dict:
    """Analyze the extracted structured data."""
    if isinstance(data, str):
        return {"error": "Not valid JSON"}
    
    return {
        "document_title": data.get("document_title", "N/A"),
        "sections": len(data.get("sections", [])),
        "subsections": sum(len(s.get("subsections", [])) for s in data.get("sections", [])),
        "images": len(data.get("images", [])),
        "tables": len(data.get("tables", [])),
        "equations": len(data.get("equations", [])),
        "key_terms": len(data.get("key_terms", [])),
        "questions": len(data.get("questions", []))
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_structured_extraction.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    if not DEEPINFRA_API_KEY:
        print("❌ DEEPINFRA_API_KEY not set in environment")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"🧪 Structured JSON Extraction Test")
    print(f"{'='*60}")
    print(f"📁 File: {pdf_path}")
    print()
    
    # Step 1: Convert PDF to images
    images = pdf_to_images(pdf_path)
    
    # Step 2: Extract structured content
    data, usage = extract_structured(images)
    
    if not data:
        print("❌ Extraction failed")
        sys.exit(1)
    
    # Step 3: Calculate cost
    cost = calculate_cost(usage)
    
    # Step 4: Analyze output
    analysis = analyze_output(data)
    
    # Step 5: Save output
    output_path = Path(pdf_path).stem + "_structured.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n📝 Saved to: {output_path}")
    
    # Print results
    print(f"\n{'='*60}")
    print(f"📊 RESULTS")
    print(f"{'='*60}")
    
    print(f"\n💰 Cost Breakdown:")
    print(f"   Input tokens:  {cost['input_tokens']:,}")
    print(f"   Output tokens: {cost['output_tokens']:,}")
    print(f"   TOTAL COST:    ${cost['total_cost']:.4f}")
    
    print(f"\n📈 Extraction Analysis:")
    print(f"   Document:      {analysis.get('document_title', 'N/A')}")
    print(f"   Sections:      {analysis.get('sections', 0)}")
    print(f"   Subsections:   {analysis.get('subsections', 0)}")
    print(f"   Images:        {analysis.get('images', 0)} ⭐")
    print(f"   Tables:        {analysis.get('tables', 0)}")
    print(f"   Equations:     {analysis.get('equations', 0)}")
    print(f"   Key Terms:     {analysis.get('key_terms', 0)}")
    print(f"   Questions:     {analysis.get('questions', 0)}")
    
    # Show first few images if found
    if isinstance(data, dict) and data.get("images"):
        print(f"\n🖼️ First 3 Images Found:")
        for i, img in enumerate(data["images"][:3]):
            print(f"   {i+1}. {img.get('description', 'N/A')[:80]}...")
    
    print(f"\n{'='*60}")
    print(f"✅ Test complete! Check {output_path} for full JSON.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
