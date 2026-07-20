"""Post ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Post(Base):
    """Persisted anonymous story post."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False, default="community")
    ingestion_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    private_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    hidden_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attribution_author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attribution_work: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attribution_year: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attribution_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attribution_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attribution_rights_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attribution_rights_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_mood: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detected_mood: Mapped[str] = mapped_column(String(64), nullable=False)
    detected_emotions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    emotion_distribution_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    keywords_json: Mapped[str] = mapped_column(Text, nullable=False)
    keyword_profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    semantic_profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    cluster_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    warning_terms_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    selected_content_notes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    pipeline_version: Mapped[str] = mapped_column(String(64), nullable=False, default="2026.07.portfolio-v1")
    processing_trace_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(64), nullable=False, default="tfidf")
    embedding_versions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    pipeline_versions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
