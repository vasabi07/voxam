"""
Ingestion task for background document processing.

Enhanced pipeline with:
1. Downloading file from R2
2. Extracting content (PDF, DOCX, PPTX, MD)
3. Extracting images with PyMuPDF + R2 upload
4. Creating chapter/section hierarchy with LLM
5. Generating embeddings and questions
6. Linking images to questions
7. Persisting to Neo4j

Usage:
    from tasks.ingestion import ingest_document
    task = ingest_document.delay(document_id, user_id, file_key)

    # Check status
    result = task.get()  # Blocks until complete
    # Or check async: task.state, task.info
"""
import sys
from pathlib import Path
# Add parent directory to path for imports (needed for Celery worker)
sys.path.insert(0, str(Path(__file__).parent.parent))

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
def ingest_document(
    self,
    document_id: str,
    user_id: str,
    file_key: str,
    extract_images: bool = True,
    create_hierarchy: bool = True,
    generate_questions: bool = True
):
    """
    Background task for enhanced document ingestion.

    Args:
        document_id: Unique document ID (from frontend)
        user_id: User who uploaded the document
        file_key: R2/S3 key for the uploaded file
        extract_images: Whether to extract and upload images to R2
        create_hierarchy: Whether to create chapter/section hierarchy
        generate_questions: Whether to generate questions

    Returns:
        dict with success status, counts, and timing
    """
    task_id = self.request.id
    start_time = time.time()

    try:
        # Import here to avoid circular imports and ensure fresh config
        from ingestion_workflow import IngestionPipeline
        from r2 import get_file
        import asyncio

        # ===== Step 1: Download file from R2 =====
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

        update_progress(task_id, 10, "processing", "Initializing ingestion pipeline")

        # ===== Step 2: Initialize pipeline =====
        config = {
            "vision_llm": "gpt-4o-mini",
            "text_llm": "gpt-4.1"
        }
        pipeline = IngestionPipeline(config)

        # ===== Step 3: Run enhanced pipeline =====
        # The ingest_document method handles all phases:
        # - Text extraction (Unstructured/OCR)
        # - Image extraction (PyMuPDF) + R2 upload
        # - Hierarchy creation (LLM)
        # - Image-chunk matching
        # - Embeddings + questions
        # - Neo4j persistence

        update_progress(task_id, 15, "extracting", "Extracting document content")

        # Get document title from filename
        title = os.path.splitext(os.path.basename(file_key))[0]

        # Run the full enhanced pipeline
        result = pipeline.ingest_document(
            file_path=file_path,
            doc_id=document_id,
            user_id=user_id,
            title=title,
            extract_images=extract_images,
            create_hierarchy=create_hierarchy,
            generate_questions=generate_questions
        )

        elapsed = time.time() - start_time

        # Build detailed summary
        details = (
            f"Processed {result['content_blocks']} blocks, "
            f"{result['questions']} questions, "
            f"{result['images_matched']} images in {elapsed:.1f}s"
        )
        update_progress(task_id, 100, "completed", details)

        # ===== Step 4: Deduct page credits =====
        page_count = result.get("page_count", 0)
        if page_count > 0:
            try:
                from credits import deduct_pages
                deduct_pages(user_id, page_count)
                print(f"💳 Deducted {page_count} pages from user {user_id}")

                # Update document pageCount in Postgres
                from supabase import create_client
                import os as os_env
                supabase = create_client(
                    os_env.getenv("NEXT_PUBLIC_SUPABASE_URL"),
                    os_env.getenv("SUPABASE_SERVICE_ROLE_KEY")
                )
                supabase.table("Document").update({
                    "pageCount": page_count,
                    "status": "READY"
                }).eq("id", document_id).execute()

            except Exception as credit_error:
                print(f"⚠️ Failed to deduct page credits: {credit_error}")

        # Clean up temp file
        try:
            os.remove(file_path)
        except Exception:
            pass  # Ignore cleanup errors

        return {
            "success": True,
            "document_id": document_id,
            "title": result.get("title"),
            "block_count": result.get("content_blocks", 0),
            "chapter_count": result.get("chapters", 0),
            "section_count": result.get("sections", 0),
            "question_count": result.get("questions", 0),
            "images_extracted": result.get("images_extracted", 0),
            "images_matched": result.get("images_matched", 0),
            "page_count": page_count,
            "elapsed_seconds": round(elapsed, 2),
        }

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)

        update_progress(task_id, 0, "failed", error_msg)

        # Clean up temp file on failure too
        try:
            os.remove(file_path)
        except:
            pass

        # Update document status to FAILED if max retries exhausted
        max_retries = 2
        if self.request.retries >= max_retries:
            try:
                from supabase import create_client
                import os as os_env
                supabase = create_client(
                    os_env.getenv("NEXT_PUBLIC_SUPABASE_URL"),
                    os_env.getenv("SUPABASE_SERVICE_ROLE_KEY")
                )
                supabase.table("Document").update({
                    "status": "FAILED"
                }).eq("id", document_id).execute()
                print(f"❌ Document {document_id} marked as FAILED after {max_retries} retries")
            except Exception as status_error:
                print(f"⚠️ Failed to update document status: {status_error}")

        # Re-raise to mark task as failed
        raise self.retry(exc=e, countdown=60, max_retries=max_retries)


@celery_app.task(bind=True, name="tasks.ingestion.ingest_document_simple")
def ingest_document_simple(self, document_id: str, user_id: str, file_key: str):
    """
    Simplified ingestion task without images or hierarchy.
    Faster for simple documents or when speed is priority.
    """
    return ingest_document(
        self,
        document_id=document_id,
        user_id=user_id,
        file_key=file_key,
        extract_images=False,
        create_hierarchy=False,
        generate_questions=True
    )
