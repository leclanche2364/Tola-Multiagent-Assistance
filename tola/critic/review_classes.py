# Batch T10 - Review Classes
# classify_review(plan_input) -> ROUTINE | CONSEQUENTIAL | MATERIAL
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReviewClass(str, Enum):
    """Review classification for a specialist plan."""

    ROUTINE = "ROUTINE"
    CONSEQUENTIAL = "CONSEQUENTIAL"
    MATERIAL = "MATERIAL"


# ---------------------------------------------------------------------------
# Known routine patterns from delegation history (T5)
# ---------------------------------------------------------------------------

ROUTINE_PATTERNS: frozenset[str] = frozenset(
    {
        "status_report",
        "daily_brief",
        "weekly_digest",
        "snapshot",
        "health_check",
        "capacity_query",
        "availability_check",
        "profile_audit",
        "delegation_status",
        "followup_reminder",
    }
)

CONSEQUENTIAL_KEYWORDS: frozenset[str] = frozenset(
    {
        "deadline",
        "budget",
        "external",
        "commitment",
        "contract",
        "vendor",
        "client",
        "approval",
        "signoff",
        "milestone",
        "release",
        "pivot",
        "scope_change",
    }
)

# ---------------------------------------------------------------------------
# Plan input shape
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlanInput:
    """Immutable plan description for classification."""

    title: str
    domain: str
    steps: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    impact_area: str = ""
    requires_external_commit: bool = False
    affects_budget: bool = False
    affects_deadline: bool = False
    affects_other_projects: bool = False
    affects_external_commitments: bool = False


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_review(plan_input: PlanInput) -> ReviewClass:
    """Classify a plan into ROUTINE, CONSEQUENTIAL, or MATERIAL.

    Deterministic: no clock reads, no network, no randomness.

    Routine: low impact, reversible, matches known patterns from
    delegation history.  Bypasses full Tola review.

    Consequential: affects deadlines, budgets, other projects, or
    external commitments.  Follows the full approval path.

    Material: highest stakes -- may require NEEDS_USER_DECISION.
    """
    title_lower = plan_input.title.lower().strip()
    domain_lower = plan_input.domain.lower().strip()
    impact_lower = plan_input.impact_area.lower().strip()

    all_text = " ".join(
        [title_lower, domain_lower, impact_lower]
        + plan_input.steps
        + plan_input.artifacts
        + plan_input.success_criteria
        + plan_input.dependencies
        + plan_input.assumptions
    )

    # Material: highest stakes
    if (
        plan_input.requires_external_commit
        or plan_input.affects_budget
        or "material" in title_lower
        or "strategy" in title_lower
        or "portfolio" in title_lower
        or "boundary" in title_lower
        or "authority" in title_lower
    ):
        return ReviewClass.MATERIAL

    # Consequential: affects deadlines, budgets, other projects, external
    if (
        plan_input.affects_deadline
        or plan_input.affects_other_projects
        or plan_input.affects_external_commitments
        or "deadline" in all_text
        or "budget" in all_text
        or "external" in all_text
        or "milestone" in all_text
        or "release" in all_text
        or "pivot" in all_text
        or "scope_change" in all_text
    ):
        return ReviewClass.CONSEQUENTIAL

    # Routine: matches known delegation-history patterns
    if title_lower in ROUTINE_PATTERNS or domain_lower in ROUTINE_PATTERNS:
        return ReviewClass.ROUTINE

    for pattern in ROUTINE_PATTERNS:
        if pattern in title_lower or pattern in domain_lower:
            return ReviewClass.ROUTINE

    # Default: consequential if impact area is non-empty and not routine
    if impact_lower and impact_lower not in ROUTINE_PATTERNS:
        return ReviewClass.CONSEQUENTIAL

    # Fallback: routine for simple, low-impact plans
    return ReviewClass.ROUTINE
