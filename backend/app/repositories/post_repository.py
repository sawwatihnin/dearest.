"""Repository layer for post persistence."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Post


class PostRepository:
    """Encapsulates database access for posts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_posts_desc(self) -> list[Post]:
        """Return posts newest-first."""
        return self._session.query(Post).order_by(Post.created_at.desc()).all()

    def list_posts_asc(self) -> list[Post]:
        """Return posts oldest-first."""
        return self._session.query(Post).order_by(Post.created_at.asc()).all()

    def get_post(self, post_id: int) -> Post | None:
        """Return one post by id."""
        return self._session.query(Post).filter(Post.id == post_id).first()

    def all_posts(self) -> list[Post]:
        """Return all posts without ordering requirements."""
        return self._session.query(Post).all()

    def get_post_by_ingestion_key(self, ingestion_key: str) -> Post | None:
        """Return one seeded public archive post by ingestion key."""
        return self._session.query(Post).filter(Post.ingestion_key == ingestion_key).first()

    def create_post(
        self,
        *,
        content_hash: str | None,
        content_type: str,
        ingestion_key: str | None,
        title: str,
        raw_text: str,
        private_raw_text: str | None,
        hidden_subject: str | None,
        attribution_author: str | None,
        attribution_work: str | None,
        attribution_year: str | None,
        attribution_source: str | None,
        attribution_url: str | None,
        attribution_rights_status: str | None,
        attribution_rights_notes: str | None,
        selected_mood: str | None,
        detected_mood: str,
        detected_emotions_json: str,
        emotion_distribution_json: str,
        summary: str,
        keywords_json: str,
        keyword_profile_json: str,
        semantic_profile_json: str,
        cluster_label: str | None,
        warning_terms_json: str,
        selected_content_notes_json: str,
        pipeline_version: str,
        processing_trace_json: str,
        embedding_json: str | None,
        embedding_model: str,
        embedding_versions_json: str = "[]",
        pipeline_versions_json: str = "[]",
    ) -> Post:
        """Persist a new post."""
        post = Post(
            content_hash=content_hash,
            content_type=content_type,
            ingestion_key=ingestion_key,
            title=title,
            raw_text=raw_text,
            private_raw_text=private_raw_text,
            hidden_subject=hidden_subject,
            attribution_author=attribution_author,
            attribution_work=attribution_work,
            attribution_year=attribution_year,
            attribution_source=attribution_source,
            attribution_url=attribution_url,
            attribution_rights_status=attribution_rights_status,
            attribution_rights_notes=attribution_rights_notes,
            selected_mood=selected_mood,
            detected_mood=detected_mood,
            detected_emotions_json=detected_emotions_json,
            emotion_distribution_json=emotion_distribution_json,
            summary=summary,
            keywords_json=keywords_json,
            keyword_profile_json=keyword_profile_json,
            semantic_profile_json=semantic_profile_json,
            cluster_label=cluster_label,
            warning_terms_json=warning_terms_json,
            selected_content_notes_json=selected_content_notes_json,
            pipeline_version=pipeline_version,
            processing_trace_json=processing_trace_json,
            embedding_json=embedding_json,
            embedding_model=embedding_model,
            embedding_versions_json=embedding_versions_json,
            pipeline_versions_json=pipeline_versions_json,
        )
        self._session.add(post)
        self._session.commit()
        self._session.refresh(post)
        return post

    def update_post(
        self,
        post: Post,
        *,
        content_hash: str | None,
        content_type: str,
        ingestion_key: str | None,
        title: str,
        raw_text: str,
        private_raw_text: str | None,
        hidden_subject: str | None,
        attribution_author: str | None,
        attribution_work: str | None,
        attribution_year: str | None,
        attribution_source: str | None,
        attribution_url: str | None,
        attribution_rights_status: str | None,
        attribution_rights_notes: str | None,
        selected_mood: str | None,
        detected_mood: str,
        detected_emotions_json: str,
        emotion_distribution_json: str,
        summary: str,
        keywords_json: str,
        keyword_profile_json: str,
        semantic_profile_json: str,
        cluster_label: str | None,
        warning_terms_json: str,
        selected_content_notes_json: str,
        pipeline_version: str,
        processing_trace_json: str,
        embedding_json: str | None,
        embedding_model: str,
        embedding_versions_json: str = "[]",
        pipeline_versions_json: str = "[]",
    ) -> Post:
        """Update an existing persisted post."""
        post.content_hash = content_hash
        post.content_type = content_type
        post.ingestion_key = ingestion_key
        post.title = title
        post.raw_text = raw_text
        post.private_raw_text = private_raw_text
        post.hidden_subject = hidden_subject
        post.attribution_author = attribution_author
        post.attribution_work = attribution_work
        post.attribution_year = attribution_year
        post.attribution_source = attribution_source
        post.attribution_url = attribution_url
        post.attribution_rights_status = attribution_rights_status
        post.attribution_rights_notes = attribution_rights_notes
        post.selected_mood = selected_mood
        post.detected_mood = detected_mood
        post.detected_emotions_json = detected_emotions_json
        post.emotion_distribution_json = emotion_distribution_json
        post.summary = summary
        post.keywords_json = keywords_json
        post.keyword_profile_json = keyword_profile_json
        post.semantic_profile_json = semantic_profile_json
        post.cluster_label = cluster_label
        post.warning_terms_json = warning_terms_json
        post.selected_content_notes_json = selected_content_notes_json
        post.pipeline_version = pipeline_version
        post.processing_trace_json = processing_trace_json
        post.embedding_json = embedding_json
        post.embedding_model = embedding_model
        post.embedding_versions_json = embedding_versions_json
        post.pipeline_versions_json = pipeline_versions_json
        self._session.add(post)
        self._session.commit()
        self._session.refresh(post)
        return post

    def delete_posts_by_titles(self, titles: list[str]) -> None:
        """Delete known legacy seeded posts by exact title."""
        if not titles:
            return
        self._session.query(Post).filter(Post.title.in_(titles)).delete(synchronize_session=False)
        self._session.commit()

    def delete_all(self) -> None:
        """Delete all posts."""
        self._session.query(Post).delete()
        self._session.commit()
