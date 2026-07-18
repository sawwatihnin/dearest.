"""Database schema compatibility helpers."""

from __future__ import annotations

from sqlalchemy import inspect, text

from .session import engine


def ensure_schema() -> None:
    """Apply lightweight compatibility migrations needed by the MVP schema."""
    inspector = inspect(engine)
    if "posts" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("posts")}
    with engine.begin() as connection:
        if "content_type" not in columns:
            connection.execute(
                text("ALTER TABLE posts ADD COLUMN content_type VARCHAR(32) NOT NULL DEFAULT 'community'")
            )
        if "content_hash" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN content_hash VARCHAR(64)"))
        if "ingestion_key" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN ingestion_key VARCHAR(255)"))
        if "title" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN title VARCHAR(255)"))
        if "private_raw_text" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN private_raw_text TEXT"))
        if "attribution_author" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN attribution_author VARCHAR(255)"))
        if "attribution_work" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN attribution_work VARCHAR(255)"))
        if "attribution_year" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN attribution_year VARCHAR(64)"))
        if "attribution_source" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN attribution_source VARCHAR(255)"))
        if "attribution_url" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN attribution_url VARCHAR(500)"))
        if "attribution_rights_status" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN attribution_rights_status VARCHAR(255)"))
        if "attribution_rights_notes" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN attribution_rights_notes TEXT"))
        if "detected_emotions_json" not in columns:
            connection.execute(
                text("ALTER TABLE posts ADD COLUMN detected_emotions_json TEXT NOT NULL DEFAULT '[]'")
            )
        if "emotion_distribution_json" not in columns:
            connection.execute(
                text("ALTER TABLE posts ADD COLUMN emotion_distribution_json TEXT NOT NULL DEFAULT '{}'")
            )
        if "keyword_profile_json" not in columns:
            connection.execute(
                text("ALTER TABLE posts ADD COLUMN keyword_profile_json TEXT NOT NULL DEFAULT '{}'")
            )
        if "semantic_profile_json" not in columns:
            connection.execute(
                text("ALTER TABLE posts ADD COLUMN semantic_profile_json TEXT NOT NULL DEFAULT '{}'")
            )
        if "cluster_label" not in columns:
            connection.execute(text("ALTER TABLE posts ADD COLUMN cluster_label VARCHAR(128)"))
        if "selected_content_notes_json" not in columns:
            connection.execute(
                text("ALTER TABLE posts ADD COLUMN selected_content_notes_json TEXT NOT NULL DEFAULT '[]'")
            )
        if "pipeline_version" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE posts ADD COLUMN pipeline_version VARCHAR(64) NOT NULL "
                    "DEFAULT '2026.07.portfolio-v1'"
                )
            )
        if "processing_trace_json" not in columns:
            connection.execute(
                text("ALTER TABLE posts ADD COLUMN processing_trace_json TEXT NOT NULL DEFAULT '{}'")
            )
    tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        if "processing_jobs" not in tables:
            connection.execute(
                text(
                    "CREATE TABLE processing_jobs ("
                    "id VARCHAR(64) PRIMARY KEY, "
                    "content_hash VARCHAR(64) NOT NULL UNIQUE, "
                    "pipeline_version VARCHAR(64) NOT NULL, "
                    "status VARCHAR(32) NOT NULL DEFAULT 'PENDING', "
                    "payload_json TEXT NOT NULL, "
                    "result_json TEXT, "
                    "post_id INTEGER, "
                    "attempt_count INTEGER NOT NULL DEFAULT 0, "
                    "error_message TEXT, "
                    "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                    "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                    "FOREIGN KEY(post_id) REFERENCES posts (id)"
                    ")"
                )
            )
        if "dead_letter_queue" not in tables:
            connection.execute(
                text(
                    "CREATE TABLE dead_letter_queue ("
                    "id INTEGER PRIMARY KEY, "
                    "job_id VARCHAR(64), "
                    "content_hash VARCHAR(64) NOT NULL, "
                    "payload_json TEXT NOT NULL, "
                    "error_type VARCHAR(255) NOT NULL, "
                    "error_message TEXT NOT NULL, "
                    "traceback_text TEXT NOT NULL, "
                    "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )
