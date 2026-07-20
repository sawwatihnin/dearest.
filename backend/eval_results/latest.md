# Dearest Evaluation Results

Date: July 18, 2026

Environment notes:

- evaluation and benchmark were run from `backend/.venv`
- `EmbeddingService().generate_embedding(...)` resolved to `tfidf` in this environment
- the checked-in benchmark logic was executed against the existing `backend/qdrant_eval` path because the machine was too low on disk for tempfile-backed runs

Embedding backend check:

```python
{'embedding_model': 'tfidf', 'vector_dim': 256}
```

## 1. Evaluation Harness Output

Command used:

```bash
./.venv/bin/python -c "from app.evaluate_archive import evaluate_moderation,evaluate_privacy,evaluate_retrieval; from dataclasses import asdict; import json; print('=== Moderation ==='); print(json.dumps(asdict(evaluate_moderation()), indent=2)); print('=== Privacy ==='); print(json.dumps(asdict(evaluate_privacy()), indent=2)); print('=== Retrieval ==='); print(json.dumps(asdict(evaluate_retrieval(qdrant_path='qdrant_eval')), indent=2))"
```

Output:

```json
=== Moderation ===
{
  "by_segment": {
    "reflective_memoir": {
      "metrics": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0
      },
      "confusion_matrix": {
        "tp": 0,
        "tn": 26,
        "fp": 0,
        "fn": 0
      }
    },
    "active_self_harm": {
      "metrics": {
        "precision": 1.0,
        "recall": 0.808,
        "f1": 0.894
      },
      "confusion_matrix": {
        "tp": 21,
        "tn": 0,
        "fp": 0,
        "fn": 5
      }
    },
    "trauma": {
      "metrics": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0
      },
      "confusion_matrix": {
        "tp": 0,
        "tn": 26,
        "fp": 0,
        "fn": 0
      }
    },
    "abuse": {
      "metrics": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0
      },
      "confusion_matrix": {
        "tp": 0,
        "tn": 26,
        "fp": 0,
        "fn": 0
      }
    },
    "grief": {
      "metrics": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0
      },
      "confusion_matrix": {
        "tp": 0,
        "tn": 26,
        "fp": 0,
        "fn": 0
      }
    },
    "harassment": {
      "metrics": {
        "precision": 1.0,
        "recall": 0.731,
        "f1": 0.844
      },
      "confusion_matrix": {
        "tp": 19,
        "tn": 0,
        "fp": 0,
        "fn": 7
      }
    },
    "threats": {
      "metrics": {
        "precision": 1.0,
        "recall": 0.615,
        "f1": 0.762
      },
      "confusion_matrix": {
        "tp": 16,
        "tn": 0,
        "fp": 0,
        "fn": 10
      }
    }
  },
  "global_metrics": {
    "precision": 1.0,
    "recall": 0.718,
    "f1": 0.836
  },
  "confusion_matrix": {
    "tp": 56,
    "tn": 104,
    "fp": 0,
    "fn": 22
  }
}
=== Privacy ===
{
  "by_type": {
    "PERSON": {
      "false_negative_rate": 0.0,
      "false_positive_rate": 0.133,
      "span_boundary_accuracy": 0.867
    },
    "EMAIL": {
      "false_negative_rate": 0.0,
      "false_positive_rate": 0.0,
      "span_boundary_accuracy": 1.0
    },
    "PHONE": {
      "false_negative_rate": 0.0,
      "false_positive_rate": 0.0,
      "span_boundary_accuracy": 1.0
    },
    "ADDRESS": {
      "false_negative_rate": 0.0,
      "false_positive_rate": 0.0,
      "span_boundary_accuracy": 1.0
    },
    "LOCATION": {
      "false_negative_rate": 0.0,
      "false_positive_rate": 0.1,
      "span_boundary_accuracy": 0.9
    },
    "ORG": {
      "false_negative_rate": 0.0,
      "false_positive_rate": 0.1,
      "span_boundary_accuracy": 0.9
    }
  },
  "total_cases": 180
}
=== Retrieval ===
{
  "baseline": {
    "recall_at_5": 0.385,
    "recall_at_10": 0.591,
    "mrr": 0.645,
    "ndcg": 0.483
  },
  "candidate": {
    "recall_at_5": 0.658,
    "recall_at_10": 0.809,
    "mrr": 0.767,
    "ndcg": 0.7
  }
}
```

## 2. Retrieval Benchmark Output

Latency command used:

```bash
./.venv/bin/python -c "from app.database import SessionLocal; from app.api.deps import build_services; from app.repositories import PostRepository; from app.ai.vector_store import LocalVectorStorage,QdrantLocalVectorStorage,VectorQuery; from statistics import mean; from time import perf_counter; import json; session=SessionLocal(); services=build_services(session); post_service=services['post_service']; embedding_service=services['embedding_service']; repo=PostRepository(session); posts=repo.all_posts(); records=[post_service._to_recommendation_record(post) for post in posts]; local_store=LocalVectorStorage(embedding_service); qdrant_store=QdrantLocalVectorStorage(embedding_service,'qdrant_eval'); qdrant_store.upsert_posts(records); sample=posts[:min(len(posts),20)]; local_lat=[]; ann_lat=[]; \
for post in sample: \
 source=post_service._to_recommendation_record(post); t=perf_counter(); local_store.query(VectorQuery(source_post=source,candidate_posts=records,limit=10,exclude_post_id=post.id)); local_lat.append((perf_counter()-t)*1000); t=perf_counter(); qdrant_store.query(VectorQuery(source_post=source,candidate_posts=records,limit=10,exclude_post_id=post.id)); ann_lat.append((perf_counter()-t)*1000); \
local_lat=sorted(local_lat); ann_lat=sorted(ann_lat); p50=lambda arr: round(arr[len(arr)//2],3) if arr else 0.0; p95=lambda arr: round(arr[min(len(arr)-1, max(0, int(len(arr)*0.95)-1))],3) if arr else 0.0; print(json.dumps({'corpus_size': len(posts), 'sampled_queries': len(sample), 'local_ms': {'mean': round(mean(local_lat),3), 'p50': p50(local_lat), 'p95': p95(local_lat)}, 'qdrant_ms': {'mean': round(mean(ann_lat),3), 'p50': p50(ann_lat), 'p95': p95(ann_lat)}}, indent=2)); session.close()"
```

Output:

```json
{
  "corpus_size": 410,
  "sampled_queries": 20,
  "local_ms": {
    "mean": 11.804,
    "p50": 11.077,
    "p95": 16.5
  },
  "qdrant_ms": {
    "mean": 1.765,
    "p50": 1.565,
    "p95": 2.722
  }
}
```

Quality-comparison command used:

```bash
./.venv/bin/python -c "from app.ai import EmbeddingService,EmotionAnalyzer,ExplanationService,ExplainabilityService,RankingService,RecommendationServiceV2,RetrievalService,ThemeExtractor; from app.ai.vector_store import LocalVectorStorage,QdrantLocalVectorStorage; from app.evaluation_gold import RETRIEVAL_DOCUMENTS, RETRIEVAL_GOLD_CASES; from app.evaluate_archive import _to_record,_build_query_record,_aggregate_retrieval_metrics; from dataclasses import asdict; import json; es=EmbeddingService(); ea=EmotionAnalyzer(); te=ThemeExtractor(); ex=ExplainabilityService(embedding_service=es); records=[_to_record(doc, es) for doc in RETRIEVAL_DOCUMENTS]; local=RecommendationServiceV2(retrieval_service=RetrievalService(embedding_service=es, vector_storage=LocalVectorStorage(es)), ranking_service=RankingService(), explanation_service=ExplanationService()); qdrant=RecommendationServiceV2(retrieval_service=RetrievalService(embedding_service=es, vector_storage=QdrantLocalVectorStorage(es, 'qdrant_eval')), ranking_service=RankingService(), explanation_service=ExplanationService()); qdrant._retrieval_service.sync_candidates(records); local_ranked={}; qdrant_ranked={}; \
for case in RETRIEVAL_GOLD_CASES: \
 q=_build_query_record(case.text, embedding_service=es, emotion_analyzer=ea, theme_extractor=te, explainability_service=ex); lb=local.build_bundle(source_post=q, candidate_posts=records, top_k=10, avoid_theme=case.avoid_theme, avoid_content_note=case.avoid_content_note); qb=qdrant.build_bundle(source_post=q, candidate_posts=records, top_k=10, avoid_theme=case.avoid_theme, avoid_content_note=case.avoid_content_note); local_ranked[case.query_id]=[item.post_id for item in lb.recommendations]; qdrant_ranked[case.query_id]=[item.post_id for item in qb.recommendations]; \
print(json.dumps({'local': asdict(_aggregate_retrieval_metrics(local_ranked)), 'qdrant': asdict(_aggregate_retrieval_metrics(qdrant_ranked))}, indent=2))"
```

Output:

```json
{
  "query_count": 110,
  "local": {
    "recall_at_5": 0.658,
    "recall_at_10": 0.809,
    "mrr": 0.766,
    "ndcg": 0.7
  },
  "qdrant": {
    "recall_at_5": 0.658,
    "recall_at_10": 0.809,
    "mrr": 0.767,
    "ndcg": 0.7
  }
}
```

Synthetic-scale benchmark command used:

```bash
./.venv/bin/python -m app.benchmark_retrieval_synthetic
```

Output:

```json
{
  "corpus_type": "synthetic",
  "corpus_size": 10000,
  "query_count": 100,
  "relevant_per_query": 3,
  "latency_sample_size": 25,
  "local_ms": {
    "mean": 205.708,
    "p50": 199.175,
    "p95": 243.478
  },
  "qdrant_ms": {
    "mean": 274.963,
    "p50": 270.971,
    "p95": 285.367
  },
  "quality": {
    "local": {
      "recall_at_5": 0.083,
      "recall_at_10": 0.167,
      "mrr": 0.075,
      "ndcg": 0.1
    },
    "qdrant": {
      "recall_at_5": 0.083,
      "recall_at_10": 0.167,
      "mrr": 0.11,
      "ndcg": 0.1
    }
  }
}
```

Interpretation note:

- the synthetic benchmark is intentionally disclosed as synthetic and TF-IDF-backed, not as a claim about production-grade semantic quality
- it is best read as a scale smoke test showing that the small-corpus qdrant latency win does not automatically carry over to every synthetic workload in this environment
