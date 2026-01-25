from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from r2 import get_file
from qp_agent import QPInputState, create_qp_workflow
from agents.chat_agent import get_chat_graph
from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
import asyncio
from livekit import api

# SSE streaming imports
import json
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage
# Security
from fastapi import Depends
from security import verify_token

app = FastAPI()

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# LiveKit credentials
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# Apply CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chat graph initialization on startup
@app.on_event("startup")
async def initialize_chat_graph():
    """Initialize chat graph on startup (within async context)."""
    get_chat_graph()  # Lazy init with AsyncRedisSaver
    print("✅ Chat graph initialized")

# Middleware for auth on /chat/ endpoints
@app.middleware("http")
async def verify_chat_request(request: Request, call_next):
    # Protect Chat endpoints with JWT auth
    if request.url.path.startswith("/chat/"):
        # Manual check because we can't easily inject dependencies into the library function
        from security import get_jwks_client, SUPABASE_JWKS_URL
        try:
            # Manually extract token because Depends() doesn't work in middleware
            auth = request.headers.get("Authorization")
            if not auth:
                return JSONResponse(status_code=401, content={"detail": "Missing Authorization header"})
            
            import jwt
            
            scheme, _, token = auth.partition(" ")
            if scheme.lower() != "bearer":
                return JSONResponse(status_code=401, content={"detail": "Invalid authentication scheme"})
            
            if not SUPABASE_JWKS_URL:
                print("⚠️  WARNING: SUPABASE_JWKS_URL not set")
                return JSONResponse(status_code=500, content={"detail": "Server configuration error"})
            
            # Get the signing key from JWKS and verify with RS256
            jwks_client = get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            
            payload = jwt.decode(
                token, 
                signing_key.key, 
                algorithms=["ES256"], 
                audience="authenticated", 
                options={"verify_exp": True}
            )
            
            # Inject user into state
            request.state.user = payload
            
        except Exception as e:
            print(f"Auth failed: {e}")
            return JSONResponse(status_code=401, content={"detail": "Invalid authentication credentials"})
            
    return await call_next(request)

llm = init_chat_model(model="gpt-4.1", temperature=0)

# Create the QP workflow once at startup for better performance
qp_workflow = create_qp_workflow()


# ============================================================
# CUSTOM HITL ENDPOINTS
# ============================================================
# These bypass AG-UI's buggy useLangGraphInterrupt

class ResumeRequest(BaseModel):
    approved: bool

@app.post("/copilotkit/resume/{thread_id}")
async def resume_interrupted_graph(thread_id: str, body: ResumeRequest, request: Request):
    """
    Resume an interrupted LangGraph with user's decision.
    Called by frontend when user responds to HITL prompt.
    """
    from langgraph.types import Command

    # SECURITY: Validate ownership - thread must belong to authenticated user
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Authentication required"})

    user_id = user.get("sub")

    # Thread IDs follow patterns: "chat-{user_id}" or "chat-{user_id}-{doc_id}" or "{user_id}:{doc_id}"
    valid_prefixes = [f"chat-{user_id}", f"{user_id}:"]
    if not any(thread_id.startswith(prefix) for prefix in valid_prefixes):
        return JSONResponse(
            status_code=403,
            content={"error": "Unauthorized access to thread"}
        )

    chat_graph = get_chat_graph()
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # Resume the graph with user's response
        result = await chat_graph.ainvoke(
            Command(resume={"approved": body.approved}),
            config=config
        )
        
        # Return the last message from the result
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            return {
                "success": True,
                "message": last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
            }
        return {"success": True, "message": "Graph resumed successfully"}
        
    except Exception as e:
        print(f"❌ Error resuming graph: {e}")
        return {"success": False, "error": str(e)}


class PresignRequest(BaseModel):
    filename: str
    content_type: str


class IngestRequest(BaseModel):
    file_key: str
    document_id: str  # Add document_id from frontend
    page_count: int = 0  # Page count from frontend (pdf.js extraction)


@app.get("/")
async def root():
    return {"message": "Hello World"}


# ============================================================
# R2 UPLOAD ENDPOINTS
# ============================================================

