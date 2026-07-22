"""Async orchestration service for durable post processing."""

from __future__ import annotations

import json
import traceback
from hashlib import sha256
from uuid import uuid4

from sqlalchemy.orm import Session

from ..request_context import get_correlation_id, set_correlation_id
from ..repositories import JobRepository
from ..schemas import JobStatusResponse, PostCreate, PostCreateResponse
from ..settings import get_settings
from ..telemetry import registry
from ..runtime_state import TransientStateStore
from .post_service import PostService


class ProcessingService:
    """Submit, resume, and inspect async post-processing jobs."""

    def __init__(self, db: Session, post_service: PostService, transient_state_store: TransientStateStore) -> None:
        self._db = db
        self._post_service = post_service
        self._jobs = JobRepository(db)
        self._transient_state_store = transient_state_store

    def content_hash_for(self, payload: PostCreate) -> str:
        pipeline_version = get_settings().pipeline_version
        body = f"{payload.text}::{pipeline_version}"
        return sha256(body.encode("utf-8")).hexdigest()

    def submit_post(self, payload: PostCreate) -> tuple[int, PostCreateResponse]:
        correlation_id = get_correlation_id()
        content_hash = self.content_hash_for(payload)
        existing = self._jobs.get_job_by_hash(content_hash)
        if existing and existing.status == "COMPLETED" and existing.result_json:
            cached = PostCreateResponse.model_validate_json(existing.result_json)
            # Completed job payloads can predate a privacy repair. Always serve the
            # current persisted post instead of an obsolete embedded snapshot.
            if cached.post is not None:
                refreshed_post = self._post_service.get_post(cached.post.id)
                if refreshed_post is not None:
                    cached.post = refreshed_post
            cached.job_id = existing.id
            cached.status = "COMPLETED"
            cached.correlation_id = existing.correlation_id
            return 200, cached
        if existing:
            return 202, PostCreateResponse(job_id=existing.id, status=existing.status, correlation_id=existing.correlation_id)

        job_id = str(uuid4())
        self._jobs.create_job(
            job_id=job_id,
            content_hash=content_hash,
            pipeline_version=get_settings().pipeline_version,
            payload_json=payload.model_dump_json(),
            correlation_id=correlation_id,
        )
        self._transient_state_store.set_stage(job_id, "PENDING", {"correlation_id": correlation_id})
        return 202, PostCreateResponse(job_id=job_id, status="PENDING", correlation_id=correlation_id)

    def submit_post_from_payload(
        self,
        payload: dict[str, object],
        correlation_id: str | None = None,
    ) -> tuple[int, PostCreateResponse]:
        if correlation_id:
            set_correlation_id(correlation_id)
        return self.submit_post(PostCreate.model_validate(payload))

    def process_job(self, job_id: str) -> JobStatusResponse:
        job = self._jobs.get_job(job_id)
        if job is None:
            raise ValueError(f"Unknown job: {job_id}")
        if job.correlation_id:
            set_correlation_id(job.correlation_id)

        if job.status == "COMPLETED" and job.result_json:
            payload = PostCreateResponse.model_validate_json(job.result_json)
            return JobStatusResponse(
                job_id=job.id,
                status=job.status,
                correlation_id=job.correlation_id,
                post=payload.post,
                similar_posts=payload.similar_posts,
                media_recommendations=payload.media_recommendations,
                explanation=payload.explanation,
                pii_detected=payload.pii_detected,
                redactions=payload.redactions,
            )

        try:
            job.status = "RUNNING"
            job.attempt_count += 1
            self._transient_state_store.set_stage(job_id, "RUNNING", {"attempt": job.attempt_count})
            self._jobs.save_job(job)
            payload = PostCreate.model_validate_json(job.payload_json)
            self._transient_state_store.set_stage(job_id, "ENRICHING")
            result = self._post_service.create_post(payload, content_hash=job.content_hash)
            result.job_id = job.id
            result.status = "COMPLETED"
            result.correlation_id = job.correlation_id
            job.status = "COMPLETED"
            job.result_json = result.model_dump_json()
            if result.post is not None:
                job.post_id = result.post.id
            job.error_message = None
            job.terminal_trace_json = json.dumps(
                {
                    "job_id": job.id,
                    "status": job.status,
                    "attempt_count": job.attempt_count,
                    "correlation_id": job.correlation_id,
                }
            )
            self._jobs.save_job(job)
            self._transient_state_store.clear_stage(job_id)
            registry.increment("dearest_processing_completed_total")
            return JobStatusResponse(
                job_id=job.id,
                status=job.status,
                correlation_id=job.correlation_id,
                post=result.post,
                similar_posts=result.similar_posts,
                media_recommendations=result.media_recommendations,
                explanation=result.explanation,
                pii_detected=result.pii_detected,
                redactions=result.redactions,
            )
        except Exception as error:  # pragma: no cover - fatal path
            trace = traceback.format_exc()
            job.status = "FAILED"
            job.error_message = str(error)
            job.terminal_trace_json = json.dumps(
                {
                    "job_id": job.id,
                    "status": job.status,
                    "attempt_count": job.attempt_count,
                    "correlation_id": job.correlation_id,
                    "error": str(error),
                }
            )
            self._jobs.save_job(job)
            self._jobs.add_dead_letter(
                job_id=job.id,
                correlation_id=job.correlation_id,
                content_hash=job.content_hash,
                payload_json=job.payload_json,
                error_type=error.__class__.__name__,
                error_message=str(error),
                traceback_text=trace,
            )
            self._transient_state_store.set_stage(job_id, "FAILED", {"error": str(error)})
            registry.increment("dearest_dlq_entries_total")
            return JobStatusResponse(
                job_id=job.id,
                status="FAILED",
                correlation_id=job.correlation_id,
                error=str(error),
            )

    def get_job_status(self, job_id: str) -> JobStatusResponse | None:
        job = self._jobs.get_job(job_id)
        if job is None:
            return None
        if job.result_json:
            payload = PostCreateResponse.model_validate_json(job.result_json)
            return JobStatusResponse(
                job_id=job.id,
                status=job.status,
                correlation_id=job.correlation_id,
                post=payload.post,
                similar_posts=payload.similar_posts,
                media_recommendations=payload.media_recommendations,
                explanation=payload.explanation,
                pii_detected=payload.pii_detected,
                redactions=payload.redactions,
                error=job.error_message,
            )
        transient = self._transient_state_store.get_stage(job_id)
        status = str(transient["stage"]) if transient and transient.get("stage") else job.status
        return JobStatusResponse(job_id=job.id, status=status, correlation_id=job.correlation_id, error=job.error_message)
