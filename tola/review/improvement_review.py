# Batch T28 -- Weekly Improvement Review.
# Plain ASCII. Stdlib only. Deterministic: no clock reads.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Rule constants (consistent with T21 improvement/ledger.py and candidates.py)
# ---------------------------------------------------------------------------

REPEATED_WEAKNESS_THRESHOLD = 3

ONE_OFF = "ONE_OFF"

SKILL_PROPOSAL_ONLY = "SKILL_PROPOSAL_ONLY"

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ImprovementCandidate:
    """An improvement candidate (proposal-only, never auto-applied)."""
    id: str
    kind: str
    subject: str
    status: str  # always PROPOSAL for skill changes
    evidence_refs: tuple[str, ...]
    applied: bool  # always False

@dataclass(frozen=True)
class ObservationKept:
    """An observation retained for the record."""
    id: str
    kind: str
    subject: str

@dataclass(frozen=True)
class ImprovementReviewResult:
    """Result of a weekly improvement review."""
    candidates: tuple[ImprovementCandidate, ...]
    observations_kept: tuple[ObservationKept, ...]

# ---------------------------------------------------------------------------
# Core review function
# ---------------------------------------------------------------------------

def _group_by_category(observations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group observations by their category (kind + subject prefix)."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for obs in observations:
        kind = obs.get("kind", "")
        subject = obs.get("subject", "")
        category = f"{kind}:{subject}"
        if category not in groups:
            groups[category] = []
        groups[category].append(obs)
    return groups


def run_improvement_review(
    observations: list[dict[str, Any]],
) -> ImprovementReviewResult:
    """Run the weekly improvement review.

    Parameters
    ----------
    observations : list of dicts with keys: id, kind, subject,
        evidence_refs, category.

    Returns
    -------
    ImprovementReviewResult
        candidates (proposal-only for skills) and observations_kept.
    """
    candidates: list[ImprovementCandidate] = []
    observations_kept: list[ObservationKept] = []

    # Keep all observations in the record.
    for obs in observations:
        observations_kept.append(ObservationKept(
            id=obs.get("id", ""),
            kind=obs.get("kind", ""),
            subject=obs.get("subject", ""),
        ))

    # Group by category for repeated-weakness detection.
    groups = _group_by_category(observations)

    for category, group in groups.items():
        kind = group[0].get("kind", "")
        subject = group[0].get("subject", "")
        count = len(group)

        # SKILL_PROPOSAL_ONLY: skill changes are always proposal-only.
        if kind == "SKILL_CHANGE":
            for obs in group:
                candidates.append(ImprovementCandidate(
                    id=obs.get("id", ""),
                    kind=kind,
                    subject=subject,
                    status=SKILL_PROPOSAL_ONLY,
                    evidence_refs=tuple(obs.get("evidence_refs", ("",))),
                    applied=False,
                ))
            continue

        # REPEATED_WEAKNESS_THRESHOLD: repeated delegation weakness,
        # plan corrections, user corrections in same category.
        if count >= REPEATED_WEAKNESS_THRESHOLD:
            primary = group[0]
            candidates.append(ImprovementCandidate(
                id=primary.get("id", ""),
                kind=kind,
                subject=subject,
                status="CANDIDATE",
                evidence_refs=tuple(o.get("evidence_refs", ("",)) for o in group),
                applied=False,
            ))

        # ONE_OFF: single failure remains observation only (no candidate).
        # This is implicit: count < threshold means no candidate created.

    return ImprovementReviewResult(
        candidates=tuple(candidates),
        observations_kept=tuple(observations_kept),
    )