"""
Batch S14 -- Adaptive Learning Strategy Fixtures.
Deterministic fixtures for S14 QA: strategy scenarios
covering S14-01..S14-06 plus edge cases.
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
from scholar.adaptive_learning_strategy.strategy import (
    AdaptiveLearningStrategy,
    LearningItem,
    StrategyResult,
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


def make_strategy(clock=None):
    """Build an AdaptiveLearningStrategy with optional injected clock."""
    return AdaptiveLearningStrategy(clock=clock or _fixed_clock)


def make_mastery_result(evidence, goal_id="goal-vent-01", topic_id=None):
    """Build a MasteryResult from a list of DimensionEvidence."""
    analyser = MasteryAnalyser(clock=_fixed_clock)
    return analyser.evaluate(evidence, goal_id, topic_id=topic_id)


# ====================================================================== #
# S14-01: Ordered items — logical progression
# ====================================================================== #

# A gap result with multiple gap types to test ordering
S14_01_GAP_RESULT_MULTI = None  # built dynamically in tests


# ====================================================================== #
# S14-02: Target depth appropriate to gap/mastery dimension
# ====================================================================== #

# Knowledge gap → target depth KNOWLEDGE
S14_02_WEAK_KNOWLEDGE_GAP = [
    make_dimension_evidence(
        MasteryDimension.KNOWLEDGE,
        "weak",
        "assessment_score",
        "ev-s14-02-001",
        "Knowledge assessment score 0.45 — weak",
        authoritative=False,
    ),
    make_dimension_evidence(
        MasteryDimension.APPLICATION,
        "strong",
        "practice_units",
        "ev-s14-02-002",
        "Application practice_units=8 — strong",
        authoritative=False,
    ),
]

# Application gap → target depth APPLICATION
S14_02_WEAK_APPLICATION_GAP = [
    make_dimension_evidence(
        MasteryDimension.KNOWLEDGE,
        "strong",
        "assessment_score",
        "ev-s14-02-003",
        "Knowledge score 0.92 — strong",
        authoritative=False,
    ),
    make_dimension_evidence(
        MasteryDimension.APPLICATION,
        "weak",
        "practice_units",
        "ev-s14-02-004",
        "Application practice_units=1 — weak",
        authoritative=False,
    ),
]

# Missing prerequisite → target depth KNOWLEDGE
S14_02_MISSING_PREREQ_DECOMPOSITION = {
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
# S14-03: Effort present
# ====================================================================== #

S14_03_GAP_WITH_EFFORT = [
    make_dimension_evidence(
        MasteryDimension.KNOWLEDGE,
        "weak",
        "assessment_score",
        "ev-s14-03-001",
        "Knowledge score 0.45 — weak",
        authoritative=False,
    ),
]


# ====================================================================== #
# S14-04: No learner-facing quiz instructions
# ====================================================================== #

# A gap that would produce a rationale — we verify the rationale
# and outcomes do NOT contain quiz language
S14_04_GAP_RESULT = None  # built dynamically in tests


# ====================================================================== #
# S14-05: No shadow teaching
# ====================================================================== #

# A gap that would produce a rationale — we verify the rationale
# and outcomes do NOT contain teaching script language
S14_05_GAP_RESULT = None  # built dynamically in tests


# ====================================================================== #
# S14-06: Rationale traceable to gap/evidence
# ====================================================================== #

S14_06_GAP_RESULT = None  # built dynamically in tests


# ====================================================================== #
# Edge: PAUSED goal — excluded from strategy
# ====================================================================== #

S14_EDGE_PAUSED_GOAL_DECOMPOSITION = {
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
# Edge: SUPERSEDED goal — excluded from strategy
# ====================================================================== #

S14_EDGE_SUPERSEDED_GOAL_DECOMPOSITION = {
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
# Edge: empty gap list → explicit empty strategy
# ====================================================================== #

S14_EDGE_EMPTY_GAP_RESULT = None  # built dynamically in tests


# ====================================================================== #
# Edge: malformed gap input rejected
# ====================================================================== #

S14_EDGE_MALFORMED_GAP_NONE = None


# ====================================================================== #
# Edge: malformed decomposition input rejected
# ====================================================================== #

S14_EDGE_MALFORMED_DECOMPOSITION_NONE = None


# ====================================================================== #
# Edge: item without rationale rejected
# ====================================================================== #

S14_EDGE_ITEM_WITHOUT_RATIONALE = None  # tested via direct LearningItem creation


# ====================================================================== #
# Edge: item without evidence trace rejected
# ====================================================================== #

S14_EDGE_ITEM_WITHOUT_EVIDENCE = None  # tested via direct LearningItem creation


# ====================================================================== #
# Edge: calendar-time fields rejected
# ====================================================================== #

S14_EDGE_CALENDAR_TIME_FIELDS = None  # tested via direct LearningItem creation


# ====================================================================== #
# Deterministic clock helper
# ====================================================================== #

def _fixed_clock():
    return "2026-09-30T12:00:00"