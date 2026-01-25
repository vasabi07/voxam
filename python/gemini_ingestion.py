"""
Gemini-based Document Ingestion Pipeline

Replaces Unstructured with Gemini 2.5 Flash for:
- Vision/OCR extraction (handwriting, scanned PDFs)
- Hierarchical document structuring
- Question generation (with pluggable model)

Neo4j Schema:
Document → Chapter → Section → Subsection → Questions
"""

import os
import io
import time
import json
from typing import List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from PIL import Image
from pdf2image import convert_from_path, convert_from_bytes
import google.generativeai as genai
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from neo4j import GraphDatabase
from openai import OpenAI

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# OpenAI for embeddings
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBED_MODEL = "text-embedding-3-small"

# Neo4j credentials
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


# ============================================================
# Pydantic Models for Hierarchical Structure
# ============================================================

class Subsection(BaseModel):
    """A subsection within a section"""
    title: str = Field(description="Subsection title")
    content: str = Field(description="Full text content of this subsection")
    page_start: int = Field(description="Starting page number")
    page_end: int = Field(description="Ending page number")


class Section(BaseModel):
    """A section within a chapter"""
    title: str = Field(description="Section title like '1.1 Laws of Heat'")
    subsections: List[Subsection] = Field(default_factory=list)


class Chapter(BaseModel):
    """A chapter within the document"""
    title: str = Field(description="Chapter title like 'Chapter 1: Thermodynamics'")
    sections: List[Section] = Field(default_factory=list)


class DocumentStructure(BaseModel):
    """Hierarchical structure of the entire document"""
    title: str = Field(description="Document title")
    chapters: List[Chapter] = Field(default_factory=list)


# ============================================================
# Question Models (reused from existing ingestion_workflow.py)
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
    """A single question with Bloom's taxonomy metadata"""
    text: str = Field(description="The question text")
    bloom_level: BloomLevel = Field(description="Bloom's taxonomy level")
    difficulty: Difficulty = Field(description="Question difficulty level")
    question_type: QuestionType = Field(description="Question type")
    expected_time: int = Field(description="Expected time to answer in minutes")
    key_points: List[str] = Field(default_factory=list, description="Key points expected in answer")
    options: Optional[List[str]] = Field(default=None, description="Options for MCQ")
    correct_answer: Optional[str] = Field(default=None, description="Correct answer for MCQ")
    explanation: Optional[str] = Field(default=None, description="Explanation for correct answer")
    
    # Image fields for multimodal questions
    image_url: Optional[str] = Field(default=None, description="R2 URL for question image")
    image_description: Optional[str] = Field(default=None, description="Description of image for LLM context and evaluation")
    image_type: Optional[str] = Field(default=None, description="Type: diagram, graph, flowchart, etc.")
    needs_image: bool = Field(default=False, description="Whether this question would benefit from a visual")
    image_prompt: Optional[str] = Field(default=None, description="Prompt to generate the image (for Flux)")


class QuestionSet(BaseModel):
    """Container for all questions from a subsection"""
    long_answer_questions: List[Question] = Field(default_factory=list)
    multiple_choice_questions: List[Question] = Field(default_factory=list)
    total_questions: int = Field(default=0)


# ============================================================
# Helper Functions
# ============================================================

def embed_text(text: str) -> List[float]:
    """Generate embeddings for text using OpenAI."""
    try:
        response = openai_client.embeddings.create(
            model=EMBED_MODEL,
            input=text[:8000]  # Truncate to stay within limits
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        return []


def pdf_to_images(file_path: str) -> List[Image.Image]:
    """Convert PDF pages to PIL Images for Gemini Vision."""
    print(f"📄 Converting PDF to images: {file_path}")
    try:
        # Check if file_path is bytes (from R2/S3) or path
        if isinstance(file_path, bytes):
            images = convert_from_bytes(file_path, dpi=150)
        else:
            images = convert_from_path(file_path, dpi=150)
        print(f"   ✅ Converted {len(images)} pages")
        return images
    except Exception as e:
        print(f"   ❌ PDF conversion error: {e}")
        return []


def get_neo4j_driver():
    """Get Neo4j database driver."""
    if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]):
        raise ValueError("Missing Neo4j credentials in .env")
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("RETURN 1")
    print("✅ Connected to Neo4j")
    return driver


