"""Emotion analysis module."""

from __future__ import annotations

import re

from .types import EmotionProfile

MOOD_LEXICON = {
    "heartbreak": {"broken", "heartbreak", "shattered", "left", "ended", "miss", "goodbye"},
    "longing": {"wish", "longing", "yearn", "ache", "waiting", "someday", "distance"},
    "anger": {"angry", "rage", "furious", "resent", "betrayed", "lied", "scream"},
    "nostalgia": {"memory", "remember", "summer", "used", "once", "old", "before"},
    "confusion": {"unclear", "confused", "mixed", "unsure", "maybe", "question", "lost"},
    "healing": {"healing", "growth", "forgive", "soften", "better", "recover", "learn"},
    "love": {"love", "adore", "tender", "safe", "home", "kiss", "devotion"},
    "grief": {"grief", "mourning", "gone", "funeral", "absence", "empty", "loss"},
}


class EmotionAnalyzer:
    """Scores emotional signals in a story without coupling to any other AI stage."""

    def analyze(self, text: str, selected_mood: str | None = None) -> EmotionProfile:
        """Return the dominant emotion, raw scores, and a simple confidence estimate."""
        scores = self.score(text, selected_mood)
        dominant_emotion = max(scores, key=scores.get)
        if scores[dominant_emotion] <= 0:
            dominant_emotion = selected_mood or "other"

        total = sum(max(score, 0) for score in scores.values())
        dominant_score = max(scores.get(dominant_emotion, 0), 0)
        confidence = round(dominant_score / total, 3) if total else 0.0
        return EmotionProfile(
            dominant_emotion=dominant_emotion,
            emotion_scores=scores,
            confidence=confidence,
        )

    def top_emotions(
        self, emotion_profile: EmotionProfile, selected_mood: str | None = None, limit: int = 3
    ) -> list[str]:
        """Return the highest-scoring emotions for UI display."""
        ranked = sorted(
            emotion_profile.emotion_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        positive = [mood for mood, score in ranked if score > 0]
        if positive:
            return positive[:limit]
        return [selected_mood or "other"]

    def score(self, text: str, selected_mood: str | None = None) -> dict[str, int]:
        """Score all known emotion buckets."""
        tokens = set(self._tokenize(text))
        scores: dict[str, int] = {}
        for mood, lexicon in MOOD_LEXICON.items():
            scores[mood] = len(tokens & lexicon)

        if selected_mood and selected_mood in scores:
            scores[selected_mood] += 2

        return scores

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z']+", text.lower())
