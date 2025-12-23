"""
Correction report generation Celery task.

This task:
1. Fetches QP from Redis
2. Fetches conversation from LangGraph checkpointer
3. Runs correction agent (Kimi-K2-Thinking) to analyze answers
4. Returns detailed report with Bloom's taxonomy breakdown
5. Cleans up QP from Redis after completion

Usage:
    from tasks.correction import run_correction
    task = run_correction.delay(exam_id, qp_id, user_id, thread_id)
"""
from celery_app import celery_app
from redis import Redis
from langgraph.checkpoint.redis import RedisSaver
from dotenv import load_dotenv
import os
import time
from datetime import datetime

load_dotenv()

REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379/0")


def update_progress(task_id: str, progress: int, status: str, message: str = ""):
    """Update task progress in Redis."""
    r = Redis.from_url(REDIS_URI, decode_responses=True)
    r.hset(f"task:{task_id}", mapping={
        "progress": progress,
        "status": status,
        "message": message,
        "updated_at": datetime.utcnow().isoformat()
    })
    r.expire(f"task:{task_id}", 3600)  # 1 hour TTL


@celery_app.task(bind=True, name="tasks.correction.run_correction")
def run_correction(self, exam_id: str, qp_id: str, user_id: str, thread_id: str):
    """
    Generate correction report from completed exam.
    
    Args:
        exam_id: Unique exam session ID
        qp_id: Question paper ID
        user_id: User who took exam
        thread_id: LangGraph checkpointer thread ID
        
    Returns:
        dict with correction report
    """
    task_id = self.request.id
    start_time = time.time()
    
    try:
        from agents.correction_agent import (
            generate_correction_report,
            CorrectionInput,
        )
        
        r = Redis.from_url(REDIS_URI, decode_responses=True)
        
        update_progress(task_id, 10, "fetching", "Fetching question paper...")
        
        # 1. Get QP from Redis
        questions = r.json().get(f"qp:{qp_id}:questions")
        
        if not questions:
            raise ValueError(f"No QP found for qp_id: {qp_id}")
        
        update_progress(task_id, 25, "fetching", "Fetching exam conversation...")
        
        # 2. Fetch conversation from LangGraph checkpointer
        try:
            checkpointer = RedisSaver.from_conn_string(REDIS_URI)
            checkpoint = checkpointer.get({"configurable": {"thread_id": thread_id}})
            
            if checkpoint and "messages" in checkpoint:
                messages = [
                    {"type": msg.type, "content": msg.content}
                    for msg in checkpoint["messages"]
                ]
            else:
                # Fallback: try to get from state
                messages = []
                print(f"⚠️ No checkpoint found for thread: {thread_id}")
        except Exception as e:
            print(f"⚠️ Error fetching checkpoint: {e}")
            messages = []
        
        if not messages:
            raise ValueError(f"No conversation found for thread_id: {thread_id}")
        
        update_progress(task_id, 40, "analyzing", "Analyzing with Kimi-K2-Thinking...")
        
        # 3. Build input for correction agent
        input_data = CorrectionInput(
            exam_id=exam_id,
            qp_id=qp_id,
            user_id=user_id,
            thread_id=thread_id,
            mode="exam",
            questions=questions,
            messages=messages,
            total_questions=len(questions),
            ended_at=datetime.utcnow(),
        )
        
        # 4. Generate correction report
        report = generate_correction_report(input_data)
        
        update_progress(task_id, 80, "complete", "Report generated!")
        
        # 5. Convert to dict for return (skip DB storage for now)
        report_dict = report.model_dump(mode="json")
        report_dict["processing_time"] = round(time.time() - start_time, 2)
        
        update_progress(task_id, 90, "cleanup", "Cleaning up...")
        
        # 6. NOW cleanup QP from Redis (after correction is done)
        r.delete(f"qp:{qp_id}:questions")
        print(f"✅ Cleaned up QP: {qp_id}")
        
        update_progress(task_id, 100, "done", "Correction complete!")
        
        return report_dict
        
    except Exception as e:
        update_progress(task_id, -1, "error", str(e))
        print(f"❌ Correction failed: {e}")
        raise self.retry(exc=e, countdown=30, max_retries=2)


# ============ Helper to trigger from exam agent ============

def trigger_correction(exam_id: str, qp_id: str, user_id: str, thread_id: str) -> str:
    """
    Trigger async correction task. Returns task ID for tracking.
    
    Call this from exam_agent.cleanup_exam()
    """
    task = run_correction.delay(
        exam_id=exam_id,
        qp_id=qp_id,
        user_id=user_id,
        thread_id=thread_id
    )
    print(f"📝 Correction triggered: task_id={task.id}, exam_id={exam_id}")
    return task.id
