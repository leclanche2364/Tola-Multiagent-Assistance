"""
Batch S5 -- Durable Learning Event Fixtures.
Deterministic event fixtures for S5 QA.
Plain ASCII. Python 3 stdlib only.
"""

STUDY_SESSION_EVENT = {
    "event_type": "study_session.recorded",
    "aggregate_id": "agg-1",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "payload": {
        "duration_minutes": 45,
        "topic": "ventilation-basics",
        "activity": "reading",
    },
}

PRACTICE_UNIT_EVENT = {
    "event_type": "practice_unit.completed",
    "aggregate_id": "agg-2",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "payload": {
        "unit_id": "pu-1",
        "score": 0.92,
        "questions_total": 20,
        "questions_correct": 18,
    },
}

ASSESSMENT_SUBMITTED_EVENT = {
    "event_type": "assessment.submitted",
    "aggregate_id": "agg-3",
    "course_id": "critical-care-101",
    "topic_id": "topic-sepsis",
    "payload": {
        "assessment_id": "asm-1",
        "status": "submitted",
        "score": 0.85,
    },
}

REASONING_SESSION_EVENT = {
    "event_type": "reasoning_session.completed",
    "aggregate_id": "agg-4",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "payload": {
        "session_id": "rs-1",
        "cases_reviewed": 3,
        "duration_minutes": 30,
    },
}

RECORDING_EVENT = {
    "event_type": "recording.transcription_completed",
    "aggregate_id": "agg-5",
    "course_id": "critical-care-101",
    "topic_id": "topic-sepsis",
    "payload": {
        "recording_id": "rec-1",
        "transcript_length_chars": 1200,
        "language": "en",
    },
}

COURSE_GOALS_UPDATED_EVENT = {
    "event_type": "course_goals.updated",
    "aggregate_id": "agg-6",
    "course_id": "critical-care-101",
    "topic_id": "",
    "payload": {
        "goal_id": "goal-1",
        "change": "target_date_extended",
        "new_target_date": "2027-01-31",
    },
}

LEARNING_PLAN_UPDATED_EVENT = {
    "event_type": "learning_plan.updated",
    "aggregate_id": "agg-7",
    "course_id": "critical-care-101",
    "topic_id": "",
    "payload": {
        "plan_id": "plan-1",
        "version": 2,
        "change": "objective_refined",
    },
}

TOPIC_PROGRESS_CHANGED_EVENT = {
    "event_type": "topic.progress_changed",
    "aggregate_id": "agg-8",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "payload": {
        "old_progress": 0.5,
        "new_progress": 0.75,
    },
}

PROFICIENCY_CONTEXT_UPDATED_EVENT = {
    "event_type": "proficiency_context.updated",
    "aggregate_id": "agg-9",
    "course_id": "critical-care-101",
    "topic_id": "",
    "payload": {
        "proficiency_id": "prof-vent-01",
        "change": "version_bumped",
        "new_version": 2,
    },
}

# ---------------------------------------------------------------------------
# Duplicate and out-of-order fixtures
# ---------------------------------------------------------------------------

DUPLICATE_EVENT_SAME_ID = {
    "event_type": "study_session.recorded",
    "aggregate_id": "agg-dup-1",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "payload": {"duration_minutes": 30},
}

OUT_OF_ORDER_CURSOR_EVENTS = [
    {
        "event_type": "study_session.recorded",
        "aggregate_id": "agg-ooo-1",
        "course_id": "critical-care-101",
        "topic_id": "topic-ventilation",
        "payload": {"step": 1},
    },
    {
        "event_type": "practice_unit.completed",
        "aggregate_id": "agg-ooo-2",
        "course_id": "critical-care-101",
        "topic_id": "topic-ventilation",
        "payload": {"step": 2},
    },
    {
        "event_type": "assessment.submitted",
        "aggregate_id": "agg-ooo-3",
        "course_id": "critical-care-101",
        "topic_id": "topic-ventilation",
        "payload": {"step": 3},
    },
]

MUTATION_ATTEMPT_EVENT = {
    "event_type": "study_session.recorded",
    "aggregate_id": "agg-mut-1",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "payload": {"duration_minutes": 60},
}

UNKNOWN_EVENT_TYPE_EVENT = {
    "event_type": "forbidden.mutation",
    "aggregate_id": "agg-bad-1",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "payload": {},
}

EMPTY_COURSE_ID_EVENT = {
    "event_type": "study_session.recorded",
    "aggregate_id": "agg-bad-2",
    "course_id": "",
    "topic_id": "topic-ventilation",
    "payload": {},
}

EMPTY_AGGREGATE_ID_EVENT = {
    "event_type": "study_session.recorded",
    "aggregate_id": "",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "payload": {},
}

EMPTY_TOPIC_ID_EVENT = {
    "event_type": "study_session.recorded",
    "aggregate_id": "agg-bad-3",
    "course_id": "critical-care-101",
    "topic_id": "",
    "payload": {},
}

MISSING_EVENT_TYPE_EVENT = {
    "aggregate_id": "agg-bad-4",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "payload": {},
}

MISSING_AGGREGATE_ID_EVENT = {
    "event_type": "study_session.recorded",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "payload": {},
}

MISSING_COURSE_ID_EVENT = {
    "event_type": "study_session.recorded",
    "aggregate_id": "agg-bad-5",
    "topic_id": "topic-ventilation",
    "payload": {},
}

MISSING_TOPIC_ID_EVENT = {
    "event_type": "study_session.recorded",
    "aggregate_id": "agg-bad-6",
    "course_id": "critical-care-101",
    "payload": {},
}

# Fixture for schema_version override
SCHEMA_VERSION_EVENT = {
    "event_type": "study_session.recorded",
    "aggregate_id": "agg-sv-1",
    "course_id": "critical-care-101",
    "topic_id": "topic-ventilation",
    "schema_version": "2.0",
    "payload": {"custom": "data"},
}