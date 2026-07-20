"""Statistical evaluation harness for moderation, privacy, and retrieval."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from .ai import (
    EmbeddingService,
    EmotionAnalyzer,
    ExplanationService,
    ExplainabilityService,
    ModerationService,
    RankingService,
    RecommendationServiceV2,
    RedactionService,
    RetrievalService,
    ThemeExtractor,
)
from .ai.vector_store import QdrantLocalVectorStorage
from .evaluation_gold import (
    MODERATION_GOLD_CASES,
    PRIVACY_GOLD_CASES,
    RETRIEVAL_DOCUMENTS,
    RETRIEVAL_GOLD_CASES,
)

@dataclass(frozen=True, slots=True)
class ClassificationMetrics:
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True, slots=True)
class ModerationEvaluation:
    by_segment: dict[str, dict[str, object]]
    global_metrics: ClassificationMetrics
    confusion_matrix: dict[str, int]


@dataclass(frozen=True, slots=True)
class PrivacyTypeMetrics:
    false_negative_rate: float
    false_positive_rate: float
    span_boundary_accuracy: float


@dataclass(frozen=True, slots=True)
class PrivacyEvaluation:
    by_type: dict[str, PrivacyTypeMetrics]
    total_cases: int


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    recall_at_5: float
    recall_at_10: float
    mrr: float
    ndcg: float


@dataclass(frozen=True, slots=True)
class RetrievalEvaluation:
    baseline: RetrievalMetrics
    candidate: RetrievalMetrics


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    moderation: ModerationEvaluation
    privacy: PrivacyEvaluation
    retrieval: RetrievalEvaluation


def main() -> None:
    report = evaluate_all()
    _print_report(report)


def evaluate_all() -> EvaluationReport:
    return EvaluationReport(
        moderation=evaluate_moderation(),
        privacy=evaluate_privacy(),
        retrieval=evaluate_retrieval(),
    )


def evaluate_moderation() -> ModerationEvaluation:
    service = ModerationService()
    grouped: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    overall: list[tuple[bool, bool]] = []
    for case in MODERATION_GOLD_CASES:
        predicted_safe = service.analyze(case.text).safe
        grouped[case.segment].append((case.expected_safe, predicted_safe))
        overall.append((case.expected_safe, predicted_safe))

    by_segment: dict[str, dict[str, object]] = {}
    for segment, items in grouped.items():
        metrics = _classification_metrics(items)
        by_segment[segment] = {
            "metrics": asdict(metrics),
            "confusion_matrix": _confusion(items),
        }

    return ModerationEvaluation(
        by_segment=by_segment,
        global_metrics=_classification_metrics(overall),
        confusion_matrix=_confusion(overall),
    )


def evaluate_privacy() -> PrivacyEvaluation:
    service = RedactionService()
    grouped: dict[str, list[tuple[bool, bool, bool]]] = defaultdict(list)
    for case in PRIVACY_GOLD_CASES:
        result = service.sanitize_story(case.text)
        fn = case.target_value in result.redacted_text
        fp = case.expected_redacted != result.redacted_text
        exact = case.expected_redacted == result.redacted_text
        grouped[case.pii_type].append((fn, fp, exact))

    metrics: dict[str, PrivacyTypeMetrics] = {}
    for pii_type, rows in grouped.items():
        total = len(rows)
        false_negatives = sum(1 for fn, _, _ in rows if fn)
        false_positives = sum(1 for _, fp, _ in rows if fp)
        exact_boundaries = sum(1 for _, _, exact in rows if exact)
        metrics[pii_type] = PrivacyTypeMetrics(
            false_negative_rate=round(false_negatives / total, 3),
            false_positive_rate=round(false_positives / total, 3),
            span_boundary_accuracy=round(exact_boundaries / total, 3),
        )
    return PrivacyEvaluation(by_type=metrics, total_cases=len(PRIVACY_GOLD_CASES))


def evaluate_retrieval(qdrant_path: str | Path | None = None) -> RetrievalEvaluation:
    embedding_service = EmbeddingService()
    emotion_analyzer = EmotionAnalyzer()
    theme_extractor = ThemeExtractor()
    explainability_service = ExplainabilityService(embedding_service=embedding_service)
    source_records = [_to_record(doc, embedding_service) for doc in RETRIEVAL_DOCUMENTS]
    baseline_ranked: dict[str, list[int]] = {}
    candidate_ranked: dict[str, list[int]] = {}

    recommendation_service = RecommendationServiceV2(
        retrieval_service=RetrievalService(
            embedding_service=embedding_service,
            vector_storage=QdrantLocalVectorStorage(
                embedding_service,
                qdrant_path or "backend/qdrant_eval",
            ),
        ),
        ranking_service=RankingService(),
        explanation_service=ExplanationService(),
    )

    for case in RETRIEVAL_GOLD_CASES:
        query = _build_query_record(
            case.text,
            embedding_service=embedding_service,
            emotion_analyzer=emotion_analyzer,
            theme_extractor=theme_extractor,
            explainability_service=explainability_service,
        )
        baseline_ranked[case.query_id] = _baseline_rank(query, source_records, embedding_service, case)
        bundle = recommendation_service.build_bundle(
            source_post=query,
            candidate_posts=source_records,
            top_k=10,
            avoid_theme=case.avoid_theme,
            avoid_content_note=case.avoid_content_note,
        )
        candidate_ranked[case.query_id] = [item.post_id for item in bundle.recommendations]

    return RetrievalEvaluation(
        baseline=_aggregate_retrieval_metrics(baseline_ranked),
        candidate=_aggregate_retrieval_metrics(candidate_ranked),
    )


def _baseline_rank(
    query: dict[str, object],
    records: list[dict[str, object]],
    embedding_service: EmbeddingService,
    case,
) -> list[int]:
    filtered = []
    for record in records:
        if case.avoid_theme and case.avoid_theme in json.loads(str(record["semantic_profile_json"])):
            continue
        if case.avoid_content_note and case.avoid_content_note in json.loads(str(record["selected_content_notes_json"])):
            continue
        filtered.append(record)
    ranked = embedding_service.calculate_similarity(query, [query, *filtered])
    return [post_id for post_id, _ in ranked[:10]]


def _aggregate_retrieval_metrics(ranked_lists: dict[str, list[int]]) -> RetrievalMetrics:
    recall5 = []
    recall10 = []
    reciprocal = []
    ndcgs = []
    relevant_lookup = {case.query_id: set(case.relevant_ids) for case in RETRIEVAL_GOLD_CASES}
    for query_id, ranked in ranked_lists.items():
        relevant = relevant_lookup[query_id]
        recall5.append(_recall_at_k(ranked, relevant, 5))
        recall10.append(_recall_at_k(ranked, relevant, 10))
        reciprocal.append(_reciprocal_rank(ranked, relevant))
        ndcgs.append(_ndcg(ranked, relevant, 10))
    return RetrievalMetrics(
        recall_at_5=round(_mean(recall5), 3),
        recall_at_10=round(_mean(recall10), 3),
        mrr=round(_mean(reciprocal), 3),
        ndcg=round(_mean(ndcgs), 3),
    )


def _classification_metrics(rows: list[tuple[bool, bool]]) -> ClassificationMetrics:
    confusion = _confusion(rows)
    tp = confusion["tp"]
    fp = confusion["fp"]
    fn = confusion["fn"]
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return ClassificationMetrics(round(precision, 3), round(recall, 3), round(f1, 3))


def _confusion(rows: list[tuple[bool, bool]]) -> dict[str, int]:
    confusion = Counter({"tp": 0, "tn": 0, "fp": 0, "fn": 0})
    for expected_safe, predicted_safe in rows:
        expected_positive = not expected_safe
        predicted_positive = not predicted_safe
        if expected_positive and predicted_positive:
            confusion["tp"] += 1
        elif expected_positive and not predicted_positive:
            confusion["fn"] += 1
        elif not expected_positive and predicted_positive:
            confusion["fp"] += 1
        else:
            confusion["tn"] += 1
    return dict(confusion)


def _to_record(doc, embedding_service: EmbeddingService) -> dict[str, object]:
    embedding = embedding_service.generate_embedding(doc.text)
    return {
        "id": doc.doc_id,
        "raw_text": doc.text,
        "summary": doc.text,
        "embedding_json": embedding_service.serialize_vector(embedding.vector),
        "embedding_model": embedding.embedding_model,
        "pipeline_version": "gold-eval-v1",
        "detected_emotions_json": json.dumps(list(doc.emotions)),
        "semantic_profile_json": json.dumps({theme: 1.0 for theme in doc.themes}),
        "keywords_json": json.dumps(list(doc.themes)),
        "selected_content_notes_json": json.dumps(["grief"] if "grief" in doc.emotions else []),
        "content_type": "public_archive",
        "timeline_year": 1900 + doc.doc_id,
        "created_at": f"{1900 + doc.doc_id}-01-01T00:00:00",
    }


def _build_query_record(
    text: str,
    *,
    embedding_service: EmbeddingService,
    emotion_analyzer: EmotionAnalyzer,
    theme_extractor: ThemeExtractor,
    explainability_service: ExplainabilityService,
) -> dict[str, object]:
    embedding = embedding_service.generate_embedding(text)
    emotion = emotion_analyzer.analyze(text)
    themes = theme_extractor.analyze(text)
    projection = explainability_service.project_story(
        text=text,
        embedding=embedding,
        emotion=emotion,
        themes=themes,
    )
    return {
        "id": 0,
        "raw_text": text,
        "summary": text,
        "embedding_json": embedding_service.serialize_vector(embedding.vector),
        "embedding_model": embedding.embedding_model,
        "pipeline_version": "gold-eval-v1",
        "detected_emotions_json": json.dumps(emotion_analyzer.top_emotions(emotion)),
        "semantic_profile_json": json.dumps(projection.semantic_profile),
        "keywords_json": json.dumps(themes.keywords),
        "content_type": "community",
        "selected_content_notes_json": "[]",
        "timeline_year": 2026,
        "created_at": "2026-07-18T00:00:00",
    }


def _recall_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    return sum(1 for item in ranked[:k] if item in relevant) / max(len(relevant), 1)


def _reciprocal_rank(ranked: list[int], relevant: set[int]) -> float:
    for index, item in enumerate(ranked, start=1):
        if item in relevant:
            return 1.0 / index
    return 0.0


def _ndcg(ranked: list[int], relevant: set[int], k: int) -> float:
    dcg = 0.0
    for index, item in enumerate(ranked[:k], start=1):
        if item in relevant:
            dcg += 1.0 / math.log2(index + 1)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return 0.0 if idcg == 0 else dcg / idcg


def _mean(values: list[float]) -> float:
    return sum(values) / max(len(values), 1)


def _print_report(report: EvaluationReport) -> None:
    print("=== Moderation ===")
    print(json.dumps(asdict(report.moderation), indent=2))
    print("=== Privacy ===")
    print(json.dumps(asdict(report.privacy), indent=2))
    print("=== Retrieval ===")
    print(json.dumps(asdict(report.retrieval), indent=2))


if __name__ == "__main__":
    main()
