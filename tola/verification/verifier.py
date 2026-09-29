# verify_outcome -- deterministic outcome ladder.
# Batch T13. Stdlib only. Plain ASCII.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from tola.verification.criteria import SuccessCriterion, CriterionKind


class VerificationOutcome(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    UNVERIFIABLE = "UNVERIFIABLE"


@dataclass(frozen=True)
class CheckResult:
    criterion_id: str
    passed: bool
    evidence_kind: str
    reason: str


@dataclass(frozen=True)
class VerificationResult:
    outcome: str
    checks: list[CheckResult] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def _check_kind_compatible(evidence_kind: str, required_kind: str) -> bool:
    """Return True if evidence kind can satisfy the criterion kind."""
    if required_kind == CriterionKind.ARTIFACT_EXISTS.value:
        return evidence_kind == "artifact"
    if required_kind == CriterionKind.FIELD_MATCH.value:
        return evidence_kind == "field"
    if required_kind == CriterionKind.THRESHOLD_MET.value:
        return evidence_kind == "metric"
    if required_kind == CriterionKind.CONFIRMATION_RECEIVED.value:
        return evidence_kind == "confirmation"
    if required_kind == CriterionKind.BOOLEAN_PROPERTY.value:
        return evidence_kind == "property"
    return False


def _evaluate(
    criterion: SuccessCriterion,
    evidence: dict[str, Any],
) -> CheckResult:
    """Evaluate one criterion against evidence. Returns CheckResult."""
    evidence_kind = evidence.get("kind", "")
    evidence_data = evidence.get("data", {})

    if not _check_kind_compatible(evidence_kind, criterion.kind):
        return CheckResult(
            criterion_id=criterion.criterion_id,
            passed=False,
            evidence_kind=evidence_kind,
            reason=f"Evidence kind '{evidence_kind}' incompatible with "
            f"criterion kind '{criterion.kind}'",
        )

    check = criterion.check
    cid = criterion.criterion_id

    if criterion.kind == CriterionKind.ARTIFACT_EXISTS.value:
        artifact_name = check.get("artifact_name", "")
        passed = str(evidence_data.get("name", "")) == str(artifact_name)
        reason = (
            "Artifact found" if passed
            else f"Artifact '{artifact_name}' not found in evidence"
        )
        return CheckResult(cid, passed, evidence_kind, reason)

    if criterion.kind == CriterionKind.FIELD_MATCH.value:
        field = check.get("field", "")
        expected = check.get("expected")
        actual = evidence_data.get(field)
        passed = actual == expected
        reason = (
            f"Field '{field}' matches" if passed
            else f"Field '{field}' mismatch: expected={expected}, got={actual}"
        )
        return CheckResult(cid, passed, evidence_kind, reason)

    if criterion.kind == CriterionKind.THRESHOLD_MET.value:
        metric = check.get("metric", "")
        threshold = check.get("threshold")
        actual = evidence_data.get(metric)
        if actual is None:
            return CheckResult(
                cid, False, evidence_kind,
                f"Metric '{metric}' missing from evidence",
            )
        try:
            passed = float(actual) >= float(threshold)
        except (TypeError, ValueError):
            return CheckResult(
                cid, False, evidence_kind,
                f"Cannot compare '{actual}' >= '{threshold}'",
            )
        reason = (
            f"Metric '{metric}' {actual} >= {threshold}" if passed
            else f"Metric '{metric}' {actual} < {threshold}"
        )
        return CheckResult(cid, passed, evidence_kind, reason)

    if criterion.kind == CriterionKind.CONFIRMATION_RECEIVED.value:
        confirmation = evidence_data.get("confirmed", False)
        passed = bool(confirmation) is True
        reason = "Confirmation received" if passed else "No confirmation in evidence"
        return CheckResult(cid, passed, evidence_kind, reason)

    if criterion.kind == CriterionKind.BOOLEAN_PROPERTY.value:
        prop = check.get("property", "")
        expected_val = check.get("value", True)
        actual = evidence_data.get(prop)
        passed = actual == expected_val
        reason = (
            f"Property '{prop}'={actual} matches {expected_val}" if passed
            else f"Property '{prop}'={actual} != {expected_val}"
        )
        return CheckResult(cid, passed, evidence_kind, reason)

    return CheckResult(cid, False, evidence_kind, "Unhandled criterion kind")


def verify_outcome(
    criteria: list[SuccessCriterion],
    evidence: dict[str, Any],
) -> VerificationResult:
    """Verify outcome against success criteria and evidence.

    Deterministic.  Every criterion needs matching evidence.
    A claimed 'complete' with unmet criteria is NOT_VERIFIED.
    Evidence of wrong kind is UNVERIFIABLE for that criterion.
    All met -> VERIFIED; some met -> PARTIALLY_VERIFIED with missing[].
    """
    if not criteria:
        return VerificationResult(
            outcome=VerificationOutcome.UNVERIFIABLE.value,
            reasons=["No criteria provided -- cannot verify"],
        )

    evidence_items = evidence.get("items", [])
    if not isinstance(evidence_items, list):
        evidence_items = []

    checks: list[CheckResult] = []
    missing: list[str] = []
    reasons: list[str] = []

    for criterion in criteria:
        # Find matching evidence for this criterion
        criterion_evidence = None
        for item in evidence_items:
            if item.get("criterion_id") == criterion.criterion_id:
                criterion_evidence = item
                break

        if criterion_evidence is None:
            missing.append(criterion.criterion_id)
            checks.append(
                CheckResult(
                    criterion_id=criterion.criterion_id,
                    passed=False,
                    evidence_kind="",
                    reason="No evidence provided for this criterion",
                )
            )
            continue

        result = _evaluate(criterion, criterion_evidence)
        checks.append(result)
        if not result.passed:
            if "incompatible" in result.reason.lower() and "kind" in result.reason.lower():
                reasons.append(
                    f"Criterion '{criterion.criterion_id}': UNVERIFIABLE -- "
                    f"{result.reason}"
                )
            else:
                missing.append(criterion.criterion_id)
                reasons.append(
                    f"Criterion '{criterion.criterion_id}': NOT_MET -- {result.reason}"
                )

    passed_count = sum(1 for c in checks if c.passed)
    total = len(checks)

    if passed_count == total:
        outcome = VerificationOutcome.VERIFIED.value
    elif passed_count == 0:
        # All failed -- check if every failure is due to wrong evidence kind
        all_unverifiable = all(
            "incompatible" in c.reason.lower() and "kind" in c.reason.lower()
            for c in checks
        )
        if all_unverifiable:
            outcome = VerificationOutcome.UNVERIFIABLE.value
        else:
            outcome = VerificationOutcome.NOT_VERIFIED.value
    else:
        outcome = VerificationOutcome.PARTIALLY_VERIFIED.value

    return VerificationResult(
        outcome=outcome,
        checks=checks,
        missing=missing,
        reasons=reasons,
    )