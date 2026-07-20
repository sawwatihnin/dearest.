"""Celery tasks for async post processing."""

from __future__ import annotations

from .api.deps import build_services
from .celery_app import celery_app
from .database import SessionLocal
from .services import ProcessingService


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_backoff_max=8,
    retry_kwargs={"max_retries": 3},
)
def process_post_job(self, job_id: str):
    with SessionLocal() as db:
        services = build_services(db)
        processing_service = services["processing_service"]
        result = processing_service.process_job(job_id)
        if result.status == "FAILED":
            raise RuntimeError(result.error or "Unknown job failure")
        return result.model_dump()
