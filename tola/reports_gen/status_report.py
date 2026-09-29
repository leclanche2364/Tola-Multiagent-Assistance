"""Portfolio status report: fuller per-project view.

portfolio_status_report(snapshot, plans, risks) -> str

Sources:
- PortfolioSnapshot (T2/T3) for per-project health with evidence lines.
- T3 evidence (HealthSignal) reused for non-ON_TRACK projects.
- T7 risk/critical-path highlights (risk_register_from_snapshot, critical_path_milestones).
- Plan versions from T6 decomposition plans.

Deterministic: sorted stable, no clock reads, no I/O.
Plain ASCII output only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from tola.portfolio.snapshot import PortfolioSnapshot
from tola.portfolio.health import HealthLabel, HealthSignal


def portfolio_status_report(
    snapshot: PortfolioSnapshot,
    plans: Optional[List[Dict[str, Any]]] = None,
    risks: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Return a fuller portfolio status report as a plain ASCII string."""
    lines: List[str] = []

    lines.append("PORTFOLIO STATUS REPORT")
    lines.append("=" * 50)

    # --- Per-project health with evidence lines ---
    lines.append("")
    lines.append("PROJECT HEALTH")
    lines.append("-" * 50)

    assessments = _collect_assessments(snapshot)
    if assessments:
        for label in _stable_health_order():
            matching = [a for a in assessments if a["label"] == label]
            for a in sorted(matching, key=lambda x: x["project_id"]):
                lines.append(f"[{a['label']}] {a['project_id']} - {a['project_name']}")
                if a["label"] != "ON_TRACK":
                    for ev in sorted(a["evidence"], key=lambda e: e["signal_type"]):
                        lines.append(f"  Evidence: {ev['signal_type']} | {ev['detail']}")
                else:
                    lines.append("  Evidence: no material signals")
                lines.append("")
    else:
        lines.append("  (no projects in snapshot)")

    # --- Risk highlights ---
    lines.append("RISK HIGHLIGHTS")
    lines.append("-" * 50)
    risk_items = _risk_highlights(snapshot, risks)
    if risk_items:
        for r in sorted(risk_items, key=lambda x: x["severity"], reverse=True):
            lines.append(f"  [{r['severity'].upper()}] {r['risk_id']}: {r['title']} ({r['status']})")
    else:
        lines.append("  (no risks recorded)")

    # --- Critical path milestones ---
    lines.append("")
    lines.append("CRITICAL PATH MILESTONES")
    lines.append("-" * 50)
    cp = _critical_path(snapshot)
    if cp:
        for i, ms in enumerate(cp, 1):
            lines.append(f"  {i}. {ms}")
    else:
        lines.append("  (no milestone chain data)")

    # --- Plan versions ---
    lines.append("")
    lines.append("PLAN VERSIONS")
    lines.append("-" * 50)
    plan_items = _plan_versions(snapshot, plans or [])
    if plan_items:
        for p in sorted(plan_items, key=lambda x: x["plan_id"]):
            lines.append(f"  {p['plan_id']}: version={p['version']} status={p['status']}")
    else:
        lines.append("  (no plans recorded)")

    # --- Snapshot metadata ---
    lines.append("")
    lines.append("SNAPSHOT META")
    lines.append("-" * 50)
    lines.append(f"  Version: {snapshot.snapshot_version}")
    lines.append(f"  Generated: {snapshot.generated_at}")
    lines.append(f"  Confidence: {snapshot.confidence}")
    if snapshot.warnings:
        lines.append("  Warnings:")
        for w in sorted(snapshot.warnings):
            lines.append(f"    - {w}")

    return "\n".join(lines)


def _collect_assessments(snapshot: PortfolioSnapshot) -> List[Dict[str, Any]]:
    """Gather project health assessments from snapshot."""
    results: List[Dict[str, Any]] = []
    for project in snapshot.projects:
        assessment = getattr(project, "_health_assessment", None)
        if assessment is None:
            label = _infer_label(project)
            evidence: List[Dict[str, str]] = []
        else:
            label = assessment.label.value if hasattr(assessment.label, "value") else str(assessment.label)
            evidence = _evidence_lines(assessment)
        results.append({
            "project_id": project.project_id,
            "project_name": project.project_name,
            "label": label,
            "evidence": evidence,
        })
    return results


def _evidence_lines(assessment: Any) -> List[Dict[str, str]]:
    """Extract evidence lines from a HealthAssessment (reuse T3 evidence)."""
    lines: List[Dict[str, str]] = []
    signals = getattr(assessment, "signals", []) or []
    for sig in sorted(signals, key=lambda s: s.type):
        detail = _signal_detail(sig)
        lines.append({
            "signal_type": sig.type,
            "entity_type": sig.entity_type,
            "entity_id": sig.entity_id,
            "detail": detail,
        })
    return lines


def _signal_detail(sig: Any) -> str:
    """Format a health signal's observed dict as a readable string."""
    observed = getattr(sig, "observed", {}) or {}
    parts = []
    for k, v in sorted(observed.items()):
        parts.append(f"{k}={v}")
    return "; ".join(parts) if parts else sig.type


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


def _risk_highlights(
    snapshot: PortfolioSnapshot,
    risks: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, str]]:
    """Extract risk highlights from snapshot and optional risk list."""
    items: List[Dict[str, str]] = []

    # Use snapshot risks first.
    for r in sorted(snapshot.risks, key=lambda r: r.risk_id):
        items.append({
            "risk_id": r.risk_id,
            "title": r.title,
            "severity": r.severity,
            "status": r.status,
        })

    # Supplement with external risk dicts if provided.
    if risks is not None:
        for r in risks:
            rid = r.get("risk_id", "")
            # Skip duplicates already in snapshot.
            if any(i["risk_id"] == rid for i in items):
                continue
            items.append({
                "risk_id": rid,
                "title": r.get("title", ""),
                "severity": r.get("severity", "medium"),
                "status": r.get("status", "open"),
            })

    return items


def _critical_path(snapshot: PortfolioSnapshot) -> List[str]:
    """Return critical path milestone IDs from T7 analysis."""
    # Try to get the dependency graph from snapshot if available.
    graph = getattr(snapshot, "_dependency_graph", None)
    if graph is not None:
        from tola.graph.risks import critical_path_milestones
        return critical_path_milestones(graph)
    # Fallback: check for milestone data in active goals.
    milestones: List[str] = []
    for goal in sorted(snapshot.active_goals, key=lambda g: g.goal_id):
        if goal.due_date:
            milestones.append(f"{goal.goal_id} (due {goal.due_date})")
    return milestones


def _plan_versions(
    snapshot: PortfolioSnapshot,
    plans: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Extract plan version info from T6 decomposition plans."""
    items: List[Dict[str, str]] = []
    for plan in sorted(plans, key=lambda p: p.get("plan_id", "")):
        items.append({
            "plan_id": plan.get("plan_id", ""),
            "version": plan.get("version", "unknown"),
            "status": plan.get("status", "unknown"),
        })
    return items