@app.post("/upload/presign")
async def get_presigned_upload_url(request_data: PresignRequest, user: dict = Depends(verify_token)):
    """
    Generate a presigned URL for direct browser-to-R2 upload.
    Returns the upload URL and file key for subsequent ingestion.
    Requires authentication.
    """
    import boto3
    from botocore.client import Config
    import time

    user_id = user.get("sub")
    filename = request_data.filename
    content_type = request_data.content_type

    # Generate unique file key
    timestamp = int(time.time() * 1000)
    file_key = f"uploads/{user_id}/{timestamp}_{filename}"

    # Create R2 client
    r2 = boto3.client(
        's3',
        region_name='auto',
        endpoint_url=os.environ['R2_ENDPOINT'],
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4'),
    )

    # Generate presigned PUT URL (5 minute expiry)
    upload_url = r2.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': os.environ['R2_BUCKET'],
            'Key': file_key,
            'ContentType': content_type,
        },
        ExpiresIn=300  # 5 minutes
    )

    return {
        "success": True,
        "upload_url": upload_url,
        "file_key": file_key,
        "expires_in": 300
    }


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str, user: dict = Depends(verify_token)):
    """
    Delete a document and clean up associated data from Neo4j and R2.
    Postgres deletion is handled by the Next.js server action.
    Requires authentication.
    """
    import boto3
    from botocore.client import Config
    from neo4j import GraphDatabase

    user_id = user.get("sub")

    print(f"\n{'='*60}")
    print(f"🗑️  Deleting document: {document_id}")
    print(f"User: {user_id}")
    print(f"{'='*60}\n")

    errors = []

    # 1. Delete from Neo4j
    try:
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")

        if neo4j_uri and neo4j_user and neo4j_password:
            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            with driver.session() as session:
                # Delete document and all related nodes (ContentBlocks, Questions)
                result = session.run("""
                    MATCH (d:Document {doc_id: $doc_id})
                    OPTIONAL MATCH (d)-[:HAS_BLOCK]->(cb:ContentBlock)
                    OPTIONAL MATCH (cb)-[:HAS_QUESTION]->(q:Question)
                    DETACH DELETE q, cb, d
                    RETURN count(d) as deleted_docs
                """, doc_id=document_id)
                record = result.single()
                deleted = record["deleted_docs"] if record else 0
                print(f"✅ Neo4j: Deleted document and related nodes (docs: {deleted})")
            driver.close()
        else:
            print("⚠️  Neo4j credentials not configured, skipping")
    except Exception as e:
        print(f"❌ Neo4j deletion failed: {e}")
        errors.append(f"Neo4j: {str(e)}")

    # 2. Delete from R2 (both document file and extracted images)
    try:
        r2_endpoint = os.getenv("R2_ENDPOINT")
        r2_access_key = os.getenv("R2_ACCESS_KEY_ID")
        r2_secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
        r2_bucket = os.getenv("R2_BUCKET")

        if r2_endpoint and r2_access_key and r2_secret_key and r2_bucket:
            r2 = boto3.client(
                's3',
                region_name='auto',
                endpoint_url=r2_endpoint,
                aws_access_key_id=r2_access_key,
                aws_secret_access_key=r2_secret_key,
                config=Config(signature_version='s3v4'),
            )

            # List and delete all objects with this document's prefix
            # Documents are stored as: uploads/{user_id}/... and documents/{doc_id}/images/...
            prefixes_to_delete = [
                f"documents/{document_id}/",  # Extracted images
            ]

            total_deleted = 0
            for prefix in prefixes_to_delete:
                paginator = r2.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=r2_bucket, Prefix=prefix):
                    objects = page.get('Contents', [])
                    if objects:
                        delete_keys = [{'Key': obj['Key']} for obj in objects]
                        r2.delete_objects(Bucket=r2_bucket, Delete={'Objects': delete_keys})
                        total_deleted += len(delete_keys)

            print(f"✅ R2: Deleted {total_deleted} objects")
        else:
            print("⚠️  R2 credentials not configured, skipping")
    except Exception as e:
        print(f"❌ R2 deletion failed: {e}")
        errors.append(f"R2: {str(e)}")

    # 3. Clear any Redis cache
    try:
        from redis import Redis
        redis_uri = os.getenv("REDIS_URI", "redis://localhost:6379/0")
        redis_client = Redis.from_url(redis_uri, decode_responses=True)

        # Clear any cached data for this document
        keys_to_delete = redis_client.keys(f"*{document_id}*")
        if keys_to_delete:
            redis_client.delete(*keys_to_delete)
            print(f"✅ Redis: Cleared {len(keys_to_delete)} cached keys")
        else:
            print("✅ Redis: No cached data to clear")
    except Exception as e:
        print(f"⚠️  Redis cleanup failed (non-critical): {e}")

    print(f"{'='*60}\n")

    if errors:
        return {
            "success": False,
            "errors": errors,
            "message": "Document partially deleted with errors"
        }

    return {
        "success": True,
        "message": "Document data cleaned up from Neo4j and R2"
    }


@app.get("/documents/{document_id}/url")
async def get_document_url(document_id: str, user: dict = Depends(verify_token)):
    """
    Get a presigned URL for viewing a document.
    Requires authentication and document ownership verification.
    """
    import boto3
    from botocore.client import Config
    from supabase import create_client

    user_id = user.get("sub")

    # Get document from Postgres to verify ownership and get file_key
    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        return {"success": False, "error": "Server configuration error"}

    supabase = create_client(supabase_url, supabase_key)
    result = supabase.table("Document").select("userId, fileKey, title").eq("id", document_id).execute()

    if not result.data:
        return {"success": False, "error": "Document not found"}

    doc = result.data[0]

    # Verify ownership
    if doc["userId"] != user_id:
        return {"success": False, "error": "Unauthorized"}

    file_key = doc.get("fileKey")
    if not file_key:
        return {"success": False, "error": "Document has no file"}

    # Generate presigned URL
    try:
        r2_endpoint = os.getenv("R2_ENDPOINT")
        r2_access_key = os.getenv("R2_ACCESS_KEY_ID")
        r2_secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
        r2_bucket = os.getenv("R2_BUCKET")

        if not all([r2_endpoint, r2_access_key, r2_secret_key, r2_bucket]):
            return {"success": False, "error": "R2 not configured"}

        r2 = boto3.client(
            's3',
            region_name='auto',
            endpoint_url=r2_endpoint,
            aws_access_key_id=r2_access_key,
            aws_secret_access_key=r2_secret_key,
            config=Config(signature_version='s3v4'),
        )

        # Generate presigned URL valid for 1 hour
        url = r2.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': r2_bucket,
                'Key': file_key,
            },
            ExpiresIn=3600  # 1 hour
        )

        return {
            "success": True,
            "url": url,
            "title": doc.get("title", "Document"),
            "expires_in": 3600
        }

    except Exception as e:
        print(f"Failed to generate presigned URL: {e}")
        return {"success": False, "error": "Failed to generate URL"}


