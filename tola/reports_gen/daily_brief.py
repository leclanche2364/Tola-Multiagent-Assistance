"""Daily brief: morning portfolio summary.

daily_brief(snapshot, escalations, delegations) -> str

Sources:
- PortfolioSnapshot (T2/T3) for project counts and health labels.
- EscalationMatrix/StopRules (T8) for open escalations.
- DelegationLedger (T5) for delegated work in flight.
- StopRules (T8) for stop decisions.

Deterministic: sorted stable, no clock reads, no I/O.
Plain ASCII output only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from tola.portfolio.snapshot import PortfolioSnapshot
from tola.portfolio.health import HealthLabel


def daily_brief(
    snapshot: PortfolioSnapshot,
    escalations: Optional[List[Dict[str, Any]]] = None,
    delegations: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Return a short morning brief as a plain ASCII string."""
    lines: List[str] = []

    # --- Portfolio summary counts by health label ---
    lines.append("DAILY BRIEF")
    lines.append("=" * 40)

    health_counts = _count_health_labels(snapshot)
    lines.append("Portfolio summary:")
    for label in _stable_health_order():
        count = health_counts.get(label, 0)
        lines.append(f"  {label}: {count}")
    total_projects = sum(health_counts.values())
    lines.append(f"  Total projects: {total_projects}")

    # --- Today's attention items (material signals only) ---
    attention_items = _material_attention_items(snapshot)
    lines.append("")
    lines.append("Today's attention items:")
    if attention_items:
        for item in attention_items:
            lines.append(f"  [{item['signal_type']}] {item['project_name']}: {item['detail']}")
    else:
        lines.append("  (none)")

    # --- Open escalations ---
    lines.append("")
    lines.append("Open escalations:")
    open_esc = _open_escalations(escalations or [])
    if open_esc:
        for esc in open_esc:
            lines.append(f"  {esc['level']}: {esc['reason']} -> {esc['recipient']}")
    else:
        lines.append("  (none)")

    # --- Delegated work in flight ---
    lines.append("")
    lines.append("Delegated work in flight:")
    in_flight = _delegations_in_flight(delegations or [])
    if in_flight:
        for d in in_flight:
            lines.append(f"  {d['delegation_id']}: {d['specialist']} [{d['status']}]")
    else:
        lines.append("  (none)")

    # --- Stop decisions ---
    lines.append("")
    lines.append("Stop decisions:")
    stops = _stop_decisions(snapshot, escalations or [])
    if stops:
        for s in stops:
            lines.append(f"  STOP: {s['rule_id']} - {s['reason']}")
    else:
        lines.append("  (no stop decisions)")

    return "\n".join(lines)


def _count_health_labels(snapshot: PortfolioSnapshot) -> Dict[str, int]:
    """Count projects by health label using T3 assessments."""
    counts: Dict[str, int] = {}
    for project in snapshot.projects:
        assessment = getattr(project, "_health_assessment", None)
        if assessment is None:
            # Fallback: infer from project status and flags.
            label = _infer_label(project)
        else:
            label = assessment.label.value if hasattr(assessment.label, "value") else str(assessment.label)
        counts[label] = counts.get(label, 0) + 1
    return counts


def _infer_label(project: Any) -> str:
    """Infer a health label from project-level signals when no T3 assessment is attached."""
    status = getattr(project, "status", "active")
    if status in ("blocked", "paused"):
        return "BLOCKED"
    if status in ("at_risk", "degraded"):
        return "AT_RISK"
    if status == "dormant":
        return "DORMANT"
    return "ON_TRACK"


def _stable_health_order() -> List[str]:
    """Return health labels in a stable, deterministic order."""
    return ["ON_TRACK", "ATTENTION", "AT_RISK", "BLOCKED", "DORMANT"]


def _material_attention_items(snapshot: PortfolioSnapshot) -> List[Dict[str, str]]:
    """Return only material attention items (not ON_TRACK noise)."""
    items: List[Dict[str, str]] = []
    for project in sorted(snapshot.projects, key=lambda p: p.project_id):
        assessment = getattr(project, "_health_assessment", None)
        if assessment is None:
            continue
        label = assessment.label.value if hasattr(assessment.label, "value") else str(assessment.label)
        if label == "ON_TRACK":
            continue
        if not hasattr(assessment, "signals"):
            continue
        for sig in sorted(assessment.signals, key=lambda s: s.type):
            items.append({
                "signal_type": sig.type,
                "project_name": project.project_name,
                "detail": _signal_detail(sig),
            })
    return items


def _signal_detail(sig: Any) -> str:
    """Format a health signal's observed dict as a readable string."""
    parts = []
    observed = getattr(sig, "observed", {}) or {}
    for k, v in sorted(observed.items()):
        parts.append(f"{k}={v}")
    return "; ".join(parts) if parts else sig.type


def _open_escalations(escalations: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Filter escalations that are still open (not resolved)."""
    open_esc: List[Dict[str, str]] = []
    for esc in sorted(escalations, key=lambda e: e.get("level", "")):
        status = esc.get("status", "open")
        if status == "resolved":
            continue
        open_esc.append({
            "level": esc.get("level", "UNKNOWN"),
            "reason": esc.get("reason", ""),
            "recipient": esc.get("recipient", "TOLA"),
        })
    return open_esc


def _delegations_in_flight(delegations: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Return delegations that are still in flight (not completed/rejected/cancelled)."""
    terminal = {"COMPLETED", "REJECTED", "CANCELLED"}
    result: List[Dict[str, str]] = []
    for d in sorted(delegations, key=lambda d: d.get("delegation_id", "")):
        status = d.get("status", "")
        if status in terminal:
            continue
        result.append({
            "delegation_id": d.get("delegation_id", ""),
            "specialist": d.get("specialist", ""),
            "status": status,
        })
    return result


def _stop_decisions(
    snapshot: PortfolioSnapshot,
    escalations: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Extract stop decisions from escalations and snapshot warnings."""
    stops: List[Dict[str, str]] = []
    for esc in sorted(escalations, key=lambda e: e.get("level", "")):
        if esc.get("level") == "STOP_AND_ESCALATE" and esc.get("status") != "resolved":
            stops.append({
                "rule_id": esc.get("rule_id", "escalation"),
                "reason": esc.get("reason", ""),
            })
    # Also surface snapshot warnings that indicate stop conditions.
    for warning in sorted(snapshot.warnings):
        if "blocked" in warning.lower() or "confidence" in warning.lower():
            stops.append({
                "rule_id": "snapshot_warning",
                "reason": warning,
            })
    return stops