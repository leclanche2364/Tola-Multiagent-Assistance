# Batch T26 -- Daily Executive Reconciliation
# tola/reconciliation/cycle.py: run_daily_cycle + DailyReconciliationResult.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from tola.reconciliation.snapshot import (
    MAX_SOURCE_AGE,
    STALE_SOURCE,
    DISCREPANCY,
    reconcile_snapshot,
    SnapshotReport,
)

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DailyReconciliationResult:
    messages: list[str] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    silent: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_iso_date(s: str) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD or full ISO)."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        pass
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _is_overdue(due_date: str, reference_date: date) -> bool:
    """Return True if due_date is on or before reference_date."""
    d = _parse_iso_date(due_date)
    if d is None:
        return False
    return d <= reference_date


def _is_due_today_or_tomorrow(due_date: str, reference_date: date) -> bool:
    """Return True if due_date is today or tomorrow."""
    d = _parse_iso_date(due_date)
    if d is None:
        return False
    return d == reference_date or d == reference_date.fromordinal(
        reference_date.toordinal() + 1
    )


def _sort_surfaced(items: list[dict]) -> list[dict]:
    """Sort surfaced items by due date then id deterministically."""
    def _sort_key(item: dict) -> tuple:
        due = item.get("due_date", "")
        due_parsed = _parse_iso_date(due)
        # Use max date for items without a parseable due date
        # so they sort last.
        due_ord = due_parsed.toordinal() if due_parsed else 9999999999
        return (due_ord, item.get("id", ""))

    return sorted(items, key=_sort_key)


def _detect_discrepancies(
    state: dict,
    current: dict,
) -> list[dict]:
    """Find objects whose current status differs from last_seen marker
    without a corresponding processed event.

    state carries a "last_seen" dict mapping entity ids to their
    last-known status. If an entity in current has a different status
    and no processed_event records the change, it is a DISCREPANCY.
    """
    last_seen: dict[str, str] = state.get("last_seen", {})
    processed_events: set[str] = set(
        state.get("processed_events", [])
    )
    discrepancies: list[dict] = []

    # Collect all entity ids from current snapshot.
    current_ids: set[str] = set()
    for key in ("active_tasks", "blocked_tasks", "risks", "pending_decisions"):
        for item in current.get(key, []):
            if isinstance(item, dict):
                oid = item.get("id", "")
                if oid:
                    current_ids.add(oid)

    for oid in sorted(current_ids):
        # Find the current status of this entity.
        current_status: str | None = None
        for key in ("active_tasks", "blocked_tasks", "risks", "pending_decisions"):
            for item in current.get(key, []):
                if isinstance(item, dict) and item.get("id") == oid:
                    current_status = item.get("status", "")
                    break
            if current_status is not None:
                break

        prev_status = last_seen.get(oid)
        if prev_status is not None and current_status != prev_status:
            # Check if a processed event covers this change.
            event_key = f"{oid}:{current_status}"
            if event_key not in processed_events:
                discrepancies.append(
                    {
                        "action": DISCREPANCY,
                        "id": oid,
                        "field": "status",
                        "last_seen": prev_status,
                        "current": current_status,
                    }
                )

    return discrepancies


def _review_deadlines(
    current: dict,
    reference_date: date,
) -> list[dict]:
    """Surface deadlines that are due, due today, or due tomorrow."""
    surfaced: list[dict] = []
    for dl in current.get("deadlines", []):
        if not isinstance(dl, dict):
            continue
        due = dl.get("due_date", "")
        if not due:
            continue
        d = _parse_iso_date(due)
        if d is None:
            continue
        # Due (overdue), today, or tomorrow.
        if d <= reference_date or d == reference_date.fromordinal(
            reference_date.toordinal() + 1
        ):
            surfaced.append(
                {
                    "id": dl.get("id", ""),
                    "kind": "DEADLINE",
                    "due_date": due,
                    "label": dl.get("label", ""),
                    "status": dl.get("status", ""),
                }
            )
    return _sort_surfaced(surfaced)


