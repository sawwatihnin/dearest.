from __future__ import annotations

import unittest

from app.ai import EmbeddingService, EmotionAnalyzer, ExplainabilityService, ThemeExtractor


class ExplainabilityLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.embedding_service = EmbeddingService()
        self.emotion_analyzer = EmotionAnalyzer()
        self.theme_extractor = ThemeExtractor()
        self.explainability_service = ExplainabilityService(embedding_service=self.embedding_service)

    def test_semantic_projection_returns_extendable_human_profile(self) -> None:
        text = (
            "I still know the evening train to your city by heart. "
            "Distance keeps teaching memory how to wait."
        )
        embedding = self.embedding_service.generate_embedding(text)
        emotion = self.emotion_analyzer.analyze(text, selected_mood="longing")
        themes = self.theme_extractor.analyze(text)

        projection = self.explainability_service.project_story(
            text=text,
            embedding=embedding,
            emotion=emotion,
            themes=themes,
        )

        self.assertIn("memory", projection.semantic_profile)
        self.assertIn("distance", projection.semantic_profile)
        self.assertTrue(all(0.0 <= score <= 1.0 for score in projection.semantic_profile.values()))
        self.assertTrue(all(0.0 <= score <= 1.0 for score in projection.keyword_profile.values()))
        self.assertTrue(all(0.0 <= score <= 1.0 for score in projection.emotion_distribution.values()))
        self.assertLessEqual(len(projection.top_motifs), 5)
        self.assertIsNotNone(projection.cluster)

    def test_match_explanation_stays_decoupled_from_ranking(self) -> None:
        source_text = "I miss the train platform where goodbye still feels unfinished."
        matched_text = "Distance keeps the station lit inside my memory."

        source_projection = self.explainability_service.project_story(
            text=source_text,
            embedding=self.embedding_service.generate_embedding(source_text),
            emotion=self.emotion_analyzer.analyze(source_text, selected_mood="longing"),
            themes=self.theme_extractor.analyze(source_text),
        )
        matched_projection = self.explainability_service.project_story(
            text=matched_text,
            embedding=self.embedding_service.generate_embedding(matched_text),
            emotion=self.emotion_analyzer.analyze(matched_text, selected_mood="nostalgia"),
            themes=self.theme_extractor.analyze(matched_text),
        )

        explanation = self.explainability_service.explain_match(
            source_profile=source_projection,
            matched_profile=matched_projection,
            embedding_similarity=0.9134,
        )

        self.assertEqual(explanation.embedding_similarity, 0.913)
        self.assertLessEqual(len(explanation.shared_concepts), 5)
        self.assertEqual(explanation.matched_story_profile, matched_projection.semantic_profile)
        self.assertEqual(explanation.top_motifs, matched_projection.top_motifs)


if __name__ == "__main__":
    unittest.main()
