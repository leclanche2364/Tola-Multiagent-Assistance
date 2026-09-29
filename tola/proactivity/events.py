# Batch T24 -- Event-Driven Executive Proactivity
# events.py: WAKE_EVENTS, LOW_VALUE_EVENTS, handle_event, WakeDecision.

from dataclasses import dataclass, field
from typing import Any, Optional

WAKE_EVENTS = frozenset([
    "TASK_STALLED",
    "TASK_AT_RISK",
    "DELEGATION_FAILED",
    "EXPERIMENT_COMPLETED",
    "RHYTHM_OVERLOAD",
    "DEADLINE_RISK",
    "APPROVAL_REQUIRED",
    "PLAN_REJECTED",
    "USER_CORRECTION",
    "OUTCOME_FAILURE",
    "MATERIAL_METRIC_CHANGE",
])

LOW_VALUE_EVENTS = frozenset([
    "TASK_ACKNOWLEDGED",
    "AGENT_HEARTBEAT",
    "PROGRESS_NOTE",
    "DIGEST_TICK",
    "LOG_ROTATED",
])

AUTHORIZED_SOURCES = frozenset([
    "monitor",
    "rhythm",
    "specialist",
    "user",
    "system",
])

REQUIRED_FIELDS = ("event_id", "event_type", "source", "payload")


@dataclass(frozen=True)
class WakeDecision:
    event_id: str
    event_type: str
    source: str
    action: str
    followup: Optional[str] = None
    reason: Optional[str] = None


def _validate(event: dict) -> Optional[str]:
    if not isinstance(event, dict):
        return "not_a_dict"
    for f in REQUIRED_FIELDS:
        if f not in event:
            return f"missing_field:{f}"
    if event.get("source") not in AUTHORIZED_SOURCES:
        return f"unauthorized_source:{event.get('source')}"
    sig = event.get("signature")
    if sig is not None and sig == "":
        return "invalid_signature"
    return None


def handle_event(event: dict, seen_registry: Optional[dict] = None) -> Optional[WakeDecision]:
    reason = _validate(event)
    if reason is not None:
        decision = WakeDecision(
            event_id=event.get("event_id", "unknown"),
            event_type=event.get("event_type", "unknown"),
            source=event.get("source", "unknown"),
            action="REJECTED",
            reason=reason,
        )
        if seen_registry is not None:
            seen_registry[event_id] = decision
        return decision

    event_id = event["event_id"]
    event_type = event["event_type"]

    if seen_registry is not None and event_id in seen_registry:
        return seen_registry[event_id]

    if event_type in LOW_VALUE_EVENTS:
        return None

    if event_type not in WAKE_EVENTS:
        return None

    action = "WAKE"
    followup = None
    if event_type == "USER_CORRECTION":
        followup = "LEARNING_OBSERVATION"

    decision = WakeDecision(
        event_id=event_id,
        event_type=event_type,
        source=event["source"],
        action=action,
        followup=followup,
    )

    if seen_registry is not None:
        seen_registry[event_id] = decision

    return decision
