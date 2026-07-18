"""Explainable semantic projection layered beside retrieval."""

from __future__ import annotations

import math

import numpy as np

from .embeddings import EmbeddingService
from .ontology import SEMANTIC_ONTOLOGY
from .types import EmbeddingResult, EmotionProfile, MatchExplanation, SemanticProjection, ThemeAnalysis

MOTIF_EMOJIS = {
    "night": "🌙",
    "train": "🚆",
    "station": "🚆",
    "home": "🏠",
    "house": "🏠",
    "room": "🛋️",
    "window": "🪟",
    "rain": "🌧",
    "storm": "⛈️",
    "light": "🕯️",
    "letter": "💌",
    "story": "📖",
    "memory": "🕰️",
    "phone": "☎️",
    "coffee": "☕",
    "summer": "☀️",
    "sea": "🌊",
    "city": "🌃",
}


class ExplainabilityService:
    """Builds human-readable semantic profiles without affecting retrieval."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        ontology: dict[str, list[str]] | None = None,
    ) -> None:
        self._embedding_service = embedding_service
        self._ontology = ontology or SEMANTIC_ONTOLOGY

    def project_story(
        self,
        *,
        text: str,
        embedding: EmbeddingResult,
        emotion: EmotionProfile,
        themes: ThemeAnalysis,
    ) -> SemanticProjection:
        """Project a story into an interpretable semantic profile."""
        semantic_profile = self._build_semantic_profile(text=text, embedding=embedding)
        emotion_distribution = self._normalize_scores(
            {label: float(score) for label, score in emotion.emotion_scores.items() if score > 0}
        )
        keyword_profile = self._normalize_keyword_profile(themes.keyword_scores)
        top_motifs = self.build_motifs(themes.keywords)
        cluster = self._derive_cluster(semantic_profile)
        return SemanticProjection(
            semantic_profile=semantic_profile,
            emotion_distribution=emotion_distribution,
            keyword_profile=keyword_profile,
            top_motifs=top_motifs,
            cluster=cluster,
        )

    def explain_match(
        self,
        *,
        source_profile: SemanticProjection,
        matched_profile: SemanticProjection,
        embedding_similarity: float,
    ) -> MatchExplanation:
        """Explain why two stories matched without changing ranking."""
        shared_concepts = self._shared_concepts(
            source_profile.semantic_profile,
            matched_profile.semantic_profile,
        )
        return MatchExplanation(
            embedding_similarity=round(embedding_similarity, 3),
            shared_concepts=shared_concepts,
            top_motifs=matched_profile.top_motifs,
            matched_story_profile=matched_profile.semantic_profile,
        )

    def _build_semantic_profile(
        self,
        *,
        text: str,
        embedding: EmbeddingResult,
    ) -> dict[str, float]:
        concept_names = list(self._ontology.keys())
        concept_examples = [self._ontology[name] for name in concept_names]

        if embedding.vector is not None and embedding.embedding_model == "sentence-transformers":
            story_vector = np.array(embedding.vector, dtype=float)
            concept_matrix = self._concept_centroids_with_sentence_vectors(concept_examples)
        else:
            story_vector, concept_matrix = self._tfidf_projection(text=text, concept_examples=concept_examples)

        raw_scores = {
            concept_name: self._cosine_similarity(story_vector, concept_matrix[index])
            for index, concept_name in enumerate(concept_names)
        }
        return self._normalize_scores(raw_scores)

    def _concept_centroids_with_sentence_vectors(
        self,
        concept_examples: list[list[str]],
    ) -> np.ndarray:
        flat_examples = [example for examples in concept_examples for example in examples]
        matrix = self._embedding_service.encode_texts(flat_examples)
        centroids: list[np.ndarray] = []
        cursor = 0
        for examples in concept_examples:
            count = len(examples)
            concept_vectors = matrix[cursor : cursor + count]
            centroids.append(np.mean(concept_vectors, axis=0))
            cursor += count
        return np.vstack(centroids)

    def _tfidf_projection(
        self,
        *,
        text: str,
        concept_examples: list[list[str]],
    ) -> tuple[np.ndarray, np.ndarray]:
        concept_documents = [" ".join(examples) for examples in concept_examples]
        matrix = self._embedding_service.encode_texts([text, *concept_documents])
        return matrix[0], matrix[1:]

    def _normalize_scores(self, values: dict[str, float]) -> dict[str, float]:
        if not values:
            return {}
        scores = list(values.values())
        min_score = min(scores)
        max_score = max(scores)
        if math.isclose(min_score, max_score):
            return {label: 0.5 for label in values}
        return {
            label: round((score - min_score) / (max_score - min_score), 3)
            for label, score in values.items()
        }

    def _normalize_keyword_profile(self, values: dict[str, float]) -> dict[str, float]:
        if not values:
            return {}
        max_score = max(values.values())
        if max_score <= 0:
            return {label: 0.0 for label in values}
        return {label: round(score / max_score, 3) for label, score in values.items()}

    def _derive_cluster(self, semantic_profile: dict[str, float]) -> str | None:
        if not semantic_profile:
            return None
        return max(semantic_profile, key=semantic_profile.get)

    def _shared_concepts(
        self,
        source_profile: dict[str, float],
        matched_profile: dict[str, float],
        limit: int = 5,
    ) -> list[str]:
        shared = [
            (concept, min(source_profile.get(concept, 0.0), matched_profile.get(concept, 0.0)))
            for concept in source_profile
            if concept in matched_profile
        ]
        shared.sort(key=lambda item: item[1], reverse=True)
        return [concept for concept, score in shared[:limit] if score > 0]

    def build_motifs(self, keywords: list[str], limit: int = 5) -> list[str]:
        motifs: list[str] = []
        for keyword in keywords:
            emoji = MOTIF_EMOJIS.get(keyword.lower(), "✦")
            motifs.append(f"{emoji} {keyword.title()}")
            if len(motifs) >= limit:
                break
        return motifs

    def _cosine_similarity(self, left: np.ndarray, right: np.ndarray) -> float:
        left_norm = np.linalg.norm(left)
        right_norm = np.linalg.norm(right)
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return float(np.dot(left, right) / (left_norm * right_norm))
