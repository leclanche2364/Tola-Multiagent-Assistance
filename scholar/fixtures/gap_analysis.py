"""
Batch S13 -- Learning Gap Analysis Fixtures.
Deterministic fixtures for S13 QA: gap analysis scenarios
covering S13-01..S13-06 plus edge cases.
Plain ASCII. Python 3 stdlib only.
"""

from scholar.mastery.model import (
    MasteryAnalyser,
    MasteryDimension,
    DimensionEvidence,
)
from scholar.learning_gap_analysis.gap_analyzer import (
    LearningGapAnalyzer,
    GapType,
)


# ---------------------------------------------------------------------------
# Clock helper (deterministic)
# ---------------------------------------------------------------------------

def _fixed_clock():
    return "2026-09-30T12:00:00"


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def make_gap_analyzer(clock=None):
    """Build a LearningGapAnalyzer with optional injected clock."""
    return LearningGapAnalyzer(clock=clock or _fixed_clock)


def make_dimension_evidence(dimension, strength, source, evidence_ref, detail, authoritative=False):
    """Build a DimensionEvidence quickly."""
    return DimensionEvidence(
        dimension=dimension,
        strength=strength,
        source=source,
        evidence_ref=evidence_ref,
        detail=detail,
        authoritative=authoritative,
    )


# ====================================================================== #
# S13-01: Missing prerequisite detected
# ====================================================================== #

S13_01_MISSING_PREREQUISITE_DECOMPOSITION = {
    "goal_id": "goal-vent-01",
    "goal_title": "Master mechanical ventilation",
    "goal_state": "ACTIVE",
    "curriculum_nodes": [
        {
            "node_id": "node-vent-basics",
            "node_title": "Ventilation Basics",
            "node_kind": "topic",
            "source_id": "src-handbook-cc101",
            "source_version": "1.0",
            "mastery_dimensions": ["KNOWLEDGE", "RECALL"],
            "learning_outcomes": ["outcome-vent-01"],
        },
    ],
    "proficiencies": [
        {
            "proficiency_id": "prof-vent-01",
            "domain": "mechanical_ventilation",
            "step": "step2",
            "verbatim_requirement": "Demonstrate knowledge of mechanical ventilation principles.",
            "knowledge_requirements": ["Know ventilator modes"],
            "application_requirements": ["Apply lung-protective strategies"],
            "rationale_requirements": ["Explain weaning criteria"],
            "linked_topics": ["ventilation-basics"],
            "linked_learning_outcomes": ["outcome-vent-01"],
            "linked_evidence": ["ev-vent-001"],
        },
    ],
    "prerequisites": [
        {
            "from_node_id": "node-vent-basics",
            "to_node_id": "node-lung-protective",
            "link_type": "prerequisite",
        },
    ],
    "missing_prerequisites": [
        "prerequisite node 'node-lung-protective' (Lung Protective Ventilation) is not covered by the goal decomposition",
    ],
    "mastery_dimensions": ["KNOWLEDGE", "RECALL"],
    "time_horizon_days": 42,
    "time_horizon_risk": False,
    "evidence_requirements": [
        {
            "evidence_id": "ev-vent-001",
            "link_type": "supports",
            "source": "proficiency",
        },
    ],
    "domain_count": 1,
    "is_multi_domain": False,
    "deterministic_key": "goal:goal-vent-01|nodes:node-vent-basics|profs:prof-vent-01|prereqs:node-vent-basics|dims:KNOWLEDGE,RECALL|horizon:42::hash=00000000",
}


# ====================================================================== #
# S13-02: Weak knowledge detected
# ====================================================================== #

S13_02_WEAK_KNOWLEDGE_MASTERY = [
    make_dimension_evidence(
        MasteryDimension.KNOWLEDGE,
        "weak",
        "assessment_score",
        "ev-s13-02-001",
        "Knowledge assessment score 0.45 — weak",
        authoritative=False,
    ),
    make_dimension_evidence(
        MasteryDimension.APPLICATION,
        "strong",
        "practice_units",
        "ev-s13-02-002",
        "Application practice_units=8 — strong",
        authoritative=False,
    ),
]


# ====================================================================== #
# S13-03: Weak application detected
# ====================================================================== #

S13_03_WEAK_APPLICATION_MASTERY = [
    make_dimension_evidence(
        MasteryDimension.KNOWLEDGE,
        "strong",
        "assessment_score",
        "ev-s13-03-001",
        "Knowledge score 0.92 — strong",
        authoritative=False,
    ),
    make_dimension_evidence(
        MasteryDimension.APPLICATION,
        "weak",
        "practice_units",
        "ev-s13-03-002",
        "Application practice_units=1 — weak",
        authoritative=False,
    ),
]


# ====================================================================== #
# S13-04: Insufficient evidence/practice detected
# ====================================================================== #

