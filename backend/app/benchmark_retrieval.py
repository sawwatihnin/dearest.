"""Benchmark brute-force cosine against qdrant-local ANN retrieval."""

from __future__ import annotations

from statistics import mean
import tempfile
from time import perf_counter

from .api.deps import build_services
from .database import SessionLocal
from .evaluate_archive import evaluate_retrieval
from .repositories import PostRepository
from .ai.vector_store import VectorQuery


def main() -> None:
    with SessionLocal() as session:
        services = build_services(session)
        post_service = services["post_service"]
        embedding_service = services["embedding_service"]
        vector_storage = services["vector_storage"]
        repository = PostRepository(session)
        posts = repository.all_posts()
        records = [post_service._to_recommendation_record(post) for post in posts]  # type: ignore[attr-defined]
        vector_storage.upsert_posts(records)

        sample = posts[: min(len(posts), 20)]
        brute_force_latencies: list[float] = []
        ann_latencies: list[float] = []

        for post in sample:
            source = post_service._to_recommendation_record(post)  # type: ignore[attr-defined]

            started = perf_counter()
            embedding_service.calculate_similarity(source, records)
            brute_force_latencies.append(round((perf_counter() - started) * 1000, 3))

            started = perf_counter()
            vector_storage.query(
                VectorQuery(
                    source_post=source,
                    candidate_posts=records,
                    limit=10,
                    exclude_post_id=post.id,
                )
            )
            ann_latencies.append(round((perf_counter() - started) * 1000, 3))

        with tempfile.TemporaryDirectory() as tmpdir:
            retrieval = evaluate_retrieval(qdrant_path=tmpdir)
        print(
            {
                "corpus_size": len(posts),
                "sampled_queries": len(sample),
                "brute_force_mean_ms": round(mean(brute_force_latencies), 3) if brute_force_latencies else 0.0,
                "ann_mean_ms": round(mean(ann_latencies), 3) if ann_latencies else 0.0,
                "retrieval_eval": {
                    "baseline": retrieval.baseline,
                    "candidate": retrieval.candidate,
                },
            }
        )


if __name__ == "__main__":
    main()
