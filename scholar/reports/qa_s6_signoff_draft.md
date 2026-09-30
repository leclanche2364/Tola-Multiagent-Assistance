# QA S6 Sign-Off Draft — Scholar Event Consumer

**Batch:** S6  
**Date:** 2026-09-30  
**Status:** DRAFT — pending review  

---

## Deliverables

| File | Description |
|------|-------------|
| `scholar/events/consumer.py` | EventConsumer: polling, dedup, processing, cursor commit |
| `scholar/fixtures/consumer.py` | Deterministic fixtures for S6 QA |
| `scholar/tests/test_s6_event_consumer.py` | 57 tests covering S6-01..S6-06 + edge cases |

---

## QA S6 Test Results

| Test ID | Description | Result |
|---------|-------------|--------|
| S6-01 | Single event processed once | PASS |
| S6-02 | Duplicate event → one logical effect | PASS |
| S6-03 | Crash before cursor commit → safe replay | PASS |
| S6-04 | Crash after cursor commit → no reprocessing | PASS |
| S6-05 | Malformed event rejected/quarantined | PASS |
| S6-06 | Out-of-order event handled safely | PASS |

**Edge cases also covered:** double-commit, quarantine recovery, interleaved duplicates, processing failure dead-lettering, state serialization, mixed valid/malformed polls, limit parameter, empty outbox.

---

## Combined Test Count

| Suite | Tests |
|-------|-------|
| S0–S5 (prior) | 308 |
| S6 (new) | 57 |
| **Combined total** | **365** |
| **All green** | **YES** |

---

## Implementation Summary

### EventConsumer (`scholar/events/consumer.py`)

- **Polling:** `poll_and_process(limit=50)` reads new events from `EventOutbox` via cursor-based replay.
- **Deduplication:** Tracks `processed_ids` set; duplicate `event_id` → `RESULT_DUPLICATE`, no logical effect.
- **Processing:** User-supplied `processor` callable invoked per event.
- **Cursor commit:** Cursor advanced ONLY after all events in the batch are handled. Crash before commit → cursor unchanged → safe replay. Crash after commit → cursor advanced → no reprocessing.
- **Quarantine:** Malformed events (missing/invalid fields, unknown event_type) are quarantined with error details. Never processed.
- **Out-of-order:** Events with `occurred_at` before `last_occurred_at` are tracked in `out_of_order` list but still processed (safe replay).
- **Dead-lettering:** Events whose processor raises are added to `processed_ids` to prevent infinite retry loops.
- **State serialization:** `get_state()` / `restore_state()` for crash recovery with cursor + processed_ids persistence.
- **Quarantine retry:** `retry_quarantined()` re-attempts quarantined events that have become valid.

### No Changes to Contracts or Outbox

No modifications were required to `scholar/intensiq/contracts.py` or `scholar/intensiq/event_outbox.py`. The consumer consumes from the existing outbox interface without extending or altering it.

---

## Defects

None. All 365 tests pass.

---

## Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| QA Reviewer | — | — | PENDING |
| Implementation | Rhythm (subagent) | 2026-09-30 | COMPLETE |

---

## Notes

- The consumer uses `EventOutbox.replay()` which is append-only and immutable — consistent with S5 design.
- `process_event()` method provides single-event idempotent processing for use cases where batch polling is not needed.
- The `_MockOutbox` helper in tests enables testing with malformed events that cannot be loaded into `EventOutbox.append()` due to its validation.