"""
Batch S12 -- Mastery Model Fixtures.
Deterministic fixtures for S12 QA: mastery evidence
scenarios covering S12-01..S12-05 plus edge cases.
Plain ASCII. Python 3 stdlib only.
"""

from scholar.mastery.model import (
    MasteryAnalyser,
    MasteryDimension,
    DimensionEvidence,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_analyser(clock=None):
    """Build a MasteryAnalyser with optional injected clock."""
    return MasteryAnalyser(clock=clock)


def make_evidence(dimension, strength, source, evidence_ref, detail, authoritative=False):
    """Build a DimensionEvidence quickly."""
    return DimensionEvidence(
        dimension=dimension,
        strength=strength,
        source=source,
        evidence_ref=evidence_ref,
        detail=detail,
        authoritative=authoritative,
    )


# ---------------------------------------------------------------------------
# S12-01: Knowledge strong + application weak (separate dimensions)
# ---------------------------------------------------------------------------

S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE = [
    make_evidence(
        MasteryDimension.KNOWLEDGE,
        "strong",
        "assessment_score",
        "ev-s12-01-001",
        "Knowledge score 0.92 — strong",
        authoritative=False,
    ),
    make_evidence(
        MasteryDimension.APPLICATION,
        "weak",
        "practice_units",
        "ev-s12-01-002",
        "Application practice_units=1 — weak",
        authoritative=False,
    ),
]


# ---------------------------------------------------------------------------
# S12-02: Weak recall detected
# ---------------------------------------------------------------------------

S12_02_WEAK_RECALL_EVIDENCE = [
    make_evidence(
        MasteryDimension.RECALL,
        "weak",
        "assessment_score",
        "ev-s12-02-001",
        "Recall assessment score 0.42 — weak",
        authoritative=False,
    ),
]


# ---------------------------------------------------------------------------
# S12-03: Practical readiness differs from theory (knowledge)
# ---------------------------------------------------------------------------

S12_03_PRACTICAL_DIFFERS_FROM_THEORY_EVIDENCE = [
    make_evidence(
        MasteryDimension.KNOWLEDGE,
        "strong",
        "assessment_score",
        "ev-s12-03-001",
        "Theory knowledge score 0.90 — strong",
        authoritative=False,
    ),
    make_evidence(
        MasteryDimension.PRACTICAL_READINESS,
        "weak",
        "topic_next_action",
        "ev-s12-03-002",
        "Practical readiness next_action=study — weak (differs from strong theory)",
        authoritative=False,
    ),
]


# ---------------------------------------------------------------------------
# S12-04: Formal competence absent — NOT inferred
# ---------------------------------------------------------------------------

S12_04_FORMAL_COMPETENCE_ABSENT_EVIDENCE = [
    make_evidence(
        MasteryDimension.KNOWLEDGE,
        "strong",
        "assessment_score",
        "ev-s12-04-001",
        "Knowledge score 0.95 — strong",
        authoritative=False,
    ),
    make_evidence(
        MasteryDimension.APPLICATION,
        "strong",
        "practice_units",
        "ev-s12-04-002",
        "Application practice_units=8 — strong",
        authoritative=False,
    ),
    # No formal competence evidence at all — must remain UNSIGNED
]


# ---------------------------------------------------------------------------
# S12-05: Formal competence changes ONLY from authoritative evidence
# ---------------------------------------------------------------------------

S12_05_AUTHORITATIVE_SIGNOFF_EVIDENCE = [
    make_evidence(
        MasteryDimension.FORMAL_COMPETENCE,
        "strong",
        "supervisor_signoff",
        "ev-s12-05-001",
        "Formal competence from supervisor signoff — authoritative",
        authoritative=True,
    ),
]

S12_05_NON_AUTHORITATIVE_CANNOT_MOVE_FC_EVIDENCE = [
    make_evidence(
        MasteryDimension.KNOWLEDGE,
        "strong",
        "assessment_score",
        "ev-s12-05-002",
        "Knowledge score 0.95 — strong",
        authoritative=False,
    ),
    make_evidence(
        MasteryDimension.APPLICATION,
        "strong",
        "practice_units",
        "ev-s12-05-003",
        "Application practice_units=8 — strong",
        authoritative=False,
    ),
    # Non-authoritative competency evidence — must NOT move formal competence
    make_evidence(
        MasteryDimension.FORMAL_COMPETENCE,
        "strong",
        "self_assessment",
        "ev-s12-05-004",
        "Self-assessment — NOT authoritative, must not sign off formal competence",
        authoritative=False,
    ),
]

S12_05_AUTHORITATIVE_SIGNOFF_WEAK_EVIDENCE = [
    make_evidence(
        MasteryDimension.FORMAL_COMPETENCE,
        "weak",
        "supervisor_signoff",
        "ev-s12-05-005",
        "Authoritative signoff but weak — formal competence stays UNSIGNED",
        authoritative=True,
    ),
]


# ---------------------------------------------------------------------------
# Edge case: unknown dimension rejected
# ---------------------------------------------------------------------------

S12_EDGE_UNKNOWN_DIMENSION_EVIDENCE = [
    make_evidence(
        MasteryDimension.KNOWLEDGE,
        "strong",
        "assessment_score",
        "ev-s12-edge-001",
        "Knowledge score 0.90 — strong",
        authoritative=False,
    ),
]


# ---------------------------------------------------------------------------
# Edge case: empty evidence list
# ---------------------------------------------------------------------------

S12_EDGE_EMPTY_EVIDENCE = []


# ---------------------------------------------------------------------------
# Edge case: all dimensions absent
# ---------------------------------------------------------------------------

S12_EDGE_ALL_ABSENT_EVIDENCE = [
    make_evidence(
        MasteryDimension.KNOWLEDGE,
        "absent",
        "none",
        "ev-s12-edge-002",
        "No knowledge evidence",
        authoritative=False,
    ),
]


# ---------------------------------------------------------------------------
# Deterministic clock helper
# ---------------------------------------------------------------------------

def _fixed_clock():
    return "2026-09-30T12:00:00"