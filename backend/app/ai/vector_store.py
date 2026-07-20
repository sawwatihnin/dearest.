"""Qdrant-backed vector storage for Dearest retrieval."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from threading import RLock
from typing import Protocol

from .embeddings import EmbeddingService, TFIDF_VECTOR_DIMENSION

_QDRANT_CLIENTS: dict[str, object] = {}
_QDRANT_LOCKS: dict[str, RLock] = {}


def _slug(value: str) -> str:
    lowered = value.lower()
    return re.sub(r"[^a-z0-9]+", "_", lowered).strip("_") or "default"


def _collection_name(pipeline_version: str, embedding_model: str, dimension: int) -> str:
    return f"dearest_{_slug(pipeline_version)}_{_slug(embedding_model)}_{dimension}"


@dataclass(slots=True)
class VectorQuery:
    source_post: dict[str, object]
    candidate_posts: list[dict[str, object]]
    limit: int = 50
    exclude_post_id: int | None = None
    avoid_theme: str | None = None
    avoid_content_note: str | None = None


class VectorStorageInterface(Protocol):
    def upsert_posts(self, posts: list[dict[str, object]]) -> int: ...
    def query(self, request: VectorQuery) -> list[tuple[int, float]]: ...
    def describe(self) -> dict[str, str]: ...


class LocalVectorStorage:
    """Deterministic in-process cosine backend used for tests and benchmarking baselines."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    def upsert_posts(self, posts: list[dict[str, object]]) -> int:
        return len([post for post in posts if self._vector_for(post) is not None])

    def query(self, request: VectorQuery) -> list[tuple[int, float]]:
        filtered = [
            candidate
            for candidate in request.candidate_posts
            if self._passes_filters(
                candidate,
                exclude_post_id=request.exclude_post_id,
                avoid_theme=request.avoid_theme,
                avoid_content_note=request.avoid_content_note,
            )
        ]
        comparison_corpus = [request.source_post, *filtered]
        scored = self._embedding_service.calculate_similarity(request.source_post, comparison_corpus)
        return [(int(post_id), float(score)) for post_id, score in scored[: request.limit]]

    def describe(self) -> dict[str, str]:
        return {
            "backend": "local-cosine",
            "filtering": "python-side filtering before cosine similarity",
            "tradeoff": "simple and deterministic, but scales linearly with corpus size",
        }

    def _passes_filters(
        self,
        post: dict[str, object],
        *,
        exclude_post_id: int | None,
        avoid_theme: str | None,
        avoid_content_note: str | None,
    ) -> bool:
        if exclude_post_id is not None and int(post["id"]) == exclude_post_id:
            return False
        if avoid_theme and avoid_theme in self._deserialize_profile_keys(post.get("semantic_profile_json")):
            return False
        if avoid_content_note and avoid_content_note in self._deserialize_list(post.get("selected_content_notes_json")):
            return False
        return True

    def _vector_for(self, post: dict[str, object]) -> list[float] | None:
        raw = post.get("embedding_json")
        if raw:
            vector = self._embedding_service.deserialize_json(str(raw), default=None)
            if isinstance(vector, list):
                return [float(value) for value in vector]
        preferred_model = str(post.get("embedding_model") or "tfidf")
        text = str(post.get("raw_text") or post.get("summary") or "")
        if not text:
            return None
        generated = self._embedding_service.generate_embedding(text, preferred_model=preferred_model)
        return generated.vector

    def _deserialize_list(self, payload: object) -> list[str]:
        parsed = self._embedding_service.deserialize_json(str(payload or "[]"), default=[])
        return [str(item) for item in parsed] if isinstance(parsed, list) else []

    def _deserialize_profile_keys(self, payload: object) -> list[str]:
        parsed = self._embedding_service.deserialize_json(str(payload or "{}"), default={})
        if not isinstance(parsed, dict):
            return []
        return [str(key) for key, value in parsed.items() if float(value) > 0]


