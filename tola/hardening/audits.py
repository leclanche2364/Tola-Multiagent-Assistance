# tola.hardening.audits -- Batch T31 audit helpers.
# Permission audit, secret/privacy audit, cost audit, autonomy matrix.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# AuditReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuditReport:
    """Result of an audit: pass/fail with violations list."""

    passed: bool
    violations: tuple[dict[str, Any], ...] = ()


# ---------------------------------------------------------------------------
# Autonomy matrix (frozen, from the plan)
# ---------------------------------------------------------------------------

AUTONOMY_MATRIX: dict[str, tuple[str, ...]] = {
    "tola.scope": ("read", "evaluate", "gate"),
    "tola.goals": ("read", "create", "update", "close"),
    "tola.delegation": ("read", "dispatch", "track", "verify"),
    "tola.monitoring": ("read", "follow_up", "alert"),
    "tola.recovery": ("read", "propose_recovery", "escalate"),
    "tola.persona": ("read", "observe", "promote"),
    "tola.benchmark": ("read", "compare", "score"),
    "tola.evolution": ("read", "propose", "apply"),
    "tola.heartbeat": ("read", "sweep", "wake"),
    "tola.reconciliation": ("read", "diff", "aggregate"),
    "tola.review": ("read", "summarize", "report"),
    "tola.pilot": ("read", "run_scenario", "score"),
    "tola.registry": ("read", "check", "route"),
}


# ---------------------------------------------------------------------------
# Permission audit
# ---------------------------------------------------------------------------

def permission_audit(
    actions: list[dict[str, Any]],
    authority_matrix: dict[str, tuple[str, ...]] | None = None,
) -> AuditReport:
    """Check every action against the supplied authority matrix.

    Each action dict must contain keys: module (str), verb (str).
    An action is a violation when its verb is not in the module's
    allowed verb set from the authority matrix.

    Returns an AuditReport with passed=True only when zero
    violations are found.
    """
    matrix = authority_matrix if authority_matrix is not None else AUTONOMY_MATRIX
    violations: list[dict[str, Any]] = []

    for action in actions:
        module = action.get("module", "")
        verb = action.get("verb", "")
        allowed = matrix.get(module, ())
        if verb not in allowed:
            violations.append(
                {
                    "type": "permission_violation",
                    "module": module,
                    "verb": verb,
                    "allowed_verbs": allowed,
                }
            )

    return AuditReport(
        passed=len(violations) == 0,
        violations=tuple(violations),
    )


# ---------------------------------------------------------------------------
# Secret / privacy audit
# ---------------------------------------------------------------------------

_SENSITIVE_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"password\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"BEGIN PRIVATE KEY"),
]

_SENSITIVE_CATEGORIES: frozenset[str] = frozenset({
    "health_conditions",
    "relationship_status",
    "finances",
    "protected_characteristics",
    "location_tracking",
})


def secret_privacy_audit(artifacts: dict[str, Any]) -> AuditReport:
    """Scan artifact dicts for sensitive-category traits or secret-like strings.

    *artifacts* is a dict of name -> content (str or dict).
    For strings: scanned against _SENSITIVE_PATTERNS.
    For dicts with a 'category' key matching a sensitive category: violation.
    For dicts with 'key' or 'value' fields matching sensitive categories: violation.

    Returns AuditReport with passed=False when any violation is found.
    """
    violations: list[dict[str, Any]] = []

    for name, content in artifacts.items():
        if isinstance(content, str):
            for pat in _SENSITIVE_PATTERNS:
                if pat.search(content):
                    violations.append(
                        {
                            "type": "secret_leak",
                            "artifact": name,
                            "pattern": pat.pattern,
                        }
                    )
        elif isinstance(content, dict):
            cat = content.get("category", "")
            if cat in _SENSITIVE_CATEGORIES:
                violations.append(
                    {
                        "type": "sensitive_category",
                        "artifact": name,
                        "category": cat,
                    }
                )
            for field in ("key", "value", "subject"):
                val = content.get(field, "")
                if isinstance(val, str) and val in _SENSITIVE_CATEGORIES:
                    violations.append(
                        {
                            "type": "sensitive_trait",
                            "artifact": name,
                            "field": field,
                            "value": val,
                        }
                    )

    return AuditReport(
        passed=len(violations) == 0,
        violations=tuple(violations),
    )


# ---------------------------------------------------------------------------
# Cost audit
# ---------------------------------------------------------------------------

def cost_audit(costs: list[dict[str, Any]], budget: float) -> AuditReport:
    """Per-line-item over-budget check with cited numbers.

    Each cost dict must contain keys: item (str), amount (float).
    An item is a violation when its amount exceeds the budget.

    Returns an AuditReport with passed=True only when no
    line item exceeds the budget.
    """
    violations: list[dict[str, Any]] = []

    for cost in costs:
        item = cost.get("item", "")
        amount = cost.get("amount", 0.0)
        if isinstance(amount, (int, float)) and amount > budget:
            violations.append(
                {
                    "type": "over_budget",
                    "item": item,
                    "amount": amount,
                    "budget": budget,
                }
            )

    return AuditReport(
        passed=len(violations) == 0,
        violations=tuple(violations),
    )