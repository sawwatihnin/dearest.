# ADR-0005: Clone-And-Run Is A First-Class Design Priority

## Context

Dearest is both a demo product and an engineering portfolio artifact, so new contributors and reviewers need to bring it up locally without first solving infrastructure orchestration.

## Decision

Prefer defaults that allow the repo to run locally with minimal external services.

## Consequences

This decision explains several other choices together: SQLite remains the active store, local vector retrieval remains the default, qdrant stays opt-in, and the embedding fallback remains available. The result is a more reproducible local path at the cost of some production realism, which is appropriate for the current product stage and documented benchmark scope.
