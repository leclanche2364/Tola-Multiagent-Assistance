"""Weekly digest: week roll-up from plain dict/list inputs.

weekly_digest(week_inputs) -> str

Inputs are plain dicts/lists (no PortfolioSnapshot required).
Deterministic: sorted stable, no clock reads, no I/O.
Plain ASCII output only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def weekly_digest(week_inputs: Dict[str, Any]) -> str:
    """Return a week roll-up digest as a plain ASCII string.

    week_inputs keys (all optional):
      - closed_items: list of dicts with 'id', 'title', 'outcome'
      - completed_items: list of dicts with 'id', 'title'
      - escalations_raised: list of dicts with 'id', 'level', 'reason'
      - escalations_resolved: list of dicts with 'id', 'resolution'
      - delegation_ledger: list of dicts with 'delegation_id', 'specialist', 'status'
      - health_transitions: list of dicts with 'project_id', 'from_label', 'to_label'
      - week_start: str (ISO date)
      - week_end: str (ISO date)
    """
    lines: List[str] = []

    lines.append("WEEKLY DIGEST")
    lines.append("=" * 50)

    week_start = week_inputs.get("week_start", "unknown")
    week_end = week_inputs.get("week_end", "unknown")
    lines.append(f"Week: {week_start} to {week_end}")

    # --- Closed/completed items ---
    lines.append("")
    lines.append("CLOSED / COMPLETED ITEMS")
    lines.append("-" * 50)
    closed = week_inputs.get("closed_items", []) or []
    completed = week_inputs.get("completed_items", []) or []
    all_closed = list(closed) + list(completed)
    if all_closed:
        for item in sorted(all_closed, key=lambda x: x.get("id", "")):
            title = item.get("title", "")
            outcome = item.get("outcome", item.get("status", ""))
            lines.append(f"  {item.get('id', '')}: {title} [{outcome}]")
    else:
        lines.append("  (no closed or completed items)")

    counts_line = f"  Total closed/completed: {len(all_closed)}"
    lines.append(counts_line)

    # --- Escalations raised/resolved ---
    lines.append("")
    lines.append("ESCALATIONS")
    lines.append("-" * 50)
    raised = week_inputs.get("escalations_raised", []) or []
    resolved = week_inputs.get("escalations_resolved", []) or []
    lines.append(f"  Raised: {len(raised)}")
    for e in sorted(raised, key=lambda x: x.get("id", "")):
        lines.append(f"    {e.get('id', '')}: [{e.get('level', '')}] {e.get('reason', '')}")
    lines.append(f"  Resolved: {len(resolved)}")
    for e in sorted(resolved, key=lambda x: x.get("id", "")):
        lines.append(f"    {e.get('id', '')}: {e.get('resolution', '')}")

    # --- Delegation ledger summary counts ---
    lines.append("")
    lines.append("DELEGATION LEDGER")
    lines.append("-" * 50)
    ledger = week_inputs.get("delegation_ledger", []) or []
    lines.append(f"  Total delegations: {len(ledger)}")
    status_counts: Dict[str, int] = {}
    for d in ledger:
        s = d.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    for status in sorted(status_counts.keys()):
        lines.append(f"  {status}: {status_counts[status]}")

    # --- Health transitions ---
    lines.append("")
    lines.append("HEALTH TRANSITIONS")
    lines.append("-" * 50)
    transitions = week_inputs.get("health_transitions", []) or []
    if transitions:
        for t in sorted(transitions, key=lambda x: (x.get("project_id", ""), x.get("from_label", ""))):
            lines.append(
                f"  {t.get('project_id', '')}: {t.get('from_label', '')} -> {t.get('to_label', '')}"
            )
    else:
        lines.append("  (no health transitions)")

    return "\n".join(lines)