"""Learning loop for Tola Daily Synthesis — Batch 10.

Captures per-brief execution outcomes, computes metrics, and produces
advisory trend summaries.  Summary is advisory input only — it never
auto-tunes capacity constants or governance limits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime, timezone

from agents.daily_synthesis.contracts import ValidationError


# ---------------------------------------------------------------------------
# Capacity constants — advisory only; summarise() must never mutate these
# ---------------------------------------------------------------------------

MAX_MAJOR_OUTCOMES: int = 3
DEFAULT_RECOVERY_BUFFER_MINUTES: int = 30
DEFAULT_CAPACITY_TOTAL_MINUTES: int = 240


class OutcomeStatus(str, Enum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Schema: planned-vs-completed record v1
# ---------------------------------------------------------------------------

@dataclass
class ExecutionRecord:
    """Per-outcome execution record for a single brief."""

    schema_version: str = "planned_vs_completed_record.v1"
    idempotency_key: str = field(default_factory=lambda: str(
        __import__("uuid").uuid5(
            __import__("uuid").UUID("b5a0e8a0-1a2b-3c4d-5e6f-7a8b9c0d1e2f"),
            "",
        )
    ))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    domain: str = ""
    planned_minutes: int = 0
    actual_minutes: int = 0
    status: str = "completed"  # completed | partial | skipped
    reason: str = ""
    fatigue_energy_predicted: str = "medium"
    fatigue_energy_actual: str = "medium"
    capacity_predicted_minutes: int = 0
    capacity_actual_available_minutes: int = 0

    REQUIRED = [
        "domain", "planned_minutes", "actual_minutes",
        "status", "fatigue_energy_predicted", "fatigue_energy_actual",
        "capacity_predicted_minutes", "capacity_actual_available_minutes",
    ]

    ENERGY_LEVELS = frozenset({"low", "medium", "high", "deep"})

    def validate(self) -> dict[str, Any]:
        d = self.__dict__
        _require_fields(d, self.REQUIRED, "planned_vs_completed_record.v1")
        _validate_schema_version(self.schema_version)
        _validate_timestamp(self.timestamp)
        if self.status not in {s.value for s in OutcomeStatus}:
            raise ValidationError(
                f"planned_vs_completed_record.v1: status must be one of "
                f"{[s.value for s in OutcomeStatus]}"
            )
        if self.planned_minutes < 0:
            raise ValidationError("planned_vs_completed_record.v1: planned_minutes must be >= 0")
        if self.actual_minutes < 0:
            raise ValidationError("planned_vs_completed_record.v1: actual_minutes must be >= 0")
        if self.fatigue_energy_predicted not in self.ENERGY_LEVELS:
            raise ValidationError(
                f"planned_vs_completed_record.v1: fatigue_energy_predicted must be one of {sorted(self.ENERGY_LEVELS)}"
            )
        if self.fatigue_energy_actual not in self.ENERGY_LEVELS:
            raise ValidationError(
                f"planned_vs_completed_record.v1: fatigue_energy_actual must be one of {sorted(self.ENERGY_LEVELS)}"
            )
        if self.capacity_predicted_minutes < 0:
            raise ValidationError("planned_vs_completed_record.v1: capacity_predicted_minutes must be >= 0")
        if self.capacity_actual_available_minutes < 0:
            raise ValidationError("planned_vs_completed_record.v1: capacity_actual_available_minutes must be >= 0")
        return d


# ---------------------------------------------------------------------------
# helpers (reuse contracts validators)
# ---------------------------------------------------------------------------

_SCHEMA_VERSIONS = frozenset({"planned_vs_completed_record.v1"})


def _validate_schema_version(value: str) -> str:
    if value not in _SCHEMA_VERSIONS:
        raise ValidationError(f"unknown schema_version: {value!r}")
    return value


def _validate_timestamp(value: str) -> str:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise ValidationError(f"invalid timestamp: {value!r}")
    return value


def _require_fields(data: dict[str, Any], required: list[str], ctx: str) -> None:
    missing = [f for f in required if data.get(f) is None]
    if missing:
        raise ValidationError(f"{ctx}: missing required fields: {', '.join(missing)}")


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

@dataclass
class BriefOutcome:
    """Per-brief computed metrics from execution records."""

    brief_date: str = ""
    completion_rate: float = 0.0
    estimation_error_minutes: int = 0
    partial_reasons: list[str] = field(default_factory=list)
    skip_reasons: list[str] = field(default_factory=list)
    fatigue_mismatches: list[str] = field(default_factory=list)
    capacity_predicted: int = 0
    capacity_actual_available: int = 0
    capacity_delta: int = 0


def record_outcome(
    brief: dict[str, Any],
    execution_records: list[dict[str, Any]],
    now: str,
) -> BriefOutcome:
    """Capture per-brief outcome metrics from caller-supplied execution records.

    Args:
        brief: The daily_command_brief.v1 dict that was executed.
        execution_records: List of dicts with keys:
            planned_minutes, actual_minutes, status (completed|partial|skipped),
            reason (required if not completed), fatigue_energy_actual.
        now: ISO timestamp of capture.

    Returns:
        BriefOutcome with computed metrics.
    """
    date_str = now[:10] if now else ""
    outcomes = brief.get("top_outcomes", [])
    total_planned = sum(o.get("estimated_minutes", 0) for o in outcomes)

    completed_count = 0
    total_actual = 0
    partial_reasons: list[str] = []
    skip_reasons: list[str] = []
    fatigue_mismatches: list[str] = []
    capacity_predicted = 0
    capacity_actual = 0

    for rec in execution_records:
        # Build and validate an ExecutionRecord
        record = ExecutionRecord(
            domain=rec.get("domain", ""),
            planned_minutes=rec.get("planned_minutes", 0),
            actual_minutes=rec.get("actual_minutes", 0),
            status=rec.get("status", "completed"),
            reason=rec.get("reason", ""),
            fatigue_energy_predicted=rec.get("fatigue_energy_predicted", "medium"),
            fatigue_energy_actual=rec.get("fatigue_energy_actual", "medium"),
            capacity_predicted_minutes=rec.get("capacity_predicted_minutes", 0),
            capacity_actual_available_minutes=rec.get("capacity_actual_available_minutes", 0),
        )
        record.validate()

        total_actual += record.actual_minutes

        if record.status == OutcomeStatus.COMPLETED.value:
            completed_count += 1
        elif record.status == OutcomeStatus.PARTIAL.value:
            partial_reasons.append(record.reason or "partial completion")
        elif record.status == OutcomeStatus.SKIPPED.value:
            skip_reasons.append(record.reason or "skipped")

        # Fatigue mismatch: predicted vs actual energy
        if record.fatigue_energy_predicted != record.fatigue_energy_actual:
            fatigue_mismatches.append(
                f"{record.domain}: predicted={record.fatigue_energy_predicted}, "
                f"actual={record.fatigue_energy_actual}"
            )

        capacity_predicted += record.capacity_predicted_minutes
        capacity_actual += record.capacity_actual_available_minutes

    completion_rate = (
        completed_count / len(execution_records) if execution_records else 0.0
    )

    return BriefOutcome(
        brief_date=date_str,
        completion_rate=round(completion_rate, 2),
        estimation_error_minutes=total_planned - total_actual,
        partial_reasons=partial_reasons,
        skip_reasons=skip_reasons,
        fatigue_mismatches=fatigue_mismatches,
        capacity_predicted=capacity_predicted,
        capacity_actual_available=capacity_actual,
        capacity_delta=capacity_predicted - capacity_actual,
    )


# ---------------------------------------------------------------------------
# Aggregation — advisory only, never auto-tunes capacity constants
# ---------------------------------------------------------------------------

@dataclass
class TrendSummary:
    """Advisory trend summary across multiple days of outcome records.

    This is advisory input only — it must never mutate capacity constants
    or governance limits.
    """

    avg_estimation_error_by_domain: dict[str, float] = field(default_factory=dict)
    most_common_skip_reasons: list[str] = field(default_factory=list)
    context_switch_overload_days: list[str] = field(default_factory=list)
    recovery_buffer_preserved: bool = True
    over_planning_frequency: float = 0.0
    under_planning_frequency: float = 0.0
    advisory_note: str = ""


def summarise(days: list[list[ExecutionRecord]]) -> TrendSummary:
    """Aggregate outcome records across stored days into an advisory trend summary.

    Args:
        days: List of days, each day being a list of ExecutionRecord instances.

    Returns:
        TrendSummary — advisory only.  Never mutates capacity constants.
    """
    if not days:
        return TrendSummary(advisory_note="No data available")

    # Flatten all records
    all_records: list[ExecutionRecord] = []
    for day in days:
        all_records.extend(day)

    if not all_records:
        return TrendSummary(advisory_note="No records to summarise")

    # Average estimation error by domain
    domain_errors: dict[str, list[int]] = {}
    for rec in all_records:
        error = rec.actual_minutes - rec.planned_minutes
        domain_errors.setdefault(rec.domain, []).append(error)

    avg_estimation_error_by_domain: dict[str, float] = {}
    for domain, errors in domain_errors.items():
        avg_estimation_error_by_domain[domain] = round(
            sum(errors) / len(errors), 2
        )

    # Most common skip reasons
    skip_reasons: list[str] = []
    for rec in all_records:
        if rec.status == OutcomeStatus.SKIPPED.value and rec.reason:
            skip_reasons.append(rec.reason)

    from collections import Counter
    skip_counter = Counter(skip_reasons)
    most_common_skip_reasons = [
        reason for reason, _ in skip_counter.most_common(3)
    ]

    # Context-switch overload days: days where planned > actual capacity
    # and more than 3 outcomes were planned (proxy for context-switch cost)
    context_switch_overload_days: list[str] = []
    for day in days:
        if not day:
            continue
        total_planned = sum(r.planned_minutes for r in day)
        total_actual = sum(r.actual_minutes for r in day)
        # Overload: planned significantly more than actual (estimation error > 30%)
        if total_planned > 0 and total_actual < total_planned * 0.7:
            # Use first record's timestamp for date
            date_hint = day[0].timestamp[:10] if day[0].timestamp else "unknown"
            context_switch_overload_days.append(date_hint)

    # Recovery buffer preserved or eaten
    # Check if actual available capacity stayed above recovery buffer
    recovery_preserved = True
    for rec in all_records:
        if rec.capacity_actual_available_minutes < DEFAULT_RECOVERY_BUFFER_MINUTES:
            recovery_preserved = False
            break

    # Over/under planning frequency
    over_count = 0
    under_count = 0
    for rec in all_records:
        if rec.status == OutcomeStatus.COMPLETED.value:
            if rec.actual_minutes > rec.planned_minutes:
                over_count += 1
            elif rec.actual_minutes < rec.planned_minutes:
                under_count += 1

    total_completed = sum(
        1 for r in all_records if r.status == OutcomeStatus.COMPLETED.value
    )
    over_planning_frequency = round(over_count / max(total_completed, 1), 2)
    under_planning_frequency = round(under_count / max(total_completed, 1), 2)

    return TrendSummary(
        avg_estimation_error_by_domain=avg_estimation_error_by_domain,
        most_common_skip_reasons=most_common_skip_reasons,
        context_switch_overload_days=context_switch_overload_days,
        recovery_buffer_preserved=recovery_preserved,
        over_planning_frequency=over_planning_frequency,
        under_planning_frequency=under_planning_frequency,
        advisory_note=(
            "Summary is advisory input only.  Capacity constants "
            "(MAX_MAJOR_OUTCOMES, DEFAULT_RECOVERY_BUFFER_MINUTES, "
            "DEFAULT_CAPACITY_TOTAL_MINUTES) are unchanged."
        ),
    )
