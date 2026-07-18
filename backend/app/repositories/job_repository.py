"""Repository layer for async processing jobs and dead letters."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import DeadLetterQueueEntry, ProcessingJob


class JobRepository:
    """Encapsulates job persistence and failure capture."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_job(self, job_id: str) -> ProcessingJob | None:
        return self._session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

    def get_job_by_hash(self, content_hash: str) -> ProcessingJob | None:
        return self._session.query(ProcessingJob).filter(ProcessingJob.content_hash == content_hash).first()

    def create_job(
        self,
        *,
        job_id: str,
        content_hash: str,
        pipeline_version: str,
        payload_json: str,
        status: str = "PENDING",
    ) -> ProcessingJob:
        job = ProcessingJob(
            id=job_id,
            content_hash=content_hash,
            pipeline_version=pipeline_version,
            payload_json=payload_json,
            status=status,
        )
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def save_job(self, job: ProcessingJob) -> ProcessingJob:
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def add_dead_letter(
        self,
        *,
        job_id: str | None,
        content_hash: str,
        payload_json: str,
        error_type: str,
        error_message: str,
        traceback_text: str,
    ) -> DeadLetterQueueEntry:
        entry = DeadLetterQueueEntry(
            job_id=job_id,
            content_hash=content_hash,
            payload_json=payload_json,
            error_type=error_type,
            error_message=error_message,
            traceback_text=traceback_text,
        )
        self._session.add(entry)
        self._session.commit()
        self._session.refresh(entry)
        return entry
