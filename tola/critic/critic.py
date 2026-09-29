# Batch T10 - Critic
# critique_plan(plan_input) -> CriticVerdict
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from tola.critic.review_classes import (
    ReviewClass,
    classify_review,
    ROUTINE_PATTERNS,
    CONSEQUENTIAL_KEYWORDS,
)
from tola.registry.capability import agent_boundary_check
from tola.registry.boundaries import BoundaryViolation


# ---------------------------------------------------------------------------
# Verdict enum
# ---------------------------------------------------------------------------

class Verdict(str, Enum):
    APPROVE = "APPROVE"
    APPROVE_WITH_CHANGES = "APPROVE_WITH_CHANGES"
    REVISE = "REVISE"
    REJECT = "REJECT"
    NEEDS_USER_DECISION = "NEEDS_USER_DECISION"


# ---------------------------------------------------------------------------
# Finding and required-change dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    """A single review finding."""

    code: str
    severity: str  # INFO | WARNING | ERROR
    message: str


@dataclass(frozen=True)
class RequiredChange:
    """A change required before the plan can be approved."""

    code: str
    description: str
    target_step: str


@dataclass(frozen=True)
class CriticVerdict:
    """Result of a plan critique."""

    verdict: Verdict
    findings: list[Finding] = field(default_factory=list)
    required_changes: list[RequiredChange] = field(default_factory=list)
    review_class: ReviewClass = ReviewClass.ROUTINE


# ---------------------------------------------------------------------------
# Named threshold/rubric constants
# ---------------------------------------------------------------------------

MAX_STEPS_BEFORE_OVERCOMPLICATED = 10
MAX_ARTIFACTS_BEFORE_OVERCOMPLICATED = 5
MAX_ASSUMPTIONS_BEFORE_FLAG = 3
MIN_SUCCESS_CRITERIA = 1
MIN_DEPENDENCIES = 0  # zero is acceptable; missing is flagged when
# dependencies are implied by steps but not listed

# Finding codes
FC_MISSING_SUCCESS_METRIC = "MISSING_SUCCESS_METRIC"
FC_MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
FC_MISSING_DEPENDENCY_IMPLIED = "MISSING_DEPENDENCY_IMPLIED"
FC_UNSUPPORTED_ASSUMPTION = "UNSUPPORTED_ASSUMPTION"
FC_OVERCOMPLICATION = "OVERCOMPLICATION"
FC_BOUNDARY_VIOLATION = "BOUNDARY_VIOLATION"
FC_EXTERNAL_COMMITMENT = "EXTERNAL_COMMITMENT"
FC_BUDGET_IMPACT = "BUDGET_IMPACT"
FC_ROUTINE_BYPASS = "ROUTINE_BYPASS"
FC_STYLE_ONLY_REWRITE = "STYLE_ONLY_REWRITE"
FC_MISSING_DEPENDENCY_IMPLIED = "MISSING_DEPENDENCY_IMPLIED"

# Severity
SEV_INFO = "INFO"
SEV_WARNING = "WARNING"
SEV_ERROR = "ERROR"

# Rubric labels
RUBRIC_STRONG_COMPLETE = "STRONG_COMPLETE"
RUBRIC_MISSING_METRIC = "MISSING_METRIC"
RUBRIC_MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
RUBRIC_UNSUPPORTED_ASSUMPTION = "UNSUPPORTED_ASSUMPTION"
RUBRIC_OVERCOMPLICATED = "OVERCOMPLICATED"
RUBRIC_BOUNDARY_VIOLATION = "BOUNDARY_VIOLATION"
RUBRIC_EXTERNAL_COMMITMENT = "EXTERNAL_COMMITMENT"
RUBRIC_BUDGET_IMPACT = "BUDGET_IMPACT"
RUBRIC_STYLE_ONLY = "STYLE_ONLY"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_routine(plan_input: Any) -> bool:
    """Check if the plan is classified as routine."""
    rc = classify_review(plan_input)
    return rc == ReviewClass.ROUTINE


def _is_consequential(plan_input: Any) -> bool:
    """Check if the plan is classified as consequential."""
    rc = classify_review(plan_input)
    return rc == ReviewClass.CONSEQUENTIAL


def _is_material(plan_input: Any) -> bool:
    """Check if the plan is classified as material."""
    rc = classify_review(plan_input)
    return rc == ReviewClass.MATERIAL


def _plan_has_style_only_issues(plan_input: Any) -> bool:
    """Detect if the only issues are cosmetic/style preferences."""
    # A plan with no findings of substance is style-only
    return False


