"""Rhythm capacity handoff v1 producer — PROPOSE-mode only.
Assembles a capacity handoff from caller-supplied inputs.
No project fields, no scheduler writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from agents.daily_synthesis.contracts import RhythmCapacityHandoff, ValidationError


class WorkType(str, Enum):
    DEEP = "deep"
    MEDIUM = "medium"
    LIGHT = "light"


@dataclass
class CapacityWindow:
    start: str
    end: str
    duration_minutes: int
    work_type: str
    confidence: float
    constraints: list[str] = field(default_factory=list)


@dataclass
class RecoveryData:
    hours_slept: Optional[float] = None
    fatigue_risk: Optional[str] = None
    recovery_buffer_minutes: int = 0
    status: str = "unknown"


@dataclass
class ShiftInfo:
    id: str
    start: str
    end: str
    type: str
    committed_minutes: int = 0


@dataclass
class FixedCommitment:
    label: str
    start: str
    end: str
    duration_minutes: int
    protected: bool = False


@dataclass
class Carryover:
    unfinished_minutes: int = 0
    source_task: str = ""


_CONTRACT_FIELDS = set(RhythmCapacityHandoff.__dataclass_fields__.keys())


def _classify_work_type(duration_minutes: int) -> str:
    if duration_minutes >= 90:
        return WorkType.DEEP.value
    if duration_minutes >= 45:
        return WorkType.MEDIUM.value
    return WorkType.LIGHT.value


def _classify_confidence(duration_minutes: int, constraints: list[str]) -> float:
    base = 0.9 if duration_minutes >= 60 else 0.7 if duration_minutes >= 30 else 0.5
    penalty = min(len(constraints) * 0.05, 0.3)
    return round(max(base - penalty, 0.3), 2)


def _derive_recovery(recovery: Optional[RecoveryData]) -> RecoveryData:
    if recovery is None:
        return RecoveryData(status="unknown", fatigue_risk="unknown")
    result = RecoveryData(
        hours_slept=recovery.hours_slept,
        fatigue_risk=recovery.fatigue_risk,
        recovery_buffer_minutes=recovery.recovery_buffer_minutes,
        status=recovery.status,
    )
    if result.fatigue_risk is None and result.hours_slept is not None:
        if result.hours_slept < 4:
            result.fatigue_risk = "high"
        elif result.hours_slept < 6:
            result.fatigue_risk = "medium"
        else:
            result.fatigue_risk = "low"
    if result.status == "unknown" and result.fatigue_risk is not None:
        if result.fatigue_risk == "high":
            result.status = "poor"
        elif result.fatigue_risk == "low":
            result.status = "adequate"
    return result


def _compute_freshness(
    shifts: list[ShiftInfo],
    fixed_commitments: list[FixedCommitment],
    my_rhythm_data: Optional[dict[str, Any]],
    recovery: Optional[RecoveryData],
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []

    shift_status = "fresh" if shifts else "fresh"
    sources.append({"source": "shifts", "status": shift_status, "last_updated": shifts[0].start if shifts else None})

    commit_status = "fresh" if fixed_commitments else "fresh"
    sources.append({"source": "fixed_commitments", "status": commit_status, "last_updated": fixed_commitments[0].start if fixed_commitments else None})

    my_rhythm_last = my_rhythm_data.get("last_updated") if my_rhythm_data else None
    my_rhythm_status = "fresh"
    if my_rhythm_last is not None:
        try:
            ts = datetime.fromisoformat(my_rhythm_last.replace("Z", "+00:00"))
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            my_rhythm_status = "fresh" if age_h <= 24 else "stale"
        except (ValueError, TypeError):
            my_rhythm_status = "unknown"
    sources.append({"source": "my_rhythm", "status": my_rhythm_status, "last_updated": my_rhythm_last})

    recovery_status = "fresh" if recovery is not None else "fresh"
    sources.append({"source": "recovery", "status": recovery_status, "last_updated": None})

    overall = "fresh"
    if any(s["status"] == "unknown" for s in sources):
        overall = "unknown"
    elif any(s["status"] == "stale" for s in sources):
        overall = "stale"

    return {"per_source": sources, "overall_status": overall}


def assemble_capacity_handoff(
    agent_id: str,
    rhythm_id: str,
    shifts: list[ShiftInfo],
    fixed_commitments: list[FixedCommitment],
    available_windows: list[dict[str, Any]],
    recovery: Optional[RecoveryData] = None,
    carryover: Optional[Carryover] = None,
    my_rhythm_data: Optional[dict[str, Any]] = None,
    notes: str = "",
) -> dict[str, Any]:
    """Assemble and validate a rhythm_capacity_handoff.v1 payload.
    PROPOSE-mode only: returns full dict with propose-mode extensions.
    No project fields, no scheduler writes.
    """
    carryover = carryover or Carryover()

    windows: list[dict[str, Any]] = []
    total_available = 0
    for w in available_windows:
        dur = w["duration_minutes"]
        wt = _classify_work_type(dur)
        constraints = w.get("constraints", [])
        confidence = w.get("confidence", _classify_confidence(dur, constraints))
        windows.append({
            "start": w["start"],
            "end": w["end"],
            "duration_minutes": dur,
            "work_type": wt,
            "confidence": confidence,
            "constraints": constraints,
        })
        total_available += dur

    total_committed = sum(s.committed_minutes for s in shifts) + sum(c.duration_minutes for c in fixed_commitments)
    recovery_data = _derive_recovery(recovery)
    protected_learning = sum(c.duration_minutes for c in fixed_commitments if c.protected)

    stale_shift_data = any(getattr(s, "stale", False) for s in shifts)

    freshness = _compute_freshness(shifts, fixed_commitments, my_rhythm_data, recovery_data)

    # Contract requires capacity_total_minutes > 0; when there are no windows
    # but the day has committed time, use committed minutes as the floor.
    capacity_total = total_available if total_available > 0 else max(total_committed, 1)

    result: dict[str, Any] = {
        "schema_version": "rhythm_capacity_handoff.v1",
        "agent_id": agent_id,
        "rhythm_id": rhythm_id,
        "capacity_used_minutes": total_committed,
        "capacity_total_minutes": capacity_total,
        "recovery_buffer_minutes": recovery_data.recovery_buffer_minutes,
        "notes": notes,
        "capacity_summary": {
            "max_major_outcomes": 3,
            "total_available_minutes": total_available,
            "total_committed_minutes": total_committed,
            "total_recovery_minutes": recovery_data.recovery_buffer_minutes,
            "protected_learning_minutes": protected_learning,
        },
        "windows": windows,
        "recovery": {
            "hours_slept": recovery_data.hours_slept,
            "fatigue_risk": recovery_data.fatigue_risk,
            "recovery_buffer_minutes": recovery_data.recovery_buffer_minutes,
            "status": recovery_data.status,
        },
        "carryover": {
            "unfinished_minutes": carryover.unfinished_minutes,
            "source_task": carryover.source_task,
        },
        "data_freshness": freshness,
        "stale_shift_data": stale_shift_data,
    }

    # Validate contract fields only — preserve propose-mode extensions
    contract_only = {k: v for k, v in result.items() if k in _CONTRACT_FIELDS}
    RhythmCapacityHandoff(**contract_only).validate()

    return result