# ============================================================
# Flux Image Generation (DeepInfra)
# ============================================================

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")

async def generate_image_with_flux(prompt: str, image_type: str = "diagram") -> Optional[bytes]:
    """
    Generate an image using Flux Schnell via DeepInfra.
    
    Args:
        prompt: Text prompt for image generation
        image_type: Type hint for styling (diagram, graph, flowchart)
        
    Returns:
        Image bytes or None if failed
    """
    import httpx
    
    if not DEEPINFRA_API_KEY:
        print("⚠️  DEEPINFRA_API_KEY not set, skipping image generation")
        return None
    
    # Enhance prompt based on image_type
    style_hints = {
        "diagram": "clean educational diagram, white background, clear labels, technical illustration style",
        "graph": "clear data visualization, labeled axes, clean lines, academic chart style",
        "flowchart": "professional flowchart, connected boxes, arrows, clean white background",
        "chart": "clean bar/pie chart, labeled sections, professional presentation style"
    }
    
    enhanced_prompt = f"{prompt}. Style: {style_hints.get(image_type, style_hints['diagram'])}"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.deepinfra.com/v1/inference/black-forest-labs/FLUX-1-schnell",
                headers={"Authorization": f"Bearer {DEEPINFRA_API_KEY}"},
                json={
                    "prompt": enhanced_prompt,
                    "width": 1024,
                    "height": 768,
                    "num_inference_steps": 4,  # Schnell is fast
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                # DeepInfra returns base64 image
                if "images" in result and result["images"]:
                    import base64
                    image_b64 = result["images"][0]
                    return base64.b64decode(image_b64)
            else:
                print(f"❌ Flux error: {response.status_code} - {response.text[:200]}")
                return None
                
    except Exception as e:
        print(f"❌ Flux generation error: {e}")
        return None


def upload_to_r2(image_bytes: bytes, file_key: str) -> Optional[str]:
    """
    Upload image to R2 and return public URL.
    
    TODO: Implement actual R2 upload
    
    Args:
        image_bytes: Image data
        file_key: R2 key (e.g., "question_images/q123.png")
        
    Returns:
        Public URL or None
    """
    # TODO: Replace with actual R2 upload logic
    # from r2 import upload_file
    # return await upload_file(image_bytes, file_key)
    
    print(f"📤 [PLACEHOLDER] Would upload {len(image_bytes)} bytes to R2: {file_key}")
    
    # Return placeholder URL for now
    # In production, return actual R2 URL
    return f"https://r2.example.com/{file_key}"


async def generate_images_for_questions(questions: List[Question], doc_id: str) -> List[Question]:
    """
    Generate images for questions that need them.
    
    Args:
        questions: List of questions (some may have needs_image=True)
        doc_id: Document ID for file naming
        
    Returns:
        Updated questions with image_url populated
    """
    import uuid
    
    for i, q in enumerate(questions):
        if q.needs_image and q.image_prompt:
            print(f"🎨 Generating image for question {i+1}: {q.text[:50]}...")
            
            # Generate with Flux
            image_bytes = await generate_image_with_flux(q.image_prompt, q.image_type or "diagram")
            
            if image_bytes:
                # Upload to R2
                image_id = f"{doc_id}_q{i}_{uuid.uuid4().hex[:8]}"
                file_key = f"question_images/{image_id}.png"
                
                image_url = upload_to_r2(image_bytes, file_key)
                
                if image_url:
                    q.image_url = image_url
                    print(f"   ✅ Image generated: {image_url}")
                    
                    # Clear the prompt (no longer needed)
                    q.image_prompt = None
                    q.needs_image = False
    
    return questions


# ============================================================
# Gemini Ingestion Pipeline
# ============================================================

class GeminiIngestionPipeline:
    """
    Document ingestion pipeline using Gemini 2.5 Flash.
    
    Phases:
    1. Vision Extraction: PDF/Image → Markdown
    2. Structuring: Markdown → Chapter/Section/Subsection hierarchy
    3. Question Generation: Subsection → Questions
    4. Neo4j Persistence: Store hierarchy with embeddings
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # Gemini model for vision/structuring
        self.gemini_model = genai.GenerativeModel(
            self.config.get("vision_model", "gemini-2.5-flash-preview-05-20")
        )
        
        # LLM for question generation (pluggable)
        question_model = self.config.get("question_model", "PLACEHOLDER_MODEL_ID")
        self.question_llm = init_chat_model(
            question_model,
            temperature=0.3,
        )
        
        # Neo4j driver
        self.neo4j_driver = None
        try:
            self.neo4j_driver = get_neo4j_driver()
        except Exception as e:
            print(f"⚠️  Neo4j not available: {e}")
    
    # ================== Phase 1: Vision Extraction ==================
    
    def extract_with_gemini(self, file_path: str) -> Tuple[str, int]:
        """
        Extract text from PDF/image using Gemini Vision.
        
        Returns:
            Tuple of (markdown_text, page_count)
        """
        print("⏳ Phase 1: Gemini Vision Extraction...")
        start_time = time.time()
        
        # Get file extension
        ext = os.path.splitext(file_path)[1].lower() if isinstance(file_path, str) else ".pdf"
        
        # Convert to images if PDF
        if ext in [".pdf", ""]:
            pages = pdf_to_images(file_path)
        elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
            # Single image
            pages = [Image.open(file_path)]
        else:
            raise ValueError(f"Unsupported format: {ext}")
        
        if not pages:
            raise ValueError("No pages extracted from document")
        
        # Extract markdown from each page
        all_markdown = []
        for i, page in enumerate(pages):
            print(f"   📝 Extracting page {i+1}/{len(pages)}...")
            
            response = self.gemini_model.generate_content([
                """Extract ALL text from this page as clean markdown.
                
Rules:
- Use ## for chapter/major titles
- Use ### for section headings
- Use #### for subsection headings
- Preserve tables as markdown tables
- Include image descriptions in [brackets]
- Preserve mathematical formulas
- Keep numbered lists and bullet points
- For handwritten text, transcribe as accurately as possible""",
                page
            ])
            
            page_md = response.text
            # Add page marker
            all_markdown.append(f"\n<!-- PAGE {i+1} -->\n{page_md}")
        
        full_markdown = "\n\n".join(all_markdown)
        elapsed = time.time() - start_time
        print(f"✅ Phase 1 complete: {len(pages)} pages in {elapsed:.2f}s")
        
        return full_markdown, len(pages)
    
    # ================== Phase 2: Hierarchical Structuring ==================
    
    def structure_document(self, markdown: str) -> DocumentStructure:
        """
        Analyze markdown and extract hierarchical structure.
        Uses LangChain structured output for guaranteed schema.
        """
        print("⏳ Phase 2: Document Structuring...")
        start_time = time.time()
        
        # Use Gemini via LangChain for structured output
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model=self.config.get("structure_model", "gemini-2.5-flash-preview-05-20"),
            temperature=0
        )
        structured_llm = llm.with_structured_output(DocumentStructure)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Analyze this document and extract its hierarchical structure.

For each subsection, include the FULL content text (not just titles).
Identify page numbers from <!-- PAGE X --> markers.

If no clear chapters exist (e.g., notes), create logical topic groups.
Aim for 3-10 subsections per section for manageable chunks."""),
            ("user", "{markdown}")
        ])
        
        chain = prompt | structured_llm
        structure = chain.invoke({"markdown": markdown})
        
        # Count items
        total_chapters = len(structure.chapters)
        total_sections = sum(len(ch.sections) for ch in structure.chapters)
        total_subsections = sum(
            len(sec.subsections) 
            for ch in structure.chapters 
            for sec in ch.sections
        )
        
        elapsed = time.time() - start_time
        print(f"✅ Phase 2 complete: {total_chapters} chapters, {total_sections} sections, {total_subsections} subsections in {elapsed:.2f}s")
        
        return structure
    
    # ================== Phase 3: Question Generation ==================
    
    def generate_questions_for_subsection(self, subsection: Subsection) -> QuestionSet:
        """
        Generate Bloom's taxonomy questions for a subsection.
        Uses configurable LLM (placeholder for GPT OSS 120B).
        """
        structured_llm = self.question_llm.with_structured_output(QuestionSet)
        
        prompt = ChatPromptTemplate.from_template("""
You are an expert educational assessment designer.

Content Title: {title}
Content: {content}

Generate questions following Bloom's Taxonomy distribution:
- Remember (25%): definitions, facts, recall
- Understand (25%): explain, summarize, interpret
- Apply (25%): solve problems, use knowledge
- Analyze (15%): break down, examine relationships
- Evaluate (10%): judge, critique, assess

For each question provide:
- text: The question (if it needs an image, naturally reference it like "Look at the diagram...")
- bloom_level: remember/understand/apply/analyze/evaluate/create
- difficulty: basic/intermediate/advanced
- question_type: long_answer or multiple_choice
- expected_time: minutes to answer
- key_points: list of expected answer points
- options: (MCQ only) 4 choices
- correct_answer: (MCQ only) the right choice
- explanation: why it's correct

IMAGE SUPPORT - CRITICAL:
For questions that would benefit from a visual (diagram, graph, flowchart):
- needs_image: true
- image_type: "diagram", "graph", "flowchart", or "chart"
- image_description: Detailed description of what the image shows (for LLM evaluation context)
- image_prompt: Prompt to generate the image (e.g., "A temperature vs time graph showing phase transition...")
- **IMPORTANT**: The question text MUST naturally reference the image (e.g., "Look at the diagram and identify...", "Based on the graph shown, what happens at...", "Refer to the flowchart and explain...")

If needs_image=true, the question text MUST start with or include a reference to the visual.
Example: "Examine the flowchart showing the water cycle. What process occurs between Stage 2 and Stage 3?"

Generate:
- 2 long_answer_questions (5-10 min each)
- 3 multiple_choice_questions (1-3 min each)
- At least 1 question should have needs_image=true if the content involves processes, relationships, or data
""")
        
        chain = prompt | structured_llm
        
        try:
            result = chain.invoke({
                "title": subsection.title,
                "content": subsection.content[:5000]  # Truncate long content
            })
            result.total_questions = len(result.long_answer_questions) + len(result.multiple_choice_questions)
            return result
        except Exception as e:
            print(f"   ❌ Question generation error: {e}")
            return QuestionSet(total_questions=0)
    
    # ================== Phase 4: Neo4j Persistence ==================
    
    def persist_to_neo4j(
        self,
        doc_id: str,
        user_id: str,
        title: str,
        structure: DocumentStructure,
        questions_map: dict = None  # {subsection_id: [Question, ...]}
    ):
        """
        Persist hierarchical structure to Neo4j with embeddings.
        Questions are pre-generated and passed in via questions_map.
        
        Schema:
        User → Document → Chapter → Section → Subsection → QuestionSet
        """
        if not self.neo4j_driver:
            print("⚠️  Neo4j not available, skipping persistence")
            return
        
        questions_map = questions_map or {}
        
        print("⏳ Phase 4: Neo4j Persistence...")
        start_time = time.time()
        
        with self.neo4j_driver.session() as session:
            # Create User and Document
            session.run("""
                MERGE (u:User {id: $user_id})
                MERGE (d:Document {documentId: $doc_id})
                ON CREATE SET 
                    d.title = $title,
                    d.created_at = datetime()
                MERGE (u)-[:UPLOADED]->(d)
            """, user_id=user_id, doc_id=doc_id, title=title)
            print(f"✅ Created Document: {doc_id}")
            
            question_count = 0
            
            # Create hierarchy
            for ch_idx, chapter in enumerate(structure.chapters):
                chapter_id = f"{doc_id}::ch::{ch_idx}"
                session.run("""
                    MATCH (d:Document {documentId: $doc_id})
                    CREATE (ch:Chapter {
                        id: $ch_id,
                        title: $title,
                        order: $order
                    })
                    CREATE (d)-[:HAS_CHAPTER]->(ch)
                """, doc_id=doc_id, ch_id=chapter_id, title=chapter.title, order=ch_idx)
                print(f"   📖 Chapter {ch_idx+1}: {chapter.title[:50]}...")
                
                for sec_idx, section in enumerate(chapter.sections):
                    section_id = f"{chapter_id}::sec::{sec_idx}"
                    session.run("""
                        MATCH (ch:Chapter {id: $ch_id})
                        CREATE (sec:Section {
                            id: $sec_id,
                            title: $title,
                            order: $order
                        })
                        CREATE (ch)-[:HAS_SECTION]->(sec)
                    """, ch_id=chapter_id, sec_id=section_id, title=section.title, order=sec_idx)
                    
                    for sub_idx, subsection in enumerate(section.subsections):
                        sub_id = f"{section_id}::sub::{sub_idx}"
                        
                        # Generate embedding
                        embedding = embed_text(subsection.content)
                        
                        session.run("""
                            MATCH (sec:Section {id: $sec_id})
                            CREATE (sub:Subsection {
                                id: $sub_id,
                                title: $title,
                                content: $content,
                                page_start: $page_start,
                                page_end: $page_end,
                                embedding: $embedding,
                                order: $order
                            })
                            CREATE (sec)-[:HAS_SUBSECTION]->(sub)
                        """, 
                            sec_id=section_id,
                            sub_id=sub_id,
                            title=subsection.title,
                            content=subsection.content[:10000],
                            page_start=subsection.page_start,
                            page_end=subsection.page_end,
                            embedding=embedding,
                            order=sub_idx
                        )
                        
                        # Store pre-generated questions if available
                        if sub_id in questions_map and questions_map[sub_id]:
                            all_questions = questions_map[sub_id]
                            questions_json = json.dumps([q.model_dump() for q in all_questions])
                            
                            session.run("""
                                MATCH (sub:Subsection {id: $sub_id})
                                CREATE (qs:QuestionSet {
                                    id: $qs_id,
                                    questions: $questions_json,
                                    total_count: $total_count,
                                    generated_at: datetime()
                                })
                                CREATE (sub)-[:HAS_QUESTIONS]->(qs)
                            """,
                                sub_id=sub_id,
                                qs_id=f"{sub_id}::qs",
                                questions_json=questions_json,
                                total_count=len(all_questions)
                            )
                            question_count += len(all_questions)
        
        elapsed = time.time() - start_time
        print(f"✅ Phase 4 complete: {question_count} questions in {elapsed:.2f}s")
    
    # ================== Phase 3: Question + Image Generation ==================
    
    async def generate_all_questions(
        self,
        structure: DocumentStructure,
        doc_id: str,
        generate_images: bool = True
    ) -> dict:
        """
        Generate questions for all subsections, then generate images.
        Returns a map of {subsection_id: [Question, ...]}
        
        Flow:
        1. Generate questions for each subsection
        2. Collect all questions needing images
        3. Generate all images in batch
        4. Return complete questions map
        """
        print("⏳ Phase 3: Question + Image Generation...")
        start_time = time.time()
        
        questions_map = {}
        all_questions_needing_images = []
        
        # Step 1: Generate questions for all subsections
        for ch_idx, chapter in enumerate(structure.chapters):
            for sec_idx, section in enumerate(chapter.sections):
                for sub_idx, subsection in enumerate(section.subsections):
                    sub_id = f"{doc_id}::ch::{ch_idx}::sec::{sec_idx}::sub::{sub_idx}"
                    
                    print(f"      ❓ Generating questions for: {subsection.title[:40]}...")
                    questions = self.generate_questions_for_subsection(subsection)
                    
                    if questions.total_questions > 0:
                        all_questions = questions.long_answer_questions + questions.multiple_choice_questions
                        questions_map[sub_id] = all_questions
                        
                        # Collect questions needing images
                        for q in all_questions:
                            if q.needs_image and q.image_prompt:
                                all_questions_needing_images.append(q)
        
        # Step 2: Generate images for all questions that need them
        if generate_images and all_questions_needing_images:
            print(f"\n🎨 Phase 3b: Generating {len(all_questions_needing_images)} images...")
            
            for i, q in enumerate(all_questions_needing_images):
                print(f"   🖼️  Image {i+1}/{len(all_questions_needing_images)}: {q.text[:50]}...")
                
                image_bytes = await generate_image_with_flux(q.image_prompt, q.image_type or "diagram")
                
                if image_bytes:
                    import uuid
                    image_id = f"{doc_id}_q{i}_{uuid.uuid4().hex[:8]}"
                    file_key = f"question_images/{image_id}.png"
                    
                    image_url = upload_to_r2(image_bytes, file_key)
                    
                    if image_url:
                        q.image_url = image_url
                        print(f"      ✅ Image generated: {image_url}")
                
                # Clear intermediate fields
                q.image_prompt = None
                q.needs_image = False
        
        elapsed = time.time() - start_time
        total_questions = sum(len(qs) for qs in questions_map.values())
        print(f"✅ Phase 3 complete: {total_questions} questions, {len(all_questions_needing_images)} images in {elapsed:.2f}s")
        
        return questions_map
    
    # ================== Main Pipeline ==================
    
    def ingest_document(
        self,
        file_path: str,
        doc_id: str,
        user_id: str,
        title: str = None,
        generate_questions: bool = True,
        generate_images: bool = True
    ) -> DocumentStructure:
        """
        Full ingestion pipeline.
        
        Args:
            file_path: Path to PDF/image file (or bytes)
            doc_id: Unique document identifier
            user_id: User who uploaded the document
            title: Optional title (extracted if not provided)
            generate_questions: Whether to generate questions
            generate_images: Whether to generate images for questions
        
        Returns:
            DocumentStructure with full hierarchy
        """
        import asyncio
        
        total_start = time.time()
        print(f"\n{'='*60}")
        print(f"🚀 Starting Gemini Ingestion Pipeline")
        print(f"Document: {doc_id}")
        print(f"User: {user_id}")
        print(f"{'='*60}\n")
        
        # Phase 1: Extract
        markdown, page_count = self.extract_with_gemini(file_path)
        
        # Phase 2: Structure
        structure = self.structure_document(markdown)
        
        # Use extracted title if not provided
        if not title:
            title = structure.title or f"Document {doc_id}"
        
        # Phase 3: Generate questions + images (before persistence)
        questions_map = {}
        if generate_questions:
            loop = asyncio.get_event_loop()
            questions_map = loop.run_until_complete(
                self.generate_all_questions(structure, doc_id, generate_images)
            )
        
        # Phase 4: Persist everything to Neo4j
        self.persist_to_neo4j(doc_id, user_id, title, structure, questions_map)
        
        total_elapsed = time.time() - total_start
        print(f"\n{'='*60}")
        print(f"✅ Pipeline complete in {total_elapsed:.2f}s ({total_elapsed/60:.1f}min)")
        print(f"{'='*60}\n")
        
        return structure


# ============================================================
# CLI for local testing
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python gemini_ingestion.py <pdf_path> [doc_id] [user_id]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    doc_id = sys.argv[2] if len(sys.argv) > 2 else f"doc_{int(time.time())}"
    user_id = sys.argv[3] if len(sys.argv) > 3 else "test_user"
    
    config = {
        "vision_model": "gemini-2.5-flash-preview-05-20",
        "structure_model": "gemini-2.5-flash-preview-05-20",
        "question_model": "PLACEHOLDER_MODEL_ID",  # Replace with actual model
    }
    
    pipeline = GeminiIngestionPipeline(config)
    structure = pipeline.ingest_document(
        file_path=pdf_path,
        doc_id=doc_id,
        user_id=user_id,
        generate_questions=False  # Skip for initial testing
    )
    
    print(f"\n📊 Results:")
    print(f"   Title: {structure.title}")
    print(f"   Chapters: {len(structure.chapters)}")
    for ch in structure.chapters:
        print(f"      • {ch.title}: {len(ch.sections)} sections")