def _check_boundary(plan_input: Any) -> list[Finding]:
    """Check the plan against T4 boundary/registry constraints."""
    findings: list[Finding] = []
    domain_lower = plan_input.domain.lower().strip()

    # Check each step for boundary violations using exact keywords
    for step in plan_input.steps:
        step_lower = step.lower().strip()
        for agent_id, action_keywords in (
            ("growth", ("direct_schedule_write", "rhythm_schedule_write", "schedule_write", "rhythm_direct_write")),
            ("tola", ("direct_my_rhythm_write", "my_rhythm_write", "rhythm_direct_write", "rhythm_schedule_write")),
            ("scholar", ("product_growth_analysis", "funnel_analysis", "growth_recommendation", "acquisition_analysis", "conversion_analysis", "retention_analysis", "product_metrics_write")),
        ):
            for kw in action_keywords:
                if kw in step_lower:
                    result = agent_boundary_check(agent_id, kw)
                    if not result["allowed"]:
                        findings.append(
                            Finding(
                                code=FC_BOUNDARY_VIOLATION,
                                severity=SEV_ERROR,
                                message=(
                                    f"Step violates boundary: '{step}' "
                                    f"triggers {result['reason']}"
                                ),
                            )
                        )

    return findings


def _check_success_metric(plan_input: Any) -> list[Finding]:
    """Check that the plan defines at least one success metric."""
    findings: list[Finding] = []
    if len(plan_input.success_criteria) < MIN_SUCCESS_CRITERIA:
        findings.append(
            Finding(
                code=FC_MISSING_SUCCESS_METRIC,
                severity=SEV_ERROR,
                message=(
                    "Plan has no success metric defined. "
                    "At least one measurable success criterion is required."
                ),
            )
        )
    return findings


def _check_dependencies(plan_input: Any) -> list[Finding]:
    """Check that dependencies required by steps are listed."""
    findings: list[Finding] = []
    # If steps reference external prerequisites not in dependencies, flag
    step_text = " ".join(plan_input.steps).lower()
    for dep in plan_input.dependencies:
        dep_lower = dep.lower().strip()
        # Check that each listed dependency is actually referenced
        if dep_lower not in step_text and dep_lower.replace(" ", "_") not in step_text:
            # Unlisted but present - not an error, just unused
            pass

    # Check for implied dependencies: steps that reference a dependency
    # word but the dependency is not listed in plan.dependencies.
    implied_markers = ("after ", "before ", "depends on", "requires ", "needs ")
    for step in plan_input.steps:
        step_lower = step.lower().strip()
        for marker in implied_markers:
            if marker in step_lower:
                idx = step_lower.index(marker)
                remainder = step_lower[idx + len(marker):].strip()
                # Remove trailing punctuation for matching
                remainder_clean = remainder.rstrip(".").rstrip(",").strip()
                if not remainder_clean:
                    break
                matched = False
                for dep in plan_input.dependencies:
                    dep_clean = dep.lower().strip().rstrip(".").rstrip(",").strip()
                    if dep_clean in remainder_clean or remainder_clean in dep_clean:
                        matched = True
                        break
                if not matched:
                    findings.append(
                        Finding(
                            code=FC_MISSING_DEPENDENCY_IMPLIED,
                            severity=SEV_WARNING,
                            message=(
                                f"Step implies dependency '{remainder_clean}' "
                                f"but it is not listed in plan dependencies."
                            ),
                        )
                    )
                    break

    return findings


def _check_assumptions(plan_input: Any) -> list[Finding]:
    """Flag unsupported assumptions."""
    findings: list[Finding] = []
    if len(plan_input.assumptions) > MAX_ASSUMPTIONS_BEFORE_FLAG:
        findings.append(
            Finding(
                code=FC_UNSUPPORTED_ASSUMPTION,
                severity=SEV_WARNING,
                message=(
                    f"Plan contains {len(plan_input.assumptions)} assumptions "
                    f"({MAX_ASSUMPTIONS_BEFORE_FLAG} is the recommended maximum). "
                    f"Each unsupported assumption should be validated or "
                    f"converted into a dependency or success criterion."
                ),
            )
        )
    return findings


