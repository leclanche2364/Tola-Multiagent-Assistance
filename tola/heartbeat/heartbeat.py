# Batch T25 -- Executive Heartbeat
# tola/heartbeat/heartbeat.py: run_heartbeat deterministic sweep.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tola.heartbeat.policy import (
    THRESHOLDS,
    IDLE_COST,
    WAKE_COST,
    NO_SIGNAL,
    WAKE,
    ACTION_ONLY,
)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class HeartbeatResult:
    wake: bool = False
    findings: list[dict] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    cost_units: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding_key(condition: dict) -> str:
    """Stable key for anti-spam dedup: kind + id."""
    return f"{condition.get('kind', '')}:{condition.get('id', '')}"


def _fingerprint(condition: dict) -> str:
    """Fingerprint for anti-spam: kind + id + severity + age bucket."""
    kind = condition.get("kind", "")
    cid = condition.get("id", "")
    severity = condition.get("severity", "")
    age_days = condition.get("age_days", None)
    # Bucket age into discrete bands so unchanged conditions match.
    if age_days is None:
        age_bucket = "unknown"
    elif age_days <= 0:
        age_bucket = "overdue"
    elif age_days <= 3:
        age_bucket = "recent"
    elif age_days <= 7:
        age_bucket = "stale"
    else:
        age_bucket = "old"
    return f"{kind}:{cid}:{severity}:{age_bucket}"


def _is_material(condition: dict) -> bool:
    """A condition is material if its material flag is truthy or severity is high/critical."""
    if condition.get("material", False):
        return True
    sev = condition.get("severity", "")
    return sev in ("high", "critical")


def _classify(condition: dict) -> tuple[str, str | None]:
    """
    Classify a condition into (signal_kind, action).
    Returns (NO_SIGNAL, None) if not material and not a wake trigger.
    """
    kind = condition.get("kind", "")
    age_days = condition.get("age_days", None)
    severity = condition.get("severity", "")

    # Overdue material task -> WAKE
    if kind == "OVERDUE_TASK" and _is_material(condition):
        return (WAKE, None)

    # Long-standing blocker -> WAKE
    if kind == "BLOCKER" and _is_material(condition):
        if age_days is not None and age_days > THRESHOLDS["BLOCKER_AGE_LIMIT"]:
            return (WAKE, None)
        # Non-material or young blocker: no signal
        return (NO_SIGNAL, None)

    # Approval beyond threshold -> WAKE
    if kind == "APPROVAL_PENDING" and _is_material(condition):
        if age_days is not None and age_days > THRESHOLDS["APPROVAL_AGE_LIMIT"]:
            return (WAKE, None)
        return (NO_SIGNAL, None)

    # Unreviewed experiment -> WAKE
    if kind == "EXPERIMENT_UNREVIEWED" and _is_material(condition):
        if age_days is not None and age_days > THRESHOLDS["EXPERIMENT_REVIEW_AGE"]:
            return (WAKE, None)
        return (NO_SIGNAL, None)

    # Stale PortfolioSnapshot -> ACTION_ONLY (refresh) or WAKE if beyond hard limit
    if kind == "SNAPSHOT_STALE":
        if age_days is not None and age_days > THRESHOLDS["SNAPSHOT_HARD_LIMIT"]:
            return (WAKE, None)
        if age_days is not None and age_days > THRESHOLDS["SNAPSHOT_MAX_AGE"]:
            return (ACTION_ONLY, "REFRESH_SNAPSHOT")
        return (NO_SIGNAL, None)

    # Not a recognised wake kind or not material -> no signal
    return (NO_SIGNAL, None)


# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------

def run_heartbeat(
    conditions: list[dict],
    now_iso: str,
    state: dict[str, str] | None = None,
) -> HeartbeatResult:
    """
    Deterministic sweep over conditions.

    Parameters
    ----------
    conditions : list[dict]
        Each dict must have keys: kind, id, severity, material (bool),
        and either age_days (int) or timestamps (dict with created/updated).
    now_iso : str
        ISO timestamp used as reference for age computation (input only).
    state : dict | None
        Optional dict of finding_key -> last_notified_fingerprint for
        anti-spam.  Mutated in-place when a new wake is emitted.

    Returns
    -------
    HeartbeatResult
        wake, findings, actions, cost_units
    """
    if state is None:
        state = {}

    result = HeartbeatResult()
    findings: list[dict] = []
    actions: list[str] = []
    any_wake = False

    for cond in conditions:
        kind = cond.get("kind", "")
        cid = cond.get("id", "")
        key = _finding_key(cond)
        fp = _fingerprint(cond)

        signal_kind, action = _classify(cond)

        if signal_kind == NO_SIGNAL:
            # No material finding; clean stale state entry if present.
            state.pop(key, None)
            continue

        # Anti-spam: identical unresolved condition already in state?
        if key in state and state[key] == fp:
            # Suppressed: same fingerprint, no new wake.
            continue

        # New or changed condition.
        state[key] = fp

        if signal_kind == WAKE:
            any_wake = True
            finding = {
                "kind": kind,
                "id": cid,
                "severity": cond.get("severity", ""),
                "age_days": cond.get("age_days"),
                "signal": WAKE,
                "evidence": f"{kind} {cid} age={cond.get('age_days')}d severity={cond.get('severity')}",
            }
            findings.append(finding)
            result.cost_units += WAKE_COST
        elif signal_kind == ACTION_ONLY and action:
            actions.append(action)
            # ACTION_ONLY does not increment cost beyond IDLE_COST baseline.

    result.wake = any_wake
    result.findings = findings
    result.actions = actions

    # If no wake findings, cost is IDLE_COST (actions like REFRESH_SNAPSHOT
    # are self-serve and do not add cost).
    if not any_wake and result.cost_units == 0:
        result.cost_units = IDLE_COST

    return result


def idle_cost_within_target(result: HeartbeatResult, target: int = IDLE_COST) -> bool:
    """Assert-style helper: True when result cost is at or below target."""
    return result.cost_units <= target
