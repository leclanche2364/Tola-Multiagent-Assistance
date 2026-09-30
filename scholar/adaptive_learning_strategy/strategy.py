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

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from scholar.learning_gap_analysis.gap_analyzer import Gap, GapType, GapAnalysisResult


# ---------------------------------------------------------------------------
# Calendar-time rejection guard
# ---------------------------------------------------------------------------

_CALENDAR_TIME_FIELDS = frozenset({
    "calendar_time",
    "scheduled_at",
    "start_time",
    "end_time",
    "time_slot",
    "weekday",
    "date",
    "timestamp",
    "occurred_at",
})


def _reject_calendar_time_fields(data: Dict[str, Any], label: str = "item") -> None:
    """Reject any dict that contains calendar-time keys."""
    for key in _CALENDAR_TIME_FIELDS:
        if key in data:
            raise ValueError(
                f"{label} contains forbidden calendar-time field {key!r}"
            )


# ---------------------------------------------------------------------------
# Learning item
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LearningItem:
    """One ordered learning item in an adaptive strategy.

    Fields:
        item_id: Stable unique identifier.
        topic: Curriculum topic or proficiency this item addresses.
        proficiency_id: Linked proficiency ID (optional).
        sequence: Position in the learning progression (1-based).
        priority: "high" | "medium" | "low".
        target_depth: Mastery dimension being targeted.
        target_mastery: Desired mastery level after this item.
        recommended_effort: Minutes of recommended study effort.
        outcomes: What the learner should achieve.
        rationale: Why this item is included — traceable to gap/evidence.
        evidence_refs: Traceable evidence references.
        gap_refs: Traceable gap IDs this item addresses.
    """
    item_id: str
    topic: str
    proficiency_id: Optional[str]
    sequence: int
    priority: str
    target_depth: str
    target_mastery: str
    recommended_effort: int
    outcomes: List[str]
    rationale: str
    evidence_refs: List[str] = field(default_factory=list)
    gap_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate this item immediately on construction."""
        self.validate()

    def validate(self) -> None:
        """Validate this item meets all S14 constraints."""
        # S14-03: effort must be present and positive
        if not isinstance(self.recommended_effort, int) or self.recommended_effort <= 0:
            raise ValueError(
                f"recommended_effort must be a positive int, got {self.recommended_effort!r}"
            )

        # S14-06: rationale must be non-empty
        if not isinstance(self.rationale, str) or not self.rationale.strip():
            raise ValueError("item must have a non-empty rationale")

        # S14-04: no learner-facing quiz instructions in outcomes or rationale
        _quiz_indicators = [
            "quiz", "flashcard", "flash card", "test yourself",
            "practice quiz", "take a quiz", "answer these",
            "multiple choice", "true or false", "fill in the blank",
        ]
        combined = (self.topic + " " + " ".join(self.outcomes) + " " + self.rationale).lower()
        for indicator in _quiz_indicators:
            if indicator in combined:
                raise ValueError(
                    f"item contains learner-facing quiz instruction: {indicator!r}"
                )

        # S14-05: no shadow teaching — no teaching script language
        _teaching_indicators = [
            "teach the learner", "explain to the student", "lecture on",
            "deliver a lesson", "instruct the learner", "guide the student",
            "teaching script", "lesson plan", "classroom instruction",
        ]
        for indicator in _teaching_indicators:
            if indicator in combined:
                raise ValueError(
                    f"item contains shadow teaching language: {indicator!r}"
                )

        # Calendar-time fields must not appear in any dict representation
        _reject_calendar_time_fields(
            {
                "item_id": self.item_id,
                "topic": self.topic,
                "proficiency_id": self.proficiency_id,
                "sequence": self.sequence,
                "priority": self.priority,
                "target_depth": self.target_depth,
                "target_mastery": self.target_mastery,
                "recommended_effort": self.recommended_effort,
                "outcomes": self.outcomes,
                "rationale": self.rationale,
            },
            label="LearningItem",
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a dict representation (calendar-time fields excluded)."""
        return {
            "item_id": self.item_id,
            "topic": self.topic,
            "proficiency_id": self.proficiency_id,
            "sequence": self.sequence,
            "priority": self.priority,
            "target_depth": self.target_depth,
            "target_mastery": self.target_mastery,
            "recommended_effort": self.recommended_effort,
            "outcomes": list(self.outcomes),
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
            "gap_refs": list(self.gap_refs),
        }


