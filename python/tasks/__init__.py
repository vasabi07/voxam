"""
Voxam background tasks module.
Import tasks here for Celery auto-discovery.
"""
from tasks.ingestion import ingest_document
from tasks.correction import run_correction, trigger_correction

__all__ = ["ingest_document", "run_correction", "trigger_correction"]
