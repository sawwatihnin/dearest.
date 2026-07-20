# ADR-0002: Span-Based Redaction

## Context

Earlier partial-name failures showed that naive string replacement can leave visible fragments like surnames behind, especially when spaCy emits adjacent entities for multi-token names.

## Decision

Use span-based replacement with reverse-ordered edits and merged adjacent person spans instead of `string.replace(...)`.

## Consequences

The privacy boundary is safer and more deterministic for full names, titles, and bodies. In the July 18, 2026 privacy evaluation over `180` cases, false-negative rate remained `0.0` across all tracked PII types, though `PERSON`, `LOCATION`, and `ORG` still show non-zero false-positive and boundary error rates that should keep future redaction work focused on precision rather than abandoning the span-based approach.
