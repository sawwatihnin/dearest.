# ADR-0007: Qdrant Is An Opt-In Backend

## Context

Qdrant-local is fully implemented in the repo and integrated through the same vector-storage boundary as the local cosine backend.

## Decision

Keep qdrant-local as an opt-in backend rather than the always-on default.

## Consequences

This preserves a clean onboarding path while still giving agents and developers a real ANN backend for experiments, reindexing, and targeted latency work. The July 18, 2026 evidence shows qdrant-local can win decisively on the small real benchmark, but the larger synthetic benchmark did not confirm a universal latency advantage, so forcing qdrant into the default path would overstate what the measured evidence currently proves.