def _review_blocked_stalled(
    current: dict,
) -> list[dict]:
    """Find blocked or stalled tasks and surface follow-up actions."""
    surfaced: list[dict] = []
    for task in current.get("active_tasks", []) + current.get("blocked_tasks", []):
        if not isinstance(task, dict):
            continue
        status = task.get("status", "")
        if status in ("stalled", "blocked"):
            surfaced.append(
                {
                    "id": task.get("id", ""),
                    "kind": "TASK_FOLLOW_UP",
                    "status": status,
                    "label": task.get("label", ""),
                }
            )
    return _sort_surfaced(surfaced)


def _review_capacity(
    current: dict,
) -> list[dict]:
    """Check Rhythm capacity signals for overload."""
    surfaced: list[dict] = []
    capacity = current.get("capacity_summary", {})
    if not isinstance(capacity, dict):
        return surfaced
    load = capacity.get("load", 0)
    overload = capacity.get("overload", False)
    # Use overload flag or a numeric threshold.
    is_overloaded = overload or (isinstance(load, (int, float)) and load > 100)
    if is_overloaded:
        surfaced.append(
            {
                "id": "capacity",
                "kind": "CAPACITY_OVERLOAD",
                "load": load,
                "overload": overload,
            }
        )
    return surfaced


def _review_decisions(
    current: dict,
    reference_date: date,
) -> list[dict]:
    """Surface decisions/approvals that are due."""
    surfaced: list[dict] = []
    for dec in current.get("pending_decisions", []):
        if not isinstance(dec, dict):
            continue
        due = dec.get("due_date", "")
        if not due:
            continue
        d = _parse_iso_date(due)
        if d is None:
            continue
        if d <= reference_date:
            surfaced.append(
                {
                    "id": dec.get("id", ""),
                    "kind": "DECISION_DUE",
                    "due_date": due,
                    "label": dec.get("label", ""),
                }
            )
    for apr in current.get("pending_approvals", []):
        if not isinstance(apr, dict):
            continue
        due = apr.get("due_date", "")
        if not due:
            continue
        d = _parse_iso_date(due)
        if d is None:
            continue
        if d <= reference_date:
            surfaced.append(
                {
                    "id": apr.get("id", ""),
                    "kind": "APPROVAL_DUE",
                    "due_date": due,
                    "label": apr.get("label", ""),
                }
            )
    return _sort_surfaced(surfaced)


def _review_material_specialist_outputs(
    current: dict,
) -> list[dict]:
    """Review material specialist outputs for review actions."""
    surfaced: list[dict] = []
    for metric in current.get("material_metrics", []):
        if not isinstance(metric, dict):
            continue
        status = metric.get("status", "")
        if status == "needs_review":
            surfaced.append(
                {
                    "id": metric.get("id", ""),
                    "kind": "MATERIAL_REVIEW",
                    "status": status,
                    "label": metric.get("label", ""),
                }
            )
    return surfaced


