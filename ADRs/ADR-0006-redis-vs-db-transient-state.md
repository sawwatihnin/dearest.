# ADR-0006: Redis Vs DB For Transient Job Stages

## Context

The async pipeline needs durable terminal job records in SQLite, but transient execution-stage updates do not need the same persistence guarantees and can create unnecessary write churn if every state hop is committed to the main jobs table.

## Decision

Keep transient execution-stage state in the Redis-compatible layer while reserving SQLite for durable job lifecycle records and terminal artifacts.

## Consequences

This keeps the current async architecture lightweight and aligned with the existing `ProcessingService` design. It does not remove the known gap where a DB-written `PENDING` job can become orphaned if Celery dispatch fails before worker pickup; that gap is documented separately and should be solved with an explicit sweep or outbox-style reconciliation path rather than by overloading transient state storage.
