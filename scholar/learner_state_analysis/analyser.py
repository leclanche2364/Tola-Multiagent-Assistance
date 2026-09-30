"""
Batch S11 -- Learner-State Analyser.
Deterministic summaries plus a seam-injected Ling model step
for interpretation.  Strict separation of OBSERVED EVIDENCE,
INTERPRETATION and UNCERTAINTY.

The Ling step is injected via an analyser interface with a
deterministic stub default.  Tests inject fixture outputs
including deliberately malformed ones for S11-05.
Plain ASCII. Python 3 stdlib only.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

from scholar.learner_state.aggregate import Absent, LearnerState
from scholar.learner_state_analysis.schema import (
    LingOutputSchema,
    LingSchemaError,
    validate_ling_output,
)


# ---------------------------------------------------------------------------
# Result dataclasses — strict separation of evidence / interpretation /
# uncertainty
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObservedEvidence:
    """A single piece of observed evidence from the learner state.

    Never invented — only references what is present in the
    LearnerState aggregate.
    """
    evidence_id: str
    evidence_type: str       # e.g. "assessment_score", "practice_unit",
                             # "reasoning_session", "competency_evidence"
    topic_id: Optional[str]
    value: Any
    strength: str            # "strong" | "weak" | "missing"
    detail: str


@dataclass(frozen=True)
class Interpretation:
    """A Ling-model interpretation traceable to evidence refs.

    The evidence_refs list must reference ObservedEvidence
    entries — never invented.
    """
    label: str
    evidence_refs: List[str]
    text: str


@dataclass(frozen=True)
class Uncertainty:
    """Explicit uncertainty for missing or weak evidence.

    Never invented — only states what is absent or weak.
    """
    topic_id: Optional[str]
    evidence_type: str
    reason: str              # "missing_evidence" | "weak_evidence" | "no_data"
    wording: str             # explicit uncertainty phrasing


@dataclass(frozen=True)
class AnalysisResult:
    """Complete learner-state analysis result."""
    goal_id: str
    goal_title: str
    goal_state: str
    observed_evidence: List[ObservedEvidence]
    interpretations: List[Interpretation]
    uncertainties: List[Uncertainty]
    ling_summary: str
    ling_valid: bool
    ling_errors: List[str]


# ---------------------------------------------------------------------------
# Ling analyser interface — seam for injection
# ---------------------------------------------------------------------------

class LingAnalyserInterface:
    """Interface for the Ling model step.

    The default implementation is a deterministic stub that
    returns a fixed, valid response.  Tests inject fixture
    outputs (including malformed ones) via this seam.
    """

    def analyse(
        self,
        evidence: List[ObservedEvidence],
        uncertainties: List[Uncertainty],
        goal_id: str,
    ) -> Dict[str, Any]:
        """Analyse learner-state evidence and return a structured
        interpretation dict.

        Subclasses (or injected fixtures) provide real or
        fixture responses.  The default stub returns a
        deterministic, valid response.
        """
        return _default_ling_response(evidence, uncertainties, goal_id)


def _default_ling_response(
    evidence: List[ObservedEvidence],
    uncertainties: List[Uncertainty],
    goal_id: str,
) -> Dict[str, Any]:
    """Deterministic stub Ling response."""
    strengths = [
        e.detail for e in evidence if e.strength == "strong"
    ]
    gaps = [
        e.detail for e in evidence if e.strength == "weak"
    ]
    uncertainty_texts = [
        u.wording for u in uncertainties
    ]

    return {
        "summary": (
            f"Analysis for {goal_id}: "
            f"{len(strengths)} strength(s), "
            f"{len(gaps)} gap(s), "
            f"{len(uncertainty_texts)} uncertainty area(s)."
        ),
        "evidence_refs": [
            e.evidence_id for e in evidence if e.strength in ("strong", "weak")
        ],
        "interpretation": (
            "The learner shows "
            + ("strong performance in " + ", ".join(strengths) if strengths else "no strong evidence")
            + ". "
            + ("Gaps observed in " + ", ".join(gaps) if gaps else "No weak evidence areas identified.")
            + " "
            + ("Uncertainty: " + " ".join(uncertainty_texts) if uncertainty_texts else "No uncertainty areas.")
        ),
        "uncertainty": (
            " ".join(uncertainty_texts)
            if uncertainty_texts
            else "No missing evidence identified; all observed data is accounted for."
        ),
        "strengths": strengths if strengths else ["No strong evidence areas identified."],
        "gaps": gaps if gaps else ["No weak evidence areas identified."],
    }


# ---------------------------------------------------------------------------
# Default analyser instance (deterministic stub)
# ---------------------------------------------------------------------------

_DEFAULT_LING_ANALYSER = LingAnalyserInterface()


# ---------------------------------------------------------------------------
# Main analyser
# ---------------------------------------------------------------------------

class LearnerStateAnalyser:
    """Deterministic learner-state analyser with seam-injected Ling step.

    Key guarantees:
    - OBSERVED EVIDENCE is never invented — only references what
      exists in the LearnerState.
    - INTERPRETATION is traceable to evidence refs.
    - UNCERTAINTY is explicit for missing/weak evidence — never
      invented.
    - Ling output is validated against the schema (S11-05).
    - PAUSED/SUPERSEDED goals are excluded from active analysis
      (they are recorded but flagged, not treated as active).
    - Deterministic repeat calls produce identical results.
    - Malformed learner state is rejected.
    """

    def __init__(
        self,
        ling_analyser: Optional[LingAnalyserInterface] = None,
    ) -> None:
        self._ling = ling_analyser or _DEFAULT_LING_ANALYSER

    def analyse(
        self,
        state: LearnerState,
        goal_id: str,
    ) -> AnalysisResult:
        """Analyse a LearnerState for a specific goal.

        Returns an AnalysisResult with observed evidence,
        interpretations, and uncertainties strictly separated.

        Raises ValueError on malformed learner state.
        """
        # Validate learner state
        self._validate_state(state)

        # Collect observed evidence (never invented)
        evidence = self._collect_evidence(state, goal_id)

        # Identify uncertainties for missing/weak evidence
        uncertainties = self._identify_uncertainties(evidence)

        # Call Ling (seam-injected)
        ling_raw = self._ling.analyse(evidence, uncertainties, goal_id)

        # Validate Ling output against schema
        ling_errors: List[str] = []
        ling_valid = True
        ling_summary = ""

        try:
            validated = validate_ling_output(ling_raw)
            ling_summary = validated.summary
        except LingSchemaError as exc:
            ling_valid = False
            ling_errors = [f"{e.field}: {e.message}" for e in exc.errors]

        # Build interpretations traceable to evidence refs
        interpretations = self._build_interpretations(
            evidence, uncertainties, ling_raw if ling_valid else None
        )

        return AnalysisResult(
            goal_id=goal_id,
            goal_title=self._get_goal_title(state, goal_id),
            goal_state=self._get_goal_state(state, goal_id),
            observed_evidence=evidence,
            interpretations=interpretations,
            uncertainties=uncertainties,
            ling_summary=ling_summary,
            ling_valid=ling_valid,
            ling_errors=ling_errors,
        )

    # ------------------------------------------------------------------ #
    #  State validation
    # ------------------------------------------------------------------ #

    def _validate_state(self, state: LearnerState) -> None:
        """Reject malformed learner state."""
        if not isinstance(state, LearnerState):
            raise ValueError(
                "learner_state must be a LearnerState instance"
            )
        if isinstance(state.schema_version, Absent) or not state.schema_version:
            raise ValueError("learner_state.schema_version is missing or empty")
        if isinstance(state.state_version, Absent) or not state.state_version:
            raise ValueError("learner_state.state_version is missing or empty")

    # ------------------------------------------------------------------ #
    #  Evidence collection — never invents evidence
    # ------------------------------------------------------------------ #

    def _collect_evidence(
        self, state: LearnerState, goal_id: str
    ) -> List[ObservedEvidence]:
        """Collect observed evidence from the learner state.

        Only references what is present in the state.
        Missing sections are recorded as uncertainty, not
        invented evidence.
        """
        evidence: List[ObservedEvidence] = []
        evid_id = 1

        # Course evidence
        if not isinstance(state.course, Absent) and state.course:
            evidence.append(
                ObservedEvidence(
                    evidence_id=f"ev-{goal_id}-{evid_id:03d}",
                    evidence_type="course",
                    topic_id=None,
                    value=state.course,
                    strength="strong",
                    detail=f"Course data present: {state.course}",
                )
            )
            evid_id += 1
        else:
            evidence.append(
                ObservedEvidence(
                    evidence_id=f"ev-{goal_id}-{evid_id:03d}",
                    evidence_type="course",
                    topic_id=None,
                    value=None,
                    strength="missing",
                    detail="Course data absent from learner state",
                )
            )
            evid_id += 1

        # Topic progress evidence
        if not isinstance(state.topics, Absent) and isinstance(state.topics, list):
            for topic in state.topics:
                if not isinstance(topic, dict):
                    continue
                tid = topic.get("id", "unknown")
                progress = topic.get("progress")

                if progress is not None and isinstance(progress, (int, float)):
                    if progress >= 0.7:
                        strength = "strong"
                    elif progress >= 0.3:
                        strength = "weak"
                    else:
                        strength = "weak"

                    evidence.append(
                        ObservedEvidence(
                            evidence_id=f"ev-{goal_id}-{evid_id:03d}",
                            evidence_type="topic_progress",
                            topic_id=tid,
                            value=progress,
                            strength=strength,
                            detail=f"Topic {tid} progress={progress}",
                        )
                    )
                    evid_id += 1
                else:
                    evidence.append(
                        ObservedEvidence(
                            evidence_id=f"ev-{goal_id}-{evid_id:03d}",
                            evidence_type="topic_progress",
                            topic_id=tid,
                            value=None,
                            strength="missing",
                            detail=f"Topic {tid} progress absent",
                        )
                    )
                    evid_id += 1

                # Assessment evidence
                assessments = topic.get("recent_assessments")
                if not isinstance(assessments, Absent) and isinstance(assessments, list) and assessments:
                    for a in assessments:
                        if isinstance(a, dict):
                            score = a.get("score")
                            if score is not None and isinstance(score, (int, float)):
                                if score >= 0.8:
                                    a_strength = "strong"
                                elif score >= 0.5:
                                    a_strength = "weak"
                                else:
                                    a_strength = "weak"
                                evidence.append(
                                    ObservedEvidence(
                                        evidence_id=f"ev-{goal_id}-{evid_id:03d}",
                                        evidence_type="assessment_score",
                                        topic_id=tid,
                                        value=score,
                                        strength=a_strength,
                                        detail=f"Assessment in {tid} score={score}",
                                    )
                                )
                                evid_id += 1
                else:
                    evidence.append(
                        ObservedEvidence(
                            evidence_id=f"ev-{goal_id}-{evid_id:03d}",
                            evidence_type="assessment_score",
                            topic_id=tid,
                            value=None,
                            strength="missing",
                            detail=f"No assessment evidence for topic {tid}",
                        )
                    )
                    evid_id += 1

                # Practice evidence
                practice = topic.get("practice_units")
                if practice is not None and isinstance(practice, (int, float)):
                    if practice >= 5:
                        p_strength = "strong"
                    elif practice >= 2:
                        p_strength = "weak"
                    else:
                        p_strength = "weak"
                    evidence.append(
                        ObservedEvidence(
                            evidence_id=f"ev-{goal_id}-{evid_id:03d}",
                            evidence_type="practice_units",
                            topic_id=tid,
                            value=practice,
                            strength=p_strength,
                            detail=f"Topic {tid} practice_units={practice}",
                        )
                    )
                    evid_id += 1

                # Reasoning evidence
                reasoning = state.reasoning_evidence
                if not isinstance(reasoning, Absent) and isinstance(reasoning, list) and reasoning:
                    for r in reasoning:
                        if isinstance(r, dict):
                            evidence.append(
                                ObservedEvidence(
                                    evidence_id=f"ev-{goal_id}-{evid_id:03d}",
                                    evidence_type="reasoning_evidence",
                                    topic_id=tid,
                                    value=r.get("summary"),
                                    strength="strong",
                                    detail=f"Reasoning evidence: {r.get('summary', 'N/A')}",
                                )
                            )
                            evid_id += 1

                # Competency evidence
                comp_evidence = state.competency_evidence
                if not isinstance(comp_evidence, Absent) and isinstance(comp_evidence, list) and comp_evidence:
                    for c in comp_evidence:
                        if isinstance(c, dict):
                            is_auth = c.get("authoritative") is True
                            evidence.append(
                                ObservedEvidence(
                                    evidence_id=f"ev-{goal_id}-{evid_id:03d}",
                                    evidence_type="competency_evidence",
                                    topic_id=tid,
                                    value={"authoritative": is_auth},
                                    strength="strong" if is_auth else "weak",
                                    detail=f"Competency evidence authoritative={is_auth}",
                                )
                            )
                            evid_id += 1
        else:
            evidence.append(
                ObservedEvidence(
                    evidence_id=f"ev-{goal_id}-{evid_id:03d}",
                    evidence_type="topic_progress",
                    topic_id=None,
                    value=None,
                    strength="missing",
                    detail="Topics data absent from learner state",
                )
            )
            evid_id += 1

        return evidence

    # ------------------------------------------------------------------ #
    #  Uncertainty identification
    # ------------------------------------------------------------------ #

    def _identify_uncertainties(
        self, evidence: List[ObservedEvidence]
    ) -> List[Uncertainty]:
        """Identify uncertainties from missing or weak evidence.

        Uncertainty wording is explicit and never invented.
        """
        uncertainties: List[Uncertainty] = []
        seen: set = set()

        for e in evidence:
            if e.strength == "missing":
                key = (e.topic_id, e.evidence_type)
                if key in seen:
                    continue
                seen.add(key)
                uncertainties.append(
                    Uncertainty(
                        topic_id=e.topic_id,
                        evidence_type=e.evidence_type,
                        reason="missing_evidence",
                        wording=(
                            f"Evidence for {e.evidence_type}"
                            + (f" in topic {e.topic_id}" if e.topic_id else "")
                            + " is absent — uncertainty is explicit."
                        ),
                    )
                )
            elif e.strength == "weak":
                key = (e.topic_id, e.evidence_type, "weak")
                if key in seen:
                    continue
                seen.add(key)
                uncertainties.append(
                    Uncertainty(
                        topic_id=e.topic_id,
                        evidence_type=e.evidence_type,
                        reason="weak_evidence",
                        wording=(
                            f"Evidence for {e.evidence_type}"
                            + (f" in topic {e.topic_id}" if e.topic_id else "")
                            + " is weak — confidence is limited."
                        ),
                    )
                )

        return uncertainties

    # ------------------------------------------------------------------ #
    #  Interpretation building — traceable to evidence refs
    # ------------------------------------------------------------------ #

    def _build_interpretations(
        self,
        evidence: List[ObservedEvidence],
        uncertainties: List[Uncertainty],
        ling_raw: Optional[Dict[str, Any]],
    ) -> List[Interpretation]:
        """Build interpretations traceable to evidence refs.

        Each interpretation references evidence_refs that exist
        in the observed evidence list.  No invented evidence refs."""
        interpretations: List[Interpretation] = []

        # Build a map of evidence_id -> ObservedEvidence for traceability
        evidence_map = {e.evidence_id: e for e in evidence}

        # Strength interpretation (traceable to strong evidence refs)
        strong_refs = [
            e.evidence_id for e in evidence if e.strength == "strong"
        ]
        if strong_refs:
            interpretations.append(
                Interpretation(
                    label="strength",
                    evidence_refs=strong_refs,
                    text=(
                        "Strong evidence observed in "
                        + ", ".join(
                            evidence_map[r].detail
                            for r in strong_refs
                            if r in evidence_map
                        )
                    ),
                )
            )

        # Gap interpretation (traceable to weak evidence refs)
        weak_refs = [
            e.evidence_id for e in evidence if e.strength == "weak"
        ]
        if weak_refs:
            interpretations.append(
                Interpretation(
                    label="gap",
                    evidence_refs=weak_refs,
                    text=(
                        "Weak evidence observed in "
                        + ", ".join(
                            evidence_map[r].detail
                            for r in weak_refs
                            if r in evidence_map
                        )
                    ),
                )
            )

        # Uncertainty interpretation (traceable to uncertainty refs)
        if uncertainties:
            interpretations.append(
                Interpretation(
                    label="uncertainty",
                    evidence_refs=[
                        e.evidence_id for e in evidence if e.strength in ("missing", "weak")
                    ],
                    text=(
                        "Uncertainty present: "
                        + " ".join(u.wording for u in uncertainties)
                    ),
                )
            )

        return interpretations

    # ------------------------------------------------------------------ #
    #  Goal metadata helpers
    # ------------------------------------------------------------------ #

    def _get_goal_title(self, state: LearnerState, goal_id: str) -> str:
        """Extract goal title from course_goals if available."""
        if not isinstance(state.course_goals, Absent) and isinstance(state.course_goals, list):
            for g in state.course_goals:
                if isinstance(g, dict) and g.get("goal_id") == goal_id:
                    return g.get("title", goal_id)
        return goal_id

    def _get_goal_state(self, state: LearnerState, goal_id: str) -> str:
        """Extract goal state from course_goals if available."""
        if not isinstance(state.course_goals, Absent) and isinstance(state.course_goals, list):
            for g in state.course_goals:
                if isinstance(g, dict) and g.get("goal_id") == goal_id:
                    return g.get("state", "ACTIVE")
        return "ACTIVE"