S13_04_INSUFFICIENT_EVIDENCE_MASTERY = [
    make_dimension_evidence(
        MasteryDimension.KNOWLEDGE,
        "weak",
        "assessment_score",
        "ev-s13-04-001",
        "Knowledge score 0.45 — weak",
        authoritative=False,
    ),
    make_dimension_evidence(
        MasteryDimension.APPLICATION,
        "absent",
        "none",
        "ev-s13-04-002",
        "No application evidence provided",
        authoritative=False,
    ),
]


# ====================================================================== #
# S13-05: Uncovered proficiency detected
# ====================================================================== #

S13_05_UNCOVERED_PROFICIENCY_DECOMPOSITION = {
    "goal_id": "goal-vent-01",
    "goal_title": "Master mechanical ventilation",
    "goal_state": "ACTIVE",
    "curriculum_nodes": [
        {
            "node_id": "node-vent-basics",
            "node_title": "Ventilation Basics",
            "node_kind": "topic",
            "source_id": "src-handbook-cc101",
            "source_version": "1.0",
            "mastery_dimensions": ["KNOWLEDGE", "RECALL"],
            "learning_outcomes": ["outcome-vent-01"],
        },
    ],
    "proficiencies": [
        {
            "proficiency_id": "prof-vent-01",
            "domain": "mechanical_ventilation",
            "step": "step2",
            "verbatim_requirement": "Demonstrate knowledge of mechanical ventilation principles.",
            "knowledge_requirements": ["Know ventilator modes"],
            "application_requirements": ["Apply lung-protective strategies"],
            "rationale_requirements": ["Explain weaning criteria"],
            "linked_topics": ["ventilation-basics"],
            "linked_learning_outcomes": ["outcome-vent-01"],
            "linked_evidence": ["ev-vent-001"],
        },
    ],
    "prerequisites": [],
    "missing_prerequisites": [],
    "mastery_dimensions": ["KNOWLEDGE", "RECALL"],
    "time_horizon_days": 42,
    "time_horizon_risk": False,
    "evidence_requirements": [
        {
            "evidence_id": "ev-vent-001",
            "link_type": "supports",
            "source": "proficiency",
        },
    ],
    "domain_count": 1,
    "is_multi_domain": False,
    "deterministic_key": "goal:goal-vent-01|nodes:node-vent-basics|profs:prof-vent-01|prereqs:|dims:KNOWLEDGE,RECALL|horizon:42::hash=00000000",
}

S13_05_UNCOVERED_PROFICIENCY_RECORDS = [
    {
        "proficiency_id": "prof-vent-01",
        "domain": "mechanical_ventilation",
        "step": "step2",
        "verbatim_requirement": "Demonstrate knowledge of mechanical ventilation principles.",
        "knowledge_requirements": ["Know ventilator modes"],
        "application_requirements": ["Apply lung-protective strategies"],
        "rationale_requirements": ["Explain weaning criteria"],
        "linked_topics": ["ventilation-basics"],
        "linked_learning_outcomes": ["outcome-vent-01"],
        "linked_evidence": ["ev-vent-001"],
        "status": "active",
        "version": 1,
    },
    {
        "proficiency_id": "prof-hemo-01",
        "domain": "haemodynamic_monitoring",
        "step": "step2",
        "verbatim_requirement": "Apply advanced haemodynamic monitoring including arterial line interpretation.",
        "knowledge_requirements": ["Know arterial line types"],
        "application_requirements": ["Interpret CVP waveforms"],
        "rationale_requirements": ["Explain cardiac output measurement"],
        "linked_topics": ["haemodynamics"],
        "linked_learning_outcomes": ["outcome-hemo-01"],
        "linked_evidence": ["ev-hemo-001"],
        "status": "active",
        "version": 1,
    },
]


# ====================================================================== #
# S13-06: Strong fixture — NOT incorrectly flagged as a gap
# ====================================================================== #

S13_06_STRONG_MASTERY = [
    make_dimension_evidence(
        MasteryDimension.KNOWLEDGE,
        "strong",
        "assessment_score",
        "ev-s13-06-001",
        "Knowledge score 0.95 — strong",
        authoritative=False,
    ),
    make_dimension_evidence(
        MasteryDimension.APPLICATION,
        "strong",
        "practice_units",
        "ev-s13-06-002",
        "Application practice_units=10 — strong",
        authoritative=False,
    ),
    make_dimension_evidence(
        MasteryDimension.RECALL,
        "strong",
        "assessment_score",
        "ev-s13-06-003",
        "Recall score 0.90 — strong",
        authoritative=False,
    ),
    make_dimension_evidence(
        MasteryDimension.PRACTICAL_READINESS,
        "strong",
        "topic_next_action",
        "ev-s13-06-004",
        "Practical readiness next_action=assess — strong",
        authoritative=False,
    ),
]

