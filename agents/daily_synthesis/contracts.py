"""Daily Synthesis v1.2 schema contracts.

Pydantic-style validators built on dataclasses + explicit validation.
No external deps beyond stdlib. Credentials passed by caller only.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class ValidationError(ValueError):
    """Raised when a payload fails schema validation."""


class ConflictResolution(Enum):
    LATEST_WINS = "latest_wins"
    KEEP_HISTORY = "keep_history"


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

_SCHEMA_VERSIONS = frozenset({
    "rhythm_capacity_handoff.v1",
    "scholar_handoff.v1",
    "growth_handoff.v1",
    "project_status_handoff.v1",
    "daily_command_brief.v1",
    "rhythm_schedule_conflict.v1",
    "daily_plan_to_rhythm.v1",
})

_GENERIC_STUDY_RE = re.compile(
    r"^\s*(study CCRN3|do assignment|read an article)\s*$", re.IGNORECASE
)


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
# rhythm_capacity_handoff.v1  — capacity only, no project fields, recovery buffer required
# ---------------------------------------------------------------------------

@dataclass
class RhythmCapacityHandoff:
    schema_version: str = "rhythm_capacity_handoff.v1"
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_id: Optional[str] = None
    rhythm_id: Optional[str] = None
    capacity_used_minutes: Optional[int] = None
    capacity_total_minutes: Optional[int] = None
    recovery_buffer_minutes: Optional[int] = None
    notes: str = ""

    REQUIRED = ["agent_id", "rhythm_id", "capacity_used_minutes", "capacity_total_minutes", "recovery_buffer_minutes"]

    def validate(self) -> dict[str, Any]:
        d = self.__dict__
        _require_fields(d, self.REQUIRED, "rhythm_capacity_handoff.v1")
        _validate_schema_version(self.schema_version)
        _validate_timestamp(self.timestamp)
        if self.capacity_used_minutes < 0 or self.capacity_total_minutes <= 0:
            raise ValidationError("rhythm_capacity_handoff.v1: capacity minutes must be non-negative and total > 0")
        if self.recovery_buffer_minutes < 0:
            raise ValidationError("rhythm_capacity_handoff.v1: recovery_buffer_minutes is required and must be >= 0")
        for disallowed in ("project_id", "project_name", "project_status"):
            if disallowed in d and d[disallowed] is not None:
                raise ValidationError(f"rhythm_capacity_handoff.v1: project field '{disallowed}' not allowed")
        return d


# ---------------------------------------------------------------------------
# scholar_handoff.v1  — rejects generic learning tasks
# ---------------------------------------------------------------------------

@dataclass
class ScholarHandoff:
    schema_version: str = "scholar_handoff.v1"
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_id: Optional[str] = None
    current_batch_id: Optional[str] = None
    exact_action: Optional[str] = None
    estimated_minutes: Optional[int] = None
    definition_of_done: Optional[str] = None
    reading_target: Optional[dict[str, Any]] = None
    source_refs: list[str] = field(default_factory=list)

    REQUIRED = ["agent_id", "current_batch_id", "exact_action", "estimated_minutes", "definition_of_done"]

    def validate(self) -> dict[str, Any]:
        d = self.__dict__
        _require_fields(d, self.REQUIRED, "scholar_handoff.v1")
        _validate_schema_version(self.schema_version)
        _validate_timestamp(self.timestamp)
        if self.estimated_minutes <= 0:
            raise ValidationError("scholar_handoff.v1: estimated_minutes must be > 0")
        if _GENERIC_STUDY_RE.match(self.exact_action):
            raise ValidationError(
                f"scholar_handoff.v1: generic learning task rejected: {self.exact_action!r}. "
                "Provide a named article/section."
            )
        if self.reading_target is not None:
            if not isinstance(self.reading_target, dict):
                raise ValidationError("scholar_handoff.v1: reading_target must be a dict")
            if self.reading_target.get("required") is True:
                _require_fields(
                    self.reading_target,
                    ["article_title", "exact_sections_to_read", "extraction_goal"],
                    "scholar_handoff.v1 reading_target",
                )
        return d


# ---------------------------------------------------------------------------
# growth_handoff.v1
# ---------------------------------------------------------------------------

@dataclass
class GrowthHandoff:
    schema_version: str = "growth_handoff.v1"
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_id: Optional[str] = None
    project_id: Optional[str] = None
    action: Optional[str] = None
    estimated_minutes: Optional[int] = None
    definition_of_done: Optional[str] = None
    source_refs: list[str] = field(default_factory=list)

    REQUIRED = ["agent_id", "project_id", "action", "estimated_minutes", "definition_of_done"]

    def validate(self) -> dict[str, Any]:
        d = self.__dict__
        _require_fields(d, self.REQUIRED, "growth_handoff.v1")
        _validate_schema_version(self.schema_version)
        _validate_timestamp(self.timestamp)
        if self.estimated_minutes <= 0:
            raise ValidationError("growth_handoff.v1: estimated_minutes must be > 0")
        return d


# ---------------------------------------------------------------------------
# project_status_handoff.v1
# ---------------------------------------------------------------------------

@dataclass
class ProjectStatusHandoff:
    schema_version: str = "project_status_handoff.v1"
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_id: Optional[str] = None
    project_id: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    next_action: Optional[str] = None

    REQUIRED = ["agent_id", "project_id", "status", "summary", "next_action"]

    def validate(self) -> dict[str, Any]:
        d = self.__dict__
        _require_fields(d, self.REQUIRED, "project_status_handoff.v1")
        _validate_schema_version(self.schema_version)
        _validate_timestamp(self.timestamp)
        return d


# ---------------------------------------------------------------------------
# daily_command_brief.v1  — top_outcomes 0-3, not_today allowed, capacity + buffer required
# ---------------------------------------------------------------------------

@dataclass
class DailyCommandBrief:
    schema_version: str = "daily_command_brief.v1"
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_id: Optional[str] = None
    date: Optional[str] = None
    top_outcomes: Optional[list[dict[str, Any]]] = None
    not_today: list[str] = field(default_factory=list)
    capacity_used_minutes: Optional[int] = None
    buffer_minutes: Optional[int] = None
    notes: str = ""

    REQUIRED = ["agent_id", "date", "top_outcomes", "capacity_used_minutes", "buffer_minutes"]

    def validate(self) -> dict[str, Any]:
        d = self.__dict__
        _require_fields(d, self.REQUIRED, "daily_command_brief.v1")
        _validate_schema_version(self.schema_version)
        _validate_timestamp(self.timestamp)
        if len(self.top_outcomes) > 3:
            raise ValidationError("daily_command_brief.v1: top_outcomes must have 0-3 items")
        for i, outcome in enumerate(self.top_outcomes):
            if not isinstance(outcome, dict):
                raise ValidationError(f"daily_command_brief.v1: top_outcomes[{i}] must be a dict")
            _require_fields(outcome, ["definition_of_done", "source_refs"], f"daily_command_brief.v1 top_outcomes[{i}]")
        if self.capacity_used_minutes < 0 or self.buffer_minutes < 0:
            raise ValidationError("daily_command_brief.v1: capacity_used and buffer minutes must be >= 0")
        return d


# ---------------------------------------------------------------------------
# rhythm_schedule_conflict.v1
# ---------------------------------------------------------------------------

class ConflictReason(str, Enum):
    OVERLAP = "overlap"
    CAPACITY_EXCEEDED = "capacity_exceeded"
    DEPENDENCY_BLOCKED = "dependency_blocked"
    PRIORITY_COLLISION = "priority_collision"
    UNKNOWN = "unknown"


@dataclass
class RhythmScheduleConflict:
    schema_version: str = "rhythm_schedule_conflict.v1"
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_id: Optional[str] = None
    outcome_id: Optional[str] = None
    reason: Optional[str] = None
    required_minutes: Optional[int] = None
    available_minutes: Optional[int] = None
    possible_alternatives: list[str] = field(default_factory=list)

    REQUIRED = ["agent_id", "outcome_id", "reason", "required_minutes", "available_minutes"]

    def validate(self) -> dict[str, Any]:
        d = self.__dict__
        _require_fields(d, self.REQUIRED, "rhythm_schedule_conflict.v1")
        _validate_schema_version(self.schema_version)
        _validate_timestamp(self.timestamp)
        if self.reason not in {r.value for r in ConflictReason}:
            raise ValidationError(f"rhythm_schedule_conflict.v1: reason must be one of {[r.value for r in ConflictReason]}")
        if self.required_minutes < 0 or self.available_minutes < 0:
            raise ValidationError("rhythm_schedule_conflict.v1: minutes must be >= 0")
        return d


# ---------------------------------------------------------------------------
# daily_plan_to_rhythm.v1  — carries exact learning detail unchanged
# ---------------------------------------------------------------------------

@dataclass
class DailyPlanToRhythm:
    schema_version: str = "daily_plan_to_rhythm.v1"
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_id: Optional[str] = None
    plan_id: Optional[str] = None
    rhythm_id: Optional[str] = None
    learning_detail: Optional[dict[str, Any]] = None
    schedule_slots: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""

    REQUIRED = ["agent_id", "plan_id", "rhythm_id", "learning_detail"]

    def validate(self) -> dict[str, Any]:
        d = self.__dict__
        _require_fields(d, self.REQUIRED, "daily_plan_to_rhythm.v1")
        _validate_schema_version(self.schema_version)
        _validate_timestamp(self.timestamp)
        if not isinstance(self.learning_detail, dict):
            raise ValidationError("daily_plan_to_rhythm.v1: learning_detail must be a dict")
        return d


# ---------------------------------------------------------------------------
# registry & duplicate/version handling
# ---------------------------------------------------------------------------

SCHEMA_REGISTRY: dict[str, type] = {
    "rhythm_capacity_handoff.v1": RhythmCapacityHandoff,
    "scholar_handoff.v1": ScholarHandoff,
    "growth_handoff.v1": GrowthHandoff,
    "project_status_handoff.v1": ProjectStatusHandoff,
    "daily_command_brief.v1": DailyCommandBrief,
    "rhythm_schedule_conflict.v1": RhythmScheduleConflict,
    "daily_plan_to_rhythm.v1": DailyPlanToRhythm,
}


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a payload against its schema_version. Returns validated dict."""
    version = payload.get("schema_version")
    if not version:
        raise ValidationError("missing schema_version")
    cls = SCHEMA_REGISTRY.get(version)
    if cls is None:
        raise ValidationError(f"unknown schema_version: {version!r}")
    instance = cls(**{k: v for k, v in payload.items() if k in cls.__dataclass_fields__})
    return instance.validate()


def handle_duplicate(
    existing: dict[str, Any], incoming: dict[str, Any], strategy: str = "latest_wins"
) -> dict[str, Any]:
    """Duplicate/version handling: latest valid wins, older kept as history."""
    strategy_enum = ConflictResolution(strategy) if strategy in {"latest_wins", "keep_history"} else ConflictResolution.LATEST_WINS
    incoming_ts = incoming.get("timestamp", "")
    existing_ts = existing.get("timestamp", "")
    if strategy_enum == ConflictResolution.LATEST_WINS:
        if incoming_ts >= existing_ts:
            return {"action": "replace", "record": incoming}
        return {"action": "keep_existing", "record": existing}
    return {"action": "keep_both", "existing": existing, "incoming": incoming}
