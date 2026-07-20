# ADR-0001: Moderation Before Persistence

## Context

Dearest accepts anonymous emotional writing, but the platform still needs to block active self-harm intent, direct threats, and harassment before that content becomes part of the searchable archive or downstream NLP traces.

## Decision

Run moderation before persistence and before the rest of the NLP pipeline.

## Consequences

Unsafe submissions are rejected before they can be stored, embedded, summarized, or recommended. The July 18, 2026 evaluation run measured `1.0` precision and `0.718` recall over `182` moderation cases, which is strong enough to justify the ordering boundary even while the classifier still has recall work left.
