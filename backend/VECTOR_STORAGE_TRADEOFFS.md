# Vector Storage Tradeoffs

Current deployed default: `qdrant`

Implemented architectural modes in code:

- `qdrant`: embedded `qdrant-client` local mode, active default
- `local`: deterministic in-process cosine backend retained for tests and baselines
- `pgvector`: interface placeholder and documented alternative, not enabled in this repo

## Measured benchmark

Benchmark command:

```bash
cd /Users/saw/Documents/dearest
backend/.venv/bin/python -m backend.app.benchmark_retrieval
```

Measured on July 18, 2026 against the current local corpus:

- corpus size: `410`
- sampled queries: `20`
- brute-force cosine mean latency: `19.966 ms`
- qdrant-local ANN mean latency: `2.929 ms`

Gold retrieval evaluation from the same benchmark run:

- brute-force baseline: `Recall@5 0.379`, `Recall@10 0.561`, `MRR 0.792`, `NDCG 0.506`
- qdrant-backed candidate stack: `Recall@5 0.682`, `Recall@10 0.818`, `MRR 0.799`, `NDCG 0.712`

Result:

- qdrant-local is materially faster at the current corpus size
- retrieval quality did not regress against the existing gold evaluation harness
- `/api/posts/{id}/similar` now reads from the ANN-backed retrieval path through `RecommendationServiceV2`

## Qdrant Local

Pros:

- real ANN index in-repo without a separate service
- native payload filtering for `avoid_theme` and `avoid_content_note`
- fastest currently measured option in this codebase

Cons:

- exclusive file lock means one process owns the local index path at a time
- adds a vector sidecar directory on disk
- not transactional with SQLite writes

## Local Cosine

Pros:

- deterministic and lightweight
- useful for tests and regression baselines
- no index management

Cons:

- linear scan latency
- Python-side filtering only
- not suitable as the default archive backend as the corpus grows

## pgvector

Pros:

- strongest relational + vector consistency story
- good long-term option if Dearest moves to PostgreSQL

Cons:

- not implemented end-to-end in this repository
- would require a database platform shift beyond the current local stack

## Recommendation

For the current repository state:

1. Keep `qdrant` as the runtime default.
2. Keep `local` only for tests, deterministic baselines, and low-friction debugging.
3. Treat `pgvector` as a future migration target, not a current backend.
