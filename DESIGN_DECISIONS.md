# Dearest Design Decisions

Last updated: July 18, 2026

This file records the current architectural choices using only the measured evidence captured in [backend/eval_results/latest.md](/Users/saw/Documents/dearest/backend/eval_results/latest.md). Short ADRs now also live in [ADRs/README.md](/Users/saw/Documents/dearest/ADRs/README.md).

## Why local cosine is still the default

The evidence is now mixed rather than one-directional. On the small real corpus benchmark, local retrieval measured `11.077 ms p50 / 16.5 ms p95`, while qdrant-local measured `1.565 ms p50 / 2.722 ms p95`, and the retrieval-quality metrics on the judged set were effectively identical. On the larger disclosed synthetic benchmark (`10,000` docs, `100` queries, `25` latency samples), local measured `199.175 ms p50 / 243.478 ms p95`, while qdrant-local measured `270.971 ms p50 / 285.367 ms p95`, with similarly weak quality for both under TF-IDF embeddings. Dearest therefore keeps local as the deliberate default because it is the simplest clone-and-run path for anyone opening the repo without needing a vector-index sidecar in the default flow, and because the current measured evidence no longer supports a universal claim that qdrant-local is always the better runtime default. Qdrant-local remains the opt-in backend for developers who want to reproduce the small-corpus ANN latency win or test the interface boundary directly.

## What the TF-IDF fallback costs versus MiniLM

A direct MiniLM-versus-TF-IDF recall comparison could not be produced in this environment because the embedding stack resolved to `{'embedding_model': 'tfidf', 'vector_dim': 256}` during the evidence pass, so the retrieval evaluation captured only the TF-IDF-backed path. The measured retrieval numbers for the current environment are therefore TF-IDF numbers (`baseline recall@5 0.385 / candidate recall@5 0.658 / candidate NDCG 0.700` on the expanded `110`-query gold set), and any claim about the incremental benefit of MiniLM over TF-IDF remains unproven in this repo until a run is captured with `embedding_model == sentence-transformers`.

## Why Alembic and schema.py still coexist

The repo now has both a formal migration boundary (`backend/alembic/`) and SQLite compatibility helpers in `backend/app/database/schema.py`; the evidence pass did not surface a measured runtime penalty for that overlap, but it did confirm that startup expects the schema to exist before the app boots. The practical removal condition is therefore concrete: the compatibility helpers can be deleted once every supported local database is migrated exclusively through Alembic and no startup, seed, or upgrade path still depends on `schema.py` adding missing columns or tables.

## What is explicitly out of scope right now

Authentication is out of scope because the current measured work is centered on anonymous submission, retrieval quality, moderation, and privacy boundaries, and no auth-related benchmark or evaluation path exists in the evidence set.

An admin UI is out of scope because the current admin surface is API-only (`/api/admin/...`) and this evidence pass did not produce any UI-facing admin requirement or test coverage.

Distributed Celery/Redis-by-default is out of scope because the measured local flow already exercises the async job contract while the current environment still runs with eager-friendly defaults, and this pass gathered no benchmark demonstrating that switching the default execution mode is required for the current local product goals.
