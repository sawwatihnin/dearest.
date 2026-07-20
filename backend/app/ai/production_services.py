"""Production-oriented service boundaries layered over the existing AI modules."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import math
import re
from time import perf_counter

from .emotion import EmotionAnalyzer
from .vector_store import QdrantLocalVectorStorage, VectorQuery, VectorStorageInterface
from .explainability import ExplainabilityService
from .moderation import ModerationService
from .narrative import NarrativeAnalyzer
from .redaction import RedactionService
from .themes import ThemeExtractor
from .types import (
    ArtifactMetadata,
    EmbeddingResult,
    GroundedExplanation,
    RankedRecommendation,
    RecommendationBundle,
    RetrievalCandidate,
    SemanticProjection,
    ThemeAnalysis,
)
from .embeddings import EmbeddingService
from ..settings import get_settings

PROCESSING_VERSION = "2026.07.async-dual-stage-v1"


def _hash_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()[:16]


class ContentSafetyService:
    """Typed content-safety boundary."""

    def __init__(self, moderation_service: ModerationService) -> None:
        self._moderation_service = moderation_service

    def analyze(self, text: str):
        started = perf_counter()
        result = self._moderation_service.analyze(text)
        result.metadata = ArtifactMetadata(
            processing_version=PROCESSING_VERSION,
            model_version="lexical-moderation-v2",
            latency_ms=round((perf_counter() - started) * 1000, 3),
            confidence=round(max(0.0, 1.0 - result.risk_score), 3),
            status="completed" if result.safe else "blocked",
            input_hash=_hash_text(text),
        )
        return result


class PrivacyService:
    """Typed privacy/redaction boundary."""

    def __init__(self, redaction_service: RedactionService) -> None:
        self._redaction_service = redaction_service

    def sanitize(self, text: str, title: str | None = None):
        started = perf_counter()
        result = self._redaction_service.sanitize_story(text, title=title)
        result.metadata = ArtifactMetadata(
            processing_version=PROCESSING_VERSION,
            model_version=result.model_name,
            latency_ms=round((perf_counter() - started) * 1000, 3),
            confidence=1.0 if result.pii_detected else 0.85,
            input_hash=_hash_text(f"{title or ''}\n{text}"),
        )
        return result

    def pass_through(self, text: str, title: str | None = None):
        started = perf_counter()
        result = self._redaction_service.pass_through_story(text, title=title)
        result.metadata = ArtifactMetadata(
            processing_version=PROCESSING_VERSION,
            model_version=result.model_name,
            latency_ms=round((perf_counter() - started) * 1000, 3),
            confidence=1.0,
            input_hash=_hash_text(f"{title or ''}\n{text}"),
        )
        return result


class EnrichmentService:
    """Typed enrichment boundary for summary, emotion, themes, and semantic profile."""

    def __init__(
        self,
        narrative_analyzer: NarrativeAnalyzer,
        emotion_analyzer: EmotionAnalyzer,
        theme_extractor: ThemeExtractor,
        explainability_service: ExplainabilityService,
        embedding_service: EmbeddingService,
    ) -> None:
        self._narrative_analyzer = narrative_analyzer
        self._emotion_analyzer = emotion_analyzer
        self._theme_extractor = theme_extractor
        self._explainability_service = explainability_service
        self._embedding_service = embedding_service

    def enrich(
        self,
        *,
        text: str,
        selected_mood: str | None,
        embedding: EmbeddingResult,
    ) -> tuple[object, object, ThemeAnalysis, SemanticProjection, ArtifactMetadata]:
        started = perf_counter()
        narrative = self._narrative_analyzer.analyze(text)
        emotion = self._emotion_analyzer.analyze(text, selected_mood=selected_mood)
        themes = self._theme_extractor.analyze(text)
        projection = self._explainability_service.project_story(
            text=text,
            embedding=embedding,
            emotion=emotion,
            themes=themes,
        )
        metadata = ArtifactMetadata(
            processing_version=PROCESSING_VERSION,
            model_version="narrative-emotion-theme-stack-v1",
            latency_ms=round((perf_counter() - started) * 1000, 3),
            confidence=round((emotion.confidence + min(len(themes.keywords), 5) / 5) / 2, 3),
            input_hash=_hash_text(text),
        )
        return narrative, emotion, themes, projection, metadata


class RetrievalService:
    """Hybrid candidate retrieval using existing embeddings plus lightweight semantic priors."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_storage: VectorStorageInterface | None = None,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_storage = vector_storage or QdrantLocalVectorStorage(
            embedding_service,
            get_settings().qdrant_path,
        )

    def retrieve(
        self,
        *,
        source_post: dict[str, object],
        candidate_posts: list[dict[str, object]],
        limit: int = 50,
        avoid_theme: str | None = None,
        avoid_content_note: str | None = None,
    ) -> list[RetrievalCandidate]:
        started = perf_counter()
        dense_ranked = self._vector_storage.query(
            VectorQuery(
                source_post=source_post,
                candidate_posts=candidate_posts,
                limit=limit,
                exclude_post_id=int(source_post["id"]) if "id" in source_post else None,
                avoid_theme=avoid_theme,
                avoid_content_note=avoid_content_note,
            )
        )
        post_lookup = {int(post["id"]): post for post in candidate_posts}
        candidates: list[RetrievalCandidate] = []
        source_emotions = set(self._deserialize_list(source_post.get("detected_emotions_json")))
        source_themes = set(self._deserialize_profile_keys(source_post.get("semantic_profile_json")))
        source_year = self._timeline_year(source_post)

        for post_id, dense_score in dense_ranked[:limit]:
            candidate = post_lookup.get(post_id)
            if candidate is None:
                continue
            candidate_emotions = set(self._deserialize_list(candidate.get("detected_emotions_json")))
            candidate_themes = set(self._deserialize_profile_keys(candidate.get("semantic_profile_json")))
            emotion_score = self._jaccard(source_emotions, candidate_emotions)
            theme_score = self._jaccard(source_themes, candidate_themes)
            narrative_score = self._narrative_overlap(
                str(source_post.get("summary") or source_post.get("raw_text") or ""),
                str(candidate.get("summary") or candidate.get("raw_text") or ""),
            )
            temporal_score = self._temporal_similarity(source_year, self._timeline_year(candidate))
            quality_score = self._quality_score(candidate)
            hybrid_score = round(
                dense_score * 0.52
                + emotion_score * 0.12
                + theme_score * 0.16
                + narrative_score * 0.14
                + temporal_score * 0.03
                + quality_score * 0.03,
                3,
            )
            candidates.append(
                RetrievalCandidate(
                    post_id=post_id,
                    score=hybrid_score,
                    dense_score=round(dense_score, 3),
                    emotion_score=round(emotion_score, 3),
                    theme_score=round(theme_score, 3),
                    temporal_score=round(temporal_score, 3),
                    narrative_score=round(narrative_score, 3),
                    quality_score=round(quality_score, 3),
                    content_type=str(candidate.get("content_type") or "community"),
                    metadata=ArtifactMetadata(
                        processing_version=PROCESSING_VERSION,
                        model_version=str(source_post.get("embedding_model") or "tfidf"),
                        latency_ms=0.0,
                        confidence=round(max(hybrid_score, dense_score), 3),
                        input_hash=_hash_text(f"{source_post.get('id')}::{post_id}"),
                    ),
                )
            )

        elapsed = round((perf_counter() - started) * 1000, 3)
        per_candidate = round(elapsed / max(len(candidates), 1), 3)
        for candidate in candidates:
            candidate.metadata.latency_ms = per_candidate
        return candidates

    def sync_candidates(self, candidate_posts: list[dict[str, object]]) -> int:
        return self._vector_storage.upsert_posts(candidate_posts)

    def _deserialize_list(self, payload: object) -> list[str]:
        if not payload:
            return []
        return self._embedding_service.deserialize_json(str(payload), default=[])  # type: ignore[arg-type]

    def _deserialize_profile_keys(self, payload: object) -> list[str]:
        if not payload:
            return []
        parsed = self._embedding_service.deserialize_json(str(payload), default={})  # type: ignore[arg-type]
        if not isinstance(parsed, dict):
            return []
        return [str(key) for key, value in parsed.items() if float(value) > 0]

    def _timeline_year(self, post: dict[str, object]) -> int | None:
        raw = post.get("timeline_year")
        if isinstance(raw, int):
            return raw
        created = str(post.get("created_at") or "")
        if len(created) >= 4 and created[:4].isdigit():
            return int(created[:4])
        return None

    def _jaccard(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    def _opening_overlap(self, left: str, right: str) -> float:
        left_tokens = {token.lower() for token in left.split()[:12]}
        right_tokens = {token.lower() for token in right.split()[:12]}
        return self._jaccard(left_tokens, right_tokens)

    def _narrative_overlap(self, left: str, right: str) -> float:
        opening = self._opening_overlap(left, right)
        left_keywords = set(self._meaningful_tokens(left))
        right_keywords = set(self._meaningful_tokens(right))
        lexical = self._jaccard(left_keywords, right_keywords)
        return max(opening, lexical)

    def _temporal_similarity(self, left_year: int | None, right_year: int | None) -> float:
        if left_year is None or right_year is None:
            return 0.0
        return max(0.0, 1.0 - min(abs(left_year - right_year), 150) / 150)

    def _quality_score(self, candidate: dict[str, object]) -> float:
        summary = str(candidate.get("summary") or "")
        keywords = self._deserialize_list(candidate.get("keywords_json"))
        return min(1.0, (len(summary.split()) / 24 + len(keywords) / 5) / 2)

    def _meaningful_tokens(self, text: str) -> list[str]:
        stopwords = {
            "about",
            "after",
            "again",
            "against",
            "because",
            "before",
            "being",
            "could",
            "every",
            "still",
            "there",
            "their",
            "these",
            "those",
            "through",
            "which",
            "would",
            "while",
            "where",
            "when",
            "with",
            "from",
            "into",
            "your",
            "ours",
            "they",
            "them",
            "than",
            "that",
            "have",
            "what",
            "know",
            "like",
            "just",
            "were",
            "been",
            "will",
            "said",
            "says",
            "once",
            "here",
            "only",
        }
        tokens = [token for token in re.findall(r"[a-zA-Z']+", text.lower()) if len(token) > 3]
        return [token for token in tokens if token not in stopwords][:18]


class RankingService:
    """Rerank retrieved candidates with diversity pressure and honest confidence labels."""

    def __init__(self) -> None:
        self._cross_encoder = self._load_cross_encoder()

    def rank(
        self,
        *,
        source_post: dict[str, object],
        candidates: list[RetrievalCandidate],
        candidate_posts: dict[int, dict[str, object]],
        top_k: int = 5,
    ) -> list[RankedRecommendation]:
        scored_candidates = self._apply_cross_encoder(source_post, candidates, candidate_posts)
        selected: list[RankedRecommendation] = []
        seen_types: set[str] = set()
        chosen_vectors: list[tuple[set[str], set[str]]] = []
        for candidate, calibrated_score in scored_candidates:
            post = candidate_posts.get(candidate.post_id)
            if post is None:
                continue
            candidate_themes = set(self._deserialize_profile_keys(post.get("semantic_profile_json")))
            candidate_emotions = set(self._deserialize_list(post.get("detected_emotions_json")))
            diversity_penalty = 0.0
            if len(selected) >= 2:
                diversity_penalty = self._mmr_penalty(candidate_themes, candidate_emotions, chosen_vectors)
            if top_k <= 5 and candidate.content_type in seen_types:
                diversity_penalty += 0.01
            blended_score = calibrated_score * 0.78 + candidate.score * 0.22
            final_score = round(max(blended_score - diversity_penalty, 0.0), 3)
            excerpt = self._supporting_excerpt(str(post.get("raw_text") or ""))
            ranked = RankedRecommendation(
                post_id=candidate.post_id,
                score=final_score,
                confidence_label=self._confidence_label(final_score),
                supporting_excerpt=excerpt,
                shared_themes=[],
                shared_emotions=[],
                shared_keywords=[],
                metadata=ArtifactMetadata(
                    processing_version=PROCESSING_VERSION,
                    model_version="hybrid-ranker-v1",
                    latency_ms=0.0,
                    confidence=final_score,
                    input_hash=_hash_text(f"rank::{candidate.post_id}::{final_score}"),
                ),
            )
            selected.append(ranked)
            seen_types.add(candidate.content_type)
            chosen_vectors.append((candidate_themes, candidate_emotions))
            if len(selected) >= top_k:
                break
        return selected

    def _apply_cross_encoder(
        self,
        source_post: dict[str, object],
        candidates: list[RetrievalCandidate],
        candidate_posts: dict[int, dict[str, object]],
    ) -> list[tuple[RetrievalCandidate, float]]:
        pairs: list[tuple[RetrievalCandidate, float]] = []
        for candidate in candidates:
            post = candidate_posts.get(candidate.post_id)
            if post is None:
                continue
            raw_logit = self._cross_encoder_score(str(source_post.get("raw_text") or ""), candidate, post)
            calibrated = self._platt_scale(raw_logit)
            pairs.append((candidate, calibrated))
        pairs.sort(key=lambda item: item[1], reverse=True)
        return pairs

    def _cross_encoder_score(self, query_text: str, candidate: RetrievalCandidate, post: dict[str, object]) -> float:
        if self._cross_encoder is not None:
            body = str(post.get("raw_text") or "")
            try:
                return float(self._cross_encoder.predict([(query_text, body)])[0])
            except Exception:
                pass
        lexical_boost = candidate.theme_score * 0.9 + candidate.emotion_score * 0.7 + candidate.narrative_score * 0.6
        return candidate.score * 2.4 + lexical_boost

    def _platt_scale(self, logit: float) -> float:
        return round(1.0 / (1.0 + math.exp(-logit)), 3)

    def _mmr_penalty(
        self,
        candidate_themes: set[str],
        candidate_emotions: set[str],
        chosen_vectors: list[tuple[set[str], set[str]]],
    ) -> float:
        if not chosen_vectors:
            return 0.0
        max_overlap = 0.0
        for chosen_themes, chosen_emotions in chosen_vectors:
            theme_overlap = self._jaccard(candidate_themes, chosen_themes)
            emotion_overlap = self._jaccard(candidate_emotions, chosen_emotions)
            max_overlap = max(max_overlap, theme_overlap * 0.65 + emotion_overlap * 0.35)
        return round(max_overlap * 0.06, 3)

    def _confidence_label(self, score: float) -> str:
        if score >= 0.8:
            return "Strong Echo"
        if score >= 0.62:
            return "Meaningful Connection"
        if score >= 0.45:
            return "Distant Resonance"
        return "No Close Match"

    def _supporting_excerpt(self, text: str) -> str:
        sentences = [segment.strip() for segment in text.replace("\n", " ").split(".") if segment.strip()]
        if not sentences:
            return text[:180].strip()
        return f"{sentences[0][:180].strip()}."

    def _deserialize_list(self, payload: object) -> list[str]:
        if not payload:
            return []
        return EmbeddingService.deserialize_json(str(payload), default=[])  # type: ignore[arg-type]

    def _deserialize_profile_keys(self, payload: object) -> list[str]:
        if not payload:
            return []
        parsed = EmbeddingService.deserialize_json(str(payload), default={})  # type: ignore[arg-type]
        if not isinstance(parsed, dict):
            return []
        return [str(key) for key, value in parsed.items() if float(value) > 0]

    def _jaccard(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    def _load_cross_encoder(self):
        try:
            from sentence_transformers import CrossEncoder

            return CrossEncoder("BAAI/bge-reranker-large")
        except Exception:
            return None


class ExplanationService:
    """Generate grounded natural-language explanations from shared metadata."""

    def explain(
        self,
        *,
        source_post: dict[str, object],
        matched_post: dict[str, object],
        recommendation: RankedRecommendation,
    ) -> GroundedExplanation:
        started = perf_counter()
        source_themes = self._top_profile_keys(source_post.get("semantic_profile_json"))
        matched_themes = self._top_profile_keys(matched_post.get("semantic_profile_json"))
        shared_themes = [theme for theme in source_themes if theme in matched_themes][:3]
        source_emotions = self._deserialize_list(source_post.get("detected_emotions_json"))
        matched_emotions = self._deserialize_list(matched_post.get("detected_emotions_json"))
        shared_emotions = [emotion for emotion in source_emotions if emotion in matched_emotions][:3]
        source_keywords = self._deserialize_list(source_post.get("keywords_json"))
        matched_keywords = self._deserialize_list(matched_post.get("keywords_json"))
        shared_keywords = [keyword for keyword in source_keywords if keyword in matched_keywords][:4]

        parts: list[str] = []
        if shared_themes:
            parts.append(f"themes of {', '.join(shared_themes)}")
        if shared_emotions:
            parts.append(f"emotions like {', '.join(shared_emotions)}")
        if shared_keywords:
            parts.append(f"language around {', '.join(shared_keywords[:2])}")
        explanation = (
            f"Both pieces echo through {' and '.join(parts)}."
            if parts
            else f"These writings sit nearby in Dearest's archive, though the resonance is {recommendation.confidence_label.lower()}."
        )
        recommendation.shared_themes = shared_themes
        recommendation.shared_emotions = shared_emotions
        recommendation.shared_keywords = shared_keywords
        return GroundedExplanation(
            narrative_explanation=explanation,
            supporting_excerpt=recommendation.supporting_excerpt,
            metadata=ArtifactMetadata(
                processing_version=PROCESSING_VERSION,
                model_version="grounded-explanation-v1",
                latency_ms=round((perf_counter() - started) * 1000, 3),
                confidence=recommendation.score,
                input_hash=_hash_text(f"explain::{source_post.get('id')}::{matched_post.get('id')}"),
            ),
        )

    def _deserialize_list(self, payload: object) -> list[str]:
        if not payload:
            return []
        return EmbeddingService.deserialize_json(str(payload), default=[])  # type: ignore[arg-type]

    def _top_profile_keys(self, payload: object) -> list[str]:
        if not payload:
            return []
        parsed = EmbeddingService.deserialize_json(str(payload), default={})  # type: ignore[arg-type]
        if not isinstance(parsed, dict):
            return []
        return [
            str(key)
            for key, value in sorted(parsed.items(), key=lambda item: float(item[1]), reverse=True)[:5]
            if float(value) > 0
        ]


class RecommendationServiceV2:
    """Compose retrieval, ranking, and explanation into a typed bundle."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        ranking_service: RankingService,
        explanation_service: ExplanationService,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._ranking_service = ranking_service
        self._explanation_service = explanation_service

    def build_bundle(
        self,
        *,
        source_post: dict[str, object],
        candidate_posts: list[dict[str, object]],
        top_k: int = 5,
        avoid_theme: str | None = None,
        avoid_content_note: str | None = None,
    ) -> RecommendationBundle:
        started = perf_counter()
        self._retrieval_service.sync_candidates(candidate_posts)
        candidates = self._retrieval_service.retrieve(
            source_post=source_post,
            candidate_posts=candidate_posts,
            limit=50,
            avoid_theme=avoid_theme,
            avoid_content_note=avoid_content_note,
        )
        lookup = {int(post["id"]): post for post in candidate_posts}
        recommendations = self._ranking_service.rank(
            source_post=source_post,
            candidates=candidates,
            candidate_posts=lookup,
            top_k=top_k,
        )
        explanations = {
            recommendation.post_id: self._explanation_service.explain(
                source_post=source_post,
                matched_post=lookup[recommendation.post_id],
                recommendation=recommendation,
            )
            for recommendation in recommendations
            if recommendation.post_id in lookup
        }
        return RecommendationBundle(
            candidates=candidates,
            recommendations=recommendations,
            explanations=explanations,
            metadata=ArtifactMetadata(
                processing_version=PROCESSING_VERSION,
                model_version="recommendation-bundle-v1",
                latency_ms=round((perf_counter() - started) * 1000, 3),
                confidence=round(
                    sum(recommendation.score for recommendation in recommendations) / max(len(recommendations), 1),
                    3,
                ),
                input_hash=_hash_text(f"bundle::{source_post.get('id')}"),
            ),
        )


class EvaluationService:
    """Small in-process evaluation helpers for operational visibility."""

    def summarize_bundle(self, bundle: RecommendationBundle) -> dict[str, object]:
        return {
            "processing_version": PROCESSING_VERSION,
            "candidate_count": len(bundle.candidates),
            "recommendation_count": len(bundle.recommendations),
            "average_score": round(
                sum(item.score for item in bundle.recommendations) / max(len(bundle.recommendations), 1),
                3,
            ),
            "confidence_labels": [item.confidence_label for item in bundle.recommendations],
            "metadata": asdict(bundle.metadata),
        }
