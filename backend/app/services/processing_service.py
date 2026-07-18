"""Async orchestration service for durable post processing."""

from __future__ import annotations

import json
import traceback
from hashlib import sha256
from uuid import uuid4

from sqlalchemy.orm import Session

from ..repositories import JobRepository
from ..schemas import JobStatusResponse, PostCreate, PostCreateResponse
from ..settings import get_settings
from .post_service import PostService


class ProcessingService:
    """Submit, resume, and inspect async post-processing jobs."""

    def __init__(self, db: Session, post_service: PostService) -> None:
        self._db = db
        self._post_service = post_service
        self._jobs = JobRepository(db)

    def content_hash_for(self, payload: PostCreate) -> str:
        pipeline_version = get_settings().pipeline_version
        body = f"{payload.text}::{pipeline_version}"
        return sha256(body.encode("utf-8")).hexdigest()

    def submit_post(self, payload: PostCreate) -> tuple[int, PostCreateResponse]:
        content_hash = self.content_hash_for(payload)
        existing = self._jobs.get_job_by_hash(content_hash)
        if existing and existing.status == "COMPLETED" and existing.result_json:
            cached = PostCreateResponse.model_validate_json(existing.result_json)
            cached.job_id = existing.id
            cached.status = "COMPLETED"
            return 200, cached
        if existing:
            return 202, PostCreateResponse(job_id=existing.id, status=existing.status)

        job_id = str(uuid4())
        self._jobs.create_job(
            job_id=job_id,
            content_hash=content_hash,
            pipeline_version=get_settings().pipeline_version,
            payload_json=payload.model_dump_json(),
        )
        return 202, PostCreateResponse(job_id=job_id, status="PENDING")

    def process_job(self, job_id: str) -> JobStatusResponse:
        job = self._jobs.get_job(job_id)
        if job is None:
            raise ValueError(f"Unknown job: {job_id}")

        if job.status == "COMPLETED" and job.result_json:
            payload = PostCreateResponse.model_validate_json(job.result_json)
            return JobStatusResponse(
                job_id=job.id,
                status=job.status,
                post=payload.post,
                similar_posts=payload.similar_posts,
                media_recommendations=payload.media_recommendations,
                explanation=payload.explanation,
                pii_detected=payload.pii_detected,
                redactions=payload.redactions,
            )

        try:
            job.status = "PROCESSING"
            job.attempt_count += 1
            self._jobs.save_job(job)
            payload = PostCreate.model_validate_json(job.payload_json)
            result = self._post_service.create_post(payload, content_hash=job.content_hash)
            result.job_id = job.id
            result.status = "COMPLETED"
            job.status = "COMPLETED"
            job.result_json = result.model_dump_json()
            if result.post is not None:
                job.post_id = result.post.id
            job.error_message = None
            self._jobs.save_job(job)
            return JobStatusResponse(
                job_id=job.id,
                status=job.status,
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
            self._jobs.save_job(job)
            self._jobs.add_dead_letter(
                job_id=job.id,
                content_hash=job.content_hash,
                payload_json=job.payload_json,
                error_type=error.__class__.__name__,
                error_message=str(error),
                traceback_text=trace,
            )
            return JobStatusResponse(
                job_id=job.id,
                status="FAILED",
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
                post=payload.post,
                similar_posts=payload.similar_posts,
                media_recommendations=payload.media_recommendations,
                explanation=payload.explanation,
                pii_detected=payload.pii_detected,
                redactions=payload.redactions,
                error=job.error_message,
            )
        return JobStatusResponse(job_id=job.id, status=job.status, error=job.error_message)
