"""
Voxam background tasks module.
Import tasks here for Celery auto-discovery.
"""
from tasks.ingestion import ingest_document
from tasks.correction import generate_correction_report

__all__ = ["ingest_document", "generate_correction_report"]
