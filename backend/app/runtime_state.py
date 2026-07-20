"""Transient stage tracking with Redis fallback."""

from __future__ import annotations

import json
from threading import Lock

from redis import Redis


class TransientStateStore:
    def __init__(self, redis_url: str | None = None) -> None:
        self._memory: dict[str, dict[str, object]] = {}
        self._lock = Lock()
        self._redis = None
        if redis_url:
            try:
                self._redis = Redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

    def set_stage(self, job_id: str, stage: str, metadata: dict[str, object] | None = None) -> None:
        payload = {"stage": stage, "metadata": metadata or {}}
        if self._redis is not None:
            self._redis.setex(f"dearest:job-stage:{job_id}", 3600, json.dumps(payload))
            return
        with self._lock:
            self._memory[job_id] = payload

    def get_stage(self, job_id: str) -> dict[str, object] | None:
        if self._redis is not None:
            raw = self._redis.get(f"dearest:job-stage:{job_id}")
            return json.loads(raw) if raw else None
        with self._lock:
            return self._memory.get(job_id)

    def clear_stage(self, job_id: str) -> None:
        if self._redis is not None:
            self._redis.delete(f"dearest:job-stage:{job_id}")
            return
        with self._lock:
            self._memory.pop(job_id, None)
