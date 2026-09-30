"""
Batch S14 -- Adaptive Learning Strategy.

Produces ordered learning items from gap analysis results and
decomposition data. Each item contains: topic/proficiency,
sequence, priority, target depth/mastery, recommended effort,
outcomes and rationale. These are PLANNING items for
Scholar/IntenSIQ, NOT learner-facing quizzes and NOT teaching
scripts.

Key guarantees:
- S14-01: Items are in logical progression order.
- S14-02: Target depth is appropriate to the gap/mastery dimension.
- S14-03: Recommended effort is present for every item.
- S14-04: No learner-facing quiz instructions.
- S14-05: No shadow teaching (no teaching scripts).
- S14-06: Every material item has a rationale traceable to gap/evidence.
- Calendar-time fields are rejected (no scheduling).
- PAUSED/SUPERSEDED goals are excluded.
- Deterministic repeat calls produce identical results.
- Malformed gap/decomposition input is rejected.
- Empty gap list produces an explicit empty strategy, not invented items.
- Clock injection for deterministic testing.

Plain ASCII. Python 3 stdlib only.
"""

from scholar.learning_gap_analysis.gap_analyzer import Gap, GapType, GapAnalysisResult


__all__ = [
    "AdaptiveLearningStrategy",
    "LearningItem",
    "StrategyResult",
    "build_strategy",
]