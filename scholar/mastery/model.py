"""
Batch S12 -- Mastery Model.

Tracks eight distinct, separately-evidenced mastery dimensions:
  KNOWLEDGE, RATIONALE, APPLICATION, CRITICAL_ANALYSIS,
  RECALL, TRANSFER, PRACTICAL_READINESS, FORMAL_COMPETENCE.

Rules enforced:
  S12-01  Knowledge strong + application weak are represented
          separately (no single blended score).
  S12-02  Weak recall is detected and surfaced.
  S12-03  Practical readiness can differ from theory (knowledge).
  S12-04  Formal competence absent -> NOT inferred (no defaults,
          no inference from theory strength).
  S12-05  Formal competence changes ONLY from authoritative
          evidence (authoritative sign-off source); non-authoritative
          evidence cannot move it.

All dimensions remain distinct and evidence-based throughout.
Plain ASCII. Python 3 stdlib only.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
#  Dimension enum — the eight distinct mastery dimensions
# ---------------------------------------------------------------------------

class MasteryDimension(str, Enum):
    KNOWLEDGE = "knowledge"
    RATIONALE = "rationale"
    APPLICATION = "application"
    CRITICAL_ANALYSIS = "critical_analysis"
    RECALL = "recall"
    TRANSFER = "transfer"
    PRACTICAL_READINESS = "practical_readiness"
    FORMAL_COMPETENCE = "formal_competence"


# ---------------------------------------------------------------------------
#  Per-dimension evidence record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DimensionEvidence:
    """A single piece of evidence for one mastery dimension.

    Never invented — only references what the learner-state
    or external authoritative source actually provides.
    """
    dimension: MasteryDimension
    strength: str            # "strong" | "weak" | "absent"
    source: str              # e.g. "assessment_score", "competency_evidence",
                             # "practical_observation", "authoritative_signoff"
    evidence_ref: str        # traceable reference to the originating evidence item
    detail: str              # human-readable description
    authoritative: bool = False  # only True for authoritative sign-off sources


# ---------------------------------------------------------------------------
#  Mastery result for one goal / topic
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MasteryResult:
    """Mastery assessment for a single goal/topic.

    Every dimension is present as a distinct value.
    No blended scores. No inference from theory strength
    into formal competence.
    """
    goal_id: str
    topic_id: Optional[str]
    dimensions: Dict[MasteryDimension, DimensionEvidence] = field(default_factory=dict)
    formal_competence_state: str = "UNSIGNED"
    evidence_trace: List[str] = field(default_factory=list)

    def dimension_strength(self, dim: MasteryDimension) -> str:
        """Return the strength for a given dimension."""
        ev = self.dimensions.get(dim)
        if ev is None:
            return "absent"
        return ev.strength

    def knowledge_strong_application_weak(self) -> bool:
        """S12-01: knowledge is strong AND application is weak."""
        return (
            self.dimension_strength(MasteryDimension.KNOWLEDGE) == "strong"
            and self.dimension_strength(MasteryDimension.APPLICATION) == "weak"
        )

    def recall_weak(self) -> bool:
        """S12-02: recall is weak."""
        return self.dimension_strength(MasteryDimension.RECALL) == "weak"

    def practical_readiness_differs_from_theory(self) -> bool:
        """S12-03: practical readiness differs from knowledge/theory strength."""
        theory = self.dimension_strength(MasteryDimension.KNOWLEDGE)
        practice = self.dimension_strength(MasteryDimension.PRACTICAL_READINESS)
        return theory != practice

    def formal_competence_unsigned(self) -> bool:
        """S12-04: formal competence is absent / unsigned."""
        return self.formal_competence_state == "UNSIGNED"


# ---------------------------------------------------------------------------
#  Formal competence sign-off authority
# ---------------------------------------------------------------------------

_AUTHORITATIVE_SOURCES = frozenset({
    "supervisor_signoff",
    "authoritative_assessment",
    "clinical_signoff",
    "pad_system_signoff",
})


def _is_authoritative_source(source: str) -> bool:
    return source in _AUTHORITATIVE_SOURCES


# ---------------------------------------------------------------------------
#  Mastery analyser
# ---------------------------------------------------------------------------

class MasteryAnalyser:
    """Deterministic mastery analyser.

    Evaluates each of the eight mastery dimensions independently
    from evidence.  Formal competence is ONLY updated from
    authoritative evidence sources (S12-05).  Non-authoritative
    evidence cannot move formal competence.
    """

    def __init__(self, clock: Optional[callable] = None) -> None:
        self._clock = clock or (lambda: "2026-09-30T12:00:00")

    def evaluate(
        self,
        evidence: List[DimensionEvidence],
        goal_id: str,
        topic_id: Optional[str] = None,
    ) -> MasteryResult:
        """Evaluate mastery dimensions from a list of evidence items.

        Each evidence item maps to exactly one dimension.
        Dimensions not covered by evidence remain "absent".
        Formal competence is ONLY updated by authoritative sources.
        """
        # Call the clock for deterministic time recording
        evaluated_at = self._clock()
        dimensions: Dict[MasteryDimension, DimensionEvidence] = {}
        evidence_trace: List[str] = []
        formal_competence_state = "UNSIGNED"

        # Group evidence by dimension
        by_dimension: Dict[str, List[DimensionEvidence]] = {}
        for ev in evidence:
            by_dimension.setdefault(ev.dimension.value, []).append(ev)
            evidence_trace.append(ev.evidence_ref)

        # Evaluate each dimension independently
        for dim in MasteryDimension:
            dim_evidence_list = by_dimension.get(dim.value, [])
            if not dim_evidence_list:
                dimensions[dim] = DimensionEvidence(
                    dimension=dim,
                    strength="absent",
                    source="none",
                    evidence_ref="",
                    detail=f"No evidence provided for {dim.value}",
                    authoritative=False,
                )
                continue

            # Use the strongest evidence for this dimension
            # (deterministic: first authoritative, then strong, then weak)
            best = self._rank_evidence(dim_evidence_list)
            dimensions[dim] = best

        # S12-05: formal competence ONLY from authoritative evidence
        # Check if any authoritative evidence exists for formal competence
        fc_evidence_list = by_dimension.get(MasteryDimension.FORMAL_COMPETENCE.value, [])
        auth_fc = [e for e in fc_evidence_list if e.authoritative]
        if auth_fc:
            # Use the strongest authoritative evidence
            best_fc = self._rank_evidence(auth_fc)
            formal_competence_state = "SIGNED_OFF" if best_fc.strength == "strong" else "UNSIGNED"
        # If no authoritative evidence, formal_competence_state stays "UNSIGNED"
        # (S12-04: absent -> NOT inferred; S12-05: non-authoritative cannot move it)

        return MasteryResult(
            goal_id=goal_id,
            topic_id=topic_id,
            dimensions=dimensions,
            formal_competence_state=formal_competence_state,
            evidence_trace=evidence_trace,
        )

    def _rank_evidence(
        self, items: List[DimensionEvidence]
    ) -> DimensionEvidence:
        """Rank evidence deterministically: authoritative first, then strong > weak > absent."""
        # Sort: authoritative first, then by strength priority
        strength_order = {"strong": 0, "weak": 1, "absent": 2}

        def sort_key(item: DimensionEvidence) -> tuple:
            auth_rank = 0 if item.authoritative else 1
            strength_rank = strength_order.get(item.strength, 2)
            return (auth_rank, strength_rank)

        sorted_items = sorted(items, key=sort_key)
        return sorted_items[0]

    def evaluate_from_learner_state(
        self,
        learner_state: Any,
        goal_id: str,
        topic_id: Optional[str] = None,
    ) -> MasteryResult:
        """Evaluate mastery from a LearnerState aggregate.

        Extracts evidence from the learner state and maps each
        piece to the appropriate mastery dimension.  This is the
        primary entry point for S12 integration.
        """
        evidence: List[DimensionEvidence] = []
        evid_id = 1

        # Extract topic-level evidence
        topics = getattr(learner_state, "topics", None)
        if topics is None or isinstance(topics, str):
            # No topics available
            pass
        elif isinstance(topics, list):
            for topic in topics:
                if not isinstance(topic, dict):
                    continue
                tid = topic.get("id", topic_id or "unknown")

                # KNOWLEDGE — from topic progress / assessment scores
                progress = topic.get("progress")
                if progress is not None:
                    if isinstance(progress, (int, float)):
                        if progress >= 0.7:
                            k_strength = "strong"
                        elif progress >= 0.3:
                            k_strength = "weak"
                        else:
                            k_strength = "weak"
                    else:
                        k_strength = "weak"
                    evidence.append(DimensionEvidence(
                        dimension=MasteryDimension.KNOWLEDGE,
                        strength=k_strength,
                        source="topic_progress",
                        evidence_ref=f"ev-{goal_id}-{evid_id:03d}",
                        detail=f"Knowledge evidence from topic {tid} progress={progress}",
                        authoritative=False,
                    ))
                    evid_id += 1

                # RECALL — from assessment scores (lower scores = weak recall)
                assessments = topic.get("recent_assessments")
                if isinstance(assessments, list) and assessments:
                    for a in assessments:
                        if isinstance(a, dict):
                            score = a.get("score")
                            if score is not None and isinstance(score, (int, float)):
                                if score >= 0.8:
                                    r_strength = "strong"
                                elif score >= 0.5:
                                    r_strength = "weak"
                                else:
                                    r_strength = "weak"
                                evidence.append(DimensionEvidence(
                                    dimension=MasteryDimension.RECALL,
                                    strength=r_strength,
                                    source="assessment_score",
                                    evidence_ref=f"ev-{goal_id}-{evid_id:03d}",
                                    detail=f"Recall evidence from assessment in {tid} score={score}",
                                    authoritative=False,
                                ))
                                evid_id += 1

                # APPLICATION — from practice_units and next_action
                practice = topic.get("practice_units")
                if practice is not None and isinstance(practice, (int, float)):
                    if practice >= 5:
                        a_strength = "strong"
                    elif practice >= 2:
                        a_strength = "weak"
                    else:
                        a_strength = "weak"
                    evidence.append(DimensionEvidence(
                        dimension=MasteryDimension.APPLICATION,
                        strength=a_strength,
                        source="practice_units",
                        evidence_ref=f"ev-{goal_id}-{evid_id:03d}",
                        detail=f"Application evidence from topic {tid} practice_units={practice}",
                        authoritative=False,
                    ))
                    evid_id += 1

                # PRACTICAL_READINESS — from next_action and practice
                next_action = topic.get("next_action")
                if next_action is not None:
                    if next_action in ("practice", "assess"):
                        pr_strength = "strong"
                    elif next_action == "review":
                        pr_strength = "weak"
                    else:
                        pr_strength = "weak"
                    evidence.append(DimensionEvidence(
                        dimension=MasteryDimension.PRACTICAL_READINESS,
                        strength=pr_strength,
                        source="topic_next_action",
                        evidence_ref=f"ev-{goal_id}-{evid_id:03d}",
                        detail=f"Practical readiness from topic {tid} next_action={next_action}",
                        authoritative=False,
                    ))
                    evid_id += 1

        # RATIONALE — from reasoning_evidence
        reasoning = getattr(learner_state, "reasoning_evidence", None)
        if isinstance(reasoning, list) and reasoning:
            for r in reasoning:
                if isinstance(r, dict):
                    evidence.append(DimensionEvidence(
                        dimension=MasteryDimension.RATIONALE,
                        strength="strong",
                        source="reasoning_evidence",
                        evidence_ref=f"ev-{goal_id}-{evid_id:03d}",
                        detail=f"Rationale evidence: {r.get('summary', 'N/A')}",
                        authoritative=False,
                    ))
                    evid_id += 1

        # CRITICAL_ANALYSIS — from competency_evidence (non-authoritative = weak)
        comp_evidence = getattr(learner_state, "competency_evidence", None)
        if isinstance(comp_evidence, list) and comp_evidence:
            for c in comp_evidence:
                if isinstance(c, dict):
                    is_auth = c.get("authoritative") is True
                    evidence.append(DimensionEvidence(
                        dimension=MasteryDimension.CRITICAL_ANALYSIS,
                        strength="strong" if is_auth else "weak",
                        source=c.get("source", "unknown"),
                        evidence_ref=f"ev-{goal_id}-{evid_id:03d}",
                        detail=f"Critical analysis evidence from {c.get('source', 'unknown')}",
                        authoritative=is_auth,
                    ))
                    evid_id += 1

        # TRANSFER — from competency_evidence with transfer indicators
        # Transfer is inferred from evidence that shows application in new contexts
        if isinstance(comp_evidence, list) and comp_evidence:
            for c in comp_evidence:
                if isinstance(c, dict):
                    # Check for transfer indicator in source or competency field
                    source = c.get("source", "")
                    competency = c.get("competency", "")
                    if "transfer" in source.lower() or "transfer" in competency.lower():
                        evidence.append(DimensionEvidence(
                            dimension=MasteryDimension.TRANSFER,
                            strength="strong" if c.get("authoritative") else "weak",
                            source=source,
                            evidence_ref=f"ev-{goal_id}-{evid_id:03d}",
                            detail=f"Transfer evidence from {source}",
                            authoritative=c.get("authoritative", False),
                        ))
                        evid_id += 1

        # FORMAL_COMPETENCE — only from authoritative sources
        # Non-authoritative competency evidence does NOT feed formal competence
        if isinstance(comp_evidence, list) and comp_evidence:
            for c in comp_evidence:
                if isinstance(c, dict) and c.get("authoritative") is True:
                    evidence.append(DimensionEvidence(
                        dimension=MasteryDimension.FORMAL_COMPETENCE,
                        strength="strong",
                        source=c.get("source", "authoritative_signoff"),
                        evidence_ref=f"ev-{goal_id}-{evid_id:03d}",
                        detail=f"Formal competence from authoritative source: {c.get('source', 'unknown')}",
                        authoritative=True,
                    ))
                    evid_id += 1

        return self.evaluate(evidence, goal_id, topic_id)