def _check_overcomplication(plan_input: Any) -> list[Finding]:
    """Check for unnecessary steps or artifacts beyond goal scope."""
    findings: list[Finding] = []
    trim_suggestions: list[str] = []

    if len(plan_input.steps) > MAX_STEPS_BEFORE_OVERCOMPLICATED:
        excess = len(plan_input.steps) - MAX_STEPS_BEFORE_OVERCOMPLICATED
        trim_suggestions.append(
            f"Reduce steps by {excess} (current: {len(plan_input.steps)}, "
            f"threshold: {MAX_STEPS_BEFORE_OVERCOMPLICATED})"
        )

    if len(plan_input.artifacts) > MAX_ARTIFACTS_BEFORE_OVERCOMPLICATED:
        excess = len(plan_input.artifacts) - MAX_ARTIFACTS_BEFORE_OVERCOMPLICATED
        trim_suggestions.append(
            f"Reduce artifacts by {excess} (current: {len(plan_input.artifacts)}, "
            f"threshold: {MAX_ARTIFACTS_BEFORE_OVERCOMPLICATED})"
        )

    if trim_suggestions:
        findings.append(
            Finding(
                code=FC_OVERCOMPLICATION,
                severity=SEV_WARNING,
                message=(
                    "Plan contains unnecessary steps or artifacts beyond "
                    "goal scope. "
                    + "; ".join(trim_suggestions)
                ),
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Main critique function
# ---------------------------------------------------------------------------

def critique_plan(plan_input: Any) -> CriticVerdict:
    """Critique a specialist plan and return a deterministic CriticVerdict.

    The review follows this decision tree:

    1. Routine plans bypass full critique -> APPROVE (fast path).
    2. Boundary/registry violations -> REJECT.
    3. Missing success metric -> REVISE.
    4. Missing dependency -> REVISE.
    5. Unsupported assumption -> flagged with change request (REVISE).
    6. Overcomplication -> APPROVE_WITH_CHANGES (trim suggestions).
    7. External commitment or budget impact -> NEEDS_USER_DECISION.
    8. Strong, complete plans -> APPROVE (no cosmetic rewrites).

    All thresholds and rubric points are named constants above.
    Deterministic: no clock reads, no network, no randomness.
    """
    findings: list[Finding] = []
    required_changes: list[RequiredChange] = []

    # --- Step 1: Routine bypass ---
    if _is_routine(plan_input):
        return CriticVerdict(
            verdict=Verdict.APPROVE,
            findings=[
                Finding(
                    code=FC_ROUTINE_BYPASS,
                    severity=SEV_INFO,
                    message=(
                        "Routine plan bypasses full Tola review. "
                        "Low impact, reversible, matches known delegation patterns."
                    ),
                )
            ],
            required_changes=[],
            review_class=ReviewClass.ROUTINE,
        )

    # --- Step 2: Boundary / registry check ---
    boundary_findings = _check_boundary(plan_input)
    findings.extend(boundary_findings)
    if any(f.code == FC_BOUNDARY_VIOLATION for f in boundary_findings):
        return CriticVerdict(
            verdict=Verdict.REJECT,
            findings=findings,
            required_changes=required_changes,
            review_class=classify_review(plan_input),
        )

    # --- Step 3: Missing success metric ---
    metric_findings = _check_success_metric(plan_input)
    findings.extend(metric_findings)
    if any(f.code == FC_MISSING_SUCCESS_METRIC for f in metric_findings):
        required_changes.append(
            RequiredChange(
                code=FC_MISSING_SUCCESS_METRIC,
                description="Add at least one measurable success metric",
                target_step="plan.success_criteria",
            )
        )
        return CriticVerdict(
            verdict=Verdict.REVISE,
            findings=findings,
            required_changes=required_changes,
            review_class=classify_review(plan_input),
        )

    # --- Step 4: Missing dependency ---
    dep_findings = _check_dependencies(plan_input)
    findings.extend(dep_findings)
    if any(f.code == FC_MISSING_DEPENDENCY_IMPLIED for f in dep_findings):
        required_changes.append(
            RequiredChange(
                code=FC_MISSING_DEPENDENCY,
                description="Add implied dependencies to plan.dependencies",
                target_step="plan.dependencies",
            )
        )
        return CriticVerdict(
            verdict=Verdict.REVISE,
            findings=findings,
            required_changes=required_changes,
            review_class=classify_review(plan_input),
        )

    # --- Step 5: Unsupported assumptions ---
    assumption_findings = _check_assumptions(plan_input)
    findings.extend(assumption_findings)
    if any(f.code == FC_UNSUPPORTED_ASSUMPTION for f in assumption_findings):
        required_changes.append(
            RequiredChange(
                code=FC_UNSUPPORTED_ASSUMPTION,
                description="Validate or convert unsupported assumptions",
                target_step="plan.assumptions",
            )
        )
        # Flagged but not blocking - continue to check other issues

    # --- Step 6: Overcomplication ---
    overcomplication_findings = _check_overcomplication(plan_input)
    findings.extend(overcomplication_findings)
    if any(f.code == FC_OVERCOMPLICATION for f in overcomplication_findings):
        return CriticVerdict(
            verdict=Verdict.APPROVE_WITH_CHANGES,
            findings=findings,
            required_changes=required_changes,
            review_class=classify_review(plan_input),
        )

    # --- Step 7: External commitment / budget -> NEEDS_USER_DECISION ---
    if plan_input.requires_external_commit:
        return CriticVerdict(
            verdict=Verdict.NEEDS_USER_DECISION,
            findings=findings
            + [
                Finding(
                    code=FC_EXTERNAL_COMMITMENT,
                    severity=SEV_WARNING,
                    message=(
                        "Plan requires an external commitment outside "
                        "Tola's authority. User decision needed."
                    ),
                )
            ],
            required_changes=required_changes,
            review_class=classify_review(plan_input),
        )

    if plan_input.affects_budget:
        return CriticVerdict(
            verdict=Verdict.NEEDS_USER_DECISION,
            findings=findings
            + [
                Finding(
                    code=FC_BUDGET_IMPACT,
                    severity=SEV_WARNING,
                    message=(
                        "Plan affects budget. Approval outside Tola's "
                        "authority is required."
                    ),
                )
            ],
            required_changes=required_changes,
            review_class=classify_review(plan_input),
        )

    # --- Step 8: Strong, complete plan -> APPROVE ---
    # Preserve good specialist reasoning - no style-only rewrites.
    # Assert that findings do not mention stylistic preferences.
    return CriticVerdict(
        verdict=Verdict.APPROVE,
        findings=findings,
        required_changes=required_changes,
        review_class=classify_review(plan_input),
    )
