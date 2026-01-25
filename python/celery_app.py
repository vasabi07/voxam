"""
Celery application configuration for Voxam background tasks.

Tasks:
- Document ingestion (PDF parsing, embedding, question generation)
- Correction report generation

Usage:
    Start worker: celery -A celery_app worker --loglevel=info
"""
from celery import Celery
from dotenv import load_dotenv
import os

load_dotenv()

# Use Redis as both broker and result backend
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379/0")

celery_app = Celery(
    "voxam",
    broker=REDIS_URI,
    backend=REDIS_URI,
    include=["tasks.ingestion", "tasks.correction"],  # Auto-discover tasks
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # Timezone
    timezone="Asia/Kolkata",
    enable_utc=True,
    
    # Task settings
    task_track_started=True,  # Track when task starts
    task_time_limit=1800,     # 30 min max per task (ingestion can be slow)
    task_soft_time_limit=1500,  # Soft limit at 25 min
    
    # Result settings
    result_expires=86400,  # Results expire after 24 hours
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time (ingestion is heavy)
    worker_concurrency=2,  # 2 workers for ingestion tasks
)

# NOTE: Add task routing when you need to scale different task types independently
# celery_app.conf.task_routes = {
#     "tasks.ingestion.*": {"queue": "ingestion"},
#     "tasks.correction.*": {"queue": "correction"},
# }
