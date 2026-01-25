"""
Test data factories for VOXAM Python backend tests.
"""
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta


def create_mock_user(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a mock user with credits."""
    defaults = {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "name": "Test User",
        "region": "india",
        "voiceMinutesUsed": 0,
        "voiceMinutesLimit": 60,
        "chatMessagesUsed": 0,
        "chatMessagesLimit": 100,
        "pagesUsed": 0,
        "pagesLimit": 50,
        "createdAt": datetime.now().isoformat(),
    }
    return {**defaults, **(overrides or {})}


def create_mock_document(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a mock document."""
    defaults = {
        "id": str(uuid.uuid4()),
        "title": "Test Document",
        "status": "READY",
        "userId": "test-user-id",
        "fileKey": "documents/test.pdf",
        "pageCount": 10,
        "createdAt": datetime.now().isoformat(),
        "archivedAt": None,
    }
    return {**defaults, **(overrides or {})}


def create_mock_question(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a mock question."""
    defaults = {
        "id": str(uuid.uuid4()),
        "text": "What is the capital of France?",
        "question_type": "multiple_choice",
        "options": ["Paris", "London", "Berlin", "Madrid"],
        "correct_answer": "Paris",
        "explanation": "Paris is the capital and largest city of France.",
        "difficulty": "basic",
        "bloom_level": "remember",
        "expected_time": 60,
        "key_points": ["Capital city", "France", "Paris"],
    }
    return {**defaults, **(overrides or {})}


def create_mock_question_paper(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a mock question paper."""
    defaults = {
        "id": str(uuid.uuid4()),
        "status": "READY",
        "documentId": "doc-123",
        "userId": "test-user-id",
        "duration": 30,
        "numQuestions": 10,
        "difficulty": ["basic", "intermediate"],
        "bloomLevel": ["remember", "understand", "apply"],
        "questionTypes": ["multiple_choice", "short_answer"],
        "questions": [create_mock_question() for _ in range(10)],
        "createdAt": datetime.now().isoformat(),
    }
    return {**defaults, **(overrides or {})}


def create_mock_exam_session(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a mock exam session."""
    defaults = {
        "id": str(uuid.uuid4()),
        "status": "SCHEDULED",
        "mode": "exam",
        "userId": "test-user-id",
        "qpId": "qp-123",
        "documentId": "doc-123",
        "startedAt": None,
        "endedAt": None,
        "createdAt": datetime.now().isoformat(),
    }
    return {**defaults, **(overrides or {})}


def create_mock_content_block(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a mock content block for retrieval tests."""
    defaults = {
        "id": str(uuid.uuid4()),
        "content": "This is test content about photosynthesis. Plants convert sunlight into energy.",
        "page": 1,
        "page_end": 1,
        "title": "Test Document",
        "doc_id": "doc-123",
        "user_id": "test-user-id",
        "chapter": "Chapter 1",
        "section": "Introduction",
        "embedding": [0.1] * 1536,
    }
    return {**defaults, **(overrides or {})}


def create_mock_correction_report(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a mock correction report."""
    defaults = {
        "exam_id": "exam-123",
        "user_id": "test-user-id",
        "total_score": 85.0,
        "questions_attempted": 10,
        "questions_correct": 8,
        "bloom_breakdown": {
            "remember": 90.0,
            "understand": 85.0,
            "apply": 80.0,
            "analyze": 75.0,
            "evaluate": 0.0,
            "create": 0.0,
        },
        "difficulty_breakdown": {
            "basic": 90.0,
            "intermediate": 80.0,
            "advanced": 70.0,
        },
        "question_results": [
            {
                "question_index": i,
                "question_text": f"Question {i+1}",
                "bloom_level": "remember",
                "difficulty": "basic",
                "user_answer_summary": "User's answer",
                "is_correct": i < 8,
                "score": 100 if i < 8 else 0,
                "feedback": "Good answer" if i < 8 else "Incorrect",
                "key_points_covered": ["Point 1"],
                "key_points_missed": [] if i < 8 else ["Point 2"],
                "improvement_tips": "Keep up the good work" if i < 8 else "Review this topic",
            }
            for i in range(10)
        ],
        "strengths": ["Good recall", "Clear explanations"],
        "weaknesses": ["Time management"],
        "overall_feedback": "Good performance overall.",
        "study_recommendations": ["Review chapter 3", "Practice more questions"],
        "generated_at": datetime.now().isoformat(),
        "model_used": "kimi-k2-thinking",
    }
    return {**defaults, **(overrides or {})}


def create_mock_jwt_payload(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a mock JWT payload."""
    defaults = {
        "sub": "test-user-id",
        "aud": "authenticated",
        "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now().timestamp()),
        "email": "test@example.com",
        "role": "authenticated",
    }
    return {**defaults, **(overrides or {})}


def create_mock_expired_jwt_payload() -> Dict[str, Any]:
    """Create an expired JWT payload."""
    return {
        "sub": "test-user-id",
        "aud": "authenticated",
        "exp": int((datetime.now() - timedelta(hours=1)).timestamp()),
        "iat": int((datetime.now() - timedelta(hours=2)).timestamp()),
    }


def create_mock_credits_response(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a mock credits response."""
    defaults = {
        "voiceMinutes": {
            "used": 10,
            "limit": 60,
            "remaining": 50,
        },
        "chatMessages": {
            "used": 5,
            "limit": 100,
            "remaining": 95,
        },
        "pages": {
            "used": 10,
            "limit": 50,
            "remaining": 40,
        },
    }
    return {**defaults, **(overrides or {})}


def create_mock_task_status(status: str = "processing", progress: int = 50) -> Dict[str, Any]:
    """Create a mock task status response."""
    return {
        "task_id": "task-123",
        "status": status,
        "progress": progress,
        "details": {
            "step": "Processing document",
            "message": "Extracting content...",
        },
        "updated_at": datetime.now().isoformat(),
    }


def create_mock_retrieval_result(num_blocks: int = 3) -> Dict[str, Any]:
    """Create a mock retrieval result with sources."""
    blocks = [create_mock_content_block({"id": f"block-{i}", "page": i+1}) for i in range(num_blocks)]
    context = "\n\n".join([
        f"[Doc:Test Document page:{b['page']}]\n{b['content']}"
        for b in blocks
    ])
    sources = [
        {
            "page": b["page"],
            "page_end": b["page_end"],
            "title": b["title"],
            "excerpt": b["content"][:100],
            "doc_id": b["doc_id"],
        }
        for b in blocks
    ]
    return {
        "context": context,
        "sources": sources,
        "citations": [f"[Doc:Test Document page:{b['page']}]" for b in blocks],
    }


def create_mock_livekit_token() -> str:
    """Create a mock LiveKit token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock-livekit-token"


def create_mock_conversation_messages() -> List[Dict[str, Any]]:
    """Create mock conversation messages for exam/chat tests."""
    return [
        {"type": "human", "content": "What is photosynthesis?"},
        {"type": "ai", "content": "Photosynthesis is the process by which plants convert sunlight into energy."},
        {"type": "human", "content": "How does it work?"},
        {"type": "ai", "content": "Plants use chlorophyll to absorb light and convert CO2 and water into glucose and oxygen."},
    ]


def create_mock_exam_state(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a mock exam agent state."""
    defaults = {
        "thread_id": "exam-test-user-id-123",
        "qp_id": "qp-123",
        "user_id": "test-user-id",
        "current_index": 0,
        "mode": "exam",
        "duration_minutes": 30,
        "current_question": create_mock_question(),
        "total_questions": 10,
        "exam_started": False,
        "correction_task_id": None,
        "response_type": None,
        "response_options": None,
        "running_summary": None,
        "summary_message_index": 0,
        "messages": [],
    }
    return {**defaults, **(overrides or {})}


def create_mock_chat_state(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a mock chat agent state."""
    defaults = {
        "messages": [],
        "credit_check_passed": None,
        "rewritten_query": None,
        "retrieved_context": None,
        "citations": None,
        "retrieved_sources": None,
        "doc_id": "doc-123",
        "user_id": "test-user-id",
        "route": None,
        "needs_web_search": None,
        "conversation_summary": None,
        "summary_message_index": 0,
    }
    return {**defaults, **(overrides or {})}
