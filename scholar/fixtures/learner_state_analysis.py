"""
Batch S11 -- Learner-State Analysis Fixtures.
Deterministic fixtures for S11 QA: learner states with
strong/weak/missing evidence, malformed states, Ling
fixture outputs (valid and malformed), and helper
builders.
Plain ASCII. Python 3 stdlib only.
"""

# ---------------------------------------------------------------------------
# Deterministic learner states
# ---------------------------------------------------------------------------

STRONG_EVIDENCE_STATE = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": [
        {
            "goal_id": "goal-vent-01",
            "title": "Master mechanical ventilation",
            "state": "ACTIVE",
        }
    ],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-ventilation",
            "progress": 0.85,
            "next_action": "practice",
            "practice_units": 8,
            "recent_assessments": [
                {"id": "a1", "status": "completed", "score": 0.92, "date": "2026-09-29"}
            ],
            "recent_study_activity": ["reading", "practice"],
        }
    ],
    "reasoning_evidence": [
        {"id": "r1", "type": "clinical_reasoning", "summary": "Patient shows improvement"}
    ],
    "competency_evidence": [
        {"source": "supervisor_signoff", "authoritative": True, "competency": "ventilation"}
    ],
    "revision_items": [],
    "cursor": "cursor-strong",
}

WEAK_EVIDENCE_STATE = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": [
        {
            "goal_id": "goal-vent-01",
            "title": "Master mechanical ventilation",
            "state": "ACTIVE",
        }
    ],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-ventilation",
            "progress": 0.3,
            "next_action": "study",
            "practice_units": 2,
            "recent_assessments": [
                {"id": "a1", "status": "completed", "score": 0.45, "date": "2026-09-28"}
            ],
            "recent_study_activity": ["reading"],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [
        {"source": "self_assessment", "authoritative": False, "competency": "ventilation"}
    ],
    "revision_items": [],
    "cursor": "cursor-weak",
}

MISSING_EVIDENCE_STATE = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": [
        {
            "goal_id": "goal-vent-01",
            "title": "Master mechanical ventilation",
            "state": "ACTIVE",
        }
    ],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-ventilation",
            "progress": 0.1,
            "next_action": "start",
            "practice_units": 1,
            "recent_assessments": [],
            "recent_study_activity": [],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-missing",
}

MIXED_EVIDENCE_STATE = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": [
        {
            "goal_id": "goal-vent-01",
            "title": "Master mechanical ventilation",
            "state": "ACTIVE",
        }
    ],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-ventilation",
            "progress": 0.75,
            "next_action": "practice",
            "practice_units": 6,
            "recent_assessments": [
                {"id": "a1", "status": "completed", "score": 0.88, "date": "2026-09-29"}
            ],
            "recent_study_activity": ["reading", "practice"],
        },
        {
            "id": "topic-sepsis",
            "progress": 0.2,
            "next_action": "start",
            "practice_units": 1,
            "recent_assessments": [],
            "recent_study_activity": [],
        }
    ],
    "reasoning_evidence": [
        {"id": "r1", "type": "clinical_reasoning", "summary": "Ventilation improving"}
    ],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-mixed",
}

# ---------------------------------------------------------------------------
# Malformed learner states (for rejection tests)
# ---------------------------------------------------------------------------

MALFORMED_STATE_MISSING_SCHEMA_VERSION = {
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "topics": [],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-bad-1",
}

MALFORMED_STATE_EMPTY_SCHEMA_VERSION = {
    "schema_version": "",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "topics": [],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-bad-2",
}

MALFORMED_STATE_MISSING_STATE_VERSION = {
    "schema_version": "1.0",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "topics": [],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-bad-3",
}

MALFORMED_STATE_NOT_DICT = "this is a string, not a dict"

# ---------------------------------------------------------------------------
# PAUSED goal state (S11 edge case: PAUSED goals excluded from active
# analysis but still recorded)
# ---------------------------------------------------------------------------

PAUSED_GOAL_STATE = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": [
        {
            "goal_id": "goal-vent-01",
            "title": "Master mechanical ventilation",
            "state": "PAUSED",
        }
    ],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-ventilation",
            "progress": 0.85,
            "next_action": "practice",
            "practice_units": 8,
            "recent_assessments": [
                {"id": "a1", "status": "completed", "score": 0.92, "date": "2026-09-29"}
            ],
            "recent_study_activity": ["reading", "practice"],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-paused",
}

SUPERSEDED_GOAL_STATE = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": [
        {
            "goal_id": "goal-vent-01",
            "title": "Master mechanical ventilation",
            "state": "SUPERSEDED",
        }
    ],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-ventilation",
            "progress": 0.85,
            "next_action": "practice",
            "practice_units": 8,
            "recent_assessments": [
                {"id": "a1", "status": "completed", "score": 0.92, "date": "2026-09-29"}
            ],
            "recent_study_activity": ["reading", "practice"],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-superseded",
}

# ---------------------------------------------------------------------------
# Ling fixture outputs
# ---------------------------------------------------------------------------

VALID_LING_OUTPUT = {
    "summary": "Analysis for goal-vent-01: 1 strength(s), 0 gap(s), 0 uncertainty area(s).",
    "evidence_refs": ["ev-goal-vent-01-001"],
    "interpretation": "The learner shows strong performance in ventilation basics.",
    "uncertainty": "No missing evidence identified; all observed data is accounted for.",
    "strengths": ["Topic ventilation progress=0.85"],
    "gaps": ["No weak evidence areas identified."],
}

MALFORMED_LING_OUTPUT_MISSING_FIELDS = {
    "summary": "Incomplete output",
    # missing evidence_refs, interpretation, uncertainty, strengths, gaps
}

MALFORMED_LING_OUTPUT_WRONG_TYPES = {
    "summary": 12345,
    "evidence_refs": "not-a-list",
    "interpretation": 42,
    "uncertainty": None,
    "strengths": "not-a-list",
    "gaps": 99,
}

MALFORMED_LING_OUTPUT_EMPTY_STRINGS = {
    "summary": "",
    "evidence_refs": [],
    "interpretation": "",
    "uncertainty": "",
    "strengths": [],
    "gaps": [],
}

MALFORMED_LING_OUTPUT_NOT_DICT = "this is a string"

MALFORMED_LING_OUTPUT_NULL = None

MALFORMED_LING_OUTPUT_EXTRA_FIELDS = {
    "summary": "Valid summary",
    "evidence_refs": ["ev-001"],
    "interpretation": "Some interpretation",
    "uncertainty": "Some uncertainty",
    "strengths": ["Strength 1"],
    "gaps": ["Gap 1"],
    "extra_field": "should be ignored or rejected",
}

# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def make_analyser(ling_analyser=None):
    """Build a LearnerStateAnalyser with optional injected Ling analyser."""
    from scholar.learner_state_analysis.analyser import LearnerStateAnalyser
    return LearnerStateAnalyser(ling_analyser=ling_analyser)


def make_state(raw: dict):
    """Build a LearnerState from a raw dict."""
    from scholar.learner_state.aggregate import build_learner_state
    return build_learner_state(raw)