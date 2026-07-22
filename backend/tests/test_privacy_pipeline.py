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
    UnsafeContentError,
)
from app.database.base import Base
from app.models import Post
from app.repositories import PostRepository
from app.schemas import PostCreate
from app.services import PostService
from app.settings import get_settings


class PrivacyPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_debug = os.environ.get("DEAREST_ADMIN_DEBUG_MODE")
        os.environ.pop("DEAREST_ADMIN_DEBUG_MODE", None)
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
        self.redaction_service = RedactionService()
        self.pipeline = pipeline
        self.repository = PostRepository(self.session)
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
        if self._previous_debug is None:
            os.environ.pop("DEAREST_ADMIN_DEBUG_MODE", None)
        else:
            os.environ["DEAREST_ADMIN_DEBUG_MODE"] = self._previous_debug
        get_settings.cache_clear()

    def test_redacts_required_examples(self) -> None:
        cases = [
            ("I am in love with Josh Allen.", "I am in love with [PERSON].", "Josh Allen"),
            ("I still think about Taylor Swift.", "I still think about [PERSON].", "Taylor Swift"),
            ("I kept rereading Barack Obama speeches.", "I kept rereading [PERSON] speeches.", "Barack Obama"),
            ("I went to UNC Chapel Hill and changed there.", "I went to [ORGANIZATION] and changed there.", "UNC Chapel Hill"),
            ("I never sent that note to Google.", "I never sent that note to [ORGANIZATION].", "Google"),
            ("My email is john@gmail.com", "My email is [EMAIL]", "john@gmail.com"),
            ("Call me at 919-555-1234 tonight.", "Call me at [PHONE] tonight.", "919-555-1234"),
            ("I kept checking https://example.com", "I kept checking [URL]", "https://example.com"),
        ]

        for source_text, expected_output, original_value in cases:
            with self.subTest(source_text=source_text):
                result = self.redaction_service.sanitize_story(source_text)
                self.assertTrue(result.pii_detected)
                self.assertNotIn(original_value, result.redacted_text)
                self.assertEqual(result.redacted_text, expected_output)

    def test_redacts_full_person_names_without_partial_leakage(self) -> None:
        cases = [
            ("I am in love with Josh Allen.", "I am in love with [PERSON].", "Allen"),
            ("I still think about Taylor Swift.", "I still think about [PERSON].", "Swift"),
            ("Barack Obama wrote the kind of sentences I wanted to keep.", "[PERSON] wrote the kind of sentences I wanted to keep.", "Obama"),
            ("I watched Michael B. Jordan smile and forgot my name.", "I watched [PERSON] smile and forgot my name.", "Jordan"),
            ("John F. Kennedy still sounds mythic in documentaries.", "[PERSON] still sounds mythic in documentaries.", "Kennedy"),
        ]

        for source_text, expected_output, leaked_fragment in cases:
            with self.subTest(source_text=source_text):
                result = self.redaction_service.sanitize_story(source_text)
                self.assertEqual(result.redacted_text, expected_output)
                self.assertNotIn(leaked_fragment, result.redacted_text)
                self.assertEqual(
                    [item.type for item in result.redactions if item.type == "PERSON"],
                    ["PERSON"],
                )

    def test_pipeline_blocks_unsafe_content_before_processing(self) -> None:
        with self.assertRaises(UnsafeContentError):
            self.pipeline.process_story("Josh Allen told me I should kill myself tonight.")

    def test_pipeline_allows_autobiographical_trauma_writing(self) -> None:
        analysis = self.pipeline.process_story(
            (
                "When I was a teenager, my father was abusive and our home was violent in ways "
                "I still struggle to name, but this letter is about surviving that grief and learning who I am."
            ),
            selected_mood="grief",
        )

        self.assertTrue(analysis.moderation.safe)
        self.assertIn("abusive", analysis.moderation.flags)
        self.assertIn("violent", analysis.moderation.flags)

    def test_pipeline_allows_war_and_illness_memoir(self) -> None:
        analysis = self.pipeline.process_story(
            (
                "I lived through war, illness, and the long trauma that followed, and I am writing this "
                "to remember my brother without disappearing into silence."
            ),
            selected_mood="grief",
        )

        self.assertTrue(analysis.moderation.safe)
        self.assertIn("war", analysis.moderation.flags)
        self.assertIn("illness", analysis.moderation.flags)
        self.assertIn("trauma", analysis.moderation.flags)

    def test_pipeline_blocks_violent_threats(self) -> None:
        with self.assertRaises(UnsafeContentError):
            self.pipeline.process_story("I am going to kill him tonight because I want him to suffer.")

    def test_pipeline_blocks_self_harm_instructions(self) -> None:
        with self.assertRaises(UnsafeContentError):
            self.pipeline.process_story("I need instructions for how to kill myself without anyone stopping me.")

    def test_pipeline_blocks_ambiguous_self_harm_disclosure(self) -> None:
        with self.assertRaises(UnsafeContentError):
            self.pipeline.process_story("I have been thinking about self harm lately and do not know what to do.")

    def test_pipeline_allows_historical_self_harm_recovery_writing(self) -> None:
        analysis = self.pipeline.process_story(
            "Years ago I survived self-harm, and this letter is about recovery and healing."
        )

        self.assertTrue(analysis.moderation.safe)
        self.assertIn("self-harm", analysis.moderation.flags)

    def test_redacts_an_unlisted_person_name(self) -> None:
        result = self.redaction_service.sanitize_story(
            "I told Sarah Johnson that I still miss our long conversations."
        )

        self.assertTrue(result.ner_executed)
        self.assertTrue(result.pii_detected)
        self.assertEqual(
            result.redacted_text,
            "I told [PERSON] that I still miss our long conversations.",
        )

    def test_post_service_returns_redactions_and_stores_only_sanitized_public_text(self) -> None:
        payload = PostCreate(
            text=(
                "I am in love with Josh Allen. "
                "My email is john@gmail.com and my site is https://example.com."
            ),
            about="Josh Allen",
            mood="love",
        )

        response = self.post_service.create_post(payload)
        stored_post = self.session.query(Post).one()
        redactions = {(item.type, item.value) for item in response.redactions}

        self.assertTrue(response.pii_detected)
        self.assertIn(("PERSON", "Josh Allen"), redactions)
        self.assertIn(("EMAIL", "john@gmail.com"), redactions)
        self.assertIn(("URL", "https://example.com"), redactions)
        self.assertNotIn("Josh Allen", response.post.raw_text)
        self.assertIn("[PERSON]", response.post.raw_text)
        self.assertNotIn("john@gmail.com", response.post.raw_text)
        self.assertNotIn("https://example.com", response.post.raw_text)
        self.assertNotIn("Josh Allen", response.post.title)
        self.assertNotIn("josh", response.post.keywords)
        self.assertNotIn("allen", response.post.keywords)
        self.assertNotIn("person", response.post.keywords)
        self.assertEqual(response.post.content_type, "community")
        self.assertEqual(response.post.source_label, "From the Dearest community")
        self.assertIsNone(response.post.attribution)
        self.assertTrue(response.post.processing.pipeline_version)
        self.assertGreaterEqual(response.post.processing.redaction_count, 3)
        self.assertTrue(any(stage.name == "redaction" for stage in response.post.processing.stages))
        self.assertEqual(stored_post.private_raw_text, None)
        self.assertEqual(stored_post.hidden_subject, "[PERSON]")

    def test_generated_title_is_derived_from_sanitized_text(self) -> None:
        analysis = self.pipeline.process_story(
            "Josh Allen still crosses my mind whenever the night gets quiet and heavy.",
            selected_mood="longing",
        )
        self.assertNotIn("Josh Allen", analysis.title)
        self.assertIn("[PERSON]", analysis.title)

    def test_debug_mode_can_store_private_raw_text(self) -> None:
        os.environ["DEAREST_ADMIN_DEBUG_MODE"] = "true"
        get_settings.cache_clear()

        payload = PostCreate(
            text="I am in love with Josh Allen and I cannot move on from it.",
            about=None,
            mood="longing",
        )
        self.post_service.create_post(payload)
        stored_post = self.session.query(Post).one()
        self.assertEqual(stored_post.private_raw_text, payload.text)


if __name__ == "__main__":
    unittest.main()
