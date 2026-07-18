"""Application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load process settings once."""
    return Settings(
        admin_debug_mode=_as_bool(os.getenv("DEAREST_ADMIN_DEBUG_MODE"), default=False),
        pipeline_trace_mode=_as_bool(os.getenv("DEAREST_PIPELINE_TRACE_MODE"), default=False),
        pipeline_version=os.getenv("DEAREST_PIPELINE_VERSION", "2026.07.async-dual-stage-v1"),
        celery_broker_url=os.getenv("DEAREST_CELERY_BROKER_URL", "redis://localhost:6379/0"),
        celery_result_backend=os.getenv("DEAREST_CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
        celery_task_always_eager=_as_bool(os.getenv("DEAREST_CELERY_TASK_ALWAYS_EAGER"), default=True),
    )
