"""
Batch S10 -- Learning-Goal Decomposition Fixtures.
Deterministic fixtures for S10 QA: decomposition inputs,
expected target structures, malformed goals, and helper
builders.
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
# Goal targets for decomposition
# ---------------------------------------------------------------------------

# A mechanical-ventilation goal that maps to relevant curriculum
# and proficiencies (S10-01).
VENT_GOAL_TARGET = {
    "goal_id": "goal-vent-01",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "Master mechanical ventilation within six weeks",
    "description": (
        "Become highly competent in mechanical ventilation including "
        "ventilator modes, lung-protective strategies, and weaning criteria."
    ),
    "source_type": "direct_user",
}

# A multi-domain goal covering ventilation AND haemodynamics (S10-02).
MULTI_DOMAIN_GOAL_TARGET = {
    "goal_id": "goal-multi-01",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "Master mechanical ventilation and haemodynamic monitoring",
    "description": (
        "Become competent in both mechanical ventilation and advanced "
        "haemodynamic monitoring within eight weeks."
    ),
    "source_type": "direct_user",
}

# A goal with a missing prerequisite (S10-03): references a topic
# that has a prerequisite node not covered by the goal.
# This is tested by creating a goal whose domain keywords match
# a curriculum node that has a prerequisite link to an unmapped node.

# A goal with an unrealistic time horizon (S10-04): 20 weeks > 42 days.
UNREALISTIC_HORIZON_GOAL_TARGET = {
    "goal_id": "goal-horizon-01",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "Master mechanical ventilation within 20 weeks",
    "description": (
        "Become highly competent in mechanical ventilation. "
        "This is a very long horizon."
    ),
    "source_type": "direct_user",
}

# A goal referencing an unknown proficiency (S10-05): the goal
# domain does not match any existing proficiency, so no invented
# mapping should be created.
UNKNOWN_PROFICIENCY_GOAL_TARGET = {
    "goal_id": "goal-unknown-01",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "Learn quantum mechanics",
    "description": "Understand quantum mechanics for no obvious clinical reason.",
    "source_type": "direct_user",
}

# A PAUSED goal — decomposition should still work (S10 edge case).
VENT_GOAL_PAUSED = {
    "goal_id": "goal-vent-paused",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "Master mechanical ventilation within six weeks",
    "description": (
        "Become highly competent in mechanical ventilation including "
        "ventilator modes, lung-protective strategies, and weaning criteria."
    ),
    "source_type": "direct_user",
}

# A SUPERSEDED goal — decomposition should still work (S10 edge case).
VENT_GOAL_SUPERSEDED = {
    "goal_id": "goal-vent-superseded",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "Master mechanical ventilation within six weeks",
    "description": (
        "Become highly competent in mechanical ventilation including "
        "ventilator modes, lung-protective strategies, and weaning criteria."
    ),
    "source_type": "direct_user",
}

# A goal with evidence requirements present.
VENT_GOAL_WITH_EVIDENCE = {
    "goal_id": "goal-vent-evidence",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "Master mechanical ventilation with evidence",
    "description": (
        "Become highly competent in mechanical ventilation. "
        "Need evidence from recent guidelines."
    ),
    "source_type": "direct_user",
}

# A malformed goal — missing title.
MALFORMED_GOAL_MISSING_TITLE = {
    "goal_id": "goal-bad-01",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "",  # empty — should be rejected
    "description": "A goal with an empty title.",
    "source_type": "direct_user",
}

# A malformed goal — non-string title.
MALFORMED_GOAL_NON_STRING_TITLE = {
    "goal_id": "goal-bad-02",
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": 12345,  # non-string — should be rejected
    "description": "A goal with a non-string title.",
    "source_type": "direct_user",
}

# A malformed goal — empty goal_id.
MALFORMED_GOAL_EMPTY_ID = {
    "goal_id": "",  # empty — should be rejected
    "source_id": "src-user-001",
    "source_version": "1.0",
    "title": "A goal with empty goal_id",
    "description": "The goal_id is empty.",
    "source_type": "direct_user",
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def make_decomposer(
    curriculum_registry=None,
    proficiency_registry=None,
    goal_registry=None,
    clock=None,
):
    """Build a LearningGoalDecomposer with optional registries."""
    from scholar.decomposition.registry import LearningGoalDecomposer
    if curriculum_registry is None:
        from scholar.curriculum.registry import CurriculumRegistry
        curriculum_registry = CurriculumRegistry(clock=clock or _fake_now)
    if proficiency_registry is None:
        from scholar.curriculum.proficiency_registry import ProficiencyRegistry
        proficiency_registry = ProficiencyRegistry(clock=clock or _fake_now)
    if goal_registry is None:
        from scholar.goals.registry import GoalRegistry
        goal_registry = GoalRegistry(clock=clock or _fake_now)
    return LearningGoalDecomposer(
        curriculum_registry=curriculum_registry,
        proficiency_registry=proficiency_registry,
        goal_registry=goal_registry,
        clock=clock or _fake_now,
    )
