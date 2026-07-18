"""Embedding and similarity service."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache

import numpy as np

from .types import EmbeddingResult

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


class EmbeddingService:
    """Generates embeddings and cosine similarity scores."""

    def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate a semantic embedding or fall back to TF-IDF mode metadata."""
        model = self._load_sentence_model()
        if model is None:
            return EmbeddingResult(embedding_model="tfidf", vector=None)

        vector = model.encode([text])[0]
        return EmbeddingResult(
            embedding_model="sentence-transformers",
            vector=vector.astype(float).tolist(),
        )

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        """Encode a batch of texts in a shared vector space for explainability work."""
        model = self._load_sentence_model()
        if model is None:
            return self._build_tfidf_matrix(texts)
        matrix = model.encode(texts)
        return np.array(matrix, dtype=float)

    def calculate_similarity(
        self,
        source_post: dict[str, object],
        posts: list[dict[str, object]],
    ) -> list[tuple[int, float]]:
        """Return ranked cosine similarity scores against a post corpus."""
        if len(posts) <= 1:
            return []

        source_index = next(
            (index for index, post in enumerate(posts) if post["id"] == source_post["id"]),
            None,
        )
        if source_index is None:
            return []

        use_sentence_vectors = all(
            post["embedding_model"] == "sentence-transformers" and post["embedding_json"] is not None
            for post in posts
        )

        if use_sentence_vectors:
            matrix = np.array([json.loads(str(post["embedding_json"])) for post in posts], dtype=float)
            scores = self._cosine_similarity_vector(matrix[source_index], matrix)
        else:
            matrix = self._build_tfidf_matrix([str(post["raw_text"]) for post in posts])
            scores = self._cosine_similarity_vector(matrix[source_index], matrix)

        ranked: list[tuple[int, float]] = []
        for index, score in enumerate(scores):
            if index == source_index:
                continue
            ranked.append((int(posts[index]["id"]), float(score)))
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    @staticmethod
    def serialize_vector(vector: list[float] | None) -> str | None:
        """Serialize an embedding vector for storage."""
        return json.dumps(vector) if vector is not None else None

    @staticmethod
    def serialize_json(payload: object) -> str:
        """Serialize an arbitrary JSON-compatible payload."""
        return json.dumps(payload)

    @staticmethod
    def deserialize_list(payload: str) -> list[str]:
        """Deserialize a stored JSON list."""
        return json.loads(payload)

    @staticmethod
    def serialize_list(items: list[str]) -> str:
        """Serialize a list to JSON."""
        return json.dumps(items)

    @staticmethod
    def serialize_dict(items: dict[str, float]) -> str:
        """Serialize a score dictionary to JSON."""
        return json.dumps(items)

    @staticmethod
    def deserialize_dict(payload: str | None) -> dict[str, float]:
        """Deserialize a stored JSON dictionary."""
        if not payload:
            return {}
        return {str(key): float(value) for key, value in json.loads(payload).items()}

    @staticmethod
    def deserialize_json(payload: str | None, default: object) -> object:
        """Deserialize any stored JSON payload with a fallback."""
        if not payload:
            return default
        return json.loads(payload)

    @lru_cache(maxsize=1)
    def _load_sentence_model(self):
        try:
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            return None

    def _cosine_similarity_vector(self, source: np.ndarray, matrix: np.ndarray) -> np.ndarray:
        source_norm = np.linalg.norm(source)
        row_norms = np.linalg.norm(matrix, axis=1)
        if source_norm == 0:
            return np.zeros(matrix.shape[0], dtype=float)

        safe_denominator = np.where(row_norms == 0, 1.0, row_norms * source_norm)
        similarities = matrix @ source / safe_denominator
        similarities[row_norms == 0] = 0.0
        return similarities

    def _build_tfidf_matrix(self, texts: list[str]) -> np.ndarray:
        documents: list[list[str]] = []
        for text in texts:
            words = [word for word in self._tokenize(text) if word not in STOPWORDS and len(word) > 2]
            bigrams = [f"{words[index]}_{words[index + 1]}" for index in range(len(words) - 1)]
            documents.append(words + bigrams)

        vocabulary = sorted({token for document in documents for token in document})
        if not vocabulary:
            return np.zeros((len(texts), 1), dtype=float)

        vocab_index = {token: idx for idx, token in enumerate(vocabulary)}
        document_frequency = Counter()
        for document in documents:
            for token in set(document):
                document_frequency[token] += 1

        total_docs = len(documents)
        matrix = np.zeros((total_docs, len(vocabulary)), dtype=float)
        for row_index, document in enumerate(documents):
            counts = Counter(document)
            doc_size = max(len(document), 1)
            for token, count in counts.items():
                tf = count / doc_size
                idf = math.log((1 + total_docs) / (1 + document_frequency[token])) + 1
                matrix[row_index, vocab_index[token]] = tf * idf
        return matrix

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z']+", text.lower())
