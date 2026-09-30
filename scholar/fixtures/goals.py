"""
Batch S9 -- Learning Goal Fixtures.
Deterministic fixtures for S9 QA: sources, goals, malformed data,
and helper builders.
Plain ASCII. Python 3 stdlib only.
"""

# ---------------------------------------------------------------------------
# Clock helper (deterministic)
# ---------------------------------------------------------------------------

def _fake_now():
    """Deterministic timestamp for testing."""
    from datetime import datetime
    return datetime(2026, 9, 30, 12, 0, 0)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

DIRECT_USER_SOURCE_V1 = {
    "source_id": "src-user-001",
    "name": "Direct User Goal Source",
    "source_type": "direct_user",
    "version": "1.0",
    "content_hash": "duhash001",
    "content": {
        "user_id": "user-1",
        "goal_category": "clinical_competency",
    },
}

TOLA_SOURCE_V1 = {
    "source_id": "src-tola-001",
    "name": "Tola Goal Source",
    "source_type": "tola",
    "version": "1.0",
    "content_hash": "tolahash001",
    "content": {
        "tola_priority": "high",
        "portfolio_goal": True,
    },
}

DIRECT_USER_SOURCE_V2 = {
    "source_id": "src-user-001",
    "name": "Direct User Goal Source v2",
    "source_type": "direct_user",
    "version": "2.0",
    "content_hash": "duhash002",
    "content": {
        "user_id": "user-1",
        "goal_category": "clinical_competency",
        "updated": True,
    },
}

TOLA_SOURCE_V2 = {
    "source_id": "src-tola-001",
    "name": "Tola Goal Source v2",
    "source_type": "tola",
    "version": "2.0",
    "content_hash": "tolahash002",
    "content": {
        "tola_priority": "critical",
        "portfolio_goal": True,
        "updated": True,
    },
}

# ---------------------------------------------------------------------------
# Goal records (deterministic)
# ---------------------------------------------------------------------------

GOAL_VENT_DIRECT_V1 = {
    "goal_id": "goal-vent-01",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "Master mechanical ventilation within six weeks",
    "description": "Become highly competent in mechanical ventilation including ventilator modes, lung-protective strategies, and weaning criteria.",
    "source_type": "direct_user",
}

GOAL_VENT_TOLA_V1 = {
    "goal_id": "goal-vent-02",
    "source_id": "src-tola-001",
    "source_version": "1.0",
    "title": "Mechanical ventilation proficiency for Step 2",
    "description": "Achieve Step 2 competency in mechanical ventilation as prioritized by Tola for portfolio review.",
    "source_type": "tola",
}

GOAL_HEMO_DIRECT_V1 = {
    "goal_id": "goal-hemo-01",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "Learn haemodynamic monitoring",
    "description": "Understand arterial line interpretation, CVP analysis, and cardiac output measurement.",
    "source_type": "direct_user",
}

# ---------------------------------------------------------------------------
# Malformed / edge-case fixtures
# ---------------------------------------------------------------------------

MALFORMED_GOAL_MISSING_TITLE = {
    "goal_id": "goal-bad-1",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "",  # empty — should be rejected
    "description": "A goal with an empty title.",
    "source_type": "direct_user",
}

MALFORMED_GOAL_MISSING_DESCRIPTION = {
    "goal_id": "goal-bad-2",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "A goal with no description",
    "description": "",  # empty — should be rejected
    "source_type": "direct_user",
}

MALFORMED_GOAL_BAD_SOURCE_TYPE = {
    "goal_id": "goal-bad-3",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "A goal with bad source type",
    "description": "This source_type is invalid.",
    "source_type": "invalid_source",  # not direct_user or tola
}

MALFORMED_GOAL_MISSING_SOURCE = {
    "goal_id": "goal-bad-4",
    "source_id": "src-nonexistent",
    "source_version": "1.0",
    "title": "A goal with missing source",
    "description": "The source does not exist.",
    "source_type": "direct_user",
}

