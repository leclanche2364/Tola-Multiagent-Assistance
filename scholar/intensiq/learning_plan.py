"""
Batch S4 -- Versioned Learning Plan Service.
GET/PUT with optimistic concurrency via expected_previous_version.
Rejects calendar-time fields. Wrong creator rejected. Goal links preserved.
Plain ASCII. Python 3 stdlib only.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from scholar.intensiq.contracts import LearningPlan, validate_learning_plan


class LearningPlanService:
    """In-memory versioned learning-plan store with optimistic concurrency."""

    def __init__(self, clock: Optional[callable] = None) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._clock = clock or datetime.utcnow

    # ------------------------------------------------------------------ #
    #  GET
    # ------------------------------------------------------------------ #

    def get(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Return the current plan for *course_id*, or None if absent."""
        return self._store.get(course_id)

    # ------------------------------------------------------------------ #
    #  PUT
    # ------------------------------------------------------------------ #

    def put(
        self,
        course_id: str,
        plan_data: Dict[str, Any],
        creator: str = "scholar",
        now: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write or update a learning plan with optimistic concurrency.

        Raises ValueError on:
        - missing required fields
        - calendar-time fields present
        - created_by != creator
        - stale version (expected_previous_version does not match current)
        - version or expected_previous_version not positive/non-negative ints
        """
        resolved_now = now or self._clock().isoformat()

        # Deep-copy so the caller's dict is not mutated
        incoming = _deep_copy(plan_data)

        existing = self._store.get(course_id)

        # Validate caller input BEFORE service-level metadata injection.
        # This ensures bad caller-provided values (wrong creator, bad
        # version numbers, calendar fields, missing fields) are caught
        # before the service overwrites anything.
        validate_learning_plan(incoming, creator=creator)

        # Reject empty plan_id (genuine contract gap: plan_id must be a
        # non-empty identifier; validate_learning_plan checks presence but
        # not emptiness).
        if not incoming.get("plan_id") or not isinstance(incoming["plan_id"], str) or not incoming["plan_id"].strip():
            raise ValueError("plan_id must be a non-empty string")

        # Now apply service-level metadata on top of the validated input.
        # NOTE: course_id comes from the plan data itself (not the route param)
        # so the stored record preserves the caller's intended course_id.
        incoming["created_by"] = creator
        incoming["updated_at"] = resolved_now

        if existing is not None:
            # Optimistic-concurrency check: caller's EPV must match
            # the current stored version.
            caller_epv = incoming.get("expected_previous_version")
            if not isinstance(caller_epv, int) or caller_epv != existing["version"]:
                actual = caller_epv if isinstance(caller_epv, int) else type(caller_epv).__name__
                raise ValueError(
                    f"Stale plan: expected previous version {existing['version']}, "
                    f"got {actual}"
                )
            incoming["version"] = existing["version"] + 1
            incoming["expected_previous_version"] = existing["version"]
        else:
            incoming["version"] = 1
            incoming["expected_previous_version"] = 0

        # Preserve goal link across versions
        if existing is not None and "goal_id" in existing:
            incoming["goal_id"] = existing["goal_id"]

        self._store[course_id] = incoming
        return incoming


def _deep_copy(data: Any) -> Any:
    """Simple deep copy for dicts/lists without importing copy module."""
    if isinstance(data, dict):
        return {k: _deep_copy(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_deep_copy(v) for v in data]
    return data