S13_06_STRONG_DECOMPOSITION = {
    "goal_id": "goal-vent-01",
    "goal_title": "Master mechanical ventilation",
    "goal_state": "ACTIVE",
    "curriculum_nodes": [
        {
            "node_id": "node-vent-basics",
            "node_title": "Ventilation Basics",
            "node_kind": "topic",
            "source_id": "src-handbook-cc101",
            "source_version": "1.0",
            "mastery_dimensions": ["KNOWLEDGE", "RECALL"],
            "learning_outcomes": ["outcome-vent-01"],
        },
    ],
    "proficiencies": [
        {
            "proficiency_id": "prof-vent-01",
            "domain": "mechanical_ventilation",
            "step": "step2",
            "verbatim_requirement": "Demonstrate knowledge of mechanical ventilation principles.",
            "knowledge_requirements": ["Know ventilator modes"],
            "application_requirements": ["Apply lung-protective strategies"],
            "rationale_requirements": ["Explain weaning criteria"],
            "linked_topics": ["ventilation-basics"],
            "linked_learning_outcomes": ["outcome-vent-01"],
            "linked_evidence": ["ev-vent-001"],
        },
    ],
    "prerequisites": [],
    "missing_prerequisites": [],
    "mastery_dimensions": ["KNOWLEDGE", "RECALL"],
    "time_horizon_days": 42,
    "time_horizon_risk": False,
    "evidence_requirements": [
        {
            "evidence_id": "ev-vent-001",
            "link_type": "supports",
            "source": "proficiency",
        },
    ],
    "domain_count": 1,
    "is_multi_domain": False,
    "deterministic_key": "goal:goal-vent-01|nodes:node-vent-basics|profs:prof-vent-01|prereqs:|dims:KNOWLEDGE,RECALL|horizon:42::hash=00000000",
}


# ====================================================================== #
# Edge case: gap without evidence_ref rejected
# ====================================================================== #

S13_EDGE_GAP_WITHOUT_EVIDENCE_REF_MASTERY = [
    make_dimension_evidence(
        MasteryDimension.KNOWLEDGE,
        "weak",
        "assessment_score",
        "",  # empty evidence_ref — gap must be rejected
        "Knowledge score 0.45 — weak but no evidence ref",
        authoritative=False,
    ),
]


# ====================================================================== #
# Edge case: PAUSED goal — excluded from gap analysis
# ====================================================================== #

S13_EDGE_PAUSED_GOAL_DECOMPOSITION = {
    "goal_id": "goal-vent-paused",
    "goal_title": "Master mechanical ventilation",
    "goal_state": "PAUSED",
    "curriculum_nodes": [],
    "proficiencies": [],
    "prerequisites": [],
    "missing_prerequisites": [],
    "mastery_dimensions": [],
    "time_horizon_days": None,
    "time_horizon_risk": False,
    "evidence_requirements": [],
    "domain_count": 0,
    "is_multi_domain": False,
    "deterministic_key": "goal:goal-vent-paused|nodes:|profs:|prereqs:|dims:|horizon:None::hash=00000000",
}


# ====================================================================== #
# Edge case: SUPERSEDED goal — excluded from gap analysis
# ====================================================================== #

S13_EDGE_SUPERSEDED_GOAL_DECOMPOSITION = {
    "goal_id": "goal-vent-superseded",
    "goal_title": "Master mechanical ventilation",
    "goal_state": "SUPERSEDED",
    "curriculum_nodes": [],
    "proficiencies": [],
    "prerequisites": [],
    "missing_prerequisites": [],
    "mastery_dimensions": [],
    "time_horizon_days": None,
    "time_horizon_risk": False,
    "evidence_requirements": [],
    "domain_count": 0,
    "is_multi_domain": False,
    "deterministic_key": "goal:goal-vent-superseded|nodes:|profs:|prereqs:|dims:|horizon:None::hash=00000000",
}


# ====================================================================== #
# Edge case: empty state — explicit empty gap list, not invented gaps
# ====================================================================== #

S13_EDGE_EMPTY_MASTERY = []

S13_EDGE_EMPTY_DECOMPOSITION = {
    "goal_id": "goal-empty-01",
    "goal_title": "Empty goal",
    "goal_state": "ACTIVE",
    "curriculum_nodes": [],
    "proficiencies": [],
    "prerequisites": [],
    "missing_prerequisites": [],
    "mastery_dimensions": [],
    "time_horizon_days": None,
    "time_horizon_risk": False,
    "evidence_requirements": [],
    "domain_count": 0,
    "is_multi_domain": False,
    "deterministic_key": "goal:goal-empty-01|nodes:|profs:|prereqs:|dims:|horizon:None::hash=00000000",
}

S13_EDGE_EMPTY_PROFICIENCY_RECORDS = []


# ====================================================================== #
# Edge case: malformed mastery input rejected
# ====================================================================== #

S13_EDGE_MALFORMED_MASTERY_NONE = None


# ====================================================================== #
# Edge case: malformed decomposition input rejected
# ====================================================================== #

S13_EDGE_MALFORMED_DECOMPOSITION_NONE = None


# ====================================================================== #
# Deterministic clock helper
# ====================================================================== #

def _fixed_clock():
    return "2026-09-30T12:00:00"
