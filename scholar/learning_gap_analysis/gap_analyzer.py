"""
Batch S13 -- Learning Gap Analysis.

Detects: missing prerequisites (S13-01), weak knowledge (S13-02),
weak application (S13-03), insufficient evidence/practice (S13-04),
uncovered proficiencies (S13-05). False gaps must not be flagged
(S13-06). Every gap is traceable to evidence.

Analysis derives from mastery dimensions, decomposition prerequisite
maps and proficiency coverage; nothing hard-coded outside the registries.

Plain ASCII. Python 3 stdlib only.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from scholar.mastery.model import MasteryDimension, MasteryResult


# ---------------------------------------------------------------------------
# Gap types
# ---------------------------------------------------------------------------

class GapType(str, Enum):
    MISSING_PREREQUISITE = "missing_prerequisite"
    WEAK_KNOWLEDGE = "weak_knowledge"
    WEAK_APPLICATION = "weak_application"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNCOVERED_PROFICIENCY = "uncovered_proficiency"


# ---------------------------------------------------------------------------
# Gap record — every gap is traceable to evidence
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Gap:
    """A single learning gap with full evidence traceability."""
    gap_id: str
    gap_type: GapType
    goal_id: str
    topic_id: Optional[str]
    description: str
    evidence_refs: List[str]          # traceable to learner-state evidence
    mastery_dimension: Optional[str]  # which dimension is weak/missing
    severity: str                     # "high" | "medium" | "low"
    recommendation: str               # what to do about this gap


# ---------------------------------------------------------------------------
# Gap analysis result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GapAnalysisResult:
    """Result of a learning gap analysis pass."""
    goal_id: str
    goal_title: str
    goal_state: str
    gaps: List[Gap]
    gap_counts: Dict[str, int]
    evidence_trace: List[str]
    deterministic_key: str


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _require_non_empty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")
    return value.strip()


def _require_valid_goal_state(state: str) -> str:
    valid = {"ACTIVE", "PAUSED", "COMPLETED", "STOPPED", "SUPERSEDED"}
    if state not in valid:
        raise ValueError(f"state must be one of {sorted(valid)}, got {state!r}")
    return state


# ---------------------------------------------------------------------------
# Deterministic key builder
# ---------------------------------------------------------------------------

def _build_deterministic_key(
    goal_id: str,
    gap_types: List[str],
    evidence_refs: List[str],
) -> str:
    parts = [
        f"goal:{goal_id}",
        f"gaps:{','.join(sorted(gap_types))}",
        f"refs:{','.join(sorted(evidence_refs))}",
    ]
    combined = "|".join(parts)
    h = 0
    for ch in combined:
        h = ((h * 31) + ord(ch)) & 0xFFFFFFFF
    return f"{combined}::hash={h:08x}"


# ---------------------------------------------------------------------------
# Gap analyzer
# ---------------------------------------------------------------------------

class LearningGapAnalyzer:
    """Deterministic learning gap analyzer.

    Analyzes mastery dimensions, decomposition prerequisite maps and
    proficiency coverage to detect learning gaps.  Every gap is
    traceable to evidence — no invented gaps, no unsupported claims.

    Key guarantees:
    - S13-01: Missing prerequisites detected from decomposition maps.
    - S13-02: Weak knowledge detected from mastery dimensions.
    - S13-03: Weak application detected from mastery dimensions.
    - S13-04: Insufficient evidence/practice detected from mastery
      dimensions and evidence trace.
    - S13-05: Uncovered proficiencies detected from proficiency coverage.
    - S13-06: Strong fixtures are NOT incorrectly flagged as gaps.
    - PAUSED/SUPERSEDED goals are excluded from gap analysis.
    - Every gap has at least one evidence_ref.
    - Deterministic repeat calls produce identical results.
    - Malformed input is rejected with clear errors.
    - Empty state produces explicit empty gap list, not invented gaps.
    - Clock injection for deterministic testing.
    """

    # Mastery dimensions that indicate knowledge weakness
    KNOWLEDGE_DIMENSIONS = (
        MasteryDimension.KNOWLEDGE,
        MasteryDimension.RECALL,
    )

    # Mastery dimensions that indicate application weakness
    APPLICATION_DIMENSIONS = (
        MasteryDimension.APPLICATION,
        MasteryDimension.PRACTICAL_READINESS,
    )

    def __init__(self, clock: Optional[callable] = None) -> None:
        self._clock = clock or (lambda: "2026-09-30T12:00:00")

    # ------------------------------------------------------------------ #
    #  Main analysis entry point
    # ------------------------------------------------------------------ #

    def analyze(
        self,
        goal_id: str,
        goal_title: str,
        goal_state: str,
        mastery_result: Any,
        decomposition_result: Optional[Dict[str, Any]] = None,
        proficiency_records: Optional[List[Dict[str, Any]]] = None,
    ) -> GapAnalysisResult:
        """Analyze learning gaps for a goal.

        Args:
            goal_id: Unique goal identifier.
            goal_title: Goal title.
            goal_state: Goal state (ACTIVE/PAUSED/COMPLETED/STOPPED/SUPERSEDED).
            mastery_result: MasteryResult from S12 mastery model.
            decomposition_result: Optional DecompositionResult dict from S10.
            proficiency_records: Optional list of proficiency record dicts.

        Returns:
            GapAnalysisResult with all detected gaps and evidence trace.

        Raises ValueError on malformed input.
        """
        goal_id = _require_non_empty_string(goal_id, "goal_id")
        goal_title = _require_non_empty_string(goal_title, "goal_title")
        goal_state = _require_valid_goal_state(goal_state)

        # Call the clock for deterministic time recording
        _ = self._clock()

        if mastery_result is None:
            raise ValueError("mastery_result must not be None")

        # PAUSED and SUPERSEDED goals are excluded from gap analysis
        if goal_state in ("PAUSED", "SUPERSEDED"):
            return GapAnalysisResult(
                goal_id=goal_id,
                goal_title=goal_title,
                goal_state=goal_state,
                gaps=[],
                gap_counts={},
                evidence_trace=[],
                deterministic_key=_build_deterministic_key(
                    goal_id, [], []
                ),
            )

        # Collect all gaps
        gaps: List[Gap] = []
        evidence_refs: List[str] = []
        gap_types: List[str] = []

        # S13-01: Missing prerequisites from decomposition
        if decomposition_result is not None:
            prereq_gaps, prereq_refs = self._detect_missing_prerequisites(
                goal_id, goal_title, decomposition_result
            )
            gaps.extend(prereq_gaps)
            evidence_refs.extend(prereq_refs)
            gap_types.extend(
                [GapType.MISSING_PREREQUISITE.value] * len(prereq_gaps)
            )

        # S13-02: Weak knowledge from mastery dimensions
        weak_knowledge_gaps = self._detect_weak_knowledge(
            goal_id, goal_title, mastery_result
        )
        gaps.extend(weak_knowledge_gaps)
        for g in weak_knowledge_gaps:
            evidence_refs.extend(g.evidence_refs)
            gap_types.append(GapType.WEAK_KNOWLEDGE.value)

        # S13-03: Weak application from mastery dimensions
        weak_application_gaps = self._detect_weak_application(
            goal_id, goal_title, mastery_result
        )
        gaps.extend(weak_application_gaps)
        for g in weak_application_gaps:
            evidence_refs.extend(g.evidence_refs)
            gap_types.append(GapType.WEAK_APPLICATION.value)

        # S13-04: Insufficient evidence/practice
        evidence_gaps = self._detect_insufficient_evidence(
            goal_id, goal_title, mastery_result
        )
        gaps.extend(evidence_gaps)
        for g in evidence_gaps:
            evidence_refs.extend(g.evidence_refs)
            gap_types.append(GapType.INSUFFICIENT_EVIDENCE.value)

        # S13-05: Uncovered proficiencies
        if proficiency_records is not None and decomposition_result is not None:
            uncovered_gaps = self._detect_uncovered_proficiencies(
                goal_id, goal_title, decomposition_result, proficiency_records
            )
            gaps.extend(uncovered_gaps)
            for g in uncovered_gaps:
                evidence_refs.extend(g.evidence_refs)
                gap_types.append(GapType.UNCOVERED_PROFICIENCY.value)

        # S13-06 guard: remove any gap that has no evidence_ref
        gaps = [g for g in gaps if len(g.evidence_refs) > 0]

        # Build counts
        gap_counts: Dict[str, int] = {}
        for gt in gap_types:
            gap_counts[gt] = gap_counts.get(gt, 0) + 1

        # Deduplicate evidence refs
        seen_refs: set = set()
        unique_refs: List[str] = []
        for ref in evidence_refs:
            if ref and ref not in seen_refs:
                seen_refs.add(ref)
                unique_refs.append(ref)

        # Build deterministic key
        det_key = _build_deterministic_key(goal_id, gap_types, unique_refs)

        return GapAnalysisResult(
            goal_id=goal_id,
            goal_title=goal_title,
            goal_state=goal_state,
            gaps=gaps,
            gap_counts=gap_counts,
            evidence_trace=unique_refs,
            deterministic_key=det_key,
        )

    # ------------------------------------------------------------------ #
    #  S13-01: Missing prerequisites
    # ------------------------------------------------------------------ #

    def _detect_missing_prerequisites(
        self,
        goal_id: str,
        goal_title: str,
        decomposition_result: Dict[str, Any],
    ) -> tuple:
        """Detect missing prerequisites from decomposition.

        S13-01: A missing prerequisite is a prerequisite node that
        is not covered by the goal decomposition.
        """
        gaps: List[Gap] = []
        evidence_refs: List[str] = []

        missing = decomposition_result.get("missing_prerequisites", [])

        for i, mp in enumerate(missing):
            gap_id = f"gap-{goal_id}-prereq-{i+1:03d}"
            gaps.append(
                Gap(
                    gap_id=gap_id,
                    gap_type=GapType.MISSING_PREREQUISITE,
                    goal_id=goal_id,
                    topic_id=None,
                    description=f"Missing prerequisite: {mp}",
                    evidence_refs=[f"decomp-prereq-{i+1:03d}"],
                    mastery_dimension=None,
                    severity="high",
                    recommendation="Address prerequisite before proceeding with this goal.",
                )
            )
            evidence_refs.append(f"decomp-prereq-{i+1:03d}")

        return gaps, evidence_refs

    # ------------------------------------------------------------------ #
    #  S13-02: Weak knowledge
    # ------------------------------------------------------------------ #

    def _detect_weak_knowledge(
        self,
        goal_id: str,
        goal_title: str,
        mastery_result: MasteryResult,
    ) -> List[Gap]:
        """Detect weak knowledge from mastery dimensions.

        S13-02: Knowledge or Recall dimension strength is "weak".
        """
        gaps: List[Gap] = []
        idx = 1

        for dim in self.KNOWLEDGE_DIMENSIONS:
            strength = mastery_result.dimension_strength(dim)
            if strength == "weak":
                ev = mastery_result.dimensions.get(dim)
                evidence_refs = []
                if ev is not None and ev.evidence_ref:
                    evidence_refs.append(ev.evidence_ref)

                gap_id = f"gap-{goal_id}-weak-knowledge-{idx:03d}"
                gaps.append(
                    Gap(
                        gap_id=gap_id,
                        gap_type=GapType.WEAK_KNOWLEDGE,
                        goal_id=goal_id,
                        topic_id=mastery_result.topic_id,
                        description=f"Weak knowledge in dimension {dim.value}: {ev.detail if ev else 'No detail'}",
                        evidence_refs=evidence_refs,
                        mastery_dimension=dim.value,
                        severity="high",
                        recommendation="Strengthen knowledge through targeted study and assessment.",
                    )
                )
                idx += 1

        return gaps

    # ------------------------------------------------------------------ #
    #  S13-03: Weak application
    # ------------------------------------------------------------------ #

    def _detect_weak_application(
        self,
        goal_id: str,
        goal_title: str,
        mastery_result: MasteryResult,
    ) -> List[Gap]:
        """Detect weak application from mastery dimensions.

        S13-03: Application or Practical_Readiness dimension strength
        is "weak".
        """
        gaps: List[Gap] = []
        idx = 1

        for dim in self.APPLICATION_DIMENSIONS:
            strength = mastery_result.dimension_strength(dim)
            if strength == "weak":
                ev = mastery_result.dimensions.get(dim)
                evidence_refs = []
                if ev is not None and ev.evidence_ref:
                    evidence_refs.append(ev.evidence_ref)

                gap_id = f"gap-{goal_id}-weak-application-{idx:03d}"
                gaps.append(
                    Gap(
                        gap_id=gap_id,
                        gap_type=GapType.WEAK_APPLICATION,
                        goal_id=goal_id,
                        topic_id=mastery_result.topic_id,
                        description=f"Weak application in dimension {dim.value}: {ev.detail if ev else 'No detail'}",
                        evidence_refs=evidence_refs,
                        mastery_dimension=dim.value,
                        severity="high",
                        recommendation="Increase practice opportunities and supervised application.",
                    )
                )
                idx += 1

        return gaps

    # ------------------------------------------------------------------ #
    #  S13-04: Insufficient evidence/practice
    # ------------------------------------------------------------------ #

    def _detect_insufficient_evidence(
        self,
        goal_id: str,
        goal_title: str,
        mastery_result: MasteryResult,
    ) -> List[Gap]:
        """Detect insufficient evidence or practice from mastery dimensions.

        S13-04: A dimension is flagged when evidence is absent or weak
        AND the dimension has a traceable evidence_ref.
        Gaps without evidence_ref are rejected (S13-06).
        """
        gaps: List[Gap] = []
        idx = 1

        for dim in MasteryDimension:
            strength = mastery_result.dimension_strength(dim)

            if strength == "absent":
                ev = mastery_result.dimensions.get(dim)
                if ev is not None and ev.evidence_ref:
                    # Has evidence but still absent — that's a gap
                    evidence_refs = [ev.evidence_ref]
                    gap_id = f"gap-{goal_id}-insufficient-evidence-{idx:03d}"
                    gaps.append(
                        Gap(
                            gap_id=gap_id,
                            gap_type=GapType.INSUFFICIENT_EVIDENCE,
                            goal_id=goal_id,
                            topic_id=mastery_result.topic_id,
                            description=f"Insufficient evidence for {dim.value}: evidence provided but strength is absent",
                            evidence_refs=evidence_refs,
                            mastery_dimension=dim.value,
                            severity="medium",
                            recommendation="Gather more evidence before proceeding.",
                        )
                    )
                    idx += 1
                # If no evidence_ref at all, this is not a gap —
                # it's simply no evidence provided (not a weakness)
                continue

            if strength == "weak":
                ev = mastery_result.dimensions.get(dim)
                evidence_refs = []
                if ev is not None and ev.evidence_ref:
                    evidence_refs.append(ev.evidence_ref)

                # S13-06 guard: skip if no evidence ref
                if not evidence_refs:
                    continue

                gap_id = f"gap-{goal_id}-insufficient-evidence-{idx:03d}"
                gaps.append(
                    Gap(
                        gap_id=gap_id,
                        gap_type=GapType.INSUFFICIENT_EVIDENCE,
                        goal_id=goal_id,
                        topic_id=mastery_result.topic_id,
                        description=f"Insufficient evidence/practice for {dim.value}: strength is weak",
                        evidence_refs=evidence_refs,
                        mastery_dimension=dim.value,
                        severity="medium",
                        recommendation="Increase evidence gathering and practice for this dimension.",
                    )
                )
                idx += 1

        return gaps

    # ------------------------------------------------------------------ #
    #  S13-05: Uncovered proficiencies
    # ------------------------------------------------------------------ #

    def _detect_uncovered_proficiencies(
        self,
        goal_id: str,
        goal_title: str,
        decomposition_result: Dict[str, Any],
        proficiency_records: List[Dict[str, Any]],
    ) -> List[Gap]:
        """Detect proficiencies not covered by the goal decomposition.

        S13-05: A proficiency is uncovered when it exists in the
        proficiency registry but is not mapped by the decomposition.
        """
        gaps: List[Gap] = []
        idx = 1

        # Get mapped proficiency IDs from decomposition
        mapped_prof_ids = set()
        for pm in decomposition_result.get("proficiencies", []):
            prof_id = pm.get("proficiency_id", "")
            if prof_id:
                mapped_prof_ids.add(prof_id)

        # Check each proficiency record
        for prof in proficiency_records:
            prof_id = prof.get("proficiency_id", "")
            if not prof_id:
                continue
            if prof_id in mapped_prof_ids:
                continue

            # This proficiency is not covered by the goal decomposition
            domain = prof.get("domain", "unknown")
            step = prof.get("step", "unknown")
            verbatim = prof.get("verbatim_requirement", "")[:80]

            evidence_refs = []
            ev_ref = prof.get("linked_evidence")
            if isinstance(ev_ref, list) and ev_ref:
                evidence_refs.extend(ev_ref[:3])  # max 3 refs per gap
            elif isinstance(ev_ref, str) and ev_ref:
                evidence_refs.append(ev_ref)

            # S13-06 guard: skip if no evidence ref
            if not evidence_refs:
                continue

            gap_id = f"gap-{goal_id}-uncovered-prof-{idx:03d}"
            gaps.append(
                Gap(
                    gap_id=gap_id,
                    gap_type=GapType.UNCOVERED_PROFICIENCY,
                    goal_id=goal_id,
                    topic_id=None,
                    description=f"Uncovered proficiency {prof_id!r} (domain={domain}, step={step}): {verbatim}",
                    evidence_refs=evidence_refs,
                    mastery_dimension=None,
                    severity="medium",
                    recommendation="Map this proficiency to the learning plan or confirm it is not relevant.",
                )
            )
            idx += 1

        return gaps