def _review_risks(
    current: dict,
) -> list[dict]:
    """Surface new risk items for action."""
    surfaced: list[dict] = []
    for risk in current.get("risks", []):
        if not isinstance(risk, dict):
            continue
        status = risk.get("status", "")
        if status in ("new", "open", "escalated"):
            surfaced.append(
                {
                    "id": risk.get("id", ""),
                    "kind": "RISK_ACTION",
                    "status": status,
                    "label": risk.get("label", ""),
                }
            )
    return _sort_surfaced(surfaced)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_daily_cycle(
    state: dict,
    now_iso: str,
    heartbeat_state: dict | None = None,
) -> DailyReconciliationResult:
    """Run the daily executive reconciliation cycle.

    Cycle steps (fixed order):
        1. Refresh snapshot (reconcile_snapshot against supplied current data)
        2. Review deadlines (due/today/tomorrow -> surfaced)
        3. Review blockers/stalled tasks (stalled -> follow-up action)
        4. Review Rhythm capacity signals (overload -> action)
        5. Review decisions/approvals due (-> surfaced)
        6. Review material specialist outputs (-> review action)

    Parameters
    ----------
    state : dict
        Must contain:
        - "previous_snapshot": dict (previous PortfolioSnapshot)
        - "current_snapshot": dict (current PortfolioSnapshot)
        - "last_seen": dict mapping entity id -> last-known status
        - "processed_events": set of event keys already processed
        - "reference_date": ISO date string (YYYY-MM-DD) used as
          the "today" for all date comparisons (no clock reads).
    now_iso : str
        ISO timestamp for the cycle run (input only, not used for
        clock reads).
    heartbeat_state : dict | None
        Optional heartbeat state for anti-spam (not used directly;
        kept for interface compatibility).

    Returns
    -------
    DailyReconciliationResult
        messages: human-readable summary strings.
        actions: list of action dicts with kind, id, and detail.
        silent: True when nothing material changed (no actions, no
                messages).
    """
    previous = state.get("previous_snapshot", {})
    current = state.get("current_snapshot", {})
    ref_date_str = state.get("reference_date", "")
    ref_date = _parse_iso_date(ref_date_str) or date.today()

    messages: list[str] = []
    actions: list[dict] = []

    # Step 1: Refresh snapshot (reconcile_snapshot).
    report = reconcile_snapshot(
        previous,
        current,
        reference_date=ref_date,
    )

    if not report.sources_fresh:
        for delta in report.deltas:
            if delta.get("action") == STALE_SOURCE:
                actions.append(
                    {
                        "action": STALE_SOURCE,
                        "source": delta["id"],
                        "reason": delta.get("reason", ""),
                    }
                )

    # Step 2: Review deadlines.
    deadline_items = _review_deadlines(current, ref_date)
    for item in deadline_items:
        actions.append(
            {
                "action": "SURFACE_DEADLINE",
                "id": item["id"],
                "due_date": item["due_date"],
                "label": item.get("label", ""),
            }
        )

    # Step 3: Review blockers/stalled tasks.
    stalled_items = _review_blocked_stalled(current)
    for item in stalled_items:
        actions.append(
            {
                "action": "FOLLOW_UP",
                "id": item["id"],
                "status": item["status"],
                "label": item.get("label", ""),
            }
        )

    # Step 4: Review Rhythm capacity signals.
    capacity_items = _review_capacity(current)
    for item in capacity_items:
        actions.append(
            {
                "action": "CAPACITY_OVERLOAD",
                "id": item["id"],
                "load": item.get("load"),
            }
        )

    # Step 5: Review decisions/approvals due.
    decision_items = _review_decisions(current, ref_date)
    for item in decision_items:
        actions.append(
            {
                "action": "SURFACE_DECISION",
                "id": item["id"],
                "due_date": item["due_date"],
                "label": item.get("label", ""),
            }
        )

    # Step 6: Review material specialist outputs.
    material_items = _review_material_specialist_outputs(current)
    for item in material_items:
        actions.append(
            {
                "action": "REVIEW_MATERIAL_OUTPUT",
                "id": item["id"],
                "status": item["status"],
                "label": item.get("label", ""),
            }
        )

    # Review risks (new risk items -> action).
    risk_items = _review_risks(current)
    for item in risk_items:
        actions.append(
            {
                "action": "RISK_ACTION",
                "id": item["id"],
                "status": item["status"],
                "label": item.get("label", ""),
            }
        )

    # Detect missed-event discrepancies.
    discrepancies = _detect_discrepancies(state, current)
    for disc in discrepancies:
        actions.append(
            {
                "action": DISCREPANCY,
                "id": disc["id"],
                "field": disc["field"],
                "last_seen": disc["last_seen"],
                "current": disc["current"],
            }
        )

    # Build messages.
    if actions:
        for a in actions:
            messages.append(
                f"{a['action']}: {a.get('id', '')} - {a.get('label', '')}"
            )

    silent = len(messages) == 0

    return DailyReconciliationResult(
        messages=messages,
        actions=actions,
        silent=silent,
    )
