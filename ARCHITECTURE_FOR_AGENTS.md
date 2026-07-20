# Dearest Architecture Handoff

Last updated: July 18, 2026

This document is the current implementation-level architecture guide for the Dearest codebase. It is written for AI agents and engineers who need to extend the system without accidentally redesigning working paths.

## 1. What Dearest Is

Dearest is an anonymous emotional writing platform with two archive content types:

- `community`: letters submitted by Dearest users
- `public_archive`: curated public-domain writing used to seed the archive

The experience currently supports:

- anonymous letter submission
- async post creation with job polling
- moderation before persistence
- PII detection and redaction before downstream NLP
- summaries, moods, keywords, semantic profiles, and embeddings
- similar letters and grounded match explanations
- Echoes chains
- historical timeline views
- archive explorer filters
- media recommendations

## 2. Current Stack

### Frontend

- React 18
- TypeScript
- Vite
- React Router
- single global stylesheet in `frontend/src/styles.css`

### Backend

- FastAPI
- SQLAlchemy
- SQLite
- Celery task wrapper for async processing
- Redis-compatible transient state settings for job stages
- Alembic migration directory is present and startup expects schema to exist

### NLP / retrieval

- spaCy-backed redaction with regex augmentation
- heuristic moderation tuned to allow autobiographical trauma writing while blocking active unsafe intent
- sentence-transformers when available
- hashed TF-IDF fallback embeddings when transformer models are unavailable
- dual-stage retrieval services exist
- local cosine vector backend is the deliberate runtime default for clone-and-run simplicity
- qdrant-local is implemented and can be enabled for ANN retrieval or reindexing work

## 3. Repo Map

### Top level

- `backend/`
- `frontend/`
- `ARCHITECTURE_FOR_AGENTS.md`

### Backend hotspots

- `backend/app/main.py`
  FastAPI app, lifespan startup, CORS, correlation IDs, rate limiting, telemetry headers.

- `backend/app/api/posts.py`
  Public API routes and admin utility endpoints.

- `backend/app/api/deps.py`
  Request-scoped dependency graph. This is the place that selects the current vector backend.

- `backend/app/services/processing_service.py`
  Async job orchestration, idempotency hashing, job persistence, DLQ path.

- `backend/app/services/post_service.py`
  Main read/write domain service. Handles post creation, summary payload building, similar letters, Echoes, archive explorer, media recommendations, and timeline assembly.

- `backend/app/ai/pipeline.py`
  Main content-processing pipeline.

- `backend/app/ai/moderation.py`
  Safety classifier and unsafe-content decisions.

- `backend/app/ai/redaction.py`
  PII detection and redaction. This is the privacy boundary.

- `backend/app/ai/embeddings.py`
  Embedding generation, TF-IDF fallback, similarity math.

- `backend/app/ai/vector_store.py`
  `VectorStorageInterface`, `LocalVectorStorage`, `QdrantLocalVectorStorage`, documented `PgvectorVectorStorage`.

- `backend/app/ai/production_services.py`
  Retrieval, ranking, explanation, evaluation helpers, and the active `RecommendationServiceV2` stack.

- `backend/app/models/post.py`
  Core content table.

- `backend/app/models/job.py`
  Async processing job table.

- `backend/app/models/dead_letter.py`
  Dead-letter queue table.

- `backend/app/repositories/post_repository.py`
- `backend/app/repositories/job_repository.py`
  Data-access layer for posts and jobs.

- `backend/app/database/session.py`
  SQLite engine configuration and pragmatic low-disk SQLite settings.

- `backend/app/database/schema.py`
  Lightweight schema compatibility helpers for existing SQLite instances.

- `backend/app/telemetry.py`
  Minimal Prometheus-style in-process telemetry registry.

- `backend/app/evaluate_archive.py`
  Evaluation harness for moderation, privacy, and retrieval.

- `backend/app/reindex_embeddings.py`
  Rebuild/backfill utility for vector storage.

