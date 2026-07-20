"""Backfill persisted embeddings into qdrant-local and update missing vectors."""

from __future__ import annotations

import argparse
from dataclasses import asdict

from .api.deps import build_services
from .database import SessionLocal
from .repositories import PostRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Dearest embeddings into the ANN index.")
    parser.add_argument("--force", action="store_true", help="Recompute embeddings for every post.")
    args = parser.parse_args()

    with SessionLocal() as session:
        services = build_services(session)
        post_service = services["post_service"]
        vector_storage = services["vector_storage"]
        repository = PostRepository(session)
        posts = repository.all_posts()
        refreshed = 0
        records = []

        for post in posts:
            if args.force or not post.embedding_json:
                refreshed_post = post_service.reindex_post(post.id)
                if refreshed_post is not None:
                    post = repository.get_post(post.id) or post
                    refreshed += 1
            records.append(post_service._to_recommendation_record(post))  # type: ignore[attr-defined]

        inserted = vector_storage.upsert_posts(records)
        print(
            {
                "posts_seen": len(posts),
                "embeddings_refreshed": refreshed,
                "vectors_upserted": inserted,
                "backend": vector_storage.describe(),
            }
        )


if __name__ == "__main__":
    main()
