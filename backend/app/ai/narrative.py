"""Narrative analysis module."""

from __future__ import annotations

import math
import re
from collections import Counter

from .types import NarrativeAnalysis

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
}


class NarrativeAnalyzer:
    """Generates summary and story-shape metadata for a narrative."""

    def analyze(self, text: str) -> NarrativeAnalysis:
        """Analyze narrative-level structure while preserving current heuristic behavior."""
        sentences = self._split_sentences(text)
        summary = self._summarize_text(text, sentences)
        opening = sentences[0] if sentences else text.strip()
        closing = sentences[-1] if sentences else text.strip()
        estimated_read_time = max(1, math.ceil(len(text.strip().split()) / 180))
        return NarrativeAnalysis(
            summary=summary,
            opening=opening,
            closing=closing,
            estimated_read_time=estimated_read_time,
        )

    def generate_title(self, text: str) -> str:
        """Create a lightweight title heuristic from the opening sentence."""
        sentences = self._split_sentences(text)
        if not sentences:
            return "Untitled letter"

        first_sentence = sentences[0].strip().strip("\"'")
        words = first_sentence.split()
        if len(words) <= 10:
            return first_sentence
        return " ".join(words[:10]).rstrip(",;:") + "..."

    def _summarize_text(self, text: str, sentences: list[str]) -> str:
        if not sentences:
            return text.strip()
        if len(sentences) == 1:
            return sentences[0]

        tokens = [token for token in self._tokenize(text) if token not in STOPWORDS]
        frequencies = Counter(tokens)
        scored_sentences: list[tuple[float, str]] = []
        for sentence in sentences:
            sentence_tokens = self._tokenize(sentence)
            if not sentence_tokens:
                continue
            score = sum(frequencies[token] for token in sentence_tokens if token in frequencies)
            score = score / math.sqrt(len(sentence_tokens))
            scored_sentences.append((score, sentence))

        top_sentences = [sentence for _, sentence in sorted(scored_sentences, reverse=True)[:2]]
        ordered = [sentence for sentence in sentences if sentence in top_sentences]
        return " ".join(ordered)

    def _split_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z']+", text.lower())
