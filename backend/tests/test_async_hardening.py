from __future__ import annotations

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai import (
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
from app.ai.vector_store import LocalVectorStorage
from app.database.base import Base
from app.repositories import PostRepository
from app.request_context import set_correlation_id
from app.runtime_state import TransientStateStore
from app.schemas import PostCreate
from app.services import PostService, ProcessingService
from app.settings import get_settings


class AsyncHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_eager = os.environ.get("DEAREST_CELERY_TASK_ALWAYS_EAGER")
        os.environ["DEAREST_CELERY_TASK_ALWAYS_EAGER"] = "true"
        get_settings.cache_clear()

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        self.session = session_factory()

        embedding_service = EmbeddingService()
        explainability_service = ExplainabilityService(embedding_service=embedding_service)
        emotion_analyzer = EmotionAnalyzer()
        recommendation_service = RecommendationService(embedding_service=embedding_service)
        recommendation_service_v2 = RecommendationServiceV2(
            retrieval_service=RetrievalService(
                embedding_service=embedding_service,
                vector_storage=LocalVectorStorage(embedding_service),
            ),
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
        self.post_service = PostService(
            repository=PostRepository(self.session),
            pipeline=pipeline,
            embedding_service=embedding_service,
            emotion_analyzer=emotion_analyzer,
            explainability_service=explainability_service,
            recommendation_service=recommendation_service,
            recommendation_service_v2=recommendation_service_v2,
            evaluation_service=EvaluationService(),
        )
        self.processing_service = ProcessingService(
            self.session,
            self.post_service,
            transient_state_store=TransientStateStore(redis_url=None),
        )

    def tearDown(self) -> None:
        self.session.close()
        if self._previous_eager is None:
            os.environ.pop("DEAREST_CELERY_TASK_ALWAYS_EAGER", None)
        else:
            os.environ["DEAREST_CELERY_TASK_ALWAYS_EAGER"] = self._previous_eager
        get_settings.cache_clear()

    def test_job_submission_preserves_correlation_id_and_cache(self) -> None:
        set_correlation_id("corr-test-123")
        payload = PostCreate(text="I still miss the station where we said goodbye forever.", mood="longing")

        status_code, created = self.processing_service.submit_post(payload)
        self.assertEqual(status_code, 202)
        self.assertEqual(created.correlation_id, "corr-test-123")

        finished = self.processing_service.process_job(created.job_id)
        self.assertEqual(finished.status, "COMPLETED")
        self.assertEqual(finished.correlation_id, "corr-test-123")

        cached_status, cached = self.processing_service.submit_post(payload)
        self.assertEqual(cached_status, 200)
        self.assertEqual(cached.status, "COMPLETED")
        self.assertEqual(cached.correlation_id, "corr-test-123")


if __name__ == "__main__":
    unittest.main()
