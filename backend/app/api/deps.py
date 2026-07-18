"""Dependency providers for FastAPI routes."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from ..ai import (
    ContentSafetyService,
    EmbeddingService,
    EmotionAnalyzer,
    EnrichmentService,
    EvaluationService,
    ExplanationService,
    ExplainabilityService,
    ModerationService,
    NarrativeAnalyzer,
    PrivacyService,
    RankingService,
    RedactionService,
    RecommendationService,
    RecommendationServiceV2,
    RetrievalService,
    StoryProcessingPipeline,
    ThemeExtractor,
)
from ..database import get_db
from ..repositories import PostRepository
from ..services import PostService, ProcessingService


def build_services(db: Session) -> dict[str, object]:
    """Build explicit request-scoped services for routes and tasks."""
    embedding_service = EmbeddingService()
    explainability_service = ExplainabilityService(embedding_service=embedding_service)
    emotion_analyzer = EmotionAnalyzer()
    recommendation_service = RecommendationService(embedding_service=embedding_service)
    moderation_service = ModerationService()
    redaction_service = RedactionService()
    content_safety_service = ContentSafetyService(moderation_service)
    privacy_service = PrivacyService(redaction_service)
    enrichment_service = EnrichmentService(
        narrative_analyzer=NarrativeAnalyzer(),
        emotion_analyzer=emotion_analyzer,
        theme_extractor=ThemeExtractor(),
        explainability_service=explainability_service,
        embedding_service=embedding_service,
    )
    retrieval_service = RetrievalService(embedding_service=embedding_service)
    ranking_service = RankingService()
    explanation_service = ExplanationService()
    recommendation_service_v2 = RecommendationServiceV2(
        retrieval_service=retrieval_service,
        ranking_service=ranking_service,
        explanation_service=explanation_service,
    )
    evaluation_service = EvaluationService()
    pipeline = StoryProcessingPipeline(
        narrative_analyzer=NarrativeAnalyzer(),
        emotion_analyzer=emotion_analyzer,
        theme_extractor=ThemeExtractor(),
        embedding_service=embedding_service,
        explainability_service=explainability_service,
        moderation_service=moderation_service,
        redaction_service=redaction_service,
        recommendation_service=recommendation_service,
    )
    repository = PostRepository(db)
    post_service = PostService(
        repository=repository,
        pipeline=pipeline,
        embedding_service=embedding_service,
        emotion_analyzer=emotion_analyzer,
        explainability_service=explainability_service,
        recommendation_service=recommendation_service,
        recommendation_service_v2=recommendation_service_v2,
        evaluation_service=evaluation_service,
    )
    return {
        "post_service": post_service,
        "embedding_service": embedding_service,
        "recommendation_service_v2": recommendation_service_v2,
        "evaluation_service": evaluation_service,
    }


def get_post_service(db: Session = Depends(get_db)) -> PostService:
    """Build a request-scoped post service using explicit dependencies."""
    return build_services(db)["post_service"]  # type: ignore[return-value]


def get_processing_service(db: Session = Depends(get_db)) -> ProcessingService:
    """Build async processing orchestration service."""
    return ProcessingService(db, get_post_service(db))
