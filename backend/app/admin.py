"""Admin-only evolutionary maintenance helpers."""

from __future__ import annotations

import json

from .database import SessionLocal
from .repositories import JobRepository, PostRepository
from .api.deps import build_services


def replay_dead_letter_entry(entry_id: int) -> dict[str, object]:
    with SessionLocal() as db:
        jobs = JobRepository(db)
        entry = jobs.get_dead_letter(entry_id)
        if entry is None:
            raise ValueError(f"Dead letter entry {entry_id} not found")
        services = build_services(db)
        processing_service = services["processing_service"]
        payload = json.loads(entry.payload_json)
        status_code, response = processing_service.submit_post_from_payload(payload, correlation_id=entry.correlation_id)
        return {"status_code": status_code, "job_id": response.job_id, "status": response.status}


def reindex_embeddings(delta_only: bool = True) -> dict[str, int]:
    with SessionLocal() as db:
        posts = PostRepository(db).all_posts()
        services = build_services(db)
        post_service = services["post_service"]
        reindexed = 0
        skipped = 0
        for post in posts:
            versions = set(json.loads(post.embedding_versions_json or "[]"))
            current_version = post.pipeline_version
            if delta_only and current_version in versions:
                skipped += 1
                continue
            post_service.reindex_post(post.id)
            reindexed += 1
        return {"reindexed": reindexed, "skipped": skipped}
