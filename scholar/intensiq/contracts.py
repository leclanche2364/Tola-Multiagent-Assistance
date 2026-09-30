"""
Batch S1 -- IntenSIQ Contract Dataclasses and Validation.
Frozen dataclasses for learner-state read, versioned learning plan, and durable events.
Plain ASCII. Python 3 stdlib only.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional


# ---------------------------------------------------------------------------
# 8.1 Learner State Read Model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LearnerStateRead:
    schema_version: str
    state_version: str
    as_of: str
    course: str
    course_goals: List[str]
    proficiency_context: List[Any]
    topics: List[Any]
    reasoning_evidence: List[Any]
    competency_evidence: List[Any]
    revision_items: List[Any]
    cursor: str


# ---------------------------------------------------------------------------
# 8.2 Versioned Learning Plan
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LearningPlan:
    plan_id: str
    goal_id: str
    course_id: str
    version: int
    expected_previous_version: int
    status: str
    objective: str
    target_date: str
    proficiency_refs: List[Any]
    ordered_learning_items: List[Any]
    weekly_minutes: int
    minimum_session_minutes: int
    review_policy: str
    mastery_targets: List[Any]
    rationale: str
    created_by: str
    updated_at: str


# ---------------------------------------------------------------------------
# 8.3 Durable Learning Events
# ---------------------------------------------------------------------------

EVENT_TYPES = frozenset({
    "study_session.recorded",
    "practice_unit.completed",
    "assessment.submitted",
    "reasoning_session.completed",
    "recording.transcription_completed",
    "course_goals.updated",
    "learning_plan.updated",
    "topic.progress_changed",
    "proficiency_context.updated",
})


@dataclass(frozen=True)
class LearningEvent:
    event_id: str
    event_type: str
    schema_version: str
    occurred_at: str
    course_id: str
    topic_id: str
    aggregate_id: str
    payload: Any


# ---------------------------------------------------------------------------
# Calendar-time field detection
# ---------------------------------------------------------------------------

_CALENDAR_TIME_KEYWORDS = (
    "scheduled_at",
    "calendar_time",
    "session_times",
    "start_time",
    "end_time",
)


def _has_calendar_time_fields(data, prefix=""):
    """Recursively check dict/list for keys containing calendar-time keywords."""
    if isinstance(data, dict):
        for key in data:
            lower = key.lower()
            for kw in _CALENDAR_TIME_KEYWORDS:
                if kw in lower:
                    return True
            if isinstance(data[key], (dict, list)):
                if _has_calendar_time_fields(data[key], prefix=key):
                    return True
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                if _has_calendar_time_fields(item):
                    return True
    return False


def validate_learning_plan(plan, creator="scholar"):
    """Validate a LearningPlan dict or dataclass.

    Raises ValueError on:
    - missing required fields
    - calendar-time fields present (keys containing scheduled_at, calendar_time,
      session_times, start_time, end_time)
    - created_by != creator (default 'scholar')
    - version or expected_previous_version not positive ints
    """
    if isinstance(plan, LearningPlan):
        plan = {
            "plan_id": plan.plan_id,
            "goal_id": plan.goal_id,
            "course_id": plan.course_id,
            "version": plan.version,
            "expected_previous_version": plan.expected_previous_version,
            "status": plan.status,
            "objective": plan.objective,
            "target_date": plan.target_date,
            "proficiency_refs": plan.proficiency_refs,
            "ordered_learning_items": plan.ordered_learning_items,
            "weekly_minutes": plan.weekly_minutes,
            "minimum_session_minutes": plan.minimum_session_minutes,
            "review_policy": plan.review_policy,
            "mastery_targets": plan.mastery_targets,
            "rationale": plan.rationale,
            "created_by": plan.created_by,
            "updated_at": plan.updated_at,
        }

    required_fields = [
        "plan_id", "goal_id", "course_id", "version",
        "expected_previous_version", "status", "objective", "target_date",
        "proficiency_refs", "ordered_learning_items", "weekly_minutes",
        "minimum_session_minutes", "review_policy", "mastery_targets",
        "rationale", "created_by", "updated_at",
    ]

    missing = [f for f in required_fields if f not in plan]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    # Calendar-time check
    if _has_calendar_time_fields(plan):
        raise ValueError("Calendar-time fields are forbidden in learning plans")

    # Creator check
    if plan.get("created_by") != creator:
        raise ValueError(
            f"created_by must be '{creator}', got '{plan.get('created_by')}'"
        )

    # Version checks
    v = plan.get("version")
    if not isinstance(v, int) or v < 1:
        raise ValueError(
            f"version must be a positive int, got {v!r}"
        )
    epv = plan.get("expected_previous_version")
    if not isinstance(epv, int) or epv < 0:
        raise ValueError(
            f"expected_previous_version must be a non-negative int, got {epv!r}"
        )
