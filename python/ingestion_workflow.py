from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.pptx import partition_pptx
from unstructured.partition.md import partition_md
from unstructured.partition.auto import partition
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Tuple
from enum import Enum
from openai import OpenAI
from neo4j import GraphDatabase
import os
import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
load_dotenv()

# OpenAI client for embeddings
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Embedding models
EMBED_MODEL_SMALL = "text-embedding-3-small"  # 1536 dims
EMBED_MODEL_LARGE = "text-embedding-3-large"  # 3072 dims (optional)

# Neo4j credentials
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def embed_text(text: str, model: str = EMBED_MODEL_SMALL) -> List[float]:
    """
    Generate embeddings for text using OpenAI.
    Truncates long text to stay within token limits.
    """
    # Rough guardrail: ~8000 chars ≈ 2000 tokens (safe for text-embedding-3)
    # text = text[:8000]
    try:
        response = openai_client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Failed to generate embedding: {e}")
        return []

def get_neo4j_driver():
    """Get Neo4j database driver"""
    if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]):
        raise ValueError("Missing Neo4j credentials in .env: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        # Test connection
        with driver.session() as session:
            session.run("RETURN 1")
        print("✅ Connected to Neo4j")
        return driver
    except Exception as e:
        print(f"❌ Cannot connect to Neo4j: {e}")
        raise e


"""
1.get the query
2. use unstructured.partition.pdf to extract content from the PDF
3. split text, images and tables
4. for each chunk create questions (must create a class to use structured output) and put all questions in a list
5. for each list item, create cyphers in neo4j graphdb 
6. for the actual chunk create a summary and have embeddings put that in the db as well
connections should be like user-> document-> topics -> chunks(embeddings) -> questions 

"""
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
    text: str = Field(description= "the question text")
    bloom_level: BloomLevel = Field(description= "the bloom's taxonomy level")
    difficulty: Difficulty = Field(description= "the question difficulty level")
    question_type: QuestionType = Field(description= "the question type")
    expected_time: int  = Field(description= "the expected time to answer the question")
    key_points: List[str] = Field(description= "the key points to consider when answering the question")
    options: Optional[List[str]] = Field(description= "the options for the question")
    correct_answer: Optional[str] = Field(description= "the correct answer for the question")
    explanation: Optional[str] = Field(description= "the explanation for the correct answer")

class QuestionSet(BaseModel):
    """Container for all questions generated from a content block"""
    long_answer_questions: List[Question] = Field(description="Long answer questions")
    multiple_choice_questions: List[Question] = Field(description="Multiple choice questions") 
    total_questions: int = Field(description="Total number of questions")

class ContentBlock:
    def __init__(self):
        self.chunk_index: int = 0
        self.text_content: str = ""
        self.related_tables: List[str] = []
        self.image_captions: List[str] = []
        self.table_descriptions: List[str] = []
        self.combined_context: str = ""
        self.questions: List[Question] = []
        self.embeddings: List[float] = []
        self.meta: dict = {}  # Store page numbers, etc.
        self.page_number: int = 1
        # Optional: bbox for scroll-to position [x1, y1, x2, y2]
        self.bbox: Optional[List[float]] = None

class IngestionPipeline:
    def __init__(self, config):
        self.config = config
        self.vision_llm = init_chat_model(model=config.get("vision_llm", "gpt-4o-mini"), temperature=0)
        self.text_llm = init_chat_model(model=config.get("text_llm", "gpt-4.1"), temperature=0)
        self.neo4j_driver = None
        
        # Initialize Neo4j if credentials available
        try:
            self.neo4j_driver = get_neo4j_driver()
        except Exception as e:
            print(f"⚠️  Neo4j not available: {e}")
            print("Continuing without graph database persistence...")


    def extract_document(self, file_path: str) -> List[ContentBlock]:
        """Extract content from any supported document format (PDF, DOCX, PPTX, MD)"""
        import os
        ext = os.path.splitext(file_path)[1].lower()
        
        supported_formats = ['.pdf', '.docx', '.doc', '.pptx', '.ppt', '.md', '.markdown']
        if ext not in supported_formats:
            raise ValueError(f"Unsupported file format: {ext}. Supported: {supported_formats}")
        
        print(f"📄 Detected format: {ext}")
        
        # Use format-specific partitioner for best results, fallback to auto
        if ext == '.pdf':
            return self._extract_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return self._extract_docx(file_path)
        elif ext in ['.pptx', '.ppt']:
            return self._extract_pptx(file_path)
        elif ext in ['.md', '.markdown']:
            return self._extract_markdown(file_path)
        else:
            return self._extract_auto(file_path)
    
    def _extract_pdf(self, pdf_path: str) -> List[ContentBlock]:
        """Extract PDF content and organize into ContentBlocks"""
        print("⏳ Starting PDF extraction...")
        start_time = time.time()
        
        chunks = partition_pdf(
            filename=pdf_path,
            infer_table_structure=True,
            strategy="hi_res",
            extract_image_block_types=["Image"],
            extract_image_block_to_payload=True,
            chunking_strategy="by_title",
            max_characters=8000,
            combine_text_under_n_chars=3000,
            new_after_n_chars=6000,
            overlap=200,
        )
        
        parse_time = time.time() - start_time
        print(f"   ✅ PDF parsed in {parse_time:.2f}s")
        
        # Collect all images with their block indices for batch processing
        all_images: List[Tuple[int, str]] = []  # (block_idx, base64)
        
        content_blocks = []
        for idx, chunk in enumerate(chunks):
            block = ContentBlock()
            block.chunk_index = idx
            
            # All chunks get text content
            block.text_content = str(chunk)

            # Extract page number (primary) and optional bbox (nice-to-have)
            if hasattr(chunk, "metadata"):
                block.page_number = chunk.metadata.page_number if chunk.metadata.page_number else 1
                
                # Optional bbox for scroll-to position
                if hasattr(chunk.metadata, "coordinates") and chunk.metadata.coordinates:
                    coords = chunk.metadata.coordinates
                    if coords.points:
                        points = list(coords.points)
                        xs = [p[0] for p in points]
                        ys = [p[1] for p in points]
                        block.bbox = [min(xs), min(ys), max(xs), max(ys)]
            
            # Handle different chunk types - collect images but don't caption yet
            if "CompositeElement" in str(type(chunk)):
                # Extract image base64 data (don't caption yet)
                images = self._extract_image_base64_from_chunk(chunk)
                for img_b64 in images:
                    all_images.append((idx, img_b64))
                # CompositeElements might also contain tables
                block.related_tables.extend(self._extract_tables_from_chunk(chunk))
                
            elif "Table" in str(type(chunk)):
                block.related_tables = [chunk]
            
            content_blocks.append(block)
        
        # Batch caption all images in parallel
        if all_images:
            print(f"🖼️  Captioning {len(all_images)} images in parallel...")
            caption_start = time.time()
            captions = self._batch_caption_images([img for _, img in all_images])
            
            # Assign captions back to their blocks
            for (block_idx, _), caption in zip(all_images, captions):
                content_blocks[block_idx].image_captions.append(caption)
            
            print(f"   ✅ Captions done in {time.time() - caption_start:.2f}s")
        
        # Build combined context for all blocks
        for block in content_blocks:
            block.combined_context = self._combine_context(block)
        
        elapsed = time.time() - start_time
        print(f"✅ PDF extraction completed in {elapsed:.2f}s ({len(content_blocks)} blocks)")
        return content_blocks
    
    def _extract_docx(self, docx_path: str) -> List[ContentBlock]:
        """Extract DOCX content and organize into ContentBlocks"""
        print("⏳ Starting DOCX extraction...")
        start_time = time.time()
        
        chunks = partition_docx(
            filename=docx_path,
            infer_table_structure=True,
            chunking_strategy="by_title",
            max_characters=8000,
            combine_text_under_n_chars=3000,
            new_after_n_chars=6000,
            overlap=200,
        )
        
        return self._chunks_to_content_blocks(chunks, start_time, "DOCX")
    
    def _extract_pptx(self, pptx_path: str) -> List[ContentBlock]:
        """Extract PPTX content and organize into ContentBlocks"""
        print("⏳ Starting PPTX extraction...")
        start_time = time.time()
        
        chunks = partition_pptx(
            filename=pptx_path,
            infer_table_structure=True,
            chunking_strategy="by_title",
            max_characters=8000,
            combine_text_under_n_chars=3000,
            new_after_n_chars=6000,
            overlap=200,
        )
        
        return self._chunks_to_content_blocks(chunks, start_time, "PPTX")
    
    def _extract_markdown(self, md_path: str) -> List[ContentBlock]:
        """Extract Markdown content and organize into ContentBlocks"""
        print("⏳ Starting Markdown extraction...")
        start_time = time.time()
        
        chunks = partition_md(
            filename=md_path,
            chunking_strategy="by_title",
            max_characters=8000,
            combine_text_under_n_chars=3000,
            new_after_n_chars=6000,
            overlap=200,
        )
        
        return self._chunks_to_content_blocks(chunks, start_time, "Markdown")
    
    def _extract_auto(self, file_path: str) -> List[ContentBlock]:
        """Auto-detect format and extract content"""
        print("⏳ Starting auto-detect extraction...")
        start_time = time.time()
        
        chunks = partition(
            filename=file_path,
            chunking_strategy="by_title",
            max_characters=8000,
            combine_text_under_n_chars=3000,
            new_after_n_chars=6000,
            overlap=200,
        )
        
        return self._chunks_to_content_blocks(chunks, start_time, "Auto")
    
    def _chunks_to_content_blocks(self, chunks, start_time: float, format_name: str) -> List[ContentBlock]:
        """Convert unstructured chunks to ContentBlocks (shared logic)"""
        parse_time = time.time() - start_time
        print(f"   ✅ {format_name} parsed in {parse_time:.2f}s")
        
        content_blocks = []
        for idx, chunk in enumerate(chunks):
            block = ContentBlock()
            block.chunk_index = idx
            block.text_content = str(chunk)
            
            # Extract page/slide number if available
            if hasattr(chunk, "metadata"):
                if hasattr(chunk.metadata, "page_number") and chunk.metadata.page_number:
                    block.page_number = chunk.metadata.page_number
                elif hasattr(chunk.metadata, "slide_number") and chunk.metadata.slide_number:
                    block.page_number = chunk.metadata.slide_number
            
            # Handle tables
            if "Table" in str(type(chunk)):
                block.related_tables = [chunk]
            
            content_blocks.append(block)
        
        # Build combined context for all blocks
        for block in content_blocks:
            block.combined_context = self._combine_context(block)
        
        elapsed = time.time() - start_time
        print(f"✅ {format_name} extraction completed in {elapsed:.2f}s ({len(content_blocks)} blocks)")
        return content_blocks
    
    # Backward compatibility alias
    def extract_pdf(self, pdf_path: str) -> List[ContentBlock]:
        """Backward compatible: Extract PDF (use extract_document for all formats)"""
        return self._extract_pdf(pdf_path)
    
    def enrich_content_blocks(self, content_blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Enrich content blocks with additional metadata, embeddings, and questions"""
        total_start = time.time()
        print(f"\n⏳ Enriching {len(content_blocks)} content blocks...")
        
        for i, block in enumerate(content_blocks):
            block_start = time.time()
            block.combined_context = self._combine_context(block)
            
            # Generate embeddings for the combined context
            if block.combined_context:
                embed_start = time.time()
                print(f"🔢 Generating embeddings for block {i+1}/{len(content_blocks)}...")
                block.embeddings = embed_text(block.combined_context)
                print(f"   ✅ Embeddings done in {time.time() - embed_start:.2f}s")
            
            # Generate questions
            question_start = time.time()
            print(f"❓ Generating questions for block {i+1}/{len(content_blocks)}...")
            block.questions = self._generate_questions(block)
            print(f"   ✅ Questions done in {time.time() - question_start:.2f}s ({len(block.questions)} questions)")
            
            block_elapsed = time.time() - block_start
            print(f"📦 Block {i+1}/{len(content_blocks)} enriched in {block_elapsed:.2f}s\n")
            
        total_elapsed = time.time() - total_start
        print(f"✅ All blocks enriched in {total_elapsed:.2f}s")
        return content_blocks

    def _combine_context(self, block: ContentBlock) -> str:
        """Combine text, image captions, and table descriptions into a single context string"""
        components = [block.text_content]
        if block.image_captions:
            components.append("\n".join(block.image_captions))
        if block.table_descriptions:
            components.append("\n".join(block.table_descriptions))
        return "\n\n".join(components)
    def _generate_questions(self, block: ContentBlock) -> List[Question]:
        """Generate structured questions for a content block"""
        # Create structured question generation prompt
        question_prompt_template = """
You are an expert educational assessment designer. Generate comprehensive questions based on the provided content.

Content: {content}

Generate exactly:
- 3 Long-answer questions (5-10 minutes each)
- 5 Multiple-choice questions (1-3 minutes each)

Follow Bloom's Taxonomy distribution:
- Remember (25%): 2 questions - definitions, facts, recall
- Understand (25%): 2 questions - explain, summarize, interpret
- Apply (25%): 2 questions - solve problems, use knowledge
- Analyze (15%): 1 question - break down, examine relationships
- Evaluate (10%): 1 question - judge, critique, assess

For Long Answer Questions:
- Provide 3-4 key points expected in the answer
- Set appropriate difficulty and time expectations

For Multiple Choice Questions:
- Provide exactly 4 options as separate strings
- Include one clearly correct answer
- Create plausible distractors
- Provide explanation for correct answer

Ensure questions reference images and tables when mentioned in the content.
"""

        # Create LangChain chain with structured output
        question_prompt = ChatPromptTemplate.from_template(question_prompt_template)
        question_chain = question_prompt | self.text_llm.with_structured_output(QuestionSet)
        
        try:
            # Generate structured questions
            question_set = question_chain.invoke({"content": block.combined_context})
            
            # Combine all questions into single list
            all_questions = question_set.long_answer_questions + question_set.multiple_choice_questions
            return all_questions
            
        except Exception as e:
            print(f"Failed to generate questions: {e}")
            return []

    def _extract_image_base64_from_chunk(self, chunk) -> List[str]:
        """Extract base64 image data from chunk without captioning"""
        images = []
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            for el in chunk.metadata.orig_elements:
                if "Image" in str(type(el)):
                    if hasattr(el.metadata, 'image_base64') and el.metadata.image_base64:
                        try:
                            import base64
                            base64.b64decode(el.metadata.image_base64)  # Validate
                            images.append(el.metadata.image_base64)
                        except Exception as e:
                            print(f"Invalid image base64: {e}")
                            continue
        return images
    
    def _batch_caption_images(self, images: List[str], max_workers: int = 5) -> List[str]:
        """
        Caption multiple images in parallel using ThreadPoolExecutor.
        GPT-4o-mini handles ~5 concurrent requests well within rate limits.
        """
        def caption_single(img_b64: str) -> str:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this educational image in detail. Focus on scientific concepts, diagrams, data, experimental setups, charts, or any educational content shown."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                        }
                    ]
                }
            ]
            try:
                response = self.vision_llm.invoke(messages)
                return response.content
            except Exception as e:
                print(f"Failed to caption image: {e}")
                return "Image description unavailable"
        
        # Parallel execution
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            captions = list(executor.map(caption_single, images))
        
        return captions
    
    def _extract_tables_from_chunk(self, chunk) -> List:
        """Extract table objects from a CompositeElement chunk"""
        tables = []
        if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
            for el in chunk.metadata.orig_elements:
                if "Table" in str(type(el)):
                    tables.append(el)
        return tables
    
    # ========== Neo4j Write Functions ==========
    
    def _upsert_document(self, tx, doc_meta: dict):
        """Create or update document node in Neo4j"""
        tx.run(
            """
            MERGE (u:User {id: $user_id})
            MERGE (d:Document {documentId: $doc_id})
            ON CREATE SET 
                d.title = $title,
                d.source = $source,
                d.created_at = datetime()
            MERGE (u)-[:UPLOADED]->(d)
            """,
            **doc_meta
        )
    
    def _create_content_block(self, tx, payload: dict):
        """Create ContentBlock node with embeddings"""
        tx.run(
            """
            MATCH (d:Document {documentId: $doc_id})
            CREATE (cb:ContentBlock {
                block_id: $block_id,
                chunk_index: $chunk_index,
                text_content: $text_content,
                combined_context: $combined_context,
                page_from: $page_from,
                page_to: $page_to,
                has_images: $has_images,
                has_tables: $has_tables,
                image_count: $image_count,
                table_count: $table_count,
                embedding: $embedding,
                page_number: $page_number,
                bbox: $bbox
            })
            MERGE (d)-[:HAS_CONTENT_BLOCK]->(cb)
            """,
            **payload
        )
    
    def _create_question_set(self, tx, block_id: str, questions: List[Question], doc_id: str):
        """
        Create a single QuestionSet node containing all questions for a ContentBlock.
        Stores questions as JSON array instead of separate nodes (78% node reduction).
        """
        from datetime import datetime
        
        # Convert questions to JSON-serializable format
        questions_json = json.dumps([
            {
                "question_id": f"{block_id}::q::{idx}",
                "text": q.text,
                "bloom_level": q.bloom_level.value,
                "difficulty": q.difficulty.value,
                "question_type": q.question_type.value,
                "expected_time": q.expected_time,
                "key_points": q.key_points or [],
                "options": q.options or [],
                "correct_answer": q.correct_answer or "",
                "explanation": q.explanation or ""
            }
            for idx, q in enumerate(questions)
        ])
        
        # Calculate difficulty distribution
        difficulty_dist = {}
        for q in questions:
            diff = q.difficulty.value
            difficulty_dist[diff] = difficulty_dist.get(diff, 0) + 1
        
        tx.run(
            """
            MATCH (cb:ContentBlock {block_id: $block_id})
            CREATE (qs:QuestionSet {
                questionset_id: $questionset_id,
                questions: $questions_json,
                total_count: $total_count,
                difficulty_distribution: $difficulty_dist,
                generated_at: $generated_at,
                doc_id: $doc_id
            })
            CREATE (cb)-[:HAS_QUESTIONS]->(qs)
            """,
            block_id=block_id,
            questionset_id=f"{block_id}::qs",
            questions_json=questions_json,
            total_count=len(questions),
            difficulty_dist=json.dumps(difficulty_dist),
            generated_at=datetime.utcnow().isoformat(),
            doc_id=doc_id
        )
    
    def persist_to_neo4j(self, doc_id: str, doc_meta: dict, content_blocks: List[ContentBlock]):
        """
        Persist document, content blocks, and questions to Neo4j.
        Creates the full graph structure with embeddings.
        """
        if not self.neo4j_driver:
            print("⚠️  Neo4j not available, skipping graph persistence")
            return
        
        persist_start = time.time()
        print("\n💾 Persisting to Neo4j...")
        
        with self.neo4j_driver.session() as session:
            # 1. Create/update document
            session.execute_write(self._upsert_document, doc_meta)
            print(f"✅ Created document: {doc_id}")
            
            # 2. Create content blocks
            block_ids = []
            for i, block in enumerate(content_blocks):
                block_id = f"{doc_id}::block::{i}"
                block_ids.append(block_id)
                
                # Extract page metadata if available
                page_from = block.meta.get("page_from")
                page_to = block.meta.get("page_to")
                
                payload = {
                    "doc_id": doc_id,
                    "block_id": block_id,
                    "chunk_index": i,
                    "text_content": block.text_content[:5000],  # Truncate long text
                    "combined_context": block.combined_context[:5000],
                    "page_from": page_from,
                    "page_to": page_to,
                    "has_images": len(block.image_captions) > 0,
                    "has_tables": len(block.related_tables) > 0,
                    "image_count": len(block.image_captions),
                    "table_count": len(block.related_tables),
                    "embedding": block.embeddings or [],
                    "page_number": block.page_number,
                    "bbox": block.bbox  # Optional: [x1, y1, x2, y2] for scroll-to
                }
                
                session.execute_write(self._create_content_block, payload)
                print(f"✅ Created ContentBlock {i+1}/{len(content_blocks)}")
                
                # 3. Create QuestionSet for this block (all questions in one node)
                if block.questions:
                    session.execute_write(
                        self._create_question_set,
                        block_id,
                        block.questions,
                        doc_id
                    )
                    print(f"  ✅ Created QuestionSet with {len(block.questions)} questions")
        
        persist_elapsed = time.time() - persist_start
        print(f"✅ Successfully persisted to Neo4j in {persist_elapsed:.2f}s")

if __name__ == "__main__":
    pipeline_start = time.time()
    print("🚀 Starting PDF Ingestion Pipeline with Graph RAG...")
    print(f"⏰ Started at: {time.strftime('%H:%M:%S')}")
    
    config = {
        "vision_llm": "gpt-4o-mini",
        "text_llm": "gpt-4.1"
    }
    
    pipeline = IngestionPipeline(config)
    
    # Document metadata
    doc_id = "chapter1_test"
    doc_meta = {
        "user_id": "test_user",
        "doc_id": doc_id,
        "title": "Chapter 1 Test Document",
        "source": "chapter1.pdf"
    }
    
    # Extract document content (supports PDF, DOCX, PPTX, MD)
    test_file = "chapter1.pdf"  # Change to test other formats: "chapter1.docx", "slides.pptx", "notes.md"
    print(f"\n📄 Extracting document: {test_file}")
    content_blocks = pipeline.extract_document(test_file)
    print(f"✅ Extracted {len(content_blocks)} content blocks")
    
    # Enrich ALL blocks with embeddings and questions
    if content_blocks:
        print(f"\n🔧 Enriching all {len(content_blocks)} blocks...")
        enriched_blocks = pipeline.enrich_content_blocks(content_blocks)
        
        # Display summary for all blocks
        print("\n📊 Block Summaries:")
        total_questions = 0
        for i, block in enumerate(enriched_blocks):
            total_questions += len(block.questions)
            print(f"  Block {i+1}: {len(block.text_content)} chars, {len(block.image_captions)} images, {len(block.questions)} questions")
        
        print(f"\n📈 Totals: {len(enriched_blocks)} blocks, {total_questions} questions")
        
        # Persist to Neo4j
        pipeline.persist_to_neo4j(doc_id, doc_meta, enriched_blocks)
        
        total_elapsed = time.time() - pipeline_start
        print(f"\n✅ Pipeline complete! Ready for vector search.")
        print(f"⏱️  Total time: {total_elapsed:.2f}s ({total_elapsed/60:.1f} min)")
    else:
        print("❌ No content blocks extracted")


        

            
        
            