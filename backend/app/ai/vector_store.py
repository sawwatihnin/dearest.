"""Vector storage abstraction for retrieval backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .embeddings import EmbeddingService


@dataclass(slots=True)
class VectorQuery:
    source_post: dict[str, object]
    candidate_posts: list[dict[str, object]]
    limit: int = 50
    exclude_post_id: int | None = None
    avoid_theme: str | None = None
    avoid_content_note: str | None = None


class VectorStorageInterface(Protocol):
    def query(self, request: VectorQuery) -> list[tuple[int, float]]: ...


class LocalVectorStorage:
    """Local vector storage with payload-style filtering before scoring."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    def query(self, request: VectorQuery) -> list[tuple[int, float]]:
        filtered: list[dict[str, object]] = []
        for candidate in request.candidate_posts:
            candidate_id = int(candidate["id"])
            if request.exclude_post_id is not None and candidate_id == request.exclude_post_id:
                continue
            if request.avoid_theme and self._has_theme(candidate, request.avoid_theme):
                continue
            if request.avoid_content_note and self._has_content_note(candidate, request.avoid_content_note):
                continue
            filtered.append(candidate)
        source_bundle = request.source_post
        search_space = [source_bundle, *filtered]
        ranked = self._embedding_service.calculate_similarity(source_bundle, search_space)
        return ranked[: request.limit]

    def _has_theme(self, candidate: dict[str, object], theme: str) -> bool:
        themes = EmbeddingService.deserialize_json(str(candidate.get("semantic_profile_json") or "{}"), default={})
        return isinstance(themes, dict) and theme in themes and float(themes[theme]) > 0

    def _has_content_note(self, candidate: dict[str, object], note: str) -> bool:
        notes = EmbeddingService.deserialize_json(
            str(candidate.get("selected_content_notes_json") or "[]"),
            default=[],
        )
        return isinstance(notes, list) and note in {str(item) for item in notes}
