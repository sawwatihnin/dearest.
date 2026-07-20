"""Application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_QDRANT_PATH = str((BACKEND_DIR / "qdrant").resolve())


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings for privacy-sensitive backend behavior."""

    admin_debug_mode: bool = False
    pipeline_trace_mode: bool = False
    pipeline_version: str = "2026.07.async-dual-stage-v1"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_always_eager: bool = False
    redis_state_url: str = "redis://localhost:6379/2"
    vector_backend: str = "local"
    qdrant_path: str = DEFAULT_QDRANT_PATH
    admin_token: str = "dearest-dev-admin"
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load process settings once."""
    cors_origins = tuple(
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "DEAREST_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    )
    return Settings(
        admin_debug_mode=_as_bool(os.getenv("DEAREST_ADMIN_DEBUG_MODE"), default=False),
        pipeline_trace_mode=_as_bool(os.getenv("DEAREST_PIPELINE_TRACE_MODE"), default=False),
        pipeline_version=os.getenv("DEAREST_PIPELINE_VERSION", "2026.07.async-dual-stage-v1"),
        celery_broker_url=os.getenv("DEAREST_CELERY_BROKER_URL", "redis://localhost:6379/0"),
        celery_result_backend=os.getenv("DEAREST_CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
        celery_task_always_eager=_as_bool(os.getenv("DEAREST_CELERY_TASK_ALWAYS_EAGER"), default=True),
        redis_state_url=os.getenv("DEAREST_REDIS_STATE_URL", "redis://localhost:6379/2"),
        vector_backend=os.getenv("DEAREST_VECTOR_BACKEND", "local").strip().lower(),
        qdrant_path=os.getenv("DEAREST_QDRANT_PATH", DEFAULT_QDRANT_PATH),
        admin_token=os.getenv("DEAREST_ADMIN_TOKEN", "dearest-dev-admin"),
        rate_limit_requests=int(os.getenv("DEAREST_RATE_LIMIT_REQUESTS", "30")),
        rate_limit_window_seconds=int(os.getenv("DEAREST_RATE_LIMIT_WINDOW_SECONDS", "60")),
        cors_origins=cors_origins,
    )