@app.post("/documents/{document_id}/retry")
async def retry_document_ingestion(document_id: str, user: dict = Depends(verify_token)):
    """
    Retry ingestion for a failed document.
    Resets status to PROCESSING and re-queues the Celery task.
    Requires authentication.
    """
    from tasks.ingestion import ingest_document
    from supabase import create_client

    user_id = user.get("sub")

    print(f"\n{'='*60}")
    print(f"🔄 Retrying ingestion for document: {document_id}")
    print(f"User: {user_id}")
    print(f"{'='*60}\n")

    # Get document from Postgres to verify ownership and get file_key
    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        return {"success": False, "error": "Database configuration missing"}

    try:
        supabase = create_client(supabase_url, supabase_key)

        # Get document
        result = supabase.table("Document").select("*").eq("id", document_id).single().execute()

        if not result.data:
            return {"success": False, "error": "Document not found"}

        doc = result.data

        # Verify ownership
        if doc.get("userId") != user_id:
            return {"success": False, "error": "Unauthorized"}

        # Check if document is in FAILED status
        if doc.get("status") not in ["FAILED", "PENDING"]:
            return {
                "success": False,
                "error": f"Document is in {doc.get('status')} status. Only FAILED or PENDING documents can be retried."
            }

        file_key = doc.get("fileKey")
        if not file_key:
            return {"success": False, "error": "Document has no file key - cannot retry"}

        # Reset status to PROCESSING
        supabase.table("Document").update({
            "status": "PROCESSING"
        }).eq("id", document_id).execute()

        # Queue the ingestion task
        task = ingest_document.delay(document_id, user_id, file_key)

        print(f"✅ Ingestion re-queued with task ID: {task.id}")

        return {
            "success": True,
            "task_id": task.id,
            "document_id": document_id,
            "status": "queued",
            "message": "Ingestion retrying. Poll /task/{task_id}/status for progress."
        }

    except Exception as e:
        print(f"❌ Retry failed: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# CREDITS ENDPOINTS
# ============================================================

@app.get("/credits")
async def get_credits(user: dict = Depends(verify_token)):
    """
    Get user's current credit balance.
    Returns voice minutes, chat messages, and pages - each with used, limit, and remaining.
    """
    from credits import get_user_credits

    user_id = user.get("sub")
    credits = get_user_credits(user_id)

    if not credits:
        return {"error": "User not found"}

    return {
        "success": True,
        "credits": credits
    }


@app.post("/ingest")
async def ingest(request_data: IngestRequest, user: dict = Depends(verify_token)):
    """
    Start document ingestion as a background task.
    Returns task_id immediately for progress tracking.
    Requires authentication - documents are linked to authenticated user.
    """
    from tasks.ingestion import ingest_document
    from credits import check_pages_for_document

    # SECURITY: User is guaranteed by verify_token dependency
    user_id = user.get("sub")

    file_key = request_data.file_key
    document_id = request_data.document_id
    page_count = request_data.page_count

    # Check page credits if page_count provided
    if page_count > 0:
        has_enough, remaining, error_msg = check_pages_for_document(user_id, page_count)
        if not has_enough:
            return {"error": error_msg}
        print(f"✅ Page credit check passed: {remaining} pages available >= {page_count} pages needed")
    
    if not file_key:
        return {"error": "file_key is required"}
    if not document_id:
        return {"error": "document_id is required"}
    
    # Queue the task
    task = ingest_document.delay(document_id, user_id, file_key)
    
    return {
        "success": True,
        "task_id": task.id,
        "document_id": document_id,
        "status": "queued",
        "message": "Ingestion started. Poll /task/{task_id}/status for progress."
    }


@app.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Get the status of a background task (ingestion or correction).
    """
    from redis import Redis
    from celery.result import AsyncResult
    from celery_app import celery_app
    
    REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379/0")
    r = Redis.from_url(REDIS_URI, decode_responses=True)
    
    # Check Redis for progress info
    progress_info = r.hgetall(f"task:{task_id}")
    
    # Check Celery for task state
    result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "celery_state": result.state,
    }
    
    if progress_info:
        response["progress"] = int(progress_info.get("progress", 0))
        response["status"] = progress_info.get("status", "unknown")
        response["details"] = progress_info.get("details", "")
    
    if result.state == "SUCCESS":
        response["result"] = result.result
    elif result.state == "FAILURE":
        response["error"] = str(result.result)
    
    return response


class IngestLocalRequest(BaseModel):
    """For local testing - ingest a file from local filesystem"""
    file_path: str
    document_id: str
    user_id: str
    title: Optional[str] = None


@app.post("/ingest-local")
async def ingest_local(request_data: IngestLocalRequest):
    """
    Ingest a local file synchronously (for testing).
    Bypasses R2 and Celery for quick local testing.
    
    1. Creates Document in Postgres
    2. Runs ingestion pipeline synchronously
    3. Saves questions to Neo4j
    4. Updates Document status to READY
    """
    import time
    from pathlib import Path
    
    file_path = request_data.file_path
    document_id = request_data.document_id
    user_id = request_data.user_id
    title = request_data.title or Path(file_path).stem
    
    print(f"\n{'='*60}")
    print(f"📄 Starting local ingestion")
    print(f"File: {file_path}")
    print(f"Document ID: {document_id}")
    print(f"User: {user_id}")
    print(f"{'='*60}\n")
    
    if not Path(file_path).exists():
        return {"error": f"File not found: {file_path}"}
    
    start_time = time.time()
    
    try:
        # Step 1: Create Document in Postgres
        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if supabase_url and supabase_key:
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_key)
            
            # Insert document record
            doc_result = supabase.table("Document").insert({
                "id": document_id,
                "userId": user_id,
                "title": title,
                "status": "PROCESSING",
                "source": "local",
            }).execute()
            print(f"✅ Created Document in Postgres: {document_id}")
        
        # Step 2: Run ingestion pipeline
        from ingestion_workflow import IngestionPipeline
        
        config = {
            "vision_llm": "gpt-4o-mini",
            "text_llm": "gpt-4.1"
        }
        pipeline = IngestionPipeline(config)
        
        print("📖 Extracting document content...")
        content_blocks = pipeline.extract_document(file_path)
        print(f"   Found {len(content_blocks)} content blocks")
        
        print("🧠 Enriching with embeddings and generating questions...")
        enriched_blocks = pipeline.enrich_content_blocks(content_blocks)
        
        # Count questions
        total_questions = sum(len(block.questions) for block in enriched_blocks)
        print(f"   Generated {total_questions} questions")
        
        print("💾 Persisting to Neo4j...")
        doc_meta = {
            "user_id": user_id,
            "doc_id": document_id,
            "title": title,
            "source": file_path,
        }
        pipeline.persist_to_neo4j(document_id, doc_meta, enriched_blocks)
        
        # Step 3: Update Document status to READY
        if supabase_url and supabase_key:
            supabase.table("Document").update({
                "status": "READY"
            }).eq("id", document_id).execute()
            print(f"✅ Document status updated to READY")
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ Ingestion complete in {elapsed:.1f}s")
        print(f"   Blocks: {len(enriched_blocks)}")
        print(f"   Questions: {total_questions}")
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "document_id": document_id,
            "title": title,
            "block_count": len(enriched_blocks),
            "question_count": total_questions,
            "elapsed_seconds": round(elapsed, 2),
            "status": "READY"
        }
        
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Update status to FAILED
        if supabase_url and supabase_key:
            try:
                supabase.table("Document").update({
                    "status": "FAILED"
                }).eq("id", document_id).execute()
            except:
                pass
        
        return {"error": f"Ingestion failed: {str(e)}"}


def create_livekit_token(identity: str, room_name: str) -> str:
    """
    Create a LiveKit access token for a participant.
    Room is automatically created when first participant joins.
    """
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_grants(
            api.VideoGrants(
                room=room_name,
                room_join=True,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )
    return token.to_jwt()


class ExamSessionRequest(BaseModel):
    qp_id: str
    thread_id: str
    session_id: str  # ExamSession database ID for tracking
    mode: str = "exam"  # "exam" or "learn"
    region: str = "india"  # "india" or "global" for geo-based TTS


@app.post("/start-exam-session")
async def start_exam_session(request_data: ExamSessionRequest, user: dict = Depends(verify_token)):
    """
    Start a new exam session with LiveKit agent

    - Checks user has enough voice minutes (EXAM mode: checks QP duration)
    - Fetches QP from Postgres (source of truth)
    - Caches QP to Redis for fast access during exam
    - Creates a unique room (auto-created by LiveKit on first connect)
    - Spawns an exam agent in the background
    - Returns connection info for the student

    Requires authentication - validates user owns the QuestionPaper.
    """
    try:
        # SECURITY: User is guaranteed by verify_token dependency
        user_id = user.get("sub")

        qp_id = request_data.qp_id
        thread_id = request_data.thread_id
        session_id = request_data.session_id
        mode = request_data.mode
        region = request_data.region

        if not qp_id or not thread_id or not session_id:
            return {"error": "qp_id, thread_id, and session_id are required"}
        
        # Validate mode
        if mode not in ["exam", "learn"]:
            return {"error": "mode must be 'exam' or 'learn'"}

        # Step 0: Check user's voice minute credits
        from credits import check_voice_minutes, check_voice_minutes_for_exam

        has_credits, remaining_minutes = check_voice_minutes(user_id)
        if not has_credits:
            return {"error": "You have no voice minutes remaining. Please purchase more credits."}

        print(f"\n{'='*60}")
        print(f"🎯 Starting new exam session")
        print(f"User: {user_id}")
        print(f"Session: {session_id}")
        print(f"QP ID: {qp_id}")
        print(f"Thread ID: {thread_id}")
        print(f"Mode: {mode.upper()}")
        print(f"Region: {region.upper()}")
        print(f"Voice minutes remaining: {remaining_minutes}")

        # Step 1: Check if QP is already cached in Redis
        from redis import Redis
        import json

        redis_client = Redis.from_url("redis://localhost:6379", decode_responses=True)
        cached_qp = redis_client.json().get(f"qp:{qp_id}:questions")

        # We need QP duration for EXAM mode credit check
        qp_duration = None

        if cached_qp:
            print(f"✅ QP found in Redis cache")
            # Still need to fetch duration from Postgres for credit check
            supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if supabase_url and supabase_key:
                from supabase import create_client
                supabase = create_client(supabase_url, supabase_key)
                qp_meta = supabase.table("QuestionPaper").select("duration").eq("id", qp_id).eq("userId", user_id).single().execute()
                if qp_meta.data:
                    qp_duration = qp_meta.data.get("duration")
        else:
            # Step 2: Fetch QP from Postgres via Supabase
            print(f"📥 Fetching QP from Postgres...")

            supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

            if not supabase_url or not supabase_key:
                return {"error": "Supabase credentials not configured"}

            try:
                from supabase import create_client
                supabase = create_client(supabase_url, supabase_key)

                # SECURITY: Filter by userId to ensure ownership
                result = supabase.table("QuestionPaper").select("questions, status, duration").eq("id", qp_id).eq("userId", user_id).single().execute()

                if not result.data:
                    return {"error": f"Question paper {qp_id} not found or access denied"}

                if result.data.get("status") != "READY":
                    return {"error": f"Question paper is not ready (status: {result.data.get('status')})"}

                questions = result.data.get("questions")
                qp_duration = result.data.get("duration")

                if not questions:
                    return {"error": "Question paper has no questions"}

                # Step 3: Cache to Redis with 4 hour TTL
                redis_client.json().set(f"qp:{qp_id}:questions", '$', questions)
                redis_client.expire(f"qp:{qp_id}:questions", 4 * 60 * 60)  # 4 hours

                print(f"✅ Cached {len(questions)} questions to Redis (TTL: 4 hours)")

            except ImportError:
                return {"error": "supabase-py not installed on server"}
            except Exception as e:
                print(f"❌ Failed to fetch QP from Postgres: {e}")
                return {"error": f"Failed to fetch question paper: {str(e)}"}

        # Step 3b: For EXAM mode, check if user has enough minutes for the QP duration
        if mode == "exam" and qp_duration:
            if remaining_minutes < qp_duration:
                return {
                    "error": f"This exam requires {qp_duration} minutes but you only have {remaining_minutes} minutes remaining. Please purchase more credits or try a shorter exam."
                }
            print(f"✅ Credit check passed: {remaining_minutes} mins available >= {qp_duration} mins required")
        
        # Step 4: Create unique room name
        room_name = f"exam-{user_id}-{os.urandom(4).hex()}"
        print(f"Room: {room_name}")
        print(f"{'='*60}\n")
        
        # Step 5: Create tokens for agent and student
        agent_token = create_livekit_token("exam-agent", room_name)
        student_token = create_livekit_token(user_id, room_name)
        
        # Step 6: Spawn the agent in background
        from agents.realtime_exam import main as start_exam_agent

        asyncio.create_task(
            start_exam_agent(
                room_name=room_name,
                token=agent_token,
                qp_id=qp_id,
                thread_id=thread_id,
                mode=mode,
                region=region,
                session_id=session_id,
                user_id=user_id,
            )
        )

        print(f"✅ Agent spawned for room: {room_name}")

        # Return connection info to student
        return {
            "success": True,
            "room_name": room_name,
            "token": student_token,
            "livekit_url": LIVEKIT_URL,
            "qp_id": qp_id,
            "thread_id": thread_id,
            "mode": mode,
            "remaining_minutes": remaining_minutes,
            "message": "Exam session started. Agent is joining the room."
        }
        
    except Exception as e:
        print(f"❌ Error starting exam session: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to start exam session: {str(e)}"}

@app.post("/create-qp")
async def create_question_paper(qp_input: QPInputState, user: dict = Depends(verify_token)):
    """
    Create a question paper based on the provided input parameters.

    1. Run QP generation workflow (fetches from Neo4j, selects questions)
    2. Save questions to Postgres QuestionPaper table
    3. Update status to READY

    Requires authentication.
    """
    try:
        print(f"\n{'='*60}")
        print(f"📝 Generating Question Paper")
        print(f"QP ID: {qp_input.qp_id}")
        print(f"Document: {qp_input.document_id}")
        print(f"Questions: {qp_input.num_questions}")
        print(f"Duration: {qp_input.duration} mins")
        print(f"{'='*60}\n")
        
        # Run the question paper generation workflow
        result = qp_workflow.invoke(qp_input)
        
        # Extract the final grouped questions from the result
        grouped_questions = result.get("grouped_questions", [])
        
        if not grouped_questions:
            return {"error": "No questions could be generated for the given criteria."}
        
        total_questions = len([q for group in grouped_questions for q in group.get("questions", [])])
        print(f"✅ Generated {total_questions} questions in {len(grouped_questions)} groups")
        
        # Save to Postgres via Supabase
        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if supabase_url and supabase_key:
            try:
                from supabase import create_client
                supabase = create_client(supabase_url, supabase_key)
                
                # Update QuestionPaper with questions and set status to READY
                supabase.table("QuestionPaper").update({
                    "questions": grouped_questions,
                    "status": "READY",
                }).eq("id", qp_input.qp_id).execute()
                
                print(f"✅ Saved to Postgres and marked as READY")
                
            except Exception as e:
                print(f"⚠️ Failed to save to Postgres: {e}")
                # Don't fail the request, QP was generated successfully
        
        print(f"{'='*60}\n")
        
        # Return the successful result
        return {
            "success": True,
            "question_paper": {
                "id": qp_input.qp_id,
                "document_id": qp_input.document_id,
                "duration": qp_input.duration,
                "num_questions": qp_input.num_questions,
                "type_of_qp": qp_input.type_of_qp,
                "questions": grouped_questions,
                "total_questions": total_questions,
                "estimated_time": sum(group.get("estimated_time", 0) for group in grouped_questions)
            }
        }
        
    except Exception as e:
        print(f"❌ Error creating question paper: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to create question paper: {str(e)}"}



class EndExamRequest(BaseModel):
    session_id: str
    thread_id: str
    qp_id: str
    # user_id removed - SECURITY: must come from authenticated JWT, not request body


@app.post("/end-exam")
async def end_exam(request_data: EndExamRequest, user: dict = Depends(verify_token)):
    """
    End an exam and trigger correction.

    1. Fetch questions from Redis (cached QP)
    2. Fetch conversation from Redis (LangGraph checkpointer)
    3. Call correction agent
    4. Save report to Postgres
    5. Update ExamSession status to COMPLETED
    """
    try:
        session_id = request_data.session_id
        thread_id = request_data.thread_id
        qp_id = request_data.qp_id
        # SECURITY: Get user_id from authenticated JWT, not request body
        user_id = user.get("sub")

        print(f"\n{'='*60}")
        print(f"📝 Ending exam and generating correction report")
        print(f"Session: {session_id}")
        print(f"Thread: {thread_id}")
        print(f"QP: {qp_id}")
        print(f"User: {user_id}")
        print(f"{'='*60}\n")
        
        # Step 1: Fetch questions from Redis
        from redis import Redis
        redis_client = Redis.from_url("redis://localhost:6379", decode_responses=True)
        
        questions = redis_client.json().get(f"qp:{qp_id}:questions")
        if not questions:
            return {"error": "Question paper not found in cache"}
        
        print(f"✅ Found {len(questions)} questions in Redis")
        
        # Step 2: Fetch conversation from LangGraph checkpointer
        # The checkpointer stores state under langgraph:<thread_id>
        from langgraph.checkpoint.redis import RedisSaver
        
        messages = []
        try:
            with RedisSaver.from_conn_string("redis://localhost:6379") as checkpointer:
                config = {"configurable": {"thread_id": thread_id}}
                state = checkpointer.get(config)
                if state and state.get("channel_values", {}).get("messages"):
                    raw_messages = state["channel_values"]["messages"]
                    # Convert to dict format for correction agent
                    for msg in raw_messages:
                        if hasattr(msg, "content"):
                            msg_type = "human" if msg.__class__.__name__ == "HumanMessage" else "ai"
                            messages.append({"type": msg_type, "content": msg.content})
        except Exception as e:
            print(f"⚠️ Could not fetch messages from checkpointer: {e}")
        
        if not messages:
            print("⚠️ No conversation found, using empty messages")
        else:
            print(f"✅ Found {len(messages)} messages in conversation")
        
        # Step 3: Generate correction report
        from agents.correction_agent import generate_correction_report, CorrectionInput
        
        correction_input = CorrectionInput(
            exam_id=session_id,
            qp_id=qp_id,
            user_id=user_id,
            thread_id=thread_id,
            mode="exam",
            questions=questions,
            messages=messages,
            total_questions=len(questions),
        )
        
        print("🧠 Generating correction report with Kimi-K2...")
        report = generate_correction_report(correction_input)
        print(f"✅ Report generated: score={report.total_score}")
        
        # Step 4: Save report to Postgres
        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        # Initialize variables that may be set in conditional blocks
        grade = None
        minutes_to_deduct = 0

        if supabase_url and supabase_key:
            try:
                from supabase import create_client
                supabase = create_client(supabase_url, supabase_key)
                
                # Calculate grade from score
                score = report.total_score
                if score >= 90: grade = "A+"
                elif score >= 80: grade = "A"
                elif score >= 70: grade = "B+"
                elif score >= 60: grade = "B"
                elif score >= 50: grade = "C"
                elif score >= 40: grade = "D"
                else: grade = "F"
                
                # Insert CorrectionReport
                report_result = supabase.table("CorrectionReport").insert({
                    "examSessionId": session_id,
                    "score": int(score),
                    "grade": grade,
                    "strengths": report.strengths,
                    "weaknesses": report.weaknesses,
                    "recommendations": report.study_recommendations,
                    "summary": report.overall_feedback,
                    "reportJson": report.model_dump(mode="json"),
                }).execute()
                
                print(f"✅ Report saved to Postgres")

                # Step 4b: Fetch session's totalConnectedSeconds and deduct voice minutes
                from credits import deduct_voice_minutes, calculate_session_minutes
                from datetime import datetime, timezone

                session_data = supabase.table("ExamSession").select(
                    "totalConnectedSeconds, lastConnectedAt, startedAt, userId"
                ).eq("id", session_id).single().execute()

                minutes_to_deduct = 0
                if session_data.data:
                    total_seconds = session_data.data.get("totalConnectedSeconds", 0)

                    # If still connected (lastConnectedAt set but not finalized), add remaining time
                    last_connected = session_data.data.get("lastConnectedAt")
                    if last_connected:
                        # User is still connected, calculate time since last connect
                        last_dt = datetime.fromisoformat(last_connected.replace('Z', '+00:00'))
                        additional_seconds = int((datetime.now(timezone.utc) - last_dt).total_seconds())
                        total_seconds += additional_seconds

                    minutes_to_deduct = calculate_session_minutes(total_seconds)

                    if minutes_to_deduct > 0:
                        deduct_voice_minutes(user_id, minutes_to_deduct)
                        print(f"💳 Deducted {minutes_to_deduct} voice minutes (from {total_seconds} seconds connected)")

                # Update ExamSession status to COMPLETED
                supabase.table("ExamSession").update({
                    "status": "COMPLETED",
                    "endedAt": datetime.now(timezone.utc).isoformat(),
                    "totalConnectedSeconds": total_seconds if session_data.data else 0,
                }).eq("id", session_id).execute()

                print(f"✅ ExamSession marked as COMPLETED")
                
            except Exception as e:
                print(f"❌ Failed to save to Postgres: {e}")
        
        # Step 5: Cleanup Redis cache (optional - leave for now for debugging)
        # redis_client.delete(f"qp:{qp_id}:questions")
        
        return {
            "success": True,
            "session_id": session_id,
            "score": report.total_score,
            "grade": grade,
            "questions_attempted": report.questions_attempted,
            "questions_correct": report.questions_correct,
            "minutes_deducted": minutes_to_deduct,
            "message": "Exam completed and report generated"
        }
        
    except Exception as e:
        print(f"❌ Error ending exam: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to end exam: {str(e)}"}


@app.get("/exam-report/{session_id}")
async def get_exam_report(session_id: str, user: dict = Depends(verify_token)):
    """
    Fetch the correction report for an exam session.
    Requires authentication and validates user owns the session.
    """
    try:
        user_id = user.get("sub")

        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            return {"error": "Supabase not configured"}

        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)

        # SECURITY: First verify user owns the exam session
        session_result = supabase.table("ExamSession").select("userId").eq("id", session_id).single().execute()
        if not session_result.data:
            return {"error": "Exam session not found"}
        if session_result.data.get("userId") != user_id:
            return JSONResponse(status_code=403, content={"error": "Access denied"})

        # Fetch the report
        result = supabase.table("CorrectionReport").select("*").eq("examSessionId", session_id).single().execute()

        if not result.data:
            return {"error": "Report not found"}

        return {
            "success": True,
            "report": result.data
        }

    except Exception as e:
        return {"error": f"Failed to fetch report: {str(e)}"}


# ============================================================
# LEARN MODE ENDPOINTS
# ============================================================

@app.get("/topics")
async def get_topics(doc_id: str, user: dict = Depends(verify_token)):
    """
    Get available topics from a document's content blocks.
    Topics are extracted from parent_header field in Neo4j.
    Requires authentication.
    """
    try:
        from lp_agent import get_available_topics

        # Note: Document ownership is enforced at Neo4j level via User->Document relationship
        # The get_available_topics function queries user's documents only
        topics = get_available_topics(doc_id)

        if not topics:
            return {"error": f"No topics found for document: {doc_id}"}

        return {
            "success": True,
            "doc_id": doc_id,
            "topics": topics,
            "total": len(topics)
        }

    except Exception as e:
        print(f"❌ Error fetching topics: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to fetch topics: {str(e)}"}


class LPCreateRequest(BaseModel):
    lp_id: str
    doc_id: str
    # user_id removed - SECURITY: must come from authenticated JWT
    topics: list[str]  # Selected topic names


@app.post("/create-lp")
async def create_learn_pack(request_data: LPCreateRequest, user: dict = Depends(verify_token)):
    """
    Create a Learn Pack from selected topics.

    1. Fetch content blocks for each topic from Neo4j
    2. Extract key concepts via LLM
    3. Store LP in Redis with 4-hour TTL
    4. Return lp_id

    Requires authentication.
    """
    try:
        from lp_agent import create_learn_pack as create_lp, LPInputState

        lp_id = request_data.lp_id
        doc_id = request_data.doc_id
        # SECURITY: Get user_id from authenticated JWT
        user_id = user.get("sub")
        selected_topics = request_data.topics

        if not selected_topics:
            return {"error": "No topics selected"}

        print(f"\n{'='*60}")
        print(f"📚 Creating Learn Pack")
        print(f"LP ID: {lp_id}")
        print(f"Document: {doc_id}")
        print(f"Topics: {selected_topics}")
        print(f"{'='*60}\n")

        lp_input = LPInputState(
            lp_id=lp_id,
            document_id=doc_id,
            user_id=user_id,
            selected_topics=selected_topics
        )

        learn_pack = create_lp(lp_input)

        return {
            "success": True,
            "lp_id": learn_pack.id,
            "doc_id": learn_pack.doc_id,
            "topics": [t["name"] for t in learn_pack.topics],
            "total_topics": learn_pack.total_topics,
            "status": learn_pack.status,
            "message": "Learn Pack created and cached in Redis"
        }

    except Exception as e:
        print(f"❌ Error creating Learn Pack: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to create Learn Pack: {str(e)}"}


class LearnSessionRequest(BaseModel):
    thread_id: str
    region: str = "india"
    # LP-based flow (legacy) - optional
    lp_id: Optional[str] = None
    # NEW: Zero-setup conversational flow - agent discovers everything
    # If lp_id is None, agent will fetch docs/topics conversationally


@app.post("/start-learn-session")
async def start_learn_session(request_data: LearnSessionRequest, user: dict = Depends(verify_token)):
    """
    Start a new learn session.

    Supports two flows:
    1. **Conversational (NEW)**: No lp_id provided - agent greets student,
       fetches their documents, lets them pick a doc and topic conversationally.

    2. **LP-based (legacy)**: lp_id provided - uses pre-created Learn Pack
       with pre-selected topics from /create-lp.

    Flow:
    - Creates a unique LiveKit room
    - Spawns a learn agent in the background
    - Returns connection info for the student

    Requires authentication.
    """
    try:
        from redis import Redis

        # SECURITY: User is guaranteed by verify_token dependency
        user_id = user.get("sub")

        lp_id = request_data.lp_id  # Optional now
        thread_id = request_data.thread_id
        region = request_data.region

        if not thread_id:
            return {"error": "thread_id is required"}

        is_conversational = lp_id is None

        print(f"\n{'='*60}")
        print(f"🎓 Starting new learn session")
        print(f"User: {user_id}")
        print(f"Thread ID: {thread_id}")
        print(f"Region: {region.upper()}")
        print(f"Mode: {'Conversational (zero-setup)' if is_conversational else 'LP-based (legacy)'}")

        if not is_conversational:
            # Legacy LP flow - verify LP exists in Redis
            print(f"LP ID: {lp_id}")
            redis_client = Redis.from_url("redis://localhost:6379", decode_responses=True)
            lp_data = redis_client.json().get(f"lp:{lp_id}:topics")

            if not lp_data:
                return {"error": f"Learn Pack {lp_id} not found in cache. Create it first with /create-lp"}

            print(f"✅ LP found in Redis cache")
            print(f"   Topics: {[t['name'] for t in lp_data.get('topics', [])]}")
        else:
            print("✅ Conversational flow - no LP required")

        # Create unique room name
        room_name = f"learn-{user_id}-{os.urandom(4).hex()}"
        print(f"Room: {room_name}")
        print(f"{'='*60}\n")

        # Create tokens for agent and student
        agent_token = create_livekit_token("learn-agent", room_name)
        student_token = create_livekit_token(user_id, room_name)

        # Spawn the learn agent in background (streaming version)
        from agents.realtime_learn_streaming import main as start_learn_agent

        asyncio.create_task(
            start_learn_agent(
                room_name=room_name,
                token=agent_token,
                lp_id=lp_id,  # None for conversational, or LP ID for legacy
                thread_id=thread_id,
                region=region,
                user_id=user_id  # Required for conversational flow
            )
        )

        print(f"✅ Learn agent spawned for room: {room_name}")

        response = {
            "success": True,
            "room_name": room_name,
            "token": student_token,
            "livekit_url": LIVEKIT_URL,
            "thread_id": thread_id,
            "mode": "conversational" if is_conversational else "lp_based",
            "message": "Learn session started. Agent is joining the room."
        }

        if lp_id:
            response["lp_id"] = lp_id

        return response

    except Exception as e:
        print(f"❌ Error starting learn session: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to start learn session: {str(e)}"}


# ============================================================
# CHAT STREAMING ENDPOINT (SSE)
# ============================================================

class ChatStreamRequest(BaseModel):
    message: str
    doc_id: Optional[str] = None


@app.post("/chat/stream")
async def chat_stream(request: Request):
    """Stream chat via SSE using LangGraph astream_events."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    body = await request.json()
    message = body.get("message", "")
    doc_id = body.get("doc_id")

    if not message:
        return JSONResponse(status_code=400, content={"error": "message is required"})

    user_id = user.get("sub")
    thread_id = f"chat-{user_id}" if not doc_id else f"chat-{user_id}-{doc_id}"

    print(f"\n{'='*60}")
    print(f"💬 Chat stream started")
    print(f"User: {user_id}")
    print(f"Thread: {thread_id}")
    print(f"Doc: {doc_id or 'none'}")
    print(f"Message: {message[:50]}...")
    print(f"{'='*60}\n")

    chat_graph = get_chat_graph()
    config = {"configurable": {"thread_id": thread_id}}

    async def event_generator():
        # Track emitted tool call IDs to avoid duplicates
        emitted_tool_calls = set()
        # Only stream from these nodes (the actual response generators)
        # Unified agent architecture - only "agent" node generates responses
        GENERATOR_NODES = {"agent"}

        try:
            async for event in chat_graph.astream_events(
                {"messages": [HumanMessage(content=message)]},
                config=config,
                version="v2"
            ):
                event_type = event.get("event")
                # Get the node that produced this event
                node_name = event.get("metadata", {}).get("langgraph_node", "")

                # Stream tokens ONLY from generator nodes (not summarization, router, etc.)
                if event_type == "on_chat_model_stream":
                    if node_name not in GENERATOR_NODES:
                        continue  # Skip tokens from internal nodes

                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        content = getattr(chunk, "content", None)
                        if content:
                            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

                # Emit tool calls ONLY from generator node completions
                elif event_type == "on_chain_end":
                    # Check node name - skip non-generator nodes
                    event_name = event.get("name", "")
                    if event_name not in GENERATOR_NODES:
                        continue

                    output = event.get("data", {}).get("output")
                    if isinstance(output, dict):
                        messages = output.get("messages", [])
                        for msg in messages:
                            tool_calls = getattr(msg, "tool_calls", [])
                            for tc in tool_calls:
                                tc_id = tc.get("id", "")
                                if tc_id and tc_id not in emitted_tool_calls:
                                    emitted_tool_calls.add(tc_id)
                                    yield f"data: {json.dumps({'type': 'tool_call', 'id': tc_id, 'name': tc.get('name', ''), 'args': tc.get('args', {})})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            print(f"✅ Chat stream completed for thread: {thread_id}")

        except Exception as e:
            print(f"❌ Chat stream error: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================
# CHAT HISTORY ENDPOINTS (for persistence across refresh/login)
# ============================================================

@app.get("/chat/history")
async def get_chat_history(request: Request, doc_id: Optional[str] = None):
    """
    Fetch chat messages from Redis checkpoint.
    Used by frontend to restore chat state after refresh/login.

    Args:
        doc_id: Optional document ID for document-specific chat history.
                If provided, fetches from thread "chat-{user_id}-{doc_id}".
                If not, fetches from general chat thread "chat-{user_id}".
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    user_id = user.get("sub")
    # Match the thread_id format used by /chat/stream endpoint
    thread_id = f"chat-{user_id}" if not doc_id else f"chat-{user_id}-{doc_id}"
    REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")

    try:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver

        async with AsyncRedisSaver.from_conn_string(REDIS_URI) as checkpointer:
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint_tuple = await checkpointer.aget_tuple(config)

            if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
                return {"messages": [], "thread_id": thread_id}

            raw_messages = checkpoint_tuple.checkpoint.get("channel_values", {}).get("messages", [])
            messages = []

            for msg in raw_messages:
                if not hasattr(msg, "content") or not hasattr(msg, "id"):
                    continue

                class_name = msg.__class__.__name__

                # Skip ToolMessage - these are raw tool outputs, not for display
                if class_name == "ToolMessage":
                    continue

                # Skip AIMessage with empty content (tool call placeholders)
                if class_name == "AIMessage" and not msg.content:
                    continue

                role = "user" if class_name == "HumanMessage" else "assistant"
                msg_data = {
                    "id": msg.id,
                    "role": role,
                    "content": msg.content,
                }
                # Extract tool_calls if present (for UI tools like request_upload_ui)
                # This ensures tool UIs are restored after page refresh
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    msg_data["toolCalls"] = [
                        {
                            "id": tc.get("id", ""),
                            "name": tc.get("name", ""),
                            "args": tc.get("args", {})
                        }
                        for tc in msg.tool_calls
                    ]
                messages.append(msg_data)

            return {"messages": messages, "thread_id": thread_id}

    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return {"messages": [], "thread_id": thread_id, "error": str(e)}


@app.delete("/chat/history")
async def clear_chat_history(request: Request):
    """
    Clear chat checkpoint from Redis.
    Called when user clicks "New Conversation" button.

    Request body (optional):
        doc_id: Document ID for document-specific chat history.
                If provided, clears thread "chat-{user_id}-{doc_id}".
                If not, clears general chat thread "chat-{user_id}".
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    # Parse optional doc_id from request body
    doc_id = None
    try:
        body = await request.json()
        doc_id = body.get("doc_id")
    except Exception:
        pass  # No body or invalid JSON is fine

    user_id = user.get("sub")
    # Match the thread_id format used by /chat/stream endpoint
    thread_id = f"chat-{user_id}" if not doc_id else f"chat-{user_id}-{doc_id}"
    REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")

    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(REDIS_URI)

        # Delete all checkpoint keys for this thread
        pattern = f"*{thread_id}*"
        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            await client.delete(*keys)

        await client.aclose()
        return {"status": "cleared", "thread_id": thread_id, "keys_deleted": len(keys)}

    except Exception as e:
        print(f"Error clearing chat history: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    