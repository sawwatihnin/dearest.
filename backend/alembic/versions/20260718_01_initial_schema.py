"""initial schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260718_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "posts" not in tables:
        op.create_table(
            "posts",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("content_hash", sa.String(length=64), nullable=True),
            sa.Column("content_type", sa.String(length=32), nullable=False, server_default="community"),
            sa.Column("ingestion_key", sa.String(length=255), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("raw_text", sa.Text(), nullable=False),
            sa.Column("private_raw_text", sa.Text(), nullable=True),
            sa.Column("hidden_subject", sa.String(length=255), nullable=True),
            sa.Column("attribution_author", sa.String(length=255), nullable=True),
            sa.Column("attribution_work", sa.String(length=255), nullable=True),
            sa.Column("attribution_year", sa.String(length=64), nullable=True),
            sa.Column("attribution_source", sa.String(length=255), nullable=True),
            sa.Column("attribution_url", sa.String(length=500), nullable=True),
            sa.Column("attribution_rights_status", sa.String(length=255), nullable=True),
            sa.Column("attribution_rights_notes", sa.Text(), nullable=True),
            sa.Column("selected_mood", sa.String(length=64), nullable=True),
            sa.Column("detected_mood", sa.String(length=64), nullable=False),
            sa.Column("detected_emotions_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("emotion_distribution_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("keywords_json", sa.Text(), nullable=False),
            sa.Column("keyword_profile_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("semantic_profile_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("cluster_label", sa.String(length=128), nullable=True),
            sa.Column("warning_terms_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("selected_content_notes_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("pipeline_version", sa.String(length=64), nullable=False, server_default="2026.07.portfolio-v1"),
            sa.Column("processing_trace_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("embedding_json", sa.Text(), nullable=True),
            sa.Column("embedding_model", sa.String(length=64), nullable=False, server_default="tfidf"),
            sa.Column("embedding_versions_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("pipeline_versions_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_posts_id", "posts", ["id"])
        op.create_index("ix_posts_content_hash", "posts", ["content_hash"])

    if "processing_jobs" not in tables:
        op.create_table(
            "processing_jobs",
            sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("pipeline_version", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
            sa.Column("correlation_id", sa.String(length=64), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("result_json", sa.Text(), nullable=True),
            sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id"), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("terminal_trace_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_processing_jobs_content_hash", "processing_jobs", ["content_hash"], unique=True)
        op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])
        op.create_index("ix_processing_jobs_correlation_id", "processing_jobs", ["correlation_id"])

    if "dead_letter_queue" not in tables:
        op.create_table(
            "dead_letter_queue",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("job_id", sa.String(length=64), nullable=True),
            sa.Column("correlation_id", sa.String(length=64), nullable=True),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("error_type", sa.String(length=255), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=False),
            sa.Column("traceback_text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_dead_letter_queue_id", "dead_letter_queue", ["id"])
        op.create_index("ix_dead_letter_queue_job_id", "dead_letter_queue", ["job_id"])
        op.create_index("ix_dead_letter_queue_correlation_id", "dead_letter_queue", ["correlation_id"])
        op.create_index("ix_dead_letter_queue_content_hash", "dead_letter_queue", ["content_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "dead_letter_queue" in tables:
        op.drop_table("dead_letter_queue")
    if "processing_jobs" in tables:
        op.drop_table("processing_jobs")
    if "posts" in tables:
        op.drop_table("posts")
