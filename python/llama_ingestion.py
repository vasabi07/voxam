"""
Llama-4-Scout Document Ingestion Pipeline

Replaces Gemini with Llama-4-Scout via DeepInfra for:
- No copyright blocks on educational content
- Structured JSON output with inline image descriptions
- 320k context window (handles up to ~120 pages)

Neo4j Schema:
Document → Chapter → Section → Subsection → QuestionSet
"""

import os
import json
import time
import base64
import uuid
from pathlib import Path
from io import BytesIO
from typing import Optional, List, Dict, Tuple, Any
from pydantic import BaseModel, Field
from enum import Enum
from dotenv import load_dotenv
from pdf2image import convert_from_path
from PIL import Image
import httpx
import fitz  # PyMuPDF for image extraction
from concurrent.futures import ThreadPoolExecutor, as_completed

# LangChain - only used for embeddings now, not question generation
from langchain.chat_models import init_chat_model

# OpenAI for embeddings
import openai

load_dotenv()

# Neo4j
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# DeepInfra
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

# Limits
MAX_PAGES = 100

# Pricing per 1M tokens (USD)
PRICING = {
    "llama-4-scout": {"input": 0.15, "output": 0.60},
    "gpt-oss-120b": {"input": 0.039, "output": 0.19},
}

# Token counter for cost tracking (thread-safe)
import threading
class TokenCounter:
    def __init__(self):
        self._lock = threading.Lock()
        self.llama_input = 0
        self.llama_output = 0
        self.gpt_oss_input = 0
        self.gpt_oss_output = 0
    
    def add_llama(self, input_tokens: int, output_tokens: int):
        with self._lock:
            self.llama_input += input_tokens
            self.llama_output += output_tokens
    
    def add_gpt_oss(self, input_tokens: int, output_tokens: int):
        with self._lock:
            self.gpt_oss_input += input_tokens
            self.gpt_oss_output += output_tokens
    
    def get_cost_usd(self) -> float:
        llama_cost = (
            (self.llama_input / 1_000_000) * PRICING["llama-4-scout"]["input"] +
            (self.llama_output / 1_000_000) * PRICING["llama-4-scout"]["output"]
        )
        gpt_cost = (
            (self.gpt_oss_input / 1_000_000) * PRICING["gpt-oss-120b"]["input"] +
            (self.gpt_oss_output / 1_000_000) * PRICING["gpt-oss-120b"]["output"]
        )
        return llama_cost + gpt_cost
    
    def get_summary(self) -> dict:
        return {
            "llama_input_tokens": self.llama_input,
            "llama_output_tokens": self.llama_output,
            "gpt_oss_input_tokens": self.gpt_oss_input,
            "gpt_oss_output_tokens": self.gpt_oss_output,
            "total_cost_usd": round(self.get_cost_usd(), 4)
        }


# ============================================================
# Pydantic Models for Extraction
# ============================================================

class Section(BaseModel):
    """A section of the document with inline image markers"""
    title: str = Field(description="Section title like '6.1 Nervous System'")
    content: str = Field(description="Full text content including [IMAGE: description] markers")


class Equation(BaseModel):
    """Mathematical equation with LaTeX and spoken form"""
    latex: str = Field(description="LaTeX notation")
    spoken: str = Field(description="How to read aloud")
    context: Optional[str] = Field(default=None, description="What this equation represents")


class TextbookQuestion(BaseModel):
    """Question from the textbook exercises"""
    question_text: str
    question_type: str = Field(description="mcq, short_answer, or long_answer")
    options: Optional[List[str]] = Field(default=None, description="MCQ options if applicable")


class ExtractedDocument(BaseModel):
    """Structured extraction result from Llama-4-Scout"""
    document_title: str
    sections: List[Section]
    equations: List[Equation] = Field(default_factory=list)
    textbook_questions: List[TextbookQuestion] = Field(default_factory=list)


# ============================================================
# Question Generation Models
# ============================================================

class BloomLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class Difficulty(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class QuestionType(str, Enum):
    LONG_ANSWER = "long_answer"
    MULTIPLE_CHOICE = "multiple_choice"


class Question(BaseModel):
    """A generated question"""
    text: str = Field(description="The question text")
    bloom_level: BloomLevel
    difficulty: Difficulty
    question_type: QuestionType
    expected_time_minutes: int = Field(description="Expected time to answer")
    correct_answer: str
    key_points: List[str] = Field(description="Key points for evaluation")
    options: Optional[List[str]] = Field(default=None, description="MCQ options")
    explanation: Optional[str] = Field(default=None)
    # Image reference (URL attached if section has image)
    image_url: Optional[str] = Field(default=None)


class QuestionSet(BaseModel):
    """Questions generated for a section"""
    long_answer_questions: List[Question] = Field(default_factory=list)
    multiple_choice_questions: List[Question] = Field(default_factory=list)


# ============================================================
# Helper Functions
# ============================================================

def embed_text(text: str) -> List[float]:
    """Generate embeddings using OpenAI."""
    client = openai.OpenAI()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def pdf_to_images(file_path: str, dpi: int = 150) -> List[Image.Image]:
    """Convert PDF to images."""
    print(f"📄 Converting PDF to images...")
    images = convert_from_path(file_path, dpi=dpi)
    print(f"   ✅ Converted {len(images)} pages")
    return images


def image_to_base64(pil_image: Image.Image) -> str:
    """Convert PIL image to base64."""
    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def get_neo4j_driver():
    """Get Neo4j driver."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("RETURN 1")
    return driver


# ============================================================
# Hybrid OCR: Router & Text Extraction
# ============================================================

def detect_pdf_type(file_path: str, threshold: int = 200) -> str:
    """
    Detect if PDF has native text or needs OCR.
    
    Args:
        file_path: Path to PDF file
        threshold: Minimum chars/page to consider native (default 200)
    
    Returns:
        "native" if PyMuPDF can extract text, "scanned" if OCR needed
    """
    doc = fitz.open(file_path)
    total_chars = sum(len(page.get_text()) for page in doc)
    avg_chars_per_page = total_chars / len(doc) if len(doc) > 0 else 0
    doc.close()
    
    pdf_type = "native" if avg_chars_per_page > threshold else "scanned"
    print(f"📋 PDF type: {pdf_type} ({avg_chars_per_page:.0f} chars/page avg)")
    return pdf_type


def extract_text_pymupdf(file_path: str) -> Dict[int, str]:
    """
    Extract text per page using PyMuPDF.
    Fast and accurate for native (non-scanned) PDFs.
    
    Returns:
        Dict mapping page_number (1-indexed) -> text content
    """
    print("📖 Extracting text with PyMuPDF...")
    doc = fitz.open(file_path)
    text_by_page = {}
    
    for page_num, page in enumerate(doc):
        text = page.get_text()
        text_by_page[page_num + 1] = text  # 1-indexed
    
    total_chars = sum(len(t) for t in text_by_page.values())
    doc.close()
    print(f"   ✅ Extracted {total_chars:,} chars from {len(text_by_page)} pages")
    return text_by_page


def extract_text_ocr(file_path: str) -> Dict[int, str]:
    """
    Extract text from scanned PDFs using DeepInfra olmOCR API.
    Falls back to this when detect_pdf_type() returns "scanned".
    
    Returns:
        Dict mapping page_number (1-indexed) -> text content
    """
    print("🔍 OCR extraction with olmOCR...")
    
    # Convert PDF to images
    images = pdf_to_images(file_path)
    text_by_page = {}
    
    for page_num, img in enumerate(images, 1):
        # Prepare image for API
        b64 = image_to_base64(img)
        
        # Call olmOCR via DeepInfra
        response = httpx.post(
            DEEPINFRA_URL,
            headers={
                "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "allenai/olmOCR-2-7B-1025",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this document page. Output only the text, no commentary."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                    ]
                }],
                "max_tokens": 8000,
                "temperature": 0
            },
            timeout=120.0
        )
        
        if response.status_code == 200:
            result = response.json()
            text_by_page[page_num] = result["choices"][0]["message"]["content"]
        else:
            print(f"   ⚠️ OCR failed for page {page_num}: {response.status_code}")
            text_by_page[page_num] = ""
    
    total_chars = sum(len(t) for t in text_by_page.values())
    print(f"   ✅ OCR extracted {total_chars:,} chars from {len(text_by_page)} pages")
    return text_by_page


# ============================================================
# Image Extraction & R2 Upload
# ============================================================

def extract_images_from_pdf(file_path: str) -> Dict[int, List[Dict[str, Any]]]:
    """
    Extract images from PDF using PyMuPDF.
    Images are sorted by y-position (top to bottom) within each page for reading order.
    
    Returns:
        Dict mapping page_number (1-indexed) -> list of {image_bytes, bbox, index, page}
        Images within each page are sorted by vertical position (reading order)
    """
    print(f"🖼️  Extracting images from PDF...")
    
    doc = fitz.open(file_path)
    images_by_page: Dict[int, List[Dict[str, Any]]] = {}
    total_images = 0
    
    for page_num, page in enumerate(doc):
        page_images = []
        image_list = page.get_images(full=True)
        
        for img_idx, img in enumerate(image_list):
            try:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Get image position on page (for matching to sections)
                img_rects = page.get_image_rects(xref)
                bbox = img_rects[0] if img_rects else None
                
                # Get y-position for sorting (top of image)
                y_pos = bbox.y0 if bbox else 0
                
                page_images.append({
                    "image_bytes": image_bytes,
                    "ext": image_ext,
                    "bbox": bbox,
                    "y_pos": y_pos,
                    "page": page_num + 1  # 1-indexed
                })
                total_images += 1
                
            except Exception as e:
                print(f"   ⚠️ Error extracting image {img_idx} from page {page_num + 1}: {e}")
                continue
        
        # Sort images by y-position (reading order: top to bottom)
        if page_images:
            page_images.sort(key=lambda x: x["y_pos"])
            # Assign index after sorting
            for idx, img in enumerate(page_images):
                img["index"] = idx
            images_by_page[page_num + 1] = page_images
    
    doc.close()
    print(f"   ✅ Extracted {total_images} images from {len(images_by_page)} pages")
    return images_by_page


def upload_image_to_r2(image_bytes: bytes, file_key: str) -> Optional[str]:
    """
    Upload image to R2 and return public URL.
    
    TODO: Implement actual R2 upload using boto3 or cloudflare SDK
    
    Args:
        image_bytes: Raw image data
        file_key: R2 key like "documents/{doc_id}/images/{image_id}.png"
        
    Returns:
        Public URL or None if failed
    """
    # PLACEHOLDER: Replace with actual R2 upload
    # Example implementation:
    # import boto3
    # s3 = boto3.client('s3',
    #     endpoint_url=os.getenv("R2_ENDPOINT"),
    #     aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    #     aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY")
    # )
    # s3.put_object(
    #     Bucket=os.getenv("R2_BUCKET"),
    #     Key=file_key,
    #     Body=image_bytes,
    #     ContentType="image/png"
    # )
    # return f"{os.getenv('R2_PUBLIC_URL')}/{file_key}"
    
    print(f"   📤 [PLACEHOLDER] Would upload {len(image_bytes)} bytes to R2: {file_key}")
    return f"https://r2.voxam.dev/{file_key}"


import re

def parse_image_markers(content: str) -> List[Dict[str, Any]]:
    """
    Parse [IMAGE_N page=X: description] markers from content.
    
    Returns:
        List of {index, page, description, full_match} for each marker
    """
    # Pattern: [IMAGE_N page=X: description]
    # Also supports legacy [IMAGE: description] format
    pattern = r'\[IMAGE(?:_(\d+))?\s*(?:page=(\d+))?\s*:\s*([^\]]+)\]'
    
    markers = []
    for match in re.finditer(pattern, content):
        img_index = int(match.group(1)) if match.group(1) else None
        page_num = int(match.group(2)) if match.group(2) else None
        description = match.group(3).strip()
        
        markers.append({
            "index": img_index,
            "page": page_num,
            "description": description,
            "full_match": match.group(0)
        })
    
    return markers


def build_image_index(
    images_by_page: Dict[int, List[Dict[str, Any]]],
    doc_id: str
) -> Dict[str, str]:
    """
    Build an index mapping (page, order) -> image_url.
    Uploads images to R2 and returns the lookup table.
    
    Args:
        images_by_page: Dict of page_num -> sorted list of images
        doc_id: Document ID for file naming
        
    Returns:
        Dict mapping "page_N_img_M" -> image_url
    """
    print(f"📋 Building image index...")
    
    image_index: Dict[str, str] = {}
    global_counter = 0
    
    for page_num in sorted(images_by_page.keys()):
        page_images = images_by_page[page_num]
        
        for img_order, img_data in enumerate(page_images):
            image_bytes = img_data["image_bytes"]
            ext = img_data.get("ext", "png")
            
            # Upload to R2
            file_key = f"documents/{doc_id}/images/p{page_num}_img{img_order}.{ext}"
            image_url = upload_image_to_r2(image_bytes, file_key)
            
            if image_url:
                # Index by page and order
                key = f"page_{page_num}_img_{img_order}"
                image_index[key] = image_url
                global_counter += 1
    
    print(f"   ✅ Indexed {global_counter} images")
    return image_index


def attach_image_urls_to_questions(
    questions: Dict[str, 'QuestionSet'],
    sections: List['Section'],
    images_by_page: Dict[int, List[Dict[str, Any]]],
    doc_id: str
) -> Dict[str, 'QuestionSet']:
    """
    Match extracted images to sections using page-based smart matching.
    
    Strategy:
    1. Parse [IMAGE_N page=X: ...] markers from section content
    2. Match to PyMuPDF images by page number + reading order
    3. Attach correct image_url to questions
    
    Args:
        questions: Dict of section_title -> QuestionSet
        sections: List of extracted sections
        images_by_page: Dict of page_num -> list of image data (sorted by y-pos)
        doc_id: Document ID for file naming
        
    Returns:
        Updated questions dict with image_url populated
    """
    print(f"🔗 Attaching image URLs to questions (smart matching)...")
    
    # Step 1: Build image index (upload all images, get URLs)
    image_index = build_image_index(images_by_page, doc_id)
    
    # Track page-level counters for images without explicit indices
    page_counters: Dict[int, int] = {}
    
    images_attached = 0
    
    for section in sections:
        # Parse image markers from section content
        markers = parse_image_markers(section.content)
        
        if not markers:
            continue
            
        section_questions = questions.get(section.title)
        if not section_questions:
            continue
        
        # Collect all image URLs for this section
        section_image_urls: List[str] = []
        
        for marker in markers:
            page = marker["page"]
            img_index = marker["index"]
            
            # If no page specified, we can't match accurately
            if page is None:
                # Fallback: use first available image from any page
                for p in sorted(images_by_page.keys()):
                    if p not in page_counters:
                        page_counters[p] = 0
                    idx = page_counters[p]
                    key = f"page_{p}_img_{idx}"
                    if key in image_index:
                        section_image_urls.append(image_index[key])
                        page_counters[p] += 1
                        break
            else:
                # Smart matching: use page + order
                if img_index is not None:
                    # Explicit index: IMAGE_1 = index 0, IMAGE_2 = index 1, etc.
                    order = img_index - 1  # Convert to 0-indexed
                else:
                    # No explicit index: use counter for this page
                    if page not in page_counters:
                        page_counters[page] = 0
                    order = page_counters[page]
                    page_counters[page] += 1
                
                key = f"page_{page}_img_{order}"
                if key in image_index:
                    section_image_urls.append(image_index[key])
                else:
                    # Fallback: try first image on that page
                    fallback_key = f"page_{page}_img_0"
                    if fallback_key in image_index:
                        section_image_urls.append(image_index[fallback_key])
        
        # Attach image URLs to questions
        # If single image: all questions get that image
        # If multiple images: distribute or use first one
        if section_image_urls:
            primary_image = section_image_urls[0]
            
            for q in section_questions.long_answer_questions:
                q.image_url = primary_image
                images_attached += 1
                
            for q in section_questions.multiple_choice_questions:
                q.image_url = primary_image
                images_attached += 1
            
            print(f"   ✅ Section '{section.title[:40]}...': {len(section_image_urls)} images matched")
    
    print(f"   ✅ Attached images to {images_attached} questions")
    return questions


# ============================================================
# Hybrid OCR: Image Description & Sectioning
# ============================================================

def describe_images_from_pages(
    file_path: str,
    token_counter: Optional['TokenCounter'] = None
) -> List[Dict[str, Any]]:
    """
    Describe educational images by sending full page screenshots to Llama-4-Scout.
    This captures ALL visual content including vector diagrams.
    
    Returns:
        List of {page, description} for pages with educational diagrams
    """
    print("🖼️  Analyzing pages for diagrams with Llama-4-Scout...")
    
    # Convert PDF to page images
    images = pdf_to_images(file_path, dpi=100)  # Lower DPI for faster processing
    
    # Limit pages to avoid API timeout (skip first page often has title only)
    # Focus on content pages
    max_pages = min(len(images), 10)
    print(f"   📋 Processing {max_pages} pages for diagrams...")
    
    # Build content - one image per page
    content = [{"type": "text", "text": """Analyze these document pages and identify educational diagrams/figures.

For EACH PAGE that contains a diagram, figure, or illustration (NOT just text), output:
{"page": X, "description": "Brief description of the diagram"}

Examples of what to look for:
- Labeled diagrams (neuron structure, brain anatomy, reflex arc, etc.)
- Scientific illustrations
- Flowcharts or process diagrams
- Data tables with visual elements

SKIP pages that only contain text without any visual diagrams.

Output a JSON array. Example:
[
  {"page": 2, "description": "Structure of a neuron showing dendrites, cell body, and axon"},
  {"page": 3, "description": "Reflex arc diagram showing sensory and motor neurons"}
]

If no diagrams found, output: []
"""}]
    
    for i, img in enumerate(images[:max_pages]):
        content.append({"type": "text", "text": f"--- PAGE {i + 1} ---"})
        b64 = image_to_base64(img)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })
    
    # Call Llama-4-Scout
    response = httpx.post(
        DEEPINFRA_URL,
        headers={
            "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 2000,
            "temperature": 0
        },
        timeout=180.0
    )
    
    if response.status_code != 200:
        print(f"   ⚠️ Llama API error: {response.status_code}")
        try:
            print(f"   ⚠️ Response: {response.text[:200]}")
        except:
            pass
        return []
    
    result = response.json()
    usage = result.get("usage", {})
    if token_counter:
        token_counter.add_llama(
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0)
        )
    
    text = result["choices"][0]["message"]["content"]
    
    # Parse JSON array - handle extra text after JSON
    try:
        start = text.find('[')
        if start != -1:
            depth = 0
            end = start
            for i, char in enumerate(text[start:], start):
                if char == '[':
                    depth += 1
                elif char == ']':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            
            json_str = text[start:end]
            descriptions = json.loads(json_str)
            print(f"   ✅ Found diagrams on {len(descriptions)} pages")
            for d in descriptions:
                print(f"      Page {d.get('page')}: {d.get('description', '')[:60]}...")
            return descriptions
    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON parse error: {e}")
    
    print(f"   ⚠️ Could not parse image descriptions")
    print(f"   📝 Raw response (first 500 chars): {text[:500]}")
    return []


def organize_sections_unstructured(
    file_path: str,
    image_descriptions: List[Dict[str, Any]]
) -> ExtractedDocument:
    """
    Use unstructured's 'by_title' strategy to organize content into sections.
    Much faster than GPT OSS and more reliable.
    
    Args:
        file_path: Path to PDF file
        image_descriptions: List of {page, description} from Llama
    
    Returns:
        ExtractedDocument with sections
    """
    from unstructured.partition.pdf import partition_pdf
    
    print("📑 Organizing into sections with unstructured (by_title)...")
    
    try:
        chunks = partition_pdf(
            filename=file_path,
            strategy="hi_res",  # hi_res for proper text extraction
            chunking_strategy="by_title",
            max_characters=8000,
            combine_text_under_n_chars=2000,
            new_after_n_chars=6000,
        )
        
        print(f"   ✅ Created {len(chunks)} chunks")
        
        # Each chunk becomes a section
        sections = []
        chunk_idx = 1
        
        for chunk in chunks:
            chunk_text = str(chunk)
            if len(chunk_text) < 100:  # Skip tiny chunks (likely headers/footers)
                continue
                
            page_num = getattr(chunk.metadata, 'page_number', 1) if hasattr(chunk, 'metadata') else 1
            
            # Add image markers for this page
            content_parts = []
            page_images = [d for d in image_descriptions if d.get("page") == page_num]
            for img in page_images:
                content_parts.append(f"[IMAGE page={page_num}: {img.get('description', 'diagram')}]")
            
            content_parts.append(chunk_text)
            
            # Try to extract a title from the first line
            lines = chunk_text.split('\n')
            first_line = lines[0].strip() if lines else ""
            if len(first_line) < 80:
                title = first_line[:60] if first_line else f"Section {chunk_idx}"
            else:
                title = f"Section {chunk_idx}"
            
            sections.append(Section(
                title=title,
                content="\n".join(content_parts)
            ))
            chunk_idx += 1
        
        print(f"   ✅ Final: {len(sections)} sections")
        
        return ExtractedDocument(
            document_title=sections[0].title if sections else "Document",
            sections=sections,
            equations=[],
            textbook_questions=[]
        )
        
    except Exception as e:
        print(f"   ⚠️ Unstructured failed: {e}")
        # Fallback: create one section per 2 pages
        return _create_page_based_sections(file_path, image_descriptions)


def _create_page_based_sections(
    file_path: str,
    image_descriptions: List[Dict[str, Any]]
) -> ExtractedDocument:
    """Fallback: create sections from pages using PyMuPDF."""
    print("   📄 Using fallback page-based sectioning...")
    
    text_by_page = extract_text_pymupdf(file_path)
    
    # Group every 2-3 pages into a section
    sections = []
    pages = sorted(text_by_page.keys())
    
    for i in range(0, len(pages), 2):
        page_group = pages[i:i+2]
        content_parts = []
        
        for page_num in page_group:
            # Add image markers for this page
            page_images = [d for d in image_descriptions if d.get("page") == page_num]
            for img in page_images:
                content_parts.append(f"[IMAGE page={page_num}: {img.get('description', 'diagram')}]")
            
            content_parts.append(text_by_page[page_num])
        
        sections.append(Section(
            title=f"Pages {page_group[0]}-{page_group[-1]}",
            content="\n".join(content_parts)
        ))
    
    return ExtractedDocument(
        document_title="Document",
        sections=sections,
        equations=[],
        textbook_questions=[]
    )


# NOTE: GPT OSS sectioning removed - use organize_sections_unstructured instead


# ============================================================
# Extraction Schema for Llama-4-Scout
# ============================================================

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "document_title": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {
                        "type": "string",
                        "description": "Full content with [IMAGE: description] markers inline"
                    }
                },
                "required": ["title", "content"]
            }
        },
        "equations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "latex": {"type": "string"},
                    "spoken": {"type": "string"},
                    "context": {"type": "string"}
                },
                "required": ["latex", "spoken"]
            }
        },
        "textbook_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_text": {"type": "string"},
                    "question_type": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["question_text", "question_type"]
            }
        }
    },
    "required": ["document_title", "sections"]
}


# ============================================================
# Llama-4-Scout Ingestion Pipeline
# ============================================================

class LlamaIngestionPipeline:
    """
    Document ingestion pipeline using Llama-4-Scout via DeepInfra.
    
    Phases:
    1. Extraction: PDF → Images → Llama-4-Scout → Structured JSON
    2. Question Generation: Section → Questions
    3. Neo4j Persistence: Store hierarchy with embeddings
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # Token counter for cost tracking
        self.token_counter = TokenCounter()
        
        # Question generation uses GPT OSS 120B via DeepInfra
        # No LangChain needed - direct API calls
        
        # Neo4j
        self.neo4j_driver = None
        try:
            self.neo4j_driver = get_neo4j_driver()
            print("✅ Connected to Neo4j")
        except Exception as e:
            print(f"⚠️ Neo4j not available: {e}")
    
    # ================== Phase 1: Extraction ==================
    
    def extract_document(self, file_path: str) -> ExtractedDocument:
        """
        Extract structured content from PDF using hybrid pipeline.
        
        Pipeline:
        1. Llama: Full page screenshots → Diagram identification
        2. Unstructured: 'by_title' sectioning (fast, reliable)
        3. Merge: Insert image markers into sections
        """
        print("⏳ Phase 1: Hybrid Extraction...")
        start_time = time.time()
        
        # Step 1: Describe images using full page screenshots
        # This captures ALL visual content including vector diagrams
        image_descriptions = describe_images_from_pages(file_path, self.token_counter)
        
        # Step 2: Organize into sections with unstructured (fast!)
        extracted = organize_sections_unstructured(file_path, image_descriptions)
        
        elapsed = time.time() - start_time
        print(f"✅ Phase 1 complete: {len(extracted.sections)} sections in {elapsed:.2f}s")
        
        return extracted
    
    # ================== Phase 2: Question Generation ==================
    
    def generate_questions(self, section: Section) -> QuestionSet:
        """
        Generate questions for a section using GPT OSS 120B via DeepInfra.
        Section content includes inline [IMAGE: ...] markers.
        """
        print(f"   📝 Generating questions for: {section.title[:50]}...")
        
        prompt = f"""Generate educational questions for this section.

## Section: {section.title}

## Content:
{section.content}

## Instructions:
1. Generate 3 long answer questions covering key concepts
2. Generate 3 multiple choice questions (4 options each with correct answer)
3. Follow Bloom's Taxonomy distribution:
   - At least 1 question at 'remember' level (recall facts from content)
   - At least 1 question at 'understand' level (explain concepts in content)
   - At least 1 question at 'apply' or 'analyze' level (apply/analyze knowledge from content)
4. Vary difficulty across basic, intermediate, advanced
5. Reference [IMAGE_N page=X: ...] markers when relevant
6. Include key_points for long answer questions (answers must come from the content)
7. Include expected_time in minutes

CRITICAL: ALL questions MUST be answerable using ONLY the provided content.
- For 'apply' and 'analyze' questions: challenge students to think deeper about what IS in the content
- Do NOT require external knowledge or information not present in the section
- The key_points answer should be derivable from the provided text

Return JSON with this structure:
{{
  "long_answer_questions": [
    {{
      "text": "question text",
      "bloom_level": "remember|understand|apply|analyze",
      "difficulty": "basic|intermediate|advanced",
      "question_type": "long_answer",
      "expected_time": 5,
      "key_points": ["point1", "point2"]
    }}
  ],
  "multiple_choice_questions": [
    {{
      "text": "question text",
      "bloom_level": "remember|understand|apply|analyze",
      "difficulty": "basic|intermediate|advanced",
      "question_type": "multiple_choice",
      "expected_time": 2,
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A"
    }}
  ]
}}"""

        # Call GPT OSS 120B via DeepInfra
        response = httpx.post(
            DEEPINFRA_URL,
            headers={
                "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-oss-120b",
                "messages": [
                    {"role": "system", "content": "Reasoning: high\nYou are an educational assessment expert. Generate high-quality questions following Bloom's Taxonomy. Always respond with valid JSON only, no markdown."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 4000,
                "temperature": 0.3
            },
            timeout=120.0
        )
        
        result = response.json()
        
        if "error" in result:
            print(f"   ⚠️ Question generation error: {result['error']}")
            return QuestionSet(long_answer_questions=[], multiple_choice_questions=[])
        
        # Track token usage
        usage = result.get("usage", {})
        if hasattr(self, 'token_counter') and self.token_counter:
            self.token_counter.add_gpt_oss(
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0)
            )
        
        content = result["choices"][0]["message"]["content"]
        
        # Extract JSON from content (may have markdown code blocks)
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
        
        try:
            questions_dict = json.loads(content)
            
            # Convert to QuestionSet with proper Question objects
            long_answers = []
            for q in questions_dict.get("long_answer_questions", []):
                long_answers.append(Question(
                    text=q.get("text", ""),
                    bloom_level=q.get("bloom_level", "understand"),
                    difficulty=q.get("difficulty", "intermediate"),
                    question_type="long_answer",
                    expected_time_minutes=q.get("expected_time", 5),
                    key_points=q.get("key_points", []) or [],
                    options=None,
                    correct_answer="",  # Long answer questions don't have a single correct answer
                    explanation=None,
                    image_url=None
                ))
            
            mcqs = []
            for q in questions_dict.get("multiple_choice_questions", []):
                mcqs.append(Question(
                    text=q.get("text", ""),
                    bloom_level=q.get("bloom_level", "remember"),
                    difficulty=q.get("difficulty", "basic"),
                    question_type="multiple_choice",
                    expected_time_minutes=q.get("expected_time", 2),
                    key_points=[],  # MCQs use correct_answer instead
                    options=q.get("options", []),
                    correct_answer=q.get("correct_answer", "") or "",
                    explanation=q.get("explanation", ""),
                    image_url=None
                ))
            
            return QuestionSet(long_answer_questions=long_answers, multiple_choice_questions=mcqs)
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️ Failed to parse questions JSON: {e}")
            return QuestionSet(long_answer_questions=[], multiple_choice_questions=[])
    
    # ================== Phase 3: Neo4j Persistence ==================
    
    def persist_to_neo4j(
        self,
        doc_id: str,
        user_id: str,
        title: str,
        extracted: ExtractedDocument,
        all_questions: Dict[str, QuestionSet]
    ):
        """
        Persist document structure and questions to Neo4j.
        """
        if not self.neo4j_driver:
            print("⚠️ Neo4j not available, skipping persistence")
            return
        
        print("⏳ Phase 3: Persisting to Neo4j...")
        start_time = time.time()
        
        with self.neo4j_driver.session() as session:
            # Create Document node
            session.run("""
                MERGE (d:Document {documentId: $doc_id})
                SET d.title = $title,
                    d.userId = $user_id,
                    d.createdAt = datetime()
            """, doc_id=doc_id, title=title, user_id=user_id)
            
            # Create sections and questions
            for idx, section in enumerate(extracted.sections):
                section_id = f"{doc_id}_section_{idx}"
                
                # Extract page numbers from IMAGE markers in content
                # Pattern: [IMAGE_N page=X: ...]
                import re
                page_matches = re.findall(r'\[IMAGE_\d+ page=(\d+)', section.content)
                if page_matches:
                    pages = [int(p) for p in page_matches]
                    page_start = min(pages)
                    page_end = max(pages)
                else:
                    # Fallback: estimate based on section index
                    # Rough: if 7 sections over 13 pages, each section ~2 pages
                    total_pages = len(extracted.sections) * 2  # Rough estimate
                    page_start = idx + 1
                    page_end = idx + 2
                
                # Generate embedding for section content
                embedding = embed_text(section.content[:8000])  # Truncate for embedding
                
                # Create ContentBlock (section) with page numbers for citations
                session.run("""
                    MATCH (d:Document {documentId: $doc_id})
                    MERGE (cb:ContentBlock {block_id: $section_id})
                    SET cb.title = $title,
                        cb.content = $content,
                        cb.chunk_index = $idx,
                        cb.page_start = $page_start,
                        cb.page_end = $page_end,
                        cb.embedding = $embedding
                    MERGE (d)-[:HAS_CONTENT_BLOCK]->(cb)
                """, 
                    doc_id=doc_id,
                    section_id=section_id,
                    title=section.title,
                    content=section.content,
                    idx=idx,
                    page_start=page_start,
                    page_end=page_end,
                    embedding=embedding
                )
                
                # Get questions for this section
                question_set = all_questions.get(section.title)
                if question_set:
                    all_qs = question_set.long_answer_questions + question_set.multiple_choice_questions
                    
                    if all_qs:
                        # Convert to JSON
                        questions_json = json.dumps([{
                            "question_id": f"{section_id}_q{i}",
                            "text": q.text,
                            "bloom_level": q.bloom_level.value,
                            "difficulty": q.difficulty.value,
                            "question_type": q.question_type.value,
                            "expected_time": q.expected_time_minutes,
                            "correct_answer": q.correct_answer,
                            "key_points": q.key_points,
                            "options": q.options or [],
                            "explanation": q.explanation or "",
                            "image_url": q.image_url
                        } for i, q in enumerate(all_qs)])
                        
                        # Create QuestionSet node
                        session.run("""
                            MATCH (cb:ContentBlock {block_id: $section_id})
                            MERGE (qs:QuestionSet {set_id: $set_id})
                            SET qs.questions = $questions_json,
                                qs.total_count = $total
                            MERGE (cb)-[:HAS_QUESTIONS]->(qs)
                        """,
                            section_id=section_id,
                            set_id=f"{section_id}_qs",
                            questions_json=questions_json,
                            total=len(all_qs)
                        )
        
        elapsed = time.time() - start_time
        print(f"✅ Phase 3 complete: Persisted to Neo4j in {elapsed:.2f}s")
    
    # ================== Main Ingestion ==================
    
    def ingest_document(
        self,
        file_path: str,
        doc_id: str,
        user_id: str,
        title: str = None,
        generate_questions: bool = True,
        extract_images: bool = True
    ) -> Dict[str, Any]:
        """
        Full ingestion pipeline.
        
        Args:
            file_path: Path to PDF file
            doc_id: Unique document identifier
            user_id: User who uploaded
            title: Optional title (defaults to filename)
            generate_questions: Whether to generate questions
            extract_images: Whether to extract and attach images
        
        Returns:
            Summary dict with extraction and question counts
        """
        print(f"\n{'='*60}")
        print(f"📚 Ingesting: {Path(file_path).name}")
        print(f"{'='*60}\n")
        
        total_start = time.time()
        
        if not title:
            title = Path(file_path).stem
        
        # Phase 1a: Extract text content with Llama-4-Scout
        extracted = self.extract_document(file_path)
        
        # Phase 1b: Extract images from PDF
        images_by_page = {}
        if extract_images:
            print("\n⏳ Phase 1b: Image Extraction...")
            images_by_page = extract_images_from_pdf(file_path)
        
        # Phase 2a: Generate questions (PARALLEL for speed)
        all_questions = {}
        if generate_questions:
            print("\n⏳ Phase 2a: Question Generation (parallel)...")
            
            # Use ThreadPoolExecutor for parallel API calls
            # 5 workers balances speed vs API rate limits
            def generate_for_section(section):
                questions = self.generate_questions(section)
                return section.title, questions
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(generate_for_section, s): s for s in extracted.sections}
                
                for future in as_completed(futures):
                    try:
                        title, questions = future.result()
                        all_questions[title] = questions
                    except Exception as e:
                        section = futures[future]
                        print(f"   ⚠️ Failed to generate questions for '{section.title[:30]}': {e}")
            
            total_qs = sum(
                len(qs.long_answer_questions) + len(qs.multiple_choice_questions)
                for qs in all_questions.values()
            )
            print(f"✅ Phase 2a complete: {total_qs} questions generated")
        
        # Phase 2b: Attach image URLs to questions
        images_attached = 0
        if extract_images and images_by_page and all_questions:
            print("\n⏳ Phase 2b: Attaching Image URLs...")
            all_questions = attach_image_urls_to_questions(
                all_questions,
                extracted.sections,
                images_by_page,
                doc_id
            )
            # Count how many questions got images
            for qs in all_questions.values():
                for q in qs.long_answer_questions + qs.multiple_choice_questions:
                    if q.image_url:
                        images_attached += 1
        
        # Phase 3: Persist to Neo4j
        self.persist_to_neo4j(doc_id, user_id, title, extracted, all_questions)
        
        total_elapsed = time.time() - total_start
        
        summary = {
            "doc_id": doc_id,
            "title": title,
            "sections": len(extracted.sections),
            "equations": len(extracted.equations),
            "questions": sum(
                len(qs.long_answer_questions) + len(qs.multiple_choice_questions)
                for qs in all_questions.values()
            ),
            "images_extracted": sum(len(imgs) for imgs in images_by_page.values()) if images_by_page else 0,
            "images_attached": images_attached,
            "elapsed_seconds": round(total_elapsed, 2)
        }
        
        # Add token usage and cost
        token_summary = self.token_counter.get_summary()
        summary["tokens"] = token_summary
        cost_usd = token_summary["total_cost_usd"]
        cost_inr = cost_usd * 85  # Approximate USD to INR
        
        print(f"\n{'='*60}")
        print(f"✅ Ingestion complete in {total_elapsed:.2f}s")
        print(f"   Sections: {summary['sections']}")
        print(f"   Questions: {summary['questions']}")
        print(f"   Images: {summary['images_extracted']} extracted, {summary['images_attached']} attached")
        print(f"   Tokens: {token_summary['llama_input_tokens'] + token_summary['gpt_oss_input_tokens']:,} in, "
              f"{token_summary['llama_output_tokens'] + token_summary['gpt_oss_output_tokens']:,} out")
        print(f"   💰 Cost: ${cost_usd:.4f} USD (₹{cost_inr:.2f})")
        print(f"{'='*60}\n")
        
        return summary


# ============================================================
# CLI for Testing
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python llama_ingestion.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    pipeline = LlamaIngestionPipeline()
    result = pipeline.ingest_document(
        file_path=pdf_path,
        doc_id=f"doc_{uuid.uuid4().hex[:8]}",
        user_id="test_user",
        generate_questions=True
    )
    
    print(json.dumps(result, indent=2))
