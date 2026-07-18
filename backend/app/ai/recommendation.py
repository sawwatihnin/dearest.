"""Recommendation service."""

from __future__ import annotations

from .embeddings import EmbeddingService
from .types import RecommendationResult


class RecommendationService:
    """Ranks similar posts using the current cosine similarity implementation."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    def prepare(self) -> RecommendationResult:
        """Prepare a recommendation placeholder during story processing."""
        return RecommendationResult()

    def find_similar_posts(
        self,
        source_post: dict[str, object],
        posts: list[dict[str, object]],
        limit: int = 5,
    ) -> RecommendationResult:
        """Find similar posts from a persisted corpus."""
        ranked = self.rank_posts(source_post, posts)
        limited = ranked[:limit]
        return RecommendationResult(
            similar_post_ids=[post_id for post_id, _ in limited],
            scores={post_id: round(score, 3) for post_id, score in limited},
        )

    def rank_posts(
        self,
        source_post: dict[str, object],
        posts: list[dict[str, object]],
    ) -> list[tuple[int, float]]:
        """Rank posts by similarity score."""
        return self._embedding_service.calculate_similarity(source_post, posts)
