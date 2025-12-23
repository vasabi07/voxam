"""
Ingestion task for background document processing.

This task handles:
1. Downloading file from R2
2. Extracting content (PDF, DOCX, PPTX, MD)
3. Generating embeddings and questions
4. Persisting to Neo4j

Usage:
    from tasks.ingestion import ingest_document
    task = ingest_document.delay(document_id, user_id, file_key)
    
    # Check status
    result = task.get()  # Blocks until complete
    # Or check async: task.state, task.info
"""
from celery import current_task
from celery_app import celery_app
from redis import Redis
from dotenv import load_dotenv
import os
import json
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
    r.expire(f"task:{task_id}", 86400)  # Expire after 24 hours


@celery_app.task(bind=True, name="tasks.ingestion.ingest_document")
def ingest_document(self, document_id: str, user_id: str, file_key: str):
    """
    Background task for document ingestion.
    
    Args:
        document_id: Unique document ID (from frontend)
        user_id: User who uploaded the document
        file_key: R2/S3 key for the uploaded file
        
    Returns:
        dict with success status, block count, question count
    """
    task_id = self.request.id
    start_time = time.time()
    
    try:
        # Import here to avoid circular imports and ensure fresh config
        from ingestion_workflow import IngestionPipeline
        from r2 import get_file
        import asyncio
        
        # Step 1: Download file from R2
        update_progress(task_id, 5, "downloading", f"Downloading file: {file_key}")
        
        # get_file is async, need to run in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            file_path = loop.run_until_complete(get_file(file_key))
        finally:
            loop.close()
            
        if not file_path:
            raise ValueError(f"Failed to download file: {file_key}")
        
        update_progress(task_id, 10, "extracting", "Extracting document content")
        
        # Step 2: Initialize pipeline
        config = {
            "vision_llm": "gpt-4o-mini",
            "text_llm": "gpt-4.1"
        }
        pipeline = IngestionPipeline(config)
        
        # Step 3: Extract document
        content_blocks = pipeline.extract_document(file_path)
        block_count = len(content_blocks)
        
        update_progress(task_id, 30, "enriching", f"Processing {block_count} content blocks")
        
        # Step 4: Enrich with embeddings and questions
        # This is the slow part - update progress periodically
        enriched_blocks = pipeline.enrich_content_blocks(content_blocks)
        
        update_progress(task_id, 70, "persisting", "Saving to database")
        
        # Step 5: Persist to Neo4j
        doc_meta = {
            "user_id": user_id,
            "doc_id": document_id,
            "title": os.path.basename(file_path),
            "source": file_key,
        }
        pipeline.persist_to_neo4j(document_id, doc_meta, enriched_blocks)
        
        # Count total questions
        total_questions = sum(len(block.questions) for block in enriched_blocks)
        
        elapsed = time.time() - start_time
        
        update_progress(task_id, 100, "completed", f"Processed {block_count} blocks, {total_questions} questions in {elapsed:.1f}s")
        
        # Clean up temp file
        try:
            os.remove(file_path)
        except Exception:
            pass  # Ignore cleanup errors
        
        return {
            "success": True,
            "document_id": document_id,
            "block_count": block_count,
            "question_count": total_questions,
            "elapsed_seconds": round(elapsed, 2),
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        
        update_progress(task_id, 0, "failed", error_msg)
        
        # Re-raise to mark task as failed
        raise self.retry(exc=e, countdown=60, max_retries=2)
