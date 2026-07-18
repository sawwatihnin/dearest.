"""Theme extraction module."""

from __future__ import annotations

import re
from collections import defaultdict

from .types import ThemeAnalysis

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "she",
    "so",
    "that",
    "the",
    "their",
    "them",
    "there",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "with",
    "you",
    "your",
    "person",
    "location",
    "organization",
    "email",
    "phone",
    "url",
    "instagram_handle",
    "twitter_handle",
    "discord_username",
    "address",
    "credit_card",
    "ssn",
}


class ThemeExtractor:
    """Extracts keywords and themes with a future-proof interface."""

    def analyze(self, text: str, limit: int = 5) -> ThemeAnalysis:
        """Return keyword and theme analysis for a story."""
        keyword_scores = self.score_keywords(text)
        keywords = [word for word, _ in sorted(keyword_scores.items(), key=lambda item: item[1], reverse=True)[:limit]]
        return ThemeAnalysis(keywords=keywords, themes=list(keywords), keyword_scores=keyword_scores)

    def extract_keywords(self, text: str, limit: int = 5) -> list[str]:
        """Use the current RAKE-style heuristic to extract keywords."""
        keyword_scores = self.score_keywords(text)
        ranked = sorted(keyword_scores.items(), key=lambda item: item[1], reverse=True)
        return [word for word, _ in ranked[:limit]]

    def score_keywords(self, text: str) -> dict[str, float]:
        """Return raw keyword salience scores for explainability and motifs."""
        phrases = re.split(r"[,.!?;:\n]", text.lower())
        word_scores: defaultdict[str, float] = defaultdict(float)
        for phrase in phrases:
            words = [word for word in self._tokenize(phrase) if word not in STOPWORDS and len(word) > 2]
            if not words:
                continue
            degree = max(len(words) - 1, 1)
            for word in words:
                word_scores[word] += degree
        return dict(word_scores)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z']+", text.lower())
