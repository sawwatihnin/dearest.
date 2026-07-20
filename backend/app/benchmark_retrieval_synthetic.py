"""Large-scale synthetic retrieval benchmark for local vs qdrant-local."""

from __future__ import annotations

import json
import math
from statistics import mean
from time import perf_counter
from dataclasses import asdict

from .ai import EmbeddingService
from .ai.vector_store import LocalVectorStorage, QdrantLocalVectorStorage, VectorQuery
from .evaluate_archive import RetrievalMetrics


TOPIC_COUNT = 100
DOCS_PER_TOPIC = 100
RELEVANT_PER_TOPIC = 3
LATENCY_QUERY_SAMPLE = 25


def build_synthetic_records() -> tuple[list[dict[str, object]], dict[str, set[int]], list[dict[str, object]]]:
    embedding_service = EmbeddingService()
    records: list[dict[str, object]] = []
    relevant_lookup: dict[str, set[int]] = {}
    queries: list[dict[str, object]] = []
    post_id = 1

    moods = ("longing", "grief", "hope", "confusion", "love")
    themes = ("distance", "memory", "home", "identity", "future")

    for topic_index in range(TOPIC_COUNT):
        anchor = f"anchor_{topic_index}"
        mood = moods[topic_index % len(moods)]
        theme = themes[topic_index % len(themes)]
        relevant_ids: set[int] = set()
        for doc_index in range(DOCS_PER_TOPIC):
            relevant = doc_index < RELEVANT_PER_TOPIC
            text = (
                f"{anchor} {theme} {mood} letter variant {doc_index} about the same feeling returning softly"
                if relevant
                else f"decoy_{topic_index}_{doc_index} {theme} {mood} unrelated archive note {doc_index}"
            )
            embedding = embedding_service.generate_embedding(text)
            record = {
                "id": post_id,
                "raw_text": text,
                "summary": text,
                "embedding_json": embedding_service.serialize_vector(embedding.vector),
                "embedding_model": embedding.embedding_model,
                "pipeline_version": "synthetic-scale-v1",
                "detected_emotions_json": json.dumps([mood]),
                "semantic_profile_json": json.dumps({theme: 1.0}),
                "keywords_json": json.dumps([anchor, theme, mood]),
                "selected_content_notes_json": "[]",
                "content_type": "public_archive",
                "timeline_year": 1900 + topic_index,
                "created_at": f"{1900 + topic_index}-01-01T00:00:00",
            }
            if relevant:
                relevant_ids.add(post_id)
            records.append(record)
            post_id += 1

        query_text = f"{anchor} {theme} {mood} I keep returning to the same unfinished story"
        query_embedding = embedding_service.generate_embedding(query_text)
        query_id = f"synthetic_q_{topic_index}"
        relevant_lookup[query_id] = relevant_ids
        queries.append(
            {
                "query_id": query_id,
                "record": {
                    "id": 1_000_000 + topic_index,
                    "raw_text": query_text,
                    "summary": query_text,
                    "embedding_json": embedding_service.serialize_vector(query_embedding.vector),
                    "embedding_model": query_embedding.embedding_model,
                    "pipeline_version": "synthetic-scale-v1",
                    "detected_emotions_json": json.dumps([mood]),
                    "semantic_profile_json": json.dumps({theme: 1.0}),
                    "keywords_json": json.dumps([anchor, theme, mood]),
                    "selected_content_notes_json": "[]",
                    "content_type": "community",
                    "timeline_year": 2026,
                    "created_at": "2026-07-18T00:00:00",
                },
            }
        )

    return records, relevant_lookup, queries


def _p50(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[len(ordered) // 2], 3)


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
    return round(ordered[index], 3)


def _recall_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def _reciprocal_rank(ranked: list[int], relevant: set[int]) -> float:
    for index, post_id in enumerate(ranked, start=1):
        if post_id in relevant:
            return 1.0 / index
    return 0.0


def _dcg(ranked: list[int], relevant: set[int], k: int) -> float:
    total = 0.0
    for index, post_id in enumerate(ranked[:k], start=1):
        if post_id in relevant:
            total += 1.0 / (1.0 if index == 1 else math.log2(index))
    return total


def _ndcg(ranked: list[int], relevant: set[int], k: int) -> float:
    ideal = list(relevant)[:k]
    ideal_dcg = _dcg(ideal, relevant, k)
    if ideal_dcg == 0:
        return 0.0
    return _dcg(ranked, relevant, k) / ideal_dcg


def _aggregate_synthetic_metrics(
    ranked_lists: dict[str, list[int]], relevant_lookup: dict[str, set[int]]
) -> RetrievalMetrics:
    recall5 = []
    recall10 = []
    reciprocal = []
    ndcgs = []
    for query_id, ranked in ranked_lists.items():
        relevant = relevant_lookup[query_id]
        recall5.append(_recall_at_k(ranked, relevant, 5))
        recall10.append(_recall_at_k(ranked, relevant, 10))
        reciprocal.append(_reciprocal_rank(ranked, relevant))
        ndcgs.append(_ndcg(ranked, relevant, 10))
    return RetrievalMetrics(
        recall_at_5=round(mean(recall5), 3),
        recall_at_10=round(mean(recall10), 3),
        mrr=round(mean(reciprocal), 3),
        ndcg=round(mean(ndcgs), 3),
    )


def main() -> None:
    records, relevant_lookup, queries = build_synthetic_records()
    embedding_service = EmbeddingService()
    local_store = LocalVectorStorage(embedding_service)
    qdrant_store = QdrantLocalVectorStorage(embedding_service, "qdrant_eval")
    qdrant_store.upsert_posts(records)

    local_ranked: dict[str, list[int]] = {}
    qdrant_ranked: dict[str, list[int]] = {}
    local_latencies: list[float] = []
    qdrant_latencies: list[float] = []

    for index, query in enumerate(queries):
        query_record = query["record"]

        started = perf_counter()
        local_hits = local_store.query(
            VectorQuery(source_post=query_record, candidate_posts=records, limit=10)
        )
        local_ranked[query["query_id"]] = [post_id for post_id, _ in local_hits]
        if index < LATENCY_QUERY_SAMPLE:
            local_latencies.append(round((perf_counter() - started) * 1000, 3))

        started = perf_counter()
        qdrant_hits = qdrant_store.query(
            VectorQuery(source_post=query_record, candidate_posts=records, limit=10)
        )
        qdrant_ranked[query["query_id"]] = [post_id for post_id, _ in qdrant_hits]
        if index < LATENCY_QUERY_SAMPLE:
            qdrant_latencies.append(round((perf_counter() - started) * 1000, 3))

    print(
        json.dumps(
            {
                "corpus_type": "synthetic",
                "corpus_size": len(records),
                "query_count": len(queries),
                "relevant_per_query": RELEVANT_PER_TOPIC,
                "latency_sample_size": LATENCY_QUERY_SAMPLE,
                "local_ms": {
                    "mean": round(mean(local_latencies), 3),
                    "p50": _p50(local_latencies),
                    "p95": _p95(local_latencies),
                },
                "qdrant_ms": {
                    "mean": round(mean(qdrant_latencies), 3),
                    "p50": _p50(qdrant_latencies),
                    "p95": _p95(qdrant_latencies),
                },
                "quality": {
                    "local": asdict(_aggregate_synthetic_metrics(local_ranked, relevant_lookup)),
                    "qdrant": asdict(_aggregate_synthetic_metrics(qdrant_ranked, relevant_lookup)),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
