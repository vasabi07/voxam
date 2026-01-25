"""
Gemini Ingestion Task for background document processing.

Uses GeminiIngestionPipeline for:
- Handwritten/scanned PDF support
- Hierarchical document structure (Chapter → Section → Subsection)
- Better cost efficiency (~90% less than Unstructured + GPT-4)

Usage:
    from tasks.gemini_ingestion import ingest_document_gemini
    task = ingest_document_gemini.delay(document_id, user_id, file_key)
"""
from celery import current_task
from celery_app import celery_app
from redis import Redis
from dotenv import load_dotenv
import os
import time

load_dotenv()

REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379/0")


def update_progress(task_id: str, progress: int, status: str, details: str = ""):
    """Update task progress in Redis for real-time status updates."""
    r = Redis.from_url(REDIS_URI, decode_responses=True)
    r.hset(f"task:{task_id}", mapping={
        "progress": progress,
        "status": status,
        "details": details,
        "updated_at": time.time(),
    })
    r.expire(f"task:{task_id}", 86400)


@celery_app.task(bind=True, name="tasks.gemini_ingestion.ingest_document_gemini")
def ingest_document_gemini(
    self,
    document_id: str,
    user_id: str,
    file_key: str,
    generate_questions: bool = True
):
    """
    Background task for document ingestion using Gemini.
    
    Args:
        document_id: Unique document ID (from frontend)
        user_id: User who uploaded the document
        file_key: R2/S3 key for the uploaded file
        generate_questions: Whether to generate questions (slower)
        
    Returns:
        dict with success status, structure info
    """
    task_id = self.request.id
    start_time = time.time()
    
    try:
        from gemini_ingestion import GeminiIngestionPipeline
        from r2 import get_file
        import asyncio
        
        # Step 1: Download file from R2
        update_progress(task_id, 5, "downloading", f"Downloading file: {file_key}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            file_path = loop.run_until_complete(get_file(file_key))
        finally:
            loop.close()
            
        if not file_path:
            raise ValueError(f"Failed to download file: {file_key}")
        
        update_progress(task_id, 10, "extracting", "Gemini Vision extraction")
        
        # Step 2: Initialize Gemini pipeline
        config = {
            "vision_model": "gemini-2.5-flash-preview-05-20",
            "structure_model": "gemini-2.5-flash-preview-05-20",
            "question_model": "PLACEHOLDER_MODEL_ID",  # Replace with actual model
        }
        pipeline = GeminiIngestionPipeline(config)
        
        # Step 3: Extract with Gemini Vision
        markdown, page_count = pipeline.extract_with_gemini(file_path)
        update_progress(task_id, 30, "structuring", f"Analyzing {page_count} pages")
        
        # Step 4: Structure document
        structure = pipeline.structure_document(markdown)
        
        # Count items
        total_chapters = len(structure.chapters)
        total_sections = sum(len(ch.sections) for ch in structure.chapters)
        total_subsections = sum(
            len(sec.subsections)
            for ch in structure.chapters
            for sec in ch.sections
        )
        
        update_progress(
            task_id,
            50,
            "persisting",
            f"Found {total_chapters} chapters, {total_sections} sections"
        )
        
        # Step 5: Persist to Neo4j (includes question generation)
        pipeline.persist_to_neo4j(
            doc_id=document_id,
            user_id=user_id,
            title=structure.title or os.path.basename(file_path),
            structure=structure,
            generate_questions=generate_questions
        )
        
        elapsed = time.time() - start_time
        
        update_progress(
            task_id,
            100,
            "completed",
            f"{total_chapters} chapters, {total_subsections} subsections in {elapsed:.1f}s"
        )
        
        # Clean up temp file
        try:
            os.remove(file_path)
        except Exception:
            pass
        
        return {
            "success": True,
            "document_id": document_id,
            "page_count": page_count,
            "chapters": total_chapters,
            "sections": total_sections,
            "subsections": total_subsections,
            "elapsed_seconds": round(elapsed, 2),
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        
        update_progress(task_id, 0, "failed", error_msg)
        
        raise self.retry(exc=e, countdown=60, max_retries=2)
