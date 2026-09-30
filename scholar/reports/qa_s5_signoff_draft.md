# QA S5 Sign-Off Draft — Durable Learning Event Outbox

**Batch:** S5
**Date:** 2026-09-30
**Environment:** Python 3 stdlib only; unittest framework
**Model route:** Ling 3.0 Flash (deterministic code layer)
**Fixtures:** `scholar/fixtures/events.py` (deterministic, no network, no real clocks)

---

## Functional Tests

| Test ID | Description | Result |
|---------|-------------|--------|
| S5-01 | Event creation: correct event emitted | PASS |
| S5-02 | Stable event ID: retained | PASS |
| S5-03 | Cursor: advances correctly | PASS |
| S5-04 | Replay: prior events remain retrievable | PASS |
| S5-05 | Pagination: no loss/duplication | PASS |
| S5-06 | Schema version: always present | PASS |
| S5-07 | Immutability: event cannot be silently mutated | PASS |

## Edge Cases Tested (beyond S5-01..S5-07)

- Duplicate IDs: each `append()` generates a unique UUID4 event ID; 100 consecutive appends produce 100 distinct IDs.
- Out-of-order cursor reads: cursor validation rejects unknown cursors; cursor after last event returns empty list; cursor-based and full replays coexist correctly.
- Mutation attempts: `update()`, `delete()`, and `clear()` all raise `ValueError` with "immutable" in the message; events remain unchanged after failed mutation attempts.
- Invalid inputs: unknown event types, empty/whitespace-only string fields, missing required kwargs all raise appropriate errors.
- Batch append: `append_batch()` stores all events; unknown event type in batch raises on first failure; prior successful appends in the batch are retained.
- Schema version override: custom `schema_version` values are stored and retrieved correctly.
- Count and `all_events()`: `count()` increments correctly; `all_events()` returns a shallow copy (mutating the returned list does not affect the outbox).

## Test Count

- Prior suite (S0–S4): **218 tests** — all green.
- New S5 suite: **90 tests** — all green.
- **Combined: 308 tests — all green.**

## Contract Changes

No changes were made to `scholar/intensiq/contracts.py`. The existing `EVENT_TYPES` frozenset and `LearningEvent` dataclass were sufficient for the outbox implementation.

## Deviations

None. All S5-01..S5-07 QA criteria are met. All edge cases pass.

## Overall

**PASS**

---

**Approved by:** (pending)
**Notes:** S5 implementation complete. Event outbox is durable, replay-safe, immutable, and cursor-paginated with no loss or duplication.