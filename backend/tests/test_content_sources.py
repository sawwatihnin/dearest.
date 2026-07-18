from __future__ import annotations

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
from app.database.base import Base
from app.repositories import PostRepository
from app.schemas import PostCreate
from app.services import PostService


class ContentSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        self.session = session_factory()

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
        self.repository = PostRepository(self.session)
        self.embedding_service = embedding_service
        self.post_service = PostService(
            repository=self.repository,
            pipeline=pipeline,
            embedding_service=embedding_service,
            emotion_analyzer=emotion_analyzer,
            explainability_service=explainability_service,
            recommendation_service=recommendation_service,
            recommendation_service_v2=recommendation_service_v2,
            evaluation_service=EvaluationService(),
        )

    def tearDown(self) -> None:
        self.session.close()

    def test_public_archive_posts_include_attribution_and_source_label(self) -> None:
        post = self.repository.create_post(
            content_hash=None,
            content_type="public_archive",
            ingestion_key="dickinson-1862-hope-001",
            title="Hope fragment",
            raw_text="Hope is the thing with feathers that perches in the soul.",
            private_raw_text=None,
            hidden_subject=None,
            attribution_author="Emily Dickinson",
            attribution_work="Poem 254",
            attribution_year="c. 1862",
            attribution_source="Public-domain transcription",
            attribution_url="https://example.org/dickinson",
            attribution_rights_status="Public domain",
            attribution_rights_notes="Verified public-domain source.",
            selected_mood="love",
            detected_mood="love",
            detected_emotions_json='["love"]',
            emotion_distribution_json='{"love": 1}',
            summary="Hope perches in the soul.",
            keywords_json='["hope"]',
            keyword_profile_json='{"hope": 1}',
            semantic_profile_json='{"hope": 1}',
            cluster_label="hope",
            warning_terms_json="[]",
            selected_content_notes_json="[]",
            pipeline_version="test-pipeline",
            processing_trace_json=self.embedding_service.serialize_json(
                {
                    "pipeline_version": "test-pipeline",
                    "embedding_backend": "tfidf",
                    "moderation_safe": True,
                    "redaction_count": 0,
                    "total_duration_ms": 4.2,
                    "stages": [{"name": "embedding", "duration_ms": 1.2, "outcome": "completed", "detail": "backend=tfidf"}],
                }
            ),
            embedding_json=None,
            embedding_model="tfidf",
        )

        summary = self.post_service.get_post(post.id)

        assert summary is not None
        self.assertEqual(summary.content_type, "public_archive")
        self.assertEqual(summary.source_label, "From the public archive")
        self.assertIsNotNone(summary.attribution)
        self.assertEqual(summary.attribution.author, "Emily Dickinson")
        self.assertEqual(summary.attribution.year, "c. 1862")
        self.assertEqual(summary.attribution.rights_status, "Public domain")
        self.assertEqual(summary.processing.pipeline_version, "test-pipeline")
        self.assertEqual(summary.processing.embedding_backend, "tfidf")

    def test_trusted_public_archive_ingest_can_skip_pii_redaction(self) -> None:
        analysis = self.post_service._pipeline.process_story(
            "Jane Eyre refused to be broken by Mr. Rochester's secrets.",
            title="Jane Eyre excerpt",
            enforce_moderation=False,
            redact_pii=False,
        )

        self.assertEqual(analysis.redaction.redacted_text, "Jane Eyre refused to be broken by Mr. Rochester's secrets.")
        self.assertEqual(analysis.redaction.redacted_title, "Jane Eyre excerpt")
        self.assertFalse(analysis.redaction.pii_detected)

    def test_each_letter_gets_song_and_movie_recommendations(self) -> None:
        created = self.post_service.create_post(
            PostCreate(
                text=(
                    "I keep replaying the version of us that knew how to stay, and memory has become "
                    "the room I return to when I cannot sleep."
                ),
                mood="longing",
                content_notes=["heartbreak"],
            )
        )

        kinds = {item.kind for item in created.media_recommendations}
        self.assertIn("song", kinds)
        self.assertIn("movie", kinds)
        self.assertTrue(all(item.explanation for item in created.media_recommendations))

    def test_archive_explorer_can_avoid_themes_and_content_notes(self) -> None:
        self.post_service.create_post(
            PostCreate(
                text=(
                    "Grief keeps folding the house back into memory, and every room still sounds like loss."
                ),
                mood="grief",
                content_notes=["grief"],
            )
        )
        self.post_service.create_post(
            PostCreate(
                text=(
                    "I want to believe healing is possible, even when change still feels larger than hope."
                ),
                mood="healing",
                content_notes=[],
            )
        )

        response = self.post_service.list_archive_explorer_posts(
            avoid_theme="loss",
            avoid_content_note="grief",
        )

        self.assertTrue(response.posts)
        self.assertTrue(all("loss" not in post.primary_themes for post in response.posts))
        self.assertTrue(all("grief" not in post.content_notes for post in response.posts))
