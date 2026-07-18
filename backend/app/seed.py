"""Public archive ingestion and legacy seed cleanup."""

from __future__ import annotations

from dataclasses import asdict

from .ai import (
    EmbeddingService,
    EmotionAnalyzer,
    ExplainabilityService,
    ModerationService,
    NarrativeAnalyzer,
    RecommendationService,
    RedactionService,
    StoryProcessingPipeline,
    ThemeExtractor,
)
from .public_archive import load_public_archive_entries
from .repositories import PostRepository

LEGACY_DEMO_TITLES = [
    "The timetable I still memorize",
    "Success that fits like borrowed clothing",
    "After the last box left",
    "A quiet definition of healing",
    "The apology after the damage",
    "What the sunlight still belongs to",
    "The summer that still glows",
    "The quiet architecture of love",
    "When strength becomes a costume",
    "After resigning",
    "The flinch that stayed",
    "The shape I keep recognizing",
]


def seed_posts(session) -> None:
    """Import vetted public archive entries without touching community submissions."""
    repository = PostRepository(session)
    repository.delete_posts_by_titles(LEGACY_DEMO_TITLES)

    entries = load_public_archive_entries()
    if not entries:
        return

    embedding_service = EmbeddingService()
    explainability_service = ExplainabilityService(embedding_service=embedding_service)
    emotion_analyzer = EmotionAnalyzer()
    pipeline = StoryProcessingPipeline(
        narrative_analyzer=NarrativeAnalyzer(),
        emotion_analyzer=emotion_analyzer,
        theme_extractor=ThemeExtractor(),
        embedding_service=embedding_service,
        explainability_service=explainability_service,
        moderation_service=ModerationService(),
        redaction_service=RedactionService(),
        recommendation_service=RecommendationService(embedding_service=embedding_service),
    )

    for entry in entries:
        analysis = pipeline.process_story(
            entry.text,
            selected_mood=entry.mood,
            title=entry.title,
            enforce_moderation=False,
            redact_pii=False,
        )
        detected_emotions = emotion_analyzer.top_emotions(analysis.emotion, entry.mood)
        record = {
            "content_hash": entry.ingestion_key,
            "content_type": "public_archive",
            "ingestion_key": entry.ingestion_key,
            "title": analysis.title,
            "raw_text": analysis.redaction.redacted_text,
            "private_raw_text": None,
            "hidden_subject": None,
            "attribution_author": entry.author,
            "attribution_work": entry.work,
            "attribution_year": entry.year,
            "attribution_source": entry.source,
            "attribution_url": str(entry.source_url) if entry.source_url else None,
            "attribution_rights_status": entry.rights_status,
            "attribution_rights_notes": entry.rights_notes,
            "selected_mood": entry.mood,
            "detected_mood": analysis.emotion.dominant_emotion,
            "detected_emotions_json": embedding_service.serialize_list(detected_emotions),
            "emotion_distribution_json": embedding_service.serialize_dict(
                analysis.semantic_projection.emotion_distribution
            ),
            "summary": analysis.narrative.summary,
            "keywords_json": embedding_service.serialize_list(analysis.themes.keywords),
            "keyword_profile_json": embedding_service.serialize_dict(
                analysis.semantic_projection.keyword_profile
            ),
            "semantic_profile_json": embedding_service.serialize_dict(
                analysis.semantic_projection.semantic_profile
            ),
            "cluster_label": analysis.semantic_projection.cluster,
            "warning_terms_json": embedding_service.serialize_list(analysis.moderation.flags),
            "selected_content_notes_json": embedding_service.serialize_list([]),
            "pipeline_version": analysis.processing_trace.pipeline_version,
            "processing_trace_json": embedding_service.serialize_json(asdict(analysis.processing_trace)),
            "embedding_json": embedding_service.serialize_vector(analysis.embedding.vector),
            "embedding_model": analysis.embedding.embedding_model,
        }
        existing = repository.get_post_by_ingestion_key(entry.ingestion_key)
        if existing is None:
            repository.create_post(**record)
        else:
            repository.update_post(existing, **record)
