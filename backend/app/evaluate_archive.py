"""Offline evaluation harness for Dearest retrieval and privacy checks."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass

from pydantic import BaseModel, Field

from .ai import (
    EmbeddingService,
    EvaluationService,
    ExplanationService,
    RankingService,
    RecommendationServiceV2,
    RetrievalService,
)
from .database import SessionLocal, ensure_schema
from .models import Post
from .repositories import PostRepository


class JudgeResult(BaseModel):
    label: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    details: dict[str, object] = Field(default_factory=dict)


@dataclass(slots=True)
class GoldQuery:
    post: Post
    relevant_ids: set[int]


PII_LEAK_PATTERN = re.compile(
    r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+|[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|https?://\S+)\b"
)


def main() -> None:
    ensure_schema()
    with SessionLocal() as session:
        repository = PostRepository(session)
        posts = repository.all_posts()
        if len(posts) < 3:
            print("No evaluation corpus available.")
            return

        embedding_service = EmbeddingService()
        recommendation_service = RecommendationServiceV2(
            retrieval_service=RetrievalService(embedding_service=embedding_service),
            ranking_service=RankingService(),
            explanation_service=ExplanationService(),
        )
        evaluation_service = EvaluationService()
        gold_queries = build_gold_queries(posts)

        ranked_lists: dict[int, list[int]] = {}
        bundles = {}
        post_lookup = {post.id: post for post in posts}
        candidate_records = [to_record(post) for post in posts]
        for query in gold_queries:
            bundle = recommendation_service.build_bundle(
                source_post=to_record(query.post),
                candidate_posts=candidate_records,
                top_k=10,
            )
            ranked_lists[query.post.id] = [item.post_id for item in bundle.recommendations]
            bundles[query.post.id] = bundle

        for k in (3, 5, 10):
            precision = mean(
                precision_at_k(ranked_lists[query.post.id], query.relevant_ids, k) for query in gold_queries
            )
            recall = mean(
                recall_at_k(ranked_lists[query.post.id], query.relevant_ids, k) for query in gold_queries
            )
            ndcg = mean(
                ndcg_at_k(ranked_lists[query.post.id], query.relevant_ids, k) for query in gold_queries
            )
            print(f"Precision@{k}: {precision:.3f}")
            print(f"Recall@{k}: {recall:.3f}")
            print(f"NDCG@{k}: {ndcg:.3f}")

        faithfulness = evaluate_faithfulness(gold_queries, ranked_lists, post_lookup, bundles)
        leakage = evaluate_adversarial_leakage(posts)
        print("Faithfulness:", faithfulness.model_dump_json())
        print("AdversarialLeakage:", leakage.model_dump_json())
        print("BundleSummary:", evaluation_service.summarize_bundle(next(iter(bundles.values()))))


def build_gold_queries(posts: list[Post]) -> list[GoldQuery]:
    theme_buckets: dict[str, list[Post]] = defaultdict(list)
    for post in posts:
        if post.cluster_label:
            theme_buckets[post.cluster_label].append(post)
    queries: list[GoldQuery] = []
    for _, bucket in sorted(theme_buckets.items(), key=lambda item: len(item[1]), reverse=True)[:8]:
        if len(bucket) < 3:
            continue
        query = bucket[0]
        relevant = {post.id for post in bucket[1:6]}
        queries.append(GoldQuery(post=query, relevant_ids=relevant))
    return queries


def to_record(post: Post) -> dict[str, object]:
    return {
        "id": post.id,
        "raw_text": post.raw_text,
        "summary": post.summary,
        "embedding_json": post.embedding_json,
        "embedding_model": post.embedding_model,
        "detected_emotions_json": post.detected_emotions_json,
        "semantic_profile_json": post.semantic_profile_json,
        "keywords_json": post.keywords_json,
        "content_type": post.content_type,
        "selected_content_notes_json": post.selected_content_notes_json,
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }


def precision_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    top = ranked[:k]
    if not top:
        return 0.0
    hits = sum(1 for item in top if item in relevant)
    return hits / len(top)


def recall_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    if not relevant:
        return 0.0
    top = ranked[:k]
    hits = sum(1 for item in top if item in relevant)
    return hits / len(relevant)


def ndcg_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    top = ranked[:k]
    dcg = 0.0
    for index, item in enumerate(top, start=1):
        if item in relevant:
            dcg += 1.0 / math.log2(index + 1)
    ideal_hits = min(len(relevant), k)
    if ideal_hits == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / idcg


def evaluate_faithfulness(
    gold_queries: list[GoldQuery],
    ranked_lists: dict[int, list[int]],
    post_lookup: dict[int, Post],
    bundles: dict[int, object],
) -> JudgeResult:
    unsupported = 0
    total = 0
    for query in gold_queries:
        source_tokens = token_set(query.post.raw_text)
        bundle = bundles[query.post.id]
        for recommendation in bundle.recommendations[:3]:
            explanation = bundle.explanations.get(recommendation.post_id)
            matched_post = post_lookup.get(recommendation.post_id)
            if explanation is None or matched_post is None:
                continue
            allowed = source_tokens | token_set(matched_post.raw_text)
            for token in token_set(explanation.narrative_explanation):
                total += 1
                if token not in allowed and token not in {"pieces", "echo", "through", "nearby", "archive", "resonance"}:
                    unsupported += 1
    score = 1.0 if total == 0 else max(0.0, 1.0 - unsupported / total)
    return JudgeResult(
        label="faithfulness",
        passed=unsupported == 0,
        score=round(score, 3),
        details={"unsupported_tokens": unsupported, "inspected_tokens": total},
    )


def evaluate_adversarial_leakage(posts: list[Post]) -> JudgeResult:
    community_posts = [post for post in posts if post.content_type == "community"]
    leaking_posts = 0
    for post in community_posts:
        text_bundle = " ".join(
            [
                post.title or "",
                post.raw_text,
                post.summary,
                post.keywords_json,
                post.semantic_profile_json,
            ]
        )
        if PII_LEAK_PATTERN.search(text_bundle):
            leaking_posts += 1
    score = 1.0 if not community_posts else max(0.0, 1.0 - leaking_posts / len(community_posts))
    return JudgeResult(
        label="adversarial_leakage",
        passed=leaking_posts == 0,
        score=round(score, 3),
        details={"leaking_posts": leaking_posts, "inspected_posts": len(community_posts)},
    )


def token_set(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z']+", text)}


def mean(values) -> float:
    values = list(values)
    return sum(values) / max(len(values), 1)


if __name__ == "__main__":
    main()
