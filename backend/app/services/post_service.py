"""Application service layer for posts."""

from __future__ import annotations

from dataclasses import asdict
import logging
import re

from ..ai import RedactionItem
from ..ai import (
    EmbeddingService,
    EmotionAnalyzer,
    EvaluationService,
    ExplainabilityService,
    RecommendationService,
    RecommendationServiceV2,
    StoryProcessingPipeline,
)
from ..models import Post
from ..media_catalog import MEDIA_CATALOG, MediaItem
from ..repositories import PostRepository
from ..schemas import (
    ArchiveExplorerResponse,
    ArchiveFilterOptions,
    EchoStep,
    EchoesResponse,
    MediaRecommendation,
    ProcessingMetadata,
    ProcessingStage,
    PostCreate,
    PostCreateResponse,
    PostSummary,
    SimilarPost,
    SimilarPostsResponse,
)
from ..settings import get_settings
from ..telemetry import registry

logger = logging.getLogger(__name__)

CONTENT_NOTE_OPTIONS = (
    "abuse",
    "war",
    "violence",
    "grief",
    "illness",
    "heartbreak",
    "identity",
    "trauma",
    "discrimination",
    "self-harm",
)

EDITORIAL_COLLECTIONS: dict[str, dict[str, set[str]]] = {
    "Letters Never Sent": {"themes": {"distance", "regret", "attachment"}, "emotions": {"longing", "heartbreak"}},
    "On Grief": {"themes": {"loss", "memory", "family"}, "emotions": {"grief", "nostalgia"}},
    "Learning to Let Go": {"themes": {"healing", "acceptance", "change"}, "emotions": {"healing", "confusion"}},
    "Finding Home": {"themes": {"home", "belonging", "connection"}, "emotions": {"love", "healing"}},
    "First Love": {"themes": {"attachment", "hope", "memory"}, "emotions": {"love", "nostalgia"}},
    "Growing Older": {"themes": {"future", "past", "identity"}, "emotions": {"nostalgia", "confusion"}},
    "Identity": {"themes": {"identity", "acceptance", "isolation"}, "emotions": {"confusion", "healing"}},
    "Distance": {"themes": {"distance", "home", "future"}, "emotions": {"longing", "heartbreak"}},
    "Hope": {"themes": {"hope", "growth", "future"}, "emotions": {"love", "healing"}},
    "Belonging": {"themes": {"belonging", "connection", "family"}, "emotions": {"love", "nostalgia"}},
}


