# Tola Batch T1 — Portfolio Data Contract

## Overview

Batch T1 defines typed portfolio data contracts with one documented
authoritative source of truth per entity.  All contracts are frozen
dataclasses with typed fields and full provenance
(`source_system`, `source_id`, `fetched_at`, `source_version`).

## Entity Contracts

| Entity      | Dataclass  | Authoritative Source |
|-------------|------------|----------------------|
| project     | Project    | Blackboard           |
| goal        | Goal       | Blackboard           |
| milestone   | Milestone  | Blackboard           |
| task        | Task       | Blackboard           |
| commitment  | Commitment | Blackboard           |
| deadline    | Deadline   | Blackboard           |
| experiment  | Experiment | Local Doc            |
| metric      | Metric     | Local Doc            |
| risk        | Risk       | Blackboard           |
| decision    | Decision   | Blackboard           |
| approval    | Approval   | Blackboard           |
| outcome     | Outcome    | Blackboard           |

## Source-of-Truth Table

```
entity_type  ->  authoritative source
-----------  ------------------------
project      ->  SOURCE_BLACKBOARD
goal         ->  SOURCE_BLACKBOARD
milestone    ->  SOURCE_BLACKBOARD
task         ->  SOURCE_BLACKBOARD
commitment   ->  SOURCE_BLACKBOARD
deadline     ->  SOURCE_BLACKBOARD
experiment   ->  SOURCE_LOCAL_DOC
metric       ->  SOURCE_LOCAL_DOC
risk         ->  SOURCE_BLACKBOARD
decision     ->  SOURCE_BLACKBOARD
approval     ->  SOURCE_BLACKBOARD
outcome      ->  SOURCE_BLACKBOARD
```

## Key Rules

- Every entity is a **frozen dataclass** — immutable after construction.
- Every entity carries **four provenance fields**: `source_system`,
  `source_id`, `fetched_at`, `source_version`.
- No contract grants Tola write capability to My Rhythm.
- Conversation-only facts (`source=conversation`) are never treated as
  authoritative operational state.
- Missing or incomplete provenance is rejected by the guards module.

## Files

- `tola/portfolio/contracts.py` — entity dataclasses and `Source` enum
- `tola/portfolio/sources.py` — `SOURCE_OF_TRUTH` registry and `resolve_source()`
- `tola/portfolio/guards.py` — `reject_conversation_only()`, `require_provenance()`, `guard_authoritative()`
- `tola/portfolio/__init__.py` — public API exports
- `tola/tests/test_t1_contracts.py` — QA T1 tests (T1-01..T1-08)

## Exceptions

- `MissingOwnershipError` — entity type not registered in `SOURCE_OF_TRUTH`
- `AmbiguousSourceError` — entity type maps to more than one source
- `GuardViolation` — conversation-only or unprovenanced fact rejected