"""Re-run the current pipeline across persisted posts."""

from __future__ import annotations

from dataclasses import asdict

from .ai import (
    EvaluationService,
    EmbeddingService,
    EmotionAnalyzer,
    ExplanationService,
    ExplainabilityService,
    ModerationService,
    NarrativeAnalyzer,
    RankingService,
    RecommendationService,
    RecommendationServiceV2,
    RedactionService,
    RetrievalService,
    StoryProcessingPipeline,
    ThemeExtractor,
)
from .database import SessionLocal, ensure_schema
from .repositories import PostRepository
from .services.post_service import PostService


def main() -> None:
    ensure_schema()
    with SessionLocal() as session:
        repository = PostRepository(session)
        embedding_service = EmbeddingService()
        explainability_service = ExplainabilityService(embedding_service=embedding_service)
        emotion_analyzer = EmotionAnalyzer()
        recommendation_service = RecommendationService(embedding_service=embedding_service)
        recommendation_service_v2 = RecommendationServiceV2(
            retrieval_service=RetrievalService(embedding_service=embedding_service),
            ranking_service=RankingService(),
            explanation_service=ExplanationService(),
        )
        pipeline = StoryProcessingPipeline(
            narrative_analyzer=NarrativeAnalyzer(),
            emotion_analyzer=emotion_analyzer,
            theme_extractor=ThemeExtractor(),
            embedding_service=embedding_service,
            explainability_service=explainability_service,
            moderation_service=ModerationService(),
            redaction_service=RedactionService(),
            recommendation_service=recommendation_service,
        )
        post_service = PostService(
            repository=repository,
            pipeline=pipeline,
            embedding_service=embedding_service,
            emotion_analyzer=emotion_analyzer,
            explainability_service=explainability_service,
            recommendation_service=recommendation_service,
            recommendation_service_v2=recommendation_service_v2,
            evaluation_service=EvaluationService(),
        )

        for post in repository.all_posts():
            source_text = post.private_raw_text or post.raw_text
            redact_pii = post.content_type != "public_archive"
            enforce_moderation = post.content_type != "public_archive"
            analysis = pipeline.process_story(
                source_text,
                selected_mood=post.selected_mood,
                title=post.title,
                enforce_moderation=enforce_moderation,
                redact_pii=redact_pii,
            )
            detected_emotions = emotion_analyzer.top_emotions(analysis.emotion, post.selected_mood)
            updated_content_notes = post_service._content_notes_for_post(post)

            repository.update_post(
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
                detected_emotions_json=embedding_service.serialize_list(detected_emotions),
                emotion_distribution_json=embedding_service.serialize_dict(
                    analysis.semantic_projection.emotion_distribution
                ),
                summary=analysis.narrative.summary,
                keywords_json=embedding_service.serialize_list(analysis.themes.keywords),
                keyword_profile_json=embedding_service.serialize_dict(
                    analysis.semantic_projection.keyword_profile
                ),
                semantic_profile_json=embedding_service.serialize_dict(
                    analysis.semantic_projection.semantic_profile
                ),
                cluster_label=analysis.semantic_projection.cluster,
                warning_terms_json=embedding_service.serialize_list(analysis.moderation.flags),
                selected_content_notes_json=embedding_service.serialize_list(updated_content_notes),
                pipeline_version=analysis.processing_trace.pipeline_version,
                processing_trace_json=embedding_service.serialize_json(asdict(analysis.processing_trace)),
                embedding_json=embedding_service.serialize_vector(analysis.embedding.vector),
                embedding_model=analysis.embedding.embedding_model,
            )


if __name__ == "__main__":
    main()
