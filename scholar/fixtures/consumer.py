"""
Batch S6 -- Consumer Fixtures.
Deterministic fixtures for S6 QA: consumer events, malformed events,
out-of-order events, and helper builders.

NOTE: These fixtures are for use with EventConsumer directly,
NOT with EventOutbox.append(). They include event_id because
the consumer validates events as-is. To load them into an
EventOutbox for testing, use make_outbox_event() which strips
event_id and lets the outbox generate its own.
Plain ASCII. Python 3 stdlib only.
"""

# ---------------------------------------------------------------------------
# Consumer events (include event_id for consumer validation)
# ---------------------------------------------------------------------------

CONSUMER_STUDY_SESSION = {
    "event_id": "evt-consumer-001",
    "event_type": "study_session.recorded",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T10:00:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-consumer-1",
    "payload": {"duration_minutes": 45, "activity": "reading"},
}

CONSUMER_PRACTICE_UNIT = {
    "event_id": "evt-consumer-002",
    "event_type": "practice_unit.completed",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T10:30:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-consumer-2",
    "payload": {"unit_id": "pu-1", "score": 0.92},
}

CONSUMER_ASSESSMENT = {
    "event_id": "evt-consumer-003",
    "event_type": "assessment.submitted",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T11:00:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-sepsis",
    "aggregate_id": "agg-consumer-3",
    "payload": {"assessment_id": "asm-1", "status": "submitted"},
}

CONSUMER_REASONING = {
    "event_id": "evt-consumer-004",
    "event_type": "reasoning_session.completed",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T11:30:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-consumer-4",
    "payload": {"session_id": "rs-1", "cases_reviewed": 3},
}

# ---------------------------------------------------------------------------
# Duplicate event (same event_id as CONSUMER_STUDY_SESSION)
# ---------------------------------------------------------------------------

DUPLICATE_CONSUMER_EVENT = {
    "event_id": "evt-consumer-001",  # same as CONSUMER_STUDY_SESSION
    "event_type": "study_session.recorded",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T10:00:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-consumer-1",
    "payload": {"duration_minutes": 45, "activity": "reading"},
}

# ---------------------------------------------------------------------------
# Out-of-order event (occurred_at before the previous event)
# ---------------------------------------------------------------------------

OUT_OF_ORDER_CONSUMER_EVENT = {
    "event_id": "evt-consumer-ooo-1",
    "event_type": "study_session.recorded",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T09:00:00",  # before the previous 10:00
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-consumer-ooo",
    "payload": {"duration_minutes": 20, "activity": "note-taking"},
}

# ---------------------------------------------------------------------------
# Malformed events (missing or invalid fields)
# ---------------------------------------------------------------------------

MALFORMED_MISSING_EVENT_ID = {
    "event_type": "study_session.recorded",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T10:00:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-malformed-1",
    "payload": {},
}

MALFORMED_MISSING_EVENT_TYPE = {
    "event_id": "evt-malformed-1",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T10:00:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-malformed-2",
    "payload": {},
}

MALFORMED_UNKNOWN_EVENT_TYPE = {
    "event_id": "evt-malformed-2",
    "event_type": "forbidden.mutation",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T10:00:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-malformed-3",
    "payload": {},
}

MALFORMED_EMPTY_EVENT_ID = {
    "event_id": "",
    "event_type": "study_session.recorded",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T10:00:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-malformed-4",
    "payload": {},
}

MALFORMED_EMPTY_COURSE_ID = {
    "event_id": "evt-malformed-3",
    "event_type": "study_session.recorded",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T10:00:00",
    "course_id": "",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-malformed-5",
    "payload": {},
}

MALFORMED_MISSING_SCHEMA_VERSION = {
    "event_id": "evt-malformed-4",
    "event_type": "study_session.recorded",
    "occurred_at": "2026-09-30T10:00:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-malformed-6",
    "payload": {},
}

MALFORMED_NON_STRING_EVENT_ID = {
    "event_id": 12345,
    "event_type": "study_session.recorded",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T10:00:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-malformed-7",
    "payload": {},
}

MALFORMED_MISSING_OCCURRED_AT = {
    "event_id": "evt-malformed-5",
    "event_type": "study_session.recorded",
    "schema_version": "1.0",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-malformed-8",
    "payload": {},
}

MALFORMED_NOT_A_DICT = "this is a string, not a dict"

# ---------------------------------------------------------------------------
# Interleaved duplicate events (for testing double-commit scenario)
# ---------------------------------------------------------------------------

INTERLEAVED_DUPLICATE_A = {
    "event_id": "evt-interleaved-1",
    "event_type": "study_session.recorded",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T10:00:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-interleaved-1",
    "payload": {"duration_minutes": 30},
}

INTERLEAVED_DUPLICATE_B = {
    "event_id": "evt-interleaved-1",  # same ID as A
    "event_type": "study_session.recorded",
    "schema_version": "1.0",
    "occurred_at": "2026-09-30T10:00:00",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "aggregate_id": "agg-interleaved-1",
    "payload": {"duration_minutes": 30},
}

# ---------------------------------------------------------------------------
# Helper: build a consumer event with overrides (includes event_id)
# ---------------------------------------------------------------------------

def make_consumer_event(**overrides):
    """Build a consumer event dict with optional overrides."""
    base = dict(CONSUMER_STUDY_SESSION)
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Helper: build an outbox-compatible event (no event_id — outbox generates it)
# ---------------------------------------------------------------------------

def make_outbox_event(**overrides):
    """Build an event dict suitable for EventOutbox.append().

    Strips event_id so the outbox generates its own.
    """
    base = {
        "event_type": "study_session.recorded",
        "aggregate_id": "agg-outbox-1",
        "course_id": "critical-care-101",
        "topic_id": "topic-ventilation",
        "payload": {"duration_minutes": 45, "activity": "reading"},
    }
    base.update(overrides)
    # Remove event_id if present — outbox generates its own
    base.pop("event_id", None)
    return base