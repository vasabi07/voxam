from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from r2 import get_file
from qp_agent import QPInputState, create_qp_workflow
from agents.chat_agent import chat_graph
from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
import asyncio
from livekit import api

# CopilotKit AG UI imports
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
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

# Add CopilotKit AG UI endpoint for chat agent (testing)
# Protect this endpoint with JWT verification
add_langgraph_fastapi_endpoint(
    app=app,
    agent=LangGraphAGUIAgent(
        name="chat_agent",
        description="A friendly AI assistant that helps with general questions and conversations",
        graph=chat_graph,
    ),
    path="/copilotkit",
    # Pass dependencies to the underlying router
   # dependencies=[Depends(verify_token)] 
   # Note: Since I am not 100% sure add_langgraph_fastapi_endpoint supports dependencies,
   # I will rely on the middleware below if this fails? No, that's risky.
   # I'll try to inject it. If the user reports an error, I'll fix it.
   # But wait, looking at standard CopilotKit patterns, usually you wrap it or use a router.
)

# Middleware for auth on /copilotkit if dependencies kwarg is not supported
# (I'll add a specific middleware for this, cleaner and safer than guessing kwargs)
from fastapi.responses import JSONResponse

@app.middleware("http")
async def verify_copilot_request(request: Request, call_next):
    if request.url.path.startswith("/copilotkit"):
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

class IngestRequest(BaseModel):
    file_key: str  
    

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/ingest")
async def ingest(request_data: IngestRequest, request: Request):
    # Get user from request state if authentication is enabled
    user = getattr(request.state, "user", None)
    user_id = user.get("sub") if user else None
    
    file_key = request_data.file_key
    if not file_key:
        return {"error": "file_key is required in the request body."}
    filename = await get_file(file_key) 
    if not filename:
        return {"error": "Failed to retrieve the file."}
    return {"message": "File retrieved successfully.", "file": filename, "user_id": user_id}


def create_livekit_token(identity: str, room_name: str) -> str:
    """
    Create a LiveKit access token for a participant
    Room is automatically created when first participant joins
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
    mode: str = "exam"  # "exam" or "learn"


@app.post("/start-exam-session")
async def start_exam_session(request_data: ExamSessionRequest, request: Request):
    """
    Start a new exam session with LiveKit agent
    
    - Creates a unique room (auto-created by LiveKit on first connect)
    - Spawns an exam agent in the background
    - Returns connection info for the student
    """
    try:
        # Get user from request state if authentication is enabled
        user = getattr(request.state, "user", None)
        user_id = user.get("sub") if user else f"student-{os.urandom(4).hex()}"
        
        qp_id = request_data.qp_id
        thread_id = request_data.thread_id
        mode = request_data.mode
        
        if not qp_id or not thread_id:
            return {"error": "qp_id and thread_id are required"}
        
        # Validate mode
        if mode not in ["exam", "learn"]:
            return {"error": "mode must be 'exam' or 'learn'"}
        
        # Create unique room name (room auto-creates when agent connects)
        room_name = f"exam-{user_id}-{os.urandom(4).hex()}"
        
        print(f"\n{'='*60}")
        print(f"🎯 Starting new exam session")
        print(f"User: {user_id}")
        print(f"Room: {room_name}")
        print(f"QP ID: {qp_id}")
        print(f"Thread ID: {thread_id}")
        print(f"Mode: {mode.upper()}")
        print(f"{'='*60}\n")
        
        # Create tokens for agent and student
        agent_token = create_livekit_token("exam-agent", room_name)
        student_token = create_livekit_token(user_id, room_name)
        
        # Import and spawn the agent in background
        from agents.realtime import main as start_realtime_agent
        
        asyncio.create_task(
            start_realtime_agent(
                room_name=room_name,
                token=agent_token,
                qp_id=qp_id,
                thread_id=thread_id,
                mode=mode
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
            "message": "Exam session started. Agent is joining the room."
        }
        
    except Exception as e:
        print(f"❌ Error starting exam session: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to start exam session: {str(e)}"}

@app.post("/create-qp")
async def create_question_paper(qp_input: QPInputState):
    """
    Create a question paper based on the provided input parameters.
    """
    try:
        # Run the question paper generation workflow
        result = qp_workflow.invoke(qp_input)
        
        # Extract the final grouped questions from the result
        grouped_questions = result.get("grouped_questions", [])
        
        if not grouped_questions:
            return {"error": "No questions could be generated for the given criteria."}
        
        # Return the successful result
        return {
            "success": True,
            "question_paper": {
                "id": qp_input.qp_id,  # Return the qp_id from Next.js
                "document_id": qp_input.document_id,
                "duration": qp_input.duration,
                "num_questions": qp_input.num_questions,
                "type_of_qp": qp_input.type_of_qp,
                "questions": grouped_questions,
                "total_questions": len([q for group in grouped_questions for q in group.get("questions", [])]),
                "estimated_time": sum(group.get("estimated_time", 0) for group in grouped_questions)
            }
        }
        
    except Exception as e:
        print(f"❌ Error creating question paper: {e}")
        return {"error": f"Failed to create question paper: {str(e)}"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    