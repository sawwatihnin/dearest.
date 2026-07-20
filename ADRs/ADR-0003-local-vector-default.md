# ADR-0003: Local Vector Storage As The Default

## Context

Dearest ships with both `LocalVectorStorage` and `QdrantLocalVectorStorage`, and the architecture already isolates backend selection behind `VectorStorageInterface`.

## Decision

Keep `local` as the runtime default for clone-and-run onboarding.

## Consequences

The evidence is mixed rather than one-directional. On the small real corpus benchmark (`410` posts, `20` sampled queries), qdrant-local was faster (`1.565 ms p50` vs `11.077 ms p50`) with effectively equal quality on the small judged set. On the larger synthetic benchmark (`10,000` docs, `100` queries, `25` latency samples), local was faster (`199.175 ms p50` vs `270.971 ms p50`) while quality remained similarly weak for both under TF-IDF embeddings. That mixed picture supports keeping the default optimized for easy local startup while preserving qdrant as a measured opt-in path.