class PostService:
    """Coordinates repositories and AI pipeline for post operations."""

    def __init__(
        self,
        repository: PostRepository,
        pipeline: StoryProcessingPipeline,
        embedding_service: EmbeddingService,
        emotion_analyzer: EmotionAnalyzer,
        explainability_service: ExplainabilityService,
        recommendation_service: RecommendationService,
        recommendation_service_v2: RecommendationServiceV2,
        evaluation_service: EvaluationService,
    ) -> None:
        self._repository = repository
        self._pipeline = pipeline
        self._embedding_service = embedding_service
        self._emotion_analyzer = emotion_analyzer
        self._explainability_service = explainability_service
        self._recommendation_service = recommendation_service
        self._recommendation_service_v2 = recommendation_service_v2
        self._evaluation_service = evaluation_service

    def list_posts(self) -> list[PostSummary]:
        """Return all posts for the API."""
        return [self._to_summary(post) for post in self._repository.list_posts_desc()]

    def get_post(self, post_id: int) -> PostSummary | None:
        """Return one post summary for the API."""
        post = self._repository.get_post(post_id)
        return self._to_summary(post) if post is not None else None

    def list_archive_explorer_posts(
        self,
        *,
        theme: str | None = None,
        emotion: str | None = None,
        tone: str | None = None,
        author: str | None = None,
        year: str | None = None,
        content_type: str | None = None,
        collection: str | None = None,
        content_note: str | None = None,
        avoid_theme: str | None = None,
        avoid_content_note: str | None = None,
        sort: str = "newest",
        semantic_to_post_id: int | None = None,
    ) -> ArchiveExplorerResponse:
        posts = [self._to_summary(post) for post in self._repository.list_posts_desc()]
        filtered = [
            post
            for post in posts
            if self._matches_filters(
                post,
                theme=theme,
                emotion=emotion,
                tone=tone,
                author=author,
                year=year,
                content_type=content_type,
                collection=collection,
                content_note=content_note,
                avoid_theme=avoid_theme,
                avoid_content_note=avoid_content_note,
            )
        ]
        sorted_posts = self._sort_explorer_posts(filtered, posts, sort=sort, semantic_to_post_id=semantic_to_post_id)
        return ArchiveExplorerResponse(posts=sorted_posts, filters=self._build_archive_filters(posts))

    def create_post(self, payload: PostCreate, content_hash: str | None = None) -> PostCreateResponse:
        """Process and persist a new story while preserving current API behavior."""
        analysis = self._pipeline.process_story(payload.text, selected_mood=payload.mood)
        detected_emotions = self._emotion_analyzer.top_emotions(analysis.emotion, payload.mood)
        settings = get_settings()
        sanitized_about = self._pipeline.sanitize_text(payload.about) if payload.about else None
        selected_content_notes = self._normalize_content_notes(payload.content_notes)
        suggested_content_notes = self._suggest_content_notes(
            text=analysis.redaction.redacted_text,
            warning_terms=analysis.moderation.flags,
            detected_mood=analysis.emotion.dominant_emotion,
            detected_emotions=detected_emotions,
            primary_themes=self._top_themes_from_profile(analysis.semantic_projection.semantic_profile),
        )
        post = self._repository.create_post(
            content_hash=content_hash,
            content_type="community",
            ingestion_key=None,
            title=analysis.title,
            raw_text=analysis.redaction.redacted_text,
            private_raw_text=payload.text if settings.admin_debug_mode else None,
            hidden_subject=sanitized_about,
            attribution_author=None,
            attribution_work=None,
            attribution_year=None,
            attribution_source=None,
            attribution_url=None,
            attribution_rights_status=None,
            attribution_rights_notes=None,
            selected_mood=payload.mood,
            detected_mood=analysis.emotion.dominant_emotion,
            detected_emotions_json=self._embedding_service.serialize_list(detected_emotions),
            emotion_distribution_json=self._embedding_service.serialize_dict(
                analysis.semantic_projection.emotion_distribution
            ),
            summary=analysis.narrative.summary,
            keywords_json=self._embedding_service.serialize_list(analysis.themes.keywords),
            keyword_profile_json=self._embedding_service.serialize_dict(
                analysis.semantic_projection.keyword_profile
            ),
            semantic_profile_json=self._embedding_service.serialize_dict(
                analysis.semantic_projection.semantic_profile
            ),
            cluster_label=analysis.semantic_projection.cluster,
            warning_terms_json=self._embedding_service.serialize_list(analysis.moderation.flags),
            selected_content_notes_json=self._embedding_service.serialize_list(
                sorted(set(selected_content_notes).union(suggested_content_notes))
            ),
            pipeline_version=analysis.processing_trace.pipeline_version,
            processing_trace_json=self._embedding_service.serialize_json(asdict(analysis.processing_trace)),
            embedding_json=self._embedding_service.serialize_vector(analysis.embedding.vector),
            embedding_model=analysis.embedding.embedding_model,
            embedding_versions_json=self._embedding_service.serialize_list([analysis.embedding.embedding_model]),
            pipeline_versions_json=self._embedding_service.serialize_list([analysis.processing_trace.pipeline_version]),
        )
        registry.increment("dearest_posts_created_total")
        self._log_saved_post(
            original_text=payload.text,
            saved_text=post.raw_text,
            keywords=analysis.themes.keywords,
            summary=analysis.narrative.summary,
            post=post,
        )
        return PostCreateResponse(
            post=self._to_summary(post),
            similar_posts=self._build_similar_posts(post, limit=5),
            media_recommendations=self._build_media_recommendations(self._to_summary(post)),
            explanation="Matched by emotional themes, keywords, and semantic similarity.",
            pii_detected=analysis.redaction.pii_detected,
            redactions=[self._to_redaction_payload(item) for item in analysis.redaction.redactions],
        )

    def reindex_post(self, post_id: int) -> PostSummary | None:
        post = self._repository.get_post(post_id)
        if post is None:
            return None
        analysis = self._pipeline.process_story(
            post.private_raw_text or post.raw_text,
            selected_mood=post.selected_mood,
            title=post.title,
            enforce_moderation=False,
            redact_pii=post.content_type == "community",
        )
        updated = self._repository.update_post(
            post,
            content_hash=post.content_hash,
            content_type=post.content_type,
            ingestion_key=post.ingestion_key,
            title=analysis.title,
            raw_text=analysis.redaction.redacted_text,
            private_raw_text=post.private_raw_text,
            hidden_subject=post.hidden_subject,
            attribution_author=post.attribution_author,
            attribution_work=post.attribution_work,
            attribution_year=post.attribution_year,
            attribution_source=post.attribution_source,
            attribution_url=post.attribution_url,
            attribution_rights_status=post.attribution_rights_status,
            attribution_rights_notes=post.attribution_rights_notes,
            selected_mood=post.selected_mood,
            detected_mood=analysis.emotion.dominant_emotion,
            detected_emotions_json=self._embedding_service.serialize_list(
                self._emotion_analyzer.top_emotions(analysis.emotion, post.selected_mood)
            ),
            emotion_distribution_json=self._embedding_service.serialize_dict(
                analysis.semantic_projection.emotion_distribution
            ),
            summary=analysis.narrative.summary,
            keywords_json=self._embedding_service.serialize_list(analysis.themes.keywords),
            keyword_profile_json=self._embedding_service.serialize_dict(analysis.semantic_projection.keyword_profile),
            semantic_profile_json=self._embedding_service.serialize_dict(analysis.semantic_projection.semantic_profile),
            cluster_label=analysis.semantic_projection.cluster,
            warning_terms_json=self._embedding_service.serialize_list(analysis.moderation.flags),
            selected_content_notes_json=post.selected_content_notes_json,
            pipeline_version=analysis.processing_trace.pipeline_version,
            processing_trace_json=self._embedding_service.serialize_json(asdict(analysis.processing_trace)),
            embedding_json=self._embedding_service.serialize_vector(analysis.embedding.vector),
            embedding_model=analysis.embedding.embedding_model,
            embedding_versions_json=self._append_version(post.embedding_versions_json, analysis.embedding.embedding_model),
            pipeline_versions_json=self._append_version(
                post.pipeline_versions_json, analysis.processing_trace.pipeline_version
            ),
        )
        return self._to_summary(updated)

    def get_similar_posts(self, post_id: int, limit: int = 5) -> SimilarPostsResponse | None:
        """Return similar posts for one source post."""
        post = self._repository.get_post(post_id)
        if post is None:
            return None
        return SimilarPostsResponse(
            source_post=self._to_summary(post),
            similar_posts=self._build_similar_posts(post, limit=limit),
            media_recommendations=self._build_media_recommendations(self._to_summary(post)),
            explanation="Matched by emotional themes, keywords, and semantic similarity.",
        )

    def get_echoes(self, post_id: int, depth: int = 5) -> EchoesResponse | None:
        source_post = self._repository.get_post(post_id)
        if source_post is None:
            return None

        posts = self._repository.list_posts_asc()
        source_summary = self._to_summary(source_post)
        visited = {source_post.id}
        chain = [EchoStep(step=0, relation_score=None, relation_explanation=None, post=source_summary)]
        current = source_post
        previous_summary = source_summary

        for step_index in range(1, depth):
            bundle = self._recommendation_service_v2.build_bundle(
                source_post=self._to_recommendation_record(current),
                candidate_posts=[self._to_recommendation_record(post) for post in posts],
                top_k=max(depth * 2, 8),
            )
            next_choice = next(
                (
                    (recommendation.post_id, recommendation.score)
                    for recommendation in bundle.recommendations
                    if recommendation.post_id not in visited
                ),
                None,
            )
            if next_choice is None:
                break
            matched_post = next(post for post in posts if post.id == next_choice[0])
            matched_summary = self._to_summary(matched_post)
            insight = self._build_match_insight(previous_summary, matched_summary, next_choice[1])
            chain.append(
                EchoStep(
                    step=step_index,
                    relation_score=round(next_choice[1], 3),
                    relation_explanation=insight["narrative_explanation"],
                    post=matched_summary,
                )
            )
            visited.add(matched_post.id)
            current = matched_post
            previous_summary = matched_summary

        return EchoesResponse(source_post=source_summary, chain=chain)

    def _build_similar_posts(self, source_post: Post, limit: int = 5) -> list[SimilarPost]:
        posts = self._repository.list_posts_asc()
        post_records = [self._to_recommendation_record(post) for post in posts]
        bundle = self._recommendation_service_v2.build_bundle(
            source_post=self._to_recommendation_record(source_post),
            candidate_posts=post_records,
            top_k=limit,
        )
        post_map = {post.id: post for post in posts if post.id in {item.post_id for item in bundle.recommendations}}
        source_summary = self._to_summary(source_post)
        explanations = bundle.explanations
        return [
            self._build_similar_post_payload(
                source_post=source_summary,
                matched_post=self._to_summary(post_map[post_id]),
                similarity_score=next(item.score for item in bundle.recommendations if item.post_id == post_id),
                confidence_label=next(item.confidence_label for item in bundle.recommendations if item.post_id == post_id),
                calibrated_confidence=next(item.score for item in bundle.recommendations if item.post_id == post_id),
                supporting_excerpt=explanations[post_id].supporting_excerpt if post_id in explanations else "",
            )
            for post_id in [item.post_id for item in bundle.recommendations]
            if post_id in post_map
        ]

    def _to_summary(self, post: Post) -> PostSummary:
        detected_emotions = self._embedding_service.deserialize_list(post.detected_emotions_json)
        if not detected_emotions:
            profile = self._emotion_analyzer.analyze(post.raw_text, post.selected_mood)
            detected_emotions = self._emotion_analyzer.top_emotions(profile, post.selected_mood)
        return PostSummary(
            id=post.id,
            content_type=post.content_type,
            source_label=self._source_label(post.content_type),
            tone=post.detected_mood,
            collections=self._collections_for_post(post),
            primary_themes=self._primary_themes(post),
            timeline_year=self._timeline_year(post),
            timeline_label=self._timeline_label(post),
            title=post.title or self._pipeline.generate_title(post.raw_text),
            raw_text=post.raw_text,
            summary=post.summary,
            attribution=self._build_attribution(post),
            selected_mood=post.selected_mood,
            detected_mood=post.detected_mood,
            detected_emotions=detected_emotions,
            emotion_distribution=self._embedding_service.deserialize_dict(post.emotion_distribution_json),
            keywords=self._embedding_service.deserialize_list(post.keywords_json),
            keyword_profile=self._embedding_service.deserialize_dict(post.keyword_profile_json),
            semantic_profile=self._embedding_service.deserialize_dict(post.semantic_profile_json),
            top_motifs=self._build_motifs_from_post(post),
            cluster=post.cluster_label,
            warning_terms=self._embedding_service.deserialize_list(post.warning_terms_json),
            content_notes=self._content_notes_for_post(post),
            suggested_content_notes=self._suggested_content_notes_for_post(post),
            embedding_model=post.embedding_model,
            processing=self._processing_metadata_for_post(post),
            created_at=post.created_at,
        )

    def _to_redaction_payload(self, item: RedactionItem) -> dict[str, str]:
        return {"type": item.type, "value": item.value}

    def _build_similar_post_payload(
        self,
        *,
        source_post: PostSummary,
        matched_post: PostSummary,
        similarity_score: float,
        confidence_label: str,
        calibrated_confidence: float,
        supporting_excerpt: str,
    ) -> SimilarPost:
        explanation = self._explainability_service.explain_match(
            source_profile=self._to_semantic_projection(source_post),
            matched_profile=self._to_semantic_projection(matched_post),
            embedding_similarity=similarity_score,
        )
        insight = self._build_match_insight(source_post, matched_post, similarity_score)
        return SimilarPost(
            post=matched_post,
            similarity_score=similarity_score,
            confidence_label=confidence_label,
            calibrated_confidence=calibrated_confidence,
            embedding_similarity=explanation.embedding_similarity,
            supporting_excerpt=supporting_excerpt,
            semantic_profile=source_post.semantic_profile,
            matched_story_profile=explanation.matched_story_profile,
            shared_concepts=explanation.shared_concepts,
            shared_themes=insight["shared_themes"],
            shared_emotions=insight["shared_emotions"],
            shared_keywords=insight["shared_keywords"],
            dominant_tone=matched_post.detected_mood,
            narrative_explanation=insight["narrative_explanation"],
            top_motifs=explanation.top_motifs,
        )

    def _to_semantic_projection(self, post: PostSummary):
        from ..ai.types import SemanticProjection

        return SemanticProjection(
            semantic_profile=post.semantic_profile,
            emotion_distribution=post.emotion_distribution,
            keyword_profile=post.keyword_profile,
            top_motifs=post.top_motifs,
            cluster=post.cluster,
        )

    def _build_motifs_from_post(self, post: Post) -> list[str]:
        keyword_profile = self._embedding_service.deserialize_dict(post.keyword_profile_json)
        keywords = sorted(keyword_profile.items(), key=lambda item: item[1], reverse=True)
        motif_seed = [keyword for keyword, _ in keywords[:5]]
        return self._explainability_service.build_motifs(motif_seed)

    def _processing_metadata_for_post(self, post: Post) -> ProcessingMetadata:
        payload = self._embedding_service.deserialize_json(post.processing_trace_json, default={})
        if not isinstance(payload, dict):
            payload = {}
        stage_items = payload.get("stages", [])
        stages: list[ProcessingStage] = []
        if isinstance(stage_items, list):
            for item in stage_items:
                if isinstance(item, dict) and "name" in item:
                    stages.append(
                        ProcessingStage(
                            name=str(item["name"]),
                            duration_ms=float(item.get("duration_ms", 0.0)),
                            outcome=str(item.get("outcome", "completed")),
                            detail=str(item["detail"]) if item.get("detail") is not None else None,
                        )
                    )

        return ProcessingMetadata(
            pipeline_version=str(payload.get("pipeline_version") or post.pipeline_version or "unknown"),
            embedding_backend=str(payload.get("embedding_backend") or post.embedding_model),
            moderation_safe=bool(payload.get("moderation_safe", True)),
            redaction_count=int(payload.get("redaction_count", 0)),
            total_duration_ms=float(payload.get("total_duration_ms", 0.0)),
            stages=stages,
        )

    def _build_attribution(self, post: Post):
        if post.content_type != "public_archive" or not post.attribution_author:
            return None
        from ..schemas import PublicArchiveAttribution

        return PublicArchiveAttribution(
            author=post.attribution_author,
            work=post.attribution_work,
            year=post.attribution_year,
            source=post.attribution_source,
            url=post.attribution_url,
            rights_status=post.attribution_rights_status,
            rights_notes=post.attribution_rights_notes,
        )

    def _source_label(self, content_type: str) -> str:
        if content_type == "public_archive":
            return "From the public archive"
        return "From the Dearest community"

    def _primary_themes(self, post: Post) -> list[str]:
        profile = self._embedding_service.deserialize_dict(post.semantic_profile_json)
        return self._top_themes_from_profile(profile)

    def _top_themes_from_profile(self, profile: dict[str, float]) -> list[str]:
        return [theme for theme, _ in sorted(profile.items(), key=lambda item: item[1], reverse=True)[:3]]

    def _content_notes_for_post(self, post: Post) -> list[str]:
        selected = set(self._embedding_service.deserialize_list(post.selected_content_notes_json))
        suggested = set(self._suggested_content_notes_for_post(post))
        return sorted(selected.union(suggested))

    def _suggested_content_notes_for_post(self, post: Post) -> list[str]:
        return self._suggest_content_notes(
            text=post.raw_text,
            warning_terms=self._embedding_service.deserialize_list(post.warning_terms_json),
            detected_mood=post.detected_mood,
            detected_emotions=self._embedding_service.deserialize_list(post.detected_emotions_json),
            primary_themes=self._primary_themes(post),
        )

    def _normalize_content_notes(self, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            slug = value.strip().lower()
            if slug in CONTENT_NOTE_OPTIONS and slug not in normalized:
                normalized.append(slug)
        return normalized

    def _suggest_content_notes(
        self,
        *,
        text: str,
        warning_terms: list[str],
        detected_mood: str,
        detected_emotions: list[str],
        primary_themes: list[str],
    ) -> list[str]:
        lowered = text.lower()
        notes: set[str] = set()
        warning_map = {
            "abuse": "abuse",
            "abusive": "abuse",
            "violent": "violence",
            "violence": "violence",
            "war": "war",
            "grief": "grief",
            "self-harm": "self-harm",
            "self harm": "self-harm",
            "illness": "illness",
            "identity": "identity",
            "trauma": "trauma",
            "discrimination": "discrimination",
        }
        for term in warning_terms:
            if term in warning_map:
                notes.add(warning_map[term])
        if detected_mood == "heartbreak" or "heartbreak" in detected_emotions:
            notes.add("heartbreak")
        if detected_mood == "grief" or "grief" in detected_emotions:
            notes.add("grief")
        if "identity" in primary_themes:
            notes.add("identity")
        if "illness" in lowered:
            notes.add("illness")
        if "trauma" in lowered:
            notes.add("trauma")
        if "discrimination" in lowered or "racism" in lowered or "prejudice" in lowered:
            notes.add("discrimination")
        return sorted(note for note in notes if note in CONTENT_NOTE_OPTIONS)

    def _collections_for_post(self, post: Post) -> list[str]:
        themes = set(self._primary_themes(post))
        emotions = set(self._embedding_service.deserialize_list(post.detected_emotions_json))
        collections: list[str] = []
        for name, rules in EDITORIAL_COLLECTIONS.items():
            if themes.intersection(rules["themes"]) or emotions.intersection(rules["emotions"]):
                collections.append(name)
        return collections

    def _timeline_year(self, post: Post) -> int | None:
        if post.content_type == "public_archive" and post.attribution_year:
            match = re.search(r"(1[6-9]\d{2}|20\d{2})", post.attribution_year)
            return int(match.group(1)) if match else None
        return post.created_at.year if post.created_at else None

    def _timeline_label(self, post: Post) -> str | None:
        if post.content_type == "public_archive":
            return post.attribution_year
        return str(post.created_at.year) if post.created_at else None

    def _build_match_insight(
        self,
        source_post: PostSummary,
        matched_post: PostSummary,
        similarity_score: float,
    ) -> dict[str, list[str] | str]:
        shared_themes = [
            theme
            for theme in source_post.primary_themes
            if theme in matched_post.primary_themes
        ][:3]
        shared_emotions = [
            emotion
            for emotion in source_post.detected_emotions
            if emotion in matched_post.detected_emotions
        ][:3]
        shared_keywords = [
            keyword
            for keyword in source_post.keywords
            if keyword in matched_post.keywords
        ][:4]
        explanation_parts: list[str] = []
        if shared_themes:
            explanation_parts.append(
                f"themes of {', '.join(shared_themes)}"
            )
        if shared_emotions:
            explanation_parts.append(
                f"emotions like {', '.join(shared_emotions)}"
            )
        if not explanation_parts and matched_post.primary_themes:
            explanation_parts.append(
                f"the emotional terrain around {', '.join(matched_post.primary_themes[:2])}"
            )
        narrative_explanation = (
            f"Both pieces explore {' and '.join(explanation_parts)}."
            if explanation_parts
            else f"These writings sit close together in Dearest's semantic archive ({round(similarity_score, 3)})."
        )
        return {
            "shared_themes": shared_themes,
            "shared_emotions": shared_emotions,
            "shared_keywords": shared_keywords,
            "narrative_explanation": narrative_explanation,
        }

    def _matches_filters(
        self,
        post: PostSummary,
        *,
        theme: str | None,
        emotion: str | None,
        tone: str | None,
        author: str | None,
        year: str | None,
        content_type: str | None,
        collection: str | None,
        content_note: str | None,
        avoid_theme: str | None,
        avoid_content_note: str | None,
    ) -> bool:
        if theme and theme not in post.primary_themes:
            return False
        if avoid_theme and avoid_theme in post.primary_themes:
            return False
        if emotion and emotion not in post.detected_emotions:
            return False
        if tone and tone != post.tone:
            return False
        if author and (post.attribution is None or post.attribution.author != author):
            return False
        if year and post.timeline_label != year:
            return False
        if content_type and post.content_type != content_type:
            return False
        if collection and collection not in post.collections:
            return False
        if content_note and content_note not in post.content_notes:
            return False
        if avoid_content_note and avoid_content_note in post.content_notes:
            return False
        return True

    def _sort_explorer_posts(
        self,
        filtered: list[PostSummary],
        all_posts: list[PostSummary],
        *,
        sort: str,
        semantic_to_post_id: int | None,
    ) -> list[PostSummary]:
        if sort == "newest":
            return sorted(filtered, key=lambda post: post.created_at, reverse=True)
        if sort == "popularity":
            popularity = self._popularity_scores(all_posts)
            return sorted(filtered, key=lambda post: popularity.get(post.id, 0.0), reverse=True)
        if sort == "semantic_similarity" and semantic_to_post_id is not None:
            scores = self._semantic_scores_for_post(semantic_to_post_id)
            return sorted(filtered, key=lambda post: scores.get(post.id, -1.0), reverse=True)
        return filtered

    def _build_archive_filters(self, posts: list[PostSummary]) -> ArchiveFilterOptions:
        return ArchiveFilterOptions(
            themes=sorted({theme for post in posts for theme in post.primary_themes}),
            emotions=sorted({emotion for post in posts for emotion in post.detected_emotions}),
            content_notes=sorted({note for post in posts for note in post.content_notes}),
            tones=sorted({post.tone for post in posts}),
            authors=sorted({post.attribution.author for post in posts if post.attribution}),
            years=sorted({post.timeline_label for post in posts if post.timeline_label}),
            content_types=["community", "public_archive"],
            collections=sorted({collection for post in posts for collection in post.collections}),
            sort_options=["newest", "popularity", "semantic_similarity"],
        )

    def _build_media_recommendations(self, source_post: PostSummary) -> list[MediaRecommendation]:
        recommendations: list[tuple[float, MediaItem, list[str], list[str]]] = []
        post_themes = set(source_post.primary_themes)
        post_emotions = set(source_post.detected_emotions)
        post_keywords = set(source_post.keywords)

        for item in MEDIA_CATALOG:
            shared_themes = [theme for theme in item.themes if theme in post_themes][:3]
            shared_emotions = [emotion for emotion in item.emotions if emotion in post_emotions][:3]
            keyword_overlap = len([keyword for keyword in post_keywords if keyword in item.description.lower()])
            score = (
                len(shared_themes) * 0.34
                + len(shared_emotions) * 0.28
                + keyword_overlap * 0.07
                + (0.18 if item.tone == source_post.detected_mood else 0.0)
            )
            if score <= 0:
                continue
            recommendations.append((score, item, shared_themes, shared_emotions))

        recommendations.sort(key=lambda value: value[0], reverse=True)
        songs = [entry for entry in recommendations if entry[1].kind == "song"][:5]
        movies = [entry for entry in recommendations if entry[1].kind == "movie"][:3]
        selected = songs + movies
        return [
            MediaRecommendation(
                kind=item.kind,  # type: ignore[arg-type]
                title=item.title,
                creator=item.creator,
                year=item.year,
                link=item.link,
                artwork_hint=item.artwork_hint,
                confidence_label=self._media_confidence_label(score),
                shared_themes=shared_themes,
                shared_emotions=shared_emotions,
                explanation=self._media_explanation(item, shared_themes, shared_emotions),
            )
            for score, item, shared_themes, shared_emotions in selected
        ]

    def _media_confidence_label(self, score: float) -> str:
        if score >= 1.05:
            return "Strong Echo"
        if score >= 0.74:
            return "Meaningful Connection"
        return "Distant Resonance"

    def _media_explanation(
        self,
        item: MediaItem,
        shared_themes: list[str],
        shared_emotions: list[str],
    ) -> str:
        reasons: list[str] = []
        if shared_themes:
            reasons.append(f"themes of {', '.join(shared_themes)}")
        if shared_emotions:
            reasons.append(f"emotions like {', '.join(shared_emotions)}")
        if not reasons:
            reasons.append(f"a similarly {item.tone} emotional register")
        return f"We recommended {item.title} because it carries {' and '.join(reasons)}."

    def _semantic_scores_for_post(self, post_id: int) -> dict[int, float]:
        posts = self._repository.list_posts_asc()
        source_post = next((post for post in posts if post.id == post_id), None)
        if source_post is None:
            return {}
        bundle = self._recommendation_service_v2.build_bundle(
            source_post=self._to_recommendation_record(source_post),
            candidate_posts=[self._to_recommendation_record(post) for post in posts],
            top_k=len(posts),
        )
        return {item.post_id: item.score for item in bundle.recommendations}

    def _to_recommendation_record(self, post: Post) -> dict[str, object]:
        summary = self._to_summary(post)
        return {
            "id": post.id,
            "raw_text": post.raw_text,
            "summary": post.summary,
            "embedding_json": post.embedding_json,
            "embedding_model": post.embedding_model,
            "pipeline_version": post.pipeline_version,
            "detected_emotions_json": post.detected_emotions_json,
            "semantic_profile_json": post.semantic_profile_json,
            "keywords_json": post.keywords_json,
            "content_type": post.content_type,
            "selected_content_notes_json": post.selected_content_notes_json,
            "timeline_year": summary.timeline_year,
            "created_at": post.created_at.isoformat() if post.created_at else None,
        }

    def _popularity_scores(self, posts: list[PostSummary]) -> dict[int, float]:
        semantic_scores = {post.id: self._semantic_scores_for_post(post.id) for post in posts}
        popularity: dict[int, float] = {}
        for post in posts:
            neighbor_scores = sorted(semantic_scores.get(post.id, {}).values(), reverse=True)[:5]
            popularity[post.id] = round(sum(neighbor_scores) / max(len(neighbor_scores), 1), 3)
        return popularity

    def _log_saved_post(
        self,
        *,
        original_text: str,
        saved_text: str,
        keywords: list[str],
        summary: str,
        post: Post,
    ) -> None:
        if not get_settings().pipeline_trace_mode:
            return
        logger.info(
            "Dearest persistence trace\n"
            "Original Text: %s\n"
            "Saved Text: %s\n"
            "Generated Keywords: %s\n"
            "Generated Summary: %s\n"
            "Database Record: %s",
            original_text,
            saved_text,
            keywords,
            summary,
            {
                "id": post.id,
                "title": post.title,
                "raw_text": post.raw_text,
                "private_raw_text": post.private_raw_text,
                "summary": post.summary,
                "keywords_json": post.keywords_json,
                "embedding_model": post.embedding_model,
            },
        )

    def _append_version(self, serialized_versions: str | None, version: str) -> str:
        versions = [item for item in self._embedding_service.deserialize_json(serialized_versions or "[]", default=[]) if item]
        if version not in versions:
            versions.append(version)
        return self._embedding_service.serialize_list([str(item) for item in versions])
