# Review engine for Batch T15.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

from typing import Any, Dict, List

from tola.decisions.register import DecisionRecord

KNOWN_TRIGGER_KINDS = frozenset((
    "HEALTH_LABEL",
    "METRIC_BELOW",
    "EVENT_OCCURRED",
))


def due_reviews(register: Dict[str, DecisionRecord], now_iso: str) -> List[DecisionRecord]:
    result = []
    for decision in register.values():
        if (
            decision.review_date is not None
            and not decision.is_superseded()
            and decision.review_date <= now_iso
        ):
            result.append(decision)
    result.sort(key=lambda d: d.review_date or "")
    return result


def check_revisit_triggers(
    register: Dict[str, DecisionRecord],
    context: Dict[str, Any],
) -> List[DecisionRecord]:
    result = []
    for decision in register.values():
        if decision.revisit_trigger is None or decision.is_superseded():
            continue
        trigger = decision.revisit_trigger
        kind = trigger.get("kind")
        if kind not in KNOWN_TRIGGER_KINDS:
            raise ValueError(f"Unknown trigger kind: {kind}")
        if _trigger_matches(trigger, context):
            result.append(decision)
    return result


def _trigger_matches(trigger: Dict[str, Any], context: Dict[str, Any]) -> bool:
    kind = trigger.get("kind")
    if kind == "HEALTH_LABEL":
        return (
            context.get("health_label") == trigger.get("equals")
            and context.get("project_id") == trigger.get("project_id")
        )
    if kind == "METRIC_BELOW":
        metric_name = trigger.get("name")
        threshold = trigger.get("threshold")
        metrics = context.get("metrics", {})
        value = metrics.get(metric_name)
        if value is None:
            return False
        try:
            return float(value) < float(threshold)
        except (TypeError, ValueError):
            return False
    if kind == "EVENT_OCCURRED":
        event_name = trigger.get("name")
        events = context.get("events", [])
        return event_name in events
    return False