class QdrantLocalVectorStorage:
    """Concrete embedded ANN backend using qdrant-local."""

    def __init__(self, embedding_service: EmbeddingService, base_path: str | Path) -> None:
        self._embedding_service = embedding_service
        self._base_path = self._resolve_base_path(Path(base_path))
        self._base_path.mkdir(parents=True, exist_ok=True)
        from qdrant_client import QdrantClient

        cache_key = str(self._base_path.resolve())
        client = _QDRANT_CLIENTS.get(cache_key)
        if client is None:
            client = QdrantClient(path=cache_key)
            _QDRANT_CLIENTS[cache_key] = client
        self._client = client
        self._lock = _QDRANT_LOCKS.setdefault(cache_key, RLock())

    def upsert_posts(self, posts: list[dict[str, object]]) -> int:
        grouped: dict[str, dict[str, object]] = {}
        for post in posts:
            embedding = self._vector_for(post)
            if embedding is None:
                continue
            collection = self._collection_for_post(post, len(embedding))
            if collection not in grouped:
                grouped[collection] = {"dimension": len(embedding), "posts": []}
            grouped[collection]["posts"].append({**post, "__vector__": embedding})

        inserted = 0
        from qdrant_client.models import PointStruct

        for collection_name, entry in grouped.items():
            dimension = int(entry["dimension"])
            batch = list(entry["posts"])
            with self._lock:
                self._ensure_collection(collection_name, dimension)
                points: list[PointStruct] = []
                for post in batch:
                    payload = {
                        "post_id": int(post["id"]),
                        "content_type": str(post.get("content_type") or "community"),
                        "pipeline_version": str(post.get("pipeline_version") or "unknown"),
                        "embedding_model": str(post.get("embedding_model") or "tfidf"),
                        "themes": list(self._deserialize_profile_keys(post.get("semantic_profile_json"))),
                        "content_notes": list(self._deserialize_list(post.get("selected_content_notes_json"))),
                    }
                    points.append(
                        PointStruct(
                            id=int(post["id"]),
                            vector=post["__vector__"],
                            payload=payload,
                        )
                    )
                self._client.upsert(collection_name=collection_name, points=points)
            inserted += len(points)
        return inserted

    def query(self, request: VectorQuery) -> list[tuple[int, float]]:
        source_vector = self._vector_for(request.source_post)
        if source_vector is None:
            return []
        collection_name = self._collection_for_post(request.source_post, len(source_vector))
        from qdrant_client.models import FieldCondition, Filter, HasIdCondition, MatchValue

        must: list[object] = []
        must_not: list[object] = []
        candidate_ids = [int(candidate["id"]) for candidate in request.candidate_posts]
        if candidate_ids:
            must.append(HasIdCondition(has_id=candidate_ids))
        if request.exclude_post_id is not None:
            must_not.append(HasIdCondition(has_id=[int(request.exclude_post_id)]))
        if request.avoid_theme:
            must_not.append(FieldCondition(key="themes", match=MatchValue(value=request.avoid_theme)))
        if request.avoid_content_note:
            must_not.append(
                FieldCondition(key="content_notes", match=MatchValue(value=request.avoid_content_note))
            )

        with self._lock:
            existing = {item.name for item in self._client.get_collections().collections}
            if collection_name not in existing:
                return []
            response = self._client.search(
                collection_name=collection_name,
                query_vector=source_vector,
                limit=request.limit,
                with_payload=True,
                query_filter=Filter(must=must or None, must_not=must_not or None),
            )
        return [(int(item.id), float(item.score)) for item in response]

    def describe(self) -> dict[str, str]:
        return {
            "backend": "qdrant-local",
            "filtering": "native qdrant payload filters for avoid_theme and avoid_content_note",
            "tradeoff": "real ANN locally without a separate service, but adds a vector index sidecar on disk",
        }

    def _resolve_base_path(self, requested_path: Path) -> Path:
        requested_path.mkdir(parents=True, exist_ok=True)
        try:
            from qdrant_client import QdrantClient

            probe = QdrantClient(path=str(requested_path.resolve()))
            probe.close()
            return requested_path
        except RuntimeError as exc:
            if "already accessed by another instance of Qdrant client" not in str(exc):
                raise
            fallback = requested_path / f"pid-{os.getpid()}"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    def _ensure_collection(self, collection_name: str, dimension: int) -> None:
        existing = {item.name for item in self._client.get_collections().collections}
        if collection_name in existing:
            return
        from qdrant_client.models import Distance, VectorParams

        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )

    def _collection_for_post(self, post: dict[str, object], dimension: int) -> str:
        return _collection_name(
            str(post.get("pipeline_version") or "unknown"),
            str(post.get("embedding_model") or "tfidf"),
            dimension,
        )

    def _vector_for(self, post: dict[str, object]) -> list[float] | None:
        raw = post.get("embedding_json")
        if raw:
            vector = self._embedding_service.deserialize_json(str(raw), default=None)
            if isinstance(vector, list):
                return [float(value) for value in vector]
        preferred_model = str(post.get("embedding_model") or "tfidf")
        text = str(post.get("raw_text") or post.get("summary") or "")
        if not text:
            return None
        generated = self._embedding_service.generate_embedding(text, preferred_model=preferred_model)
        return generated.vector

    def _deserialize_list(self, payload: object) -> list[str]:
        parsed = self._embedding_service.deserialize_json(str(payload or "[]"), default=[])
        return [str(item) for item in parsed] if isinstance(parsed, list) else []

    def _deserialize_profile_keys(self, payload: object) -> list[str]:
        parsed = self._embedding_service.deserialize_json(str(payload or "{}"), default={})
        if not isinstance(parsed, dict):
            return []
        return [str(key) for key, value in parsed.items() if float(value) > 0]


class PgvectorVectorStorage:
    """Documented alternative backend behind the same protocol."""

    def upsert_posts(self, posts: list[dict[str, object]]) -> int:  # pragma: no cover - documented alternative
        raise NotImplementedError("pgvector backend is documented as an alternative, not enabled in this repo.")

    def query(self, request: VectorQuery) -> list[tuple[int, float]]:  # pragma: no cover - documented alternative
        raise NotImplementedError("pgvector backend is documented as an alternative, not enabled in this repo.")

    def describe(self) -> dict[str, str]:
        return {
            "backend": "pgvector",
            "filtering": "would use SQL + vector payload filters",
            "tradeoff": "best transactional locality, but not the active backend in this repository",
        }
