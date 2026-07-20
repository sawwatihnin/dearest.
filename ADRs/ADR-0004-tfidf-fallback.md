# ADR-0004: TF-IDF Fallback Instead Of Requiring Transformers

## Context

The repo aims to run locally even when sentence-transformer weights are unavailable, disk is constrained, or model initialization fails.

## Decision

Keep the hashed TF-IDF embedding fallback instead of making transformer embeddings a hard requirement.

## Consequences

The current environment resolved to `embedding_model = tfidf`, which let evaluation and benchmarks run end to end without external model downloads. The tradeoff is honesty: the repo currently has no measured MiniLM-versus-TF-IDF comparison, so the fallback preserves functionality and evidence capture, but not proof that semantic quality matches the transformer path.