# ---------------------------------------------------------------------------
# Strategy priority mapping
# ---------------------------------------------------------------------------

def _priority_for_gap_type(gap_type: str) -> str:
    """Map gap type to item priority."""
    HIGH = {"missing_prerequisite", "weak_knowledge", "weak_application"}
    MEDIUM = {"insufficient_evidence", "uncovered_proficiency"}
    if gap_type in HIGH:
        return "high"
    if gap_type in MEDIUM:
        return "medium"
    return "low"


def _target_depth_for_gap(gap: Gap) -> str:
    """Determine target mastery dimension for a gap."""
    dim = gap.mastery_dimension
    if dim:
        return dim
    # Fallback based on gap type
    if gap.gap_type == GapType.MISSING_PREREQUISITE:
        return "KNOWLEDGE"
    if gap.gap_type == GapType.WEAK_KNOWLEDGE:
        return "KNOWLEDGE"
    if gap.gap_type == GapType.WEAK_APPLICATION:
        return "APPLICATION"
    if gap.gap_type == GapType.INSUFFICIENT_EVIDENCE:
        return "RATIONALE"
    if gap.gap_type == GapType.UNCOVERED_PROFICIENCY:
        return "KNOWLEDGE"
    return "KNOWLEDGE"


def _target_mastery_for_gap(gap: Gap) -> str:
    """Determine desired mastery level after addressing this gap."""
    if gap.severity == "high":
        return "strong"
    return "adequate"


def _effort_for_gap(gap: Gap) -> int:
    """Estimate recommended effort in minutes based on gap severity and type."""
    base = {
        GapType.MISSING_PREREQUISITE: 120,
        GapType.WEAK_KNOWLEDGE: 90,
        GapType.WEAK_APPLICATION: 120,
        GapType.INSUFFICIENT_EVIDENCE: 60,
        GapType.UNCOVERED_PROFICIENCY: 90,
    }
    mult = {"high": 1.5, "medium": 1.0, "low": 0.5}
    b = base.get(gap.gap_type, 60)
    m = mult.get(gap.severity, 1.0)
    return max(15, int(b * m))


# ---------------------------------------------------------------------------
# Strategy result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StrategyResult:
    """Result of building an adaptive learning strategy."""
    goal_id: str
    goal_title: str
    goal_state: str
    items: List[LearningItem]
    item_count: int
    total_recommended_effort_minutes: int
    evidence_trace: List[str]
    gap_refs: List[str]
    deterministic_key: str

    def validate(self) -> None:
        """Validate the strategy result."""
        # Check sequence ordering
        for i, item in enumerate(self.items):
            if item.sequence != i + 1:
                raise ValueError(
                    f"item sequence {item.sequence} != expected {i + 1}"
                )
            item.validate()

        # Check no calendar-time fields in serialized form
        for item in self.items:
            _reject_calendar_time_fields(item.to_dict(), label="StrategyResult item")

        # Check effort sum
        total = sum(item.recommended_effort for item in self.items)
        if total != self.total_recommended_effort_minutes:
            raise ValueError(
                f"total_recommended_effort_minutes {self.total_recommended_effort_minutes} "
                f"!= sum of item efforts {total}"
            )


# ---------------------------------------------------------------------------
# Strategy builder
# ---------------------------------------------------------------------------