- `backend/app/tasks.py`
  Celery task entrypoint.

- `backend/app/seed.py`
  Local seed behavior on startup.

### Frontend hotspots

- `frontend/src/App.tsx`
  Routes, page-level data fetching, async job polling, story-page composition.

- `frontend/src/api.ts`
  All frontend HTTP calls. API base is currently hardcoded to `http://127.0.0.1:8000/api`.

- `frontend/src/types.ts`
  Client-side contract mirror for posts, jobs, similarity, Echoes, and explorer filters.

- `frontend/src/components/ArchiveEnhancements.tsx`
  Archive explorer controls, attribution, content note panel, media recs, Echoes UI, timeline UI, similar-letter cards.

- `frontend/src/components/BehindArchiveExperience.tsx`
  “Behind the Archive” page.

- `frontend/src/styles.css`
  Global look and layout system.

## 4. Runtime Defaults

These defaults matter because earlier architecture docs assumed different behavior.

- `vector_backend` default: `local`
- `DEAREST_VECTOR_BACKEND=qdrant` opt-in is supported
- qdrant initialization failure falls back to local vector storage in `backend/app/api/deps.py`
- Celery eager mode defaults effectively on for local dev via `get_settings()`
- CORS allows localhost and `127.0.0.1` on arbitrary Vite-style ports

The current retrieval default is a deliberate onboarding/default-runtime choice:

- use local vector storage by default
- keep qdrant available as an opt-in implementation path and tooling target
- prioritize clone-and-run simplicity with no vector-index sidecar requirement for the default path
- preserve the same API response shapes either way
- accept that Section 7.2's benchmark favors qdrant-local on latency while keeping the default optimized for local onboarding and deterministic fallback behavior

## 5. End-to-End Write Flow

### 5.1 Frontend submission flow

Source:

- `frontend/src/App.tsx`
- `frontend/src/api.ts`

Flow:

1. User submits a letter from `/write`.
2. Frontend calls `createPost(...)`.
3. Backend returns either:
   - `200` with cached completed payload, or
   - `202` with `job_id` and `status`
4. Frontend polls `GET /api/jobs/{job_id}` until completion.
5. On completion, frontend navigates to `/archive/:id`.

### 5.2 Backend async orchestration flow

Source:

- `backend/app/api/posts.py`
- `backend/app/services/processing_service.py`
- `backend/app/tasks.py`

Flow:

1. `POST /api/posts` enters `ProcessingService.submit_post(...)`.
2. A deterministic content hash is computed:
   - `sha256(text + "::" + pipeline_version)`
3. If a matching completed job exists, cached JSON is returned.
4. If a matching in-flight job exists, API returns `202` for the existing job.
5. Otherwise a new processing job is inserted.
6. API returns `202 Accepted`.
7. `process_post_job.delay(job_id)` is triggered.
8. Celery task rehydrates services and calls `processing_service.process_job(job_id)`.
9. On success, completed job payload is stored in `processing_jobs.result_json`.
10. On failure, status becomes `FAILED` and a dead-letter entry is written.

Known gap:

- the job row is durably written before Celery dispatch
- if `process_post_job.delay(job_id)` fails after the DB write succeeds, there is currently no orphan-sweep or reconciliation worker for `PENDING` jobs that never get picked up
- that gap should be treated as a real operational sharp edge, not an already-solved recovery path

### 5.3 Processing stages

The pipeline order is:

1. moderation
2. privacy / PII redaction
3. narrative summary and title generation
4. emotion analysis
5. keyword and theme extraction
6. embeddings
7. semantic projection / explainability metadata
8. persistence
9. recommendation payload generation

Critical rule:

- after redaction, downstream AI components must use sanitized text only

## 6. Moderation and Privacy Boundary

### 6.1 Moderation

Source:

- `backend/app/ai/moderation.py`

Current intent:

- block active self-harm intent
- block self-harm encouragement or instructions
- block direct violent threat patterns
- block direct harassment patterns that cross policy boundaries
- allow autobiographical writing about grief, abuse, illness, war, heartbreak, discrimination, and identity when it is reflective rather than actively unsafe

### 6.2 Privacy / redaction

Source:

- `backend/app/ai/redaction.py`

spaCy model fallback order:

- `en_core_web_lg`
- `en_core_web_md`
- `en_core_web_sm`

Structured/regex redaction coverage includes:

- `PERSON`
- `ORG`
- `GPE`
- `LOC`
- `FAC`
- email
- phone
- URL
- social handles
- Discord-style usernames
- street addresses
- credit card numbers
- SSNs

Important implementation guarantees:

- span-based replacement, not naive `string.replace`
- adjacent person tokens are merged
- full names should redact as one unit
- titles and bodies both pass through privacy handling
- public-facing archive content should display sanitized text only
- raw text is only appropriate for debug/admin pathways

## 7. Retrieval and Recommendation Architecture

### 7.1 The active stack

Source:

- `backend/app/ai/production_services.py`
- `backend/app/ai/vector_store.py`
- `backend/app/services/post_service.py`

Active layers:

1. `VectorStorageInterface`
2. retrieval service
3. ranking service
4. explanation service
5. `RecommendationServiceV2`

Boundary note:

- `PostService` calls `RecommendationServiceV2.build_bundle(...)` abstractly and does not branch on vector backend type
- backend selection happens in `backend/app/api/deps.py` through `_build_vector_storage(...)`
- switching between `local` and `qdrant` requires zero modification to `backend/app/services/post_service.py` in the current code

### 7.2 Vector storage behavior

Current implementations:

- `LocalVectorStorage`
  deterministic in-process cosine retrieval, current default

- `QdrantLocalVectorStorage`
  embedded ANN retrieval with payload filters

- `PgvectorVectorStorage`
  documented alternative, not active in this repo

Measured benchmark evidence from July 18, 2026 is checked in at:

- `backend/eval_results/latest.md`

Current benchmark table at corpus size `410` and query sample size `20`:

| Backend | Mean ms | P50 ms | P95 ms | Recall@5 | Recall@10 | MRR | NDCG |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `LocalVectorStorage` | 11.804 | 11.077 | 16.5 | 0.658 | 0.809 | 0.766 | 0.700 |
| `QdrantLocalVectorStorage` | 1.765 | 1.565 | 2.722 | 0.658 | 0.809 | 0.767 | 0.700 |

Sample-size note:

- the latency sample here is a demo-scale benchmark over a `410`-post corpus with `20` sampled queries, and the retrieval-quality columns are drawn from the checked-in gold retrieval set (`110` queries over `20` reference documents); these numbers are useful directional evidence, not a claim of statistical significance or noise-free precision

Additional scale benchmark, also from July 18, 2026:

| Corpus | Backend | Mean ms | P50 ms | P95 ms | Recall@5 | Recall@10 | MRR | NDCG |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| synthetic `10,000` docs / `100` queries | `LocalVectorStorage` | 205.708 | 199.175 | 243.478 | 0.083 | 0.167 | 0.075 | 0.100 |
| synthetic `10,000` docs / `100` queries | `QdrantLocalVectorStorage` | 274.963 | 270.971 | 285.367 | 0.083 | 0.167 | 0.110 | 0.100 |

Sample-size and corpus note:

- this second benchmark is intentionally disclosed as synthetic, not production-ground-truth data
- corpus size was `10,000` with `100` synthetic queries and a `25`-query latency sample
- because the environment resolved to hashed TF-IDF embeddings rather than MiniLM, and because the synthetic corpus was anchor-token-driven rather than human writing, treat this as a scaling smoke test rather than a decisive product-quality ranking result

Interpretation:

- qdrant-local is materially faster on the measured corpus
- retrieval quality is effectively identical on the small checked-in gold set
- the larger synthetic benchmark did not reproduce the small-corpus latency win, so the evidence is mixed rather than one-directional
- Dearest still keeps `local` as the default because it is the simplest clone-and-run path for new contributors, while qdrant-local remains the recommended opt-in when a developer specifically wants to test ANN behavior or reproduce the small-corpus latency win
- qdrant tooling and evaluation paths still exist
- if qdrant is enabled but cannot initialize, the dependency builder falls back to local

### 7.3 Embedding behavior

Source:

- `backend/app/ai/embeddings.py`

Behavior:

- preferred transformer path: `all-MiniLM-L6-v2`
- fallback path: fixed-dimension hashed TF-IDF vectors
- vectors are serialized into `posts.embedding_json`
- `embedding_model` records which backend produced the vector

Latest evidence note:

- the July 18, 2026 evidence pass resolved `EmbeddingService().generate_embedding(...)` to `tfidf`
- a direct MiniLM-versus-TF-IDF retrieval comparison is therefore implemented but not yet benchmarked in this environment

### 7.4 Similar letters

Source:

- `backend/app/services/post_service.py`

Status:

- implemented and exercised by the app
- retrieval quality is benchmarked at the backend level in Sections 7.2 and 12
- card-level UX quality is not separately benchmarked in this document

`GET /api/posts/{id}/similar` returns:

- `source_post`
- `similar_posts`
- `media_recommendations`
- top-level explanation string

Each `SimilarPost` includes:

- similarity score
- confidence label
- calibrated confidence placeholder
- shared concepts
- shared themes
- shared emotions
- shared keywords
- dominant tone
- narrative explanation
- supporting excerpt

### 7.5 Echoes

Source:

- `backend/app/services/post_service.py`

Status:

- implemented and used by the story page
- not separately benchmarked as a chain-quality metric in this document

Echoes is a chain walk built by repeatedly asking `RecommendationServiceV2` for the next best unseen writing. It returns:

- `source_post`
- ordered `chain`
- each step includes a `relation_explanation`

### 7.6 Timeline

Timeline data is assembled on the frontend from:

- the current story
- similar posts
- Echoes chain entries

The UI label is currently:

- `Letters like yours throughout the years`

Status:

- implemented in the frontend
- not separately benchmarked in this document

## 8. Data Model

### 8.1 Posts

Source:

- `backend/app/models/post.py`

Core post fields:

- `id`
- `content_hash`
- `content_type`
- `ingestion_key`
- `title`
- `raw_text`
- `private_raw_text`
- `hidden_subject`
- attribution fields
- `selected_mood`
- `detected_mood`
- `detected_emotions_json`
- `emotion_distribution_json`
- `summary`
- `keywords_json`
- `keyword_profile_json`
- `semantic_profile_json`
- `cluster_label`
- `warning_terms_json`
- `selected_content_notes_json`
- `pipeline_version`
- `processing_trace_json`
- `embedding_json`
- `embedding_model`
- `embedding_versions_json`
- `pipeline_versions_json`
- `created_at`

Content-type contract:

- `community` entries do not require author attribution
- `public_archive` entries use attribution metadata and rights metadata

### 8.2 Jobs

Processing jobs track:

- `id`
- `content_hash`
- `pipeline_version`
- `status`
- `correlation_id`
- `payload_json`
- `result_json`
- `post_id`
- `attempt_count`
- `error_message`
- `terminal_trace_json`

### 8.3 Dead-letter queue

Dead-letter entries track:

- failed job identity
- correlation ID
- content hash
- original payload
- error type/message
- traceback

## 9. Public Archive Representation

Verified public-domain content is represented inside the same `posts` table with:

- `content_type = "public_archive"`
- attribution metadata filled
- optional collections, themes, emotions, notes, etc. generated through the same NLP path

This keeps semantic search shared across:

- community letters
- public archive writings

Frontend rule:

- the UI must clearly distinguish public archive results from community letters

Current rendering behavior:

- public archive story pages show attribution metadata and source links
- community story pages do not render the extra attribution panel

## 10. Frontend Information Architecture

Routes:

- `/`
- `/write`
- `/archive`
- `/archive/:id`
- `/post/:id`
- `/behind-the-archive`

### Home

Purpose:

- cinematic landing page only

### Write

Purpose:

- submission surface
- async submit progress
- optional content note selection

### Archive

Purpose:

- explorer and browsing surface
- supports content-type, mood, theme, year, collection, and avoid-filter controls

### Story page

Purpose:

- reading page
- emotional fingerprint
- media recommendations
- Echoes
- timeline
- similar letters

Important note:

- community stories no longer show a standalone source attribution panel
- public archive stories still do

### Behind the Archive

Purpose:

- AI/process explanation page

## 11. Telemetry, Rate Limiting, and Observability

### Middleware

Source:

- `backend/app/main.py`

Status:

- implemented
- not separately stress-benchmarked in this evidence pass

Current middleware responsibilities:

- assign or propagate `X-Correlation-ID`
- attach `X-Request-Id` and `X-Correlation-Id` response headers
- apply simple in-memory IP-based rate limiting
- emit latency observations to telemetry registry

### Metrics

Source:

- `backend/app/telemetry.py`
- `GET /api/metrics`

Status:

- implemented
- not separately load-tested in this document

Current telemetry style:

- in-process counters
- in-process latency distributions
- Prometheus-like plaintext render

Examples of tracked concerns in the codebase:

- rate-limit blocks
- processing completions
- dead-letter queue entries
- embedding fallback events

## 12. Evaluation and Testing

### Evaluation harness

Source:

- `backend/app/evaluate_archive.py`
- `backend/app/evaluation_gold.py`

The harness currently measures:

- moderation precision / recall / F1 / confusion
- privacy false-negative and false-positive rates by PII type
- retrieval recall@5 / recall@10 / MRR / NDCG

Latest captured run:

- full raw output is checked in at `backend/eval_results/latest.md`

Moderation, July 18, 2026:

- gold-set size note: `182` total moderation cases, with `26` cases per segment, so segment-level figures are more useful than before but still not large enough to treat as production-certification evidence
- global precision: `1.0`
- global recall: `0.718`
- global F1: `0.836`
- global confusion: `tp=56 tn=104 fp=0 fn=22`
- segment recall:
  - `active_self_harm`: `0.808`
  - `threats`: `0.615`
  - `harassment`: `0.731`
  - reflective safe segments (`reflective_memoir`, `trauma`, `abuse`, `grief`) were evaluated as all-true-negative sets in this gold split

Privacy, July 18, 2026:

- gold-set size note: `180` total privacy cases, with `30` examples per PII type, so the numbers are materially better grounded than the earlier six-per-type run but still not a substitute for adversarial real-world evaluation
- `PERSON`: `FNR 0.0 / FPR 0.133 / boundary 0.867`
- `EMAIL`: `FNR 0.0 / FPR 0.0 / boundary 1.0`
- `PHONE`: `FNR 0.0 / FPR 0.0 / boundary 1.0`
- `ADDRESS`: `FNR 0.0 / FPR 0.0 / boundary 1.0`
- `LOCATION`: `FNR 0.0 / FPR 0.1 / boundary 0.9`
- `ORG`: `FNR 0.0 / FPR 0.1 / boundary 0.9`

Retrieval, July 18, 2026:

- gold-set size note: `110` retrieval queries over the same `20` reference documents, so the candidate-stack lift is better supported than before but still bounded by the small archive reference set
- baseline: `recall@5 0.385 / recall@10 0.591 / MRR 0.645 / NDCG 0.483`
- candidate stack: `recall@5 0.658 / recall@10 0.809 / MRR 0.767 / NDCG 0.700`

### Tests

Test coverage lives under:

- `backend/tests/`

Notable focus areas include:

- privacy pipeline
- async hardening
- evaluation harness
- content source handling
- qdrant retrieval behavior

## 13. Database / Migration State

Two migration mechanisms coexist:

- Alembic exists as the formal migration boundary
- `backend/app/database/schema.py` still contains compatibility helpers for SQLite instances

Startup behavior in `backend/app/main.py` currently expects schema to already exist:

- if the `posts` table is missing, app startup raises and tells the operator to run Alembic migrations first

Practical implication for agents:

- do not assume `ensure_schema()` is the primary schema bootstrap forever
- prefer evolving Alembic for deliberate schema changes
- keep compatibility helpers only when they are still needed for local upgrade safety

## 14. Operational Scripts

Useful repo scripts and utilities:

- `backend/dev.sh`
  start backend in local dev mode

- `frontend` Vite scripts
  start frontend and build client

- `backend/app/reindex_embeddings.py`
  refresh embeddings and backfill vector store

- `backend/app/benchmark_retrieval.py`
  retrieval benchmarking utility

- `backend/app/benchmark_retrieval_synthetic.py`
  larger-scale synthetic retrieval benchmark for evidence maturity

- `backend/app/evaluate_archive.py`
  evaluation harness runner

- `backend/app/ingest_public_archive.py`
  public archive ingestion path

## 15. Failure Demonstration

The implemented failure path today is:

1. submission enters moderation
2. unsafe content is rejected before persistence
3. safe content is redacted before downstream NLP
4. a processing job row is written
5. Celery dispatch is attempted
6. worker execution retries transient failures
7. terminal worker failure marks the job `FAILED`
8. a dead-letter record is written with payload, traceback, and correlation ID
9. admin replay tooling can replay a dead-letter entry back through processing

Important honesty note:

- this is not a fully transactional outbox design
- if DB write succeeds and dispatch never fires, the job can remain orphaned in `PENDING`
- that specific case is a known gap today

## 16. Architecture Decision Records

Short ADRs live in:

- `ADRs/`

The current set records the measured reasons for moderation ordering, span-based privacy, local-by-default retrieval, TF-IDF fallback, clone-and-run philosophy, Redis-vs-DB transient stage tracking, and qdrant as an opt-in path.

## 17. Current Sharp Edges

These are the main realities an agent should respect before changing architecture:

- the async API contract is live even though local Celery execution often runs eagerly
- vector retrieval has both local and qdrant implementations; local remains the deliberate default for clone-and-run simplicity, while qdrant-local is the measured faster opt-in path on the small real benchmark and a mixed-result path on the larger synthetic benchmark
- startup seeding is still part of app lifespan
- SQLite is still the persistence layer, so avoid features that assume high-concurrency production RDBMS semantics
- frontend contracts expect current response shapes, especially for jobs, similar posts, Echoes, and explorer filters
- privacy and moderation happen before downstream NLP and must stay that way
- community and public archive content must remain clearly labeled and not be visually conflated
- the async path still lacks an orphan-job sweeper for DB-written but never-dispatched `PENDING` jobs

## 18. Safe Extension Rules For Agents

When extending the system:

1. Preserve API response shapes unless you are intentionally versioning them.
2. Do not move moderation after NLP.
3. Do not move privacy/redaction after embeddings, summaries, or keyword extraction.
4. Do not present `public_archive` content as if it were a user submission.
5. Preserve the current default/opt-in split: `local` is the clone-and-run default, `qdrant-local` is the faster optional retrieval backend.
6. Prefer extending `PostService` and `RecommendationServiceV2` rather than adding parallel orchestration paths.
7. Keep frontend story-page enhancements compatible with the current route/data model.
8. If you change schema, update Alembic and then update this document.

## 19. Best First Files To Read

If you are new to the repo, read in this order:

1. `backend/app/api/posts.py`
2. `backend/app/services/processing_service.py`
3. `backend/app/services/post_service.py`
4. `backend/app/ai/pipeline.py`
5. `backend/app/ai/redaction.py`
6. `backend/app/ai/production_services.py`
7. `backend/app/ai/vector_store.py`
8. `frontend/src/App.tsx`
9. `frontend/src/components/ArchiveEnhancements.tsx`
10. `frontend/src/api.ts`
