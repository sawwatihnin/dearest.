# **_Dearest._**

**_Dearest._** is a demo-ready anonymous emotional writing platform. Users can publish anonymous diary-style stories, receive lightweight AI summaries and emotional tags, and discover related writing from both the Dearest community and a curated public archive.

## Stack

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + SQLite + SQLAlchemy
- NLP: extractive summarization, RAKE-style keyword extraction, keyword-based mood detection, cosine similarity with sentence-transformers fallback to TF-IDF

## Archive content model

Dearest supports two clearly separated archive sources:

- `community`: anonymous letters submitted by real Dearest users
- `public_archive`: verified public-domain or otherwise legally permitted writing imported locally

Both sources live in the same semantic search corpus so similarity matching can compare across them, but the API and UI label them distinctly.

## Folder structure

```text
dearest/
├── backend/
│   ├── app/
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── nlp.py
│   │   ├── schemas.py
│   │   └── seed.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── styles.css
│   │   └── types.ts
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.app.json
│   ├── tsconfig.json
│   └── vite.config.ts
└── README.md
```

## Run locally

### 1. Backend

```bash
cd /Users/saw/Documents/dearest/backend
./dev.sh
```

If you prefer to run the steps manually:

```bash
cd /Users/saw/Documents/dearest/backend
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload
```

Before starting the API, apply the schema migration once:

```bash
cd /Users/saw/Documents/dearest
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
```

Use `python3 -m uvicorn`, not bare `uvicorn`, so the command always resolves inside the active environment. The API starts at `http://127.0.0.1:8000`.

### 2. Frontend

```bash
cd /Users/saw/Documents/dearest/frontend
./dev.sh
```

If you prefer the manual path:

```bash
cd /Users/saw/Documents/dearest/frontend
npm install
npm run dev
```

Vite will usually start at `http://127.0.0.1:5173`, but it may choose another local port if 5173 is already in use.

## Common setup pitfall

If you see `zsh: command not found: uvicorn`, you are either:

- outside the backend virtual environment, or
- using `uvicorn ...` directly instead of `python3 -m uvicorn ...`

The safest path is:

```bash
cd /Users/saw/Documents/dearest/backend
./dev.sh
```

## Public archive ingestion

Dearest does **not** scrape external sites automatically and does **not** ship with fabricated literary content.

To add verified public-domain material:

1. Copy [backend/data/public_archive_entries.example.json](/Users/saw/Documents/dearest/backend/data/public_archive_entries.example.json) to `backend/data/public_archive_entries.json`
2. Add only texts you have verified are public domain or otherwise legally permitted
3. Include attribution metadata and rights notes for each entry
4. Run:

```bash
cd /Users/saw/Documents/dearest/backend
source .venv/bin/activate
python -m app.ingest_public_archive
```

The ingestion is idempotent by `ingestion_key`, so re-running it updates existing public-archive entries without touching community letters.

## MVP features

- Landing page with product framing and polished cinematic styling
- Anonymous post creation with optional private subject and mood selection
- Backend NLP processing on submit:
  - Extractive summary
  - RAKE-style keyword extraction
  - Mood detection using weighted lexical scoring
  - Content warning detection for high-risk terms
  - Sentence-transformers embeddings when available, otherwise TF-IDF similarity
- Submission results with summary, mood, keywords, and similar posts
- Archive page that can display both community letters and public-archive works with source labels
- "How the AI works" explanation for demo viewers

## Portfolio-ready upgrades

The current codebase now keeps a versioned processing trace for every stored letter:

- pipeline version
- embedding backend used for retrieval
- moderation/redaction outcomes
- per-stage timings for moderation, redaction, narrative analysis, emotion analysis, theme extraction, embedding, and semantic projection

That metadata is persisted in SQLite, returned by the API, and surfaced in the reading experience so the project demonstrates both product polish and backend traceability.

## Reprocessing and evaluation

Re-run the current pipeline across existing stored entries:

```bash
cd /Users/saw/Documents/dearest/backend
source .venv/bin/activate
python -m app.reprocess_posts
```

Run a lightweight local archive evaluation:

```bash
cd /Users/saw/Documents/dearest/backend
source .venv/bin/activate
python -m app.evaluate_archive
```

The evaluation script reports:

- community vs public archive counts
- embedding backend distribution
- dominant semantic clusters
- top-1 same-source vs cross-source retrieval counts

Backfill the ANN index for existing posts:

```bash
cd /Users/saw/Documents/dearest
backend/.venv/bin/python -m backend.app.reindex_embeddings
```

Benchmark brute-force cosine against qdrant-local ANN:

```bash
cd /Users/saw/Documents/dearest
backend/.venv/bin/python -m backend.app.benchmark_retrieval
```

## Notes on algorithm choices

- Summarization is intentionally extractive and lightweight so the demo remains local, deterministic, and fast.
- Keyword extraction uses a simple RAKE-style scoring pass over phrase segments, which works well for emotional writing without extra infrastructure.
- Mood detection uses curated lexicons plus a boost from the user-selected mood so the UI and detected label stay aligned when phrasing is ambiguous.
- Similarity uses sentence embeddings only if `sentence-transformers` is installed locally. Otherwise the app falls back to hashed TF-IDF vectors so the ANN index can still persist and query embeddings locally.
- Semantic matching searches across both `community` and `public_archive` content types, then returns source metadata so the UI can distinguish them clearly.
- The active local retrieval backend is qdrant-local; a deterministic in-process cosine backend remains in the repo for tests and baselines.

## Optional upgrade

If you want semantic embeddings beyond TF-IDF, activate the backend venv and install:

```bash
pip install sentence-transformers
```

The backend will detect it automatically and begin storing sentence embeddings for new posts.