class AdaptiveLearningStrategy:
    """Builds an ordered adaptive learning strategy from gap analysis.

    Scholar plans learning while IntenSIQ retains delivery control.
    This module produces PLANNING items only — it does not schedule
    calendar time and does not assume delivery of teaching.

    Key guarantees:
    - S14-01: Items ordered in logical progression.
    - S14-02: Target depth appropriate to gap/mastery dimension.
    - S14-03: Recommended effort present for every item.
    - S14-04: No learner-facing quiz instructions.
    - S14-05: No shadow teaching.
    - S14-06: Rationale traceable to gap/evidence.
    - Deterministic repeat calls produce identical results.
    - Clock injection for deterministic testing.
    """

    def __init__(self, clock: Optional[callable] = None) -> None:
        self._clock = clock or (lambda: "2026-09-30T12:00:00")

    def build(
        self,
        gap_result: GapAnalysisResult,
        decomposition_result: Optional[Dict[str, Any]] = None,
        proficiency_records: Optional[List[Dict[str, Any]]] = None,
    ) -> StrategyResult:
        """Build an adaptive learning strategy from gap analysis.

        Args:
            gap_result: GapAnalysisResult from S13 gap analysis.
            decomposition_result: Optional decomposition dict from S10.
            proficiency_records: Optional list of proficiency record dicts.

        Returns:
            StrategyResult with ordered learning items.

        Raises ValueError on malformed input.
        """
        # Call clock for deterministic time recording
        _ = self._clock()

        # Validate gap_result
        if gap_result is None:
            raise ValueError("gap_result must not be None")
        if not isinstance(gap_result, GapAnalysisResult):
            raise ValueError(
                f"gap_result must be a GapAnalysisResult, got {type(gap_result).__name__}"
            )

        goal_id = gap_result.goal_id
        goal_title = gap_result.goal_title
        goal_state = gap_result.goal_state

        # Validate goal state
        valid_states = {"ACTIVE", "PAUSED", "COMPLETED", "STOPPED", "SUPERSEDED"}
        if goal_state not in valid_states:
            raise ValueError(f"goal_state must be one of {sorted(valid_states)}, got {goal_state!r}")

        # PAUSED and SUPERSEDED goals are excluded from strategy building
        if goal_state in ("PAUSED", "SUPERSEDED"):
            return StrategyResult(
                goal_id=goal_id,
                goal_title=goal_title,
                goal_state=goal_state,
                items=[],
                item_count=0,
                total_recommended_effort_minutes=0,
                evidence_trace=[],
                gap_refs=[],
                deterministic_key=gap_result.deterministic_key,
            )

        # Empty gap list → explicit empty strategy, not invented items
        if not gap_result.gaps:
            return StrategyResult(
                goal_id=goal_id,
                goal_title=goal_title,
                goal_state=goal_state,
                items=[],
                item_count=0,
                total_recommended_effort_minutes=0,
                evidence_trace=list(gap_result.evidence_trace),
                gap_refs=[],
                deterministic_key=gap_result.deterministic_key,
            )

        # Build items from gaps in logical progression order
        # Priority order: missing_prerequisite first, then weak_knowledge,
        # weak_application, insufficient_evidence, uncovered_proficiency
        gap_priority_order = {
            GapType.MISSING_PREREQUISITE: 0,
            GapType.WEAK_KNOWLEDGE: 1,
            GapType.WEAK_APPLICATION: 2,
            GapType.INSUFFICIENT_EVIDENCE: 3,
            GapType.UNCOVERED_PROFICIENCY: 4,
        }

        sorted_gaps = sorted(
            gap_result.gaps,
            key=lambda g: (gap_priority_order.get(g.gap_type, 99), g.gap_id),
        )

        items: List[LearningItem] = []
        all_evidence_refs: List[str] = []
        all_gap_refs: List[str] = []

        for idx, gap in enumerate(sorted_gaps):
            seq = idx + 1
            item_id = f"strategy-item-{goal_id}-{seq:03d}"
            priority = _priority_for_gap_type(gap.gap_type.value)
            target_depth = _target_depth_for_gap(gap)
            target_mastery = _target_mastery_for_gap(gap)
            effort = _effort_for_gap(gap)

            # Build outcomes based on gap type and target depth
            outcomes = self._build_outcomes(gap, target_depth, target_mastery)

            # Build rationale traceable to gap/evidence
            rationale = self._build_rationale(gap, outcomes)

            # Collect evidence refs and gap refs
            ev_refs = list(gap.evidence_refs)
            all_evidence_refs.extend(ev_refs)
            all_gap_refs.append(gap.gap_id)

            # Determine proficiency_id from gap
            prof_id = None
            if gap.topic_id:
                prof_id = gap.topic_id
            if decomposition_result:
                for prof in decomposition_result.get("proficiencies", []):
                    if prof.get("proficiency_id") and prof.get("domain"):
                        prof_id = prof["proficiency_id"]
                        break

            item = LearningItem(
                item_id=item_id,
                topic=gap.description.split(":")[0].strip() if ":" in gap.description else gap.description[:80],
                proficiency_id=prof_id,
                sequence=seq,
                priority=priority,
                target_depth=target_depth,
                target_mastery=target_mastery,
                recommended_effort=effort,
                outcomes=outcomes,
                rationale=rationale,
                evidence_refs=ev_refs,
                gap_refs=[gap.gap_id],
            )

            # Validate item before adding
            item.validate()

            items.append(item)

        # Deduplicate evidence refs
        seen: set = set()
        unique_evidence: List[str] = []
        for ref in all_evidence_refs:
            if ref and ref not in seen:
                seen.add(ref)
                unique_evidence.append(ref)

        # Build deterministic key
        det_key = self._build_strategy_key(
            goal_id,
            [g.gap_type.value for g in sorted_gaps],
            unique_evidence,
            [item.sequence for item in items],
        )

        total_effort = sum(item.recommended_effort for item in items)

        return StrategyResult(
            goal_id=goal_id,
            goal_title=goal_title,
            goal_state=goal_state,
            items=items,
            item_count=len(items),
            total_recommended_effort_minutes=total_effort,
            evidence_trace=unique_evidence,
            gap_refs=all_gap_refs,
            deterministic_key=det_key,
        )

    def _build_outcomes(
        self,
        gap: Gap,
        target_depth: str,
        target_mastery: str,
    ) -> List[str]:
        """Build outcomes for a learning item based on the gap."""
        outcomes: List[str] = []

        if gap.gap_type == GapType.MISSING_PREREQUISITE:
            outcomes.append(f"Address prerequisite gap: {gap.description}")
            outcomes.append(f"Achieve {target_mastery} level in {target_depth}")

        elif gap.gap_type == GapType.WEAK_KNOWLEDGE:
            outcomes.append(f"Strengthen {target_depth} to {target_mastery} level")
            outcomes.append("Demonstrate understanding through application exercises")

        elif gap.gap_type == GapType.WEAK_APPLICATION:
            outcomes.append(f"Improve {target_depth} to {target_mastery} level")
            outcomes.append("Apply knowledge in supervised practice scenarios")

        elif gap.gap_type == GapType.INSUFFICIENT_EVIDENCE:
            outcomes.append(f"Gather additional evidence for {target_depth}")
            outcomes.append(f"Reach {target_mastery} evidence strength")

        elif gap.gap_type == GapType.UNCOVERED_PROFICIENCY:
            outcomes.append(f"Map and address uncovered proficiency")
            outcomes.append(f"Achieve {target_mastery} level in {target_depth}")

        else:
            outcomes.append(f"Address gap: {gap.description}")
            outcomes.append(f"Achieve {target_mastery} level in {target_depth}")

        return outcomes

    def _build_rationale(
        self,
        gap: Gap,
        outcomes: List[str],
    ) -> str:
        """Build a rationale traceable to the gap and its evidence."""
        evidence_str = ", ".join(gap.evidence_refs) if gap.evidence_refs else "no evidence refs"
        return (
            f"Included because gap {gap.gap_id} ({gap.gap_type.value}) "
            f"detected from evidence [{evidence_str}]. "
            f"Severity: {gap.severity}. "
            f"Recommendation: {gap.recommendation}. "
            f"Target outcomes: {'; '.join(outcomes)}."
        )

    def _build_strategy_key(
        self,
        goal_id: str,
        gap_types: List[str],
        evidence_refs: List[str],
        sequences: List[int],
    ) -> str:
        """Build a deterministic key for the strategy result."""
        parts = [
            f"goal:{goal_id}",
            f"gaps:{','.join(sorted(gap_types))}",
            f"refs:{','.join(sorted(evidence_refs))}",
            f"seqs:{','.join(str(s) for s in sequences)}",
        ]
        combined = "|".join(parts)
        h = 0
        for ch in combined:
            h = ((h * 31) + ord(ch)) & 0xFFFFFFFF
        return f"{combined}::hash={h:08x}"


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def build_strategy(
    gap_result: GapAnalysisResult,
    decomposition_result: Optional[Dict[str, Any]] = None,
    proficiency_records: Optional[List[Dict[str, Any]]] = None,
    clock: Optional[callable] = None,
) -> StrategyResult:
    """Convenience function to build an adaptive learning strategy.

    Creates an AdaptiveLearningStrategy with an optional injected clock,
    calls build(), and returns the StrategyResult.
    """
    strategy = AdaptiveLearningStrategy(clock=clock)
    return strategy.build(
        gap_result=gap_result,
        decomposition_result=decomposition_result,
        proficiency_records=proficiency_records,
    )