MALFORMED_GOAL_MISSING_SOURCE_VERSION = {
    "goal_id": "goal-bad-5",
    "source_id": "src-user-001",
    "source_version": "99.0",  # does not exist
    "title": "A goal with missing source version",
    "description": "The source version does not exist.",
    "source_type": "direct_user",
}

MALFORMED_GOAL_NON_STRING_TITLE = {
    "goal_id": "goal-bad-6",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": 12345,  # non-string
    "description": "A goal with a non-string title.",
    "source_type": "direct_user",
}

MALFORMED_GOAL_EMPTY_GOAL_ID = {
    "goal_id": "",  # empty — should be rejected
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "A goal with empty goal_id",
    "description": "The goal_id is empty.",
    "source_type": "direct_user",
}

MALFORMED_GOAL_NON_STRING_SOURCE_TYPE = {
    "goal_id": "goal-bad-7",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "A goal with non-string source_type",
    "description": "The source_type is not a string.",
    "source_type": 42,  # non-string
}

# ---------------------------------------------------------------------------
# Duplicate attempt fixtures
# ---------------------------------------------------------------------------

DUPLICATE_GOAL_ATTEMPT = {
    "goal_id": "goal-vent-01",  # same as GOAL_VENT_DIRECT_V1
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "A duplicate goal",
    "description": "This goal_id already exists.",
    "source_type": "direct_user",
}

# ---------------------------------------------------------------------------
# Invalid transition fixtures
# ---------------------------------------------------------------------------

# Attempting to pause a COMPLETED goal
INVALID_TRANSITION_PAUSE_COMPLETED = {
    "goal_id": "goal-completed-01",
    "attempt": "pause",
    "from_state": "COMPLETED",
}

# Attempting to resume a STOPPED goal
INVALID_TRANSITION_RESUME_STOPPED = {
    "goal_id": "goal-stopped-01",
    "attempt": "resume",
    "from_state": "STOPPED",
}

# Attempting to complete a SUPERSEDED goal
INVALID_TRANSITION_COMPLETE_SUPERSEDED = {
    "goal_id": "goal-superseded-01",
    "attempt": "complete",
    "from_state": "SUPERSEDED",
}

# Attempting to stop a COMPLETED goal
INVALID_TRANSITION_STOP_COMPLETED = {
    "goal_id": "goal-completed-02",
    "attempt": "stop",
    "from_state": "COMPLETED",
}

# Attempting to supersede a STOPPED goal
INVALID_TRANSITION_SUPERSEDE_STOPPED = {
    "goal_id": "goal-stopped-02",
    "attempt": "supersede",
    "from_state": "STOPPED",
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def make_registry(clock=None) -> "GoalRegistry":
    """Create a fresh GoalRegistry with deterministic clock."""
    from scholar.goals.registry import GoalRegistry
    return GoalRegistry(clock=clock or _fake_now)


def make_source(**overrides) -> dict:
    """Build a source dict with optional overrides."""
    base = dict(DIRECT_USER_SOURCE_V1)
    base.update(overrides)
    return base


def make_goal(**overrides) -> dict:
    """Build a goal dict with optional overrides."""
    base = dict(GOAL_VENT_DIRECT_V1)
    base.update(overrides)
    return base


def make_tola_goal(**overrides) -> dict:
    """Build a Tola-sourced goal dict with optional overrides."""
    base = dict(GOAL_VENT_TOLA_V1)
    base.update(overrides)
    return base


def make_paused_goal_payload(**overrides) -> dict:
    """Build a payload for creating a goal that will be paused."""
    base = dict(GOAL_VENT_DIRECT_V1)
    base.update(overrides)
    return base


def make_supersede_payload(**overrides) -> dict:
    """Build a supersede payload dict with optional overrides."""
    base = dict(GOAL_VENT_DIRECT_V1)
    base.update(overrides)
    return base
