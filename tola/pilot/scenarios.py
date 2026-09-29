# Batch T30 -- Controlled Tola Pilot scenarios.
# Plain ASCII. Stdlib only. Deterministic frozen scenario dicts.

from __future__ import annotations

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

PILOT_VERSION = "T30.0.0"

# ---------------------------------------------------------------------------
# 15 tracked metric constants (named, matching QA T30)
# ---------------------------------------------------------------------------

METRIC_DELEGATION_ACCURACY = "delegation_accuracy"
METRIC_FIRST_PASS_COMPLETION = "first_pass_completion"
METRIC_PARTIAL_RATE = "partial_rate"
METRIC_BLOCKED_RATE = "blocked_rate"
METRIC_STALLED_RECOVERY = "stalled_recovery"
METRIC_INCORRECT_ESCALATION = "incorrect_escalation"
METRIC_MISSED_MATERIAL_EVENTS = "missed_material_events"
METRIC_USER_CORRECTION_RATE = "user_correction_rate"
METRIC_PLAN_REVISION_RATE = "plan_revision_rate"
METRIC_BRIEFING_USEFULNESS = "briefing_usefulness"
METRIC_NOTIFICATION_NOISE = "notification_noise"
METRIC_PREFERENCE_ACCURACY = "preference_accuracy"
METRIC_PROPOSAL_QUALITY = "proposal_quality"
METRIC_COST = "cost"
METRIC_LATENCY = "latency"

ALL_METRICS = frozenset([
    METRIC_DELEGATION_ACCURACY,
    METRIC_FIRST_PASS_COMPLETION,
    METRIC_PARTIAL_RATE,
    METRIC_BLOCKED_RATE,
    METRIC_STALLED_RECOVERY,
    METRIC_INCORRECT_ESCALATION,
    METRIC_MISSED_MATERIAL_EVENTS,
    METRIC_USER_CORRECTION_RATE,
    METRIC_PLAN_REVISION_RATE,
    METRIC_BRIEFING_USEFULNESS,
    METRIC_NOTIFICATION_NOISE,
    METRIC_PREFERENCE_ACCURACY,
    METRIC_PROPOSAL_QUALITY,
    METRIC_COST,
    METRIC_LATENCY,
])

# ---------------------------------------------------------------------------
# Critical metrics (authority / integrity / privacy)
# ---------------------------------------------------------------------------

CRITICAL_METRICS = frozenset([
    METRIC_INCORRECT_ESCALATION,
    METRIC_MISSED_MATERIAL_EVENTS,
    METRIC_USER_CORRECTION_RATE,
    METRIC_PLAN_REVISION_RATE,
    METRIC_PREFERENCE_ACCURACY,
])

# ---------------------------------------------------------------------------
# Scenario fixtures
# ---------------------------------------------------------------------------

NOW_ISO = "2026-09-29T12:00:00"


def _make_proposal(
    tags=None,
    goal_refs=None,
    expected_value=0.8,
    evidence="",
    smallest_viable_version="",
    ambiguous=False,
    consequential=False,
    dependencies=None,
    displaces=None,
    stop_condition="",
    revisit_trigger="",
    priority="normal",
):
    p: dict = {"tags": tags or [], "goal_refs": goal_refs or []}
    if expected_value != 0.8:
        p["expected_value"] = expected_value
    if evidence:
        p["evidence"] = evidence
    if smallest_viable_version:
        p["smallest_viable_version"] = smallest_viable_version
    if ambiguous:
        p["ambiguous"] = True
    if consequential:
        p["consequential"] = True
    if dependencies:
        p["dependencies"] = dependencies
    if displaces:
        p["displaces"] = displaces
    if stop_condition:
        p["stop_condition"] = stop_condition
    if revisit_trigger:
        p["revisit_trigger"] = revisit_trigger
    if priority != "normal":
        p["priority"] = priority
    return p


def _make_context(
    active_goals=None,
    capacity_summary=None,
    available_dependencies=None,
    current_priorities=None,
    committed_work=None,
    evidence="",
    expected_value_score=0.8,
):
    c: dict = {}
    if active_goals is not None:
        c["active_goals"] = active_goals
    if capacity_summary is not None:
        c["capacity_summary"] = capacity_summary
    if available_dependencies is not None:
        c["available_dependencies"] = available_dependencies
    if current_priorities is not None:
        c["current_priorities"] = current_priorities
    if committed_work is not None:
        c["committed_work"] = committed_work
    if evidence:
        c["evidence"] = evidence
    if expected_value_score != 0.8:
        c["expected_value_score"] = expected_value_score
    return c


# ===========================================================================
# Scenario 1: MULTI_PROJECT -- multiple active projects with varying priority
# ===========================================================================

SCENARIO_MULTI_PROJECT = {
    "id": "MULTI_PROJECT",
    "name": "Multiple Active Projects",
    "inputs": {
        "proposals": [
            _make_proposal(
                tags=["growth"],
                goal_refs=["g1"],
                expected_value=0.9,
                evidence="revenue impact",
                priority="high",
            ),
            _make_proposal(
                tags=["maintenance"],
                goal_refs=["g2"],
                expected_value=0.5,
                evidence="preventive",
                priority="normal",
            ),
            _make_proposal(
                tags=["research"],
                goal_refs=["g3"],
                expected_value=0.3,
                evidence="exploratory",
                priority="low",
            ),
        ],
        "context": _make_context(
            active_goals=[
                {"id": "g1", "name": "Growth Sprint", "tags": ["growth"]},
                {"id": "g2", "name": "Platform Health", "tags": ["maintenance"]},
            ],
            capacity_summary={"remaining_capacity": 2, "active_tasks": 1, "max_parallel_tasks": 4},
            current_priorities=["g1"],
        ),
    },
    "expected": {
        "evaluator_decision": "START",
        "first_proposal_verdict": "START",
        "second_proposal_verdict": "DEFER",
        "third_proposal_verdict": "STOP",
        "num_started": 1,
        "num_deferred": 1,
        "num_stopped": 1,
    },
}

# ===========================================================================
# Scenario 2: CAPACITY_CONFLICT -- capacity conflict blocks START
# ===========================================================================

SCENARIO_CAPACITY_CONFLICT = {
    "id": "CAPACITY_CONFLICT",
    "name": "Capacity Conflict",
    "inputs": {
        "proposals": [
            _make_proposal(
                tags=["growth"],
                goal_refs=["g1"],
                expected_value=0.85,
                evidence="high value",
                priority="high",
            ),
        ],
        "context": _make_context(
            active_goals=[
                {"id": "g1", "name": "Growth Sprint", "tags": ["growth"]},
            ],
            capacity_summary={"remaining_capacity": 0, "active_tasks": 4, "max_parallel_tasks": 4},
            current_priorities=["g1"],
        ),
    },
    "expected": {
        "evaluator_decision": "DEFER",
        "verdict": "DEFER",
        "reason_contains": "capacity",
    },
}

# ===========================================================================
# Scenario 3: PLAN_CRITIQUE -- specialist plan critique via scope evaluator
# ===========================================================================

SCENARIO_PLAN_CRITIQUE = {
    "id": "PLAN_CRITIQUE",
    "name": "Specialist Plan Critique",
    "inputs": {
        "proposals": [
            _make_proposal(
                tags=["growth"],
                goal_refs=["g1"],
                expected_value=0.6,
                evidence="medium evidence",
                priority="medium",
            ),
            _make_proposal(
                tags=["growth"],
                goal_refs=["g1"],
                expected_value=0.9,
                evidence="strong evidence",
                smallest_viable_version="Reduce to MVP slice",
                priority="high",
            ),
        ],
        "context": _make_context(
            active_goals=[
                {"id": "g1", "name": "Growth Sprint", "tags": ["growth"]},
            ],
            capacity_summary={"remaining_capacity": 1, "active_tasks": 2, "max_parallel_tasks": 4},
            current_priorities=["g1"],
        ),
    },
    "expected": {
        "first_verdict": "START",
        "second_verdict": "SHAPE_SMALLER",
        "critique_detected": True,
        "shape_smaller_reason": "smallest_viable_version",
    },
}

# ===========================================================================
# Scenario 4: STALLED_TASK -- stalled task detection via reconciliation
# ===========================================================================

SCENARIO_STALLED_TASK = {
    "id": "STALLED_TASK",
    "name": "Stalled Task",
    "inputs": {
        "reconciliation_state": {
            "previous_snapshot": {},
            "current_snapshot": {
                "active_tasks": [
                    {"id": "t1", "status": "stalled", "label": "Write report"},
                ],
                "blocked_tasks": [],
                "risks": [],
                "pending_decisions": [],
                "deadlines": [],
                "material_metrics": [],
                "capacity_summary": {},
            },
            "last_seen": {"t1": "active"},
            "processed_events": set(),
            "reference_date": "2026-09-29",
        },
    },
    "expected": {
        "reconciliation_action": "FOLLOW_UP",
        "stalled_task_id": "t1",
        "recovery_triggered": True,
    },
}

# ===========================================================================
# Scenario 5: PARTIAL_OUTPUT -- partial specialist output (incomplete result)
# ===========================================================================

SCENARIO_PARTIAL_OUTPUT = {
    "id": "PARTIAL_OUTPUT",
    "name": "Partial Specialist Output",
    "inputs": {
        "proposals": [
            _make_proposal(
                tags=["growth"],
                goal_refs=["g1"],
                expected_value=0.5,
                evidence="partial evidence",
                priority="medium",
            ),
        ],
        "context": _make_context(
            active_goals=[
                {"id": "g1", "name": "Growth Sprint", "tags": ["growth"]},
            ],
            capacity_summary={"remaining_capacity": 1, "active_tasks": 1, "max_parallel_tasks": 4},
            current_priorities=["g1"],
        ),
        "specialist_result": {
            "complete": False,
            "sections_done": ["analysis"],
            "sections_missing": ["recommendation", "next_steps"],
            "status": "partial",
        },
    },
    "expected": {
        "verdict": "START",
        "partial_detected": True,
        "incomplete_result_closed": False,
    },
}

# ===========================================================================
# Scenario 6: USER_CORRECTION -- user correction triggers learning observation
# ===========================================================================

SCENARIO_USER_CORRECTION = {
    "id": "USER_CORRECTION",
    "name": "User Correction",
    "inputs": {
        "events": [
            {
                "event_id": "uc-1",
                "event_type": "USER_CORRECTION",
                "source": "user",
                "payload": {"correction": "wrong delegation", "target": "specialist"},
            },
        ],
    },
    "expected": {
        "wakeup_action": "WAKE",
        "followup": "LEARNING_OBSERVATION",
        "correction_rate_increments": 1,
    },
}

# ===========================================================================
# Scenario 7: EXPLICIT_PREFERENCE -- explicit user preference
# ===========================================================================

SCENARIO_EXPLICIT_PREFERENCE = {
    "id": "EXPLICIT_PREFERENCE",
    "name": "Explicit Preference",
    "inputs": {
        "observations": [
            {
                "id": "obs-1",
                "kind": "EXPLICIT_PREFERENCE",
                "subject": "communication_style",
                "key": "communication_style",
                "value": "concise",
                "direction": "positive",
                "evidence_refs": ("user_feedback_1",),
                "observed_at": "2026-09-29T12:00:00",
                "project_id": "p1",
                "confidence": 0.95,
            },
        ],
    },
    "expected": {
        "preference_promoted": False,
        "preference_blocked": False,
        "sensitive_blocked": False,
        "observations_kept": 1,
    },
}

# ===========================================================================
# Scenario 8: REPEATED_INFERRED_PREFERENCE -- repeated inferred preference
# ===========================================================================

SCENARIO_REPEATED_INFERRED_PREFERENCE = {
    "id": "REPEATED_INFERRED_PREFERENCE",
    "name": "Repeated Inferred Preference",
    "inputs": {
        "observations": [
            {
                "id": f"obs-{i}",
                "kind": "BEHAVIOURAL_OBSERVATION",
                "subject": "communication_style",
                "key": "communication_style",
                "value": "concise",
                "direction": "positive",
                "evidence_refs": (f"evidence_{i}",),
                "observed_at": "2026-09-29T12:00:00",
                "project_id": "p1",
                "confidence": 0.8,
            }
            for i in range(5)
        ],
    },
    "expected": {
        "preference_promoted": True,
        "preference_blocked": False,
        "sensitive_blocked": False,
        "observations_kept": 5,
        "promotion_count": 1,
    },
}

# ===========================================================================
# Scenario 9: MATERIAL_EVENT -- material event triggers heartbeat wake
# ===========================================================================

SCENARIO_MATERIAL_EVENT = {
    "id": "MATERIAL_EVENT",
    "name": "Material Event",
    "inputs": {
        "conditions": [
            {
                "kind": "OVERDUE_TASK",
                "id": "ot-1",
                "severity": "high",
                "material": True,
                "age_days": -1,
            },
        ],
        "event": {
            "event_id": "me-1",
            "event_type": "TASK_STALLED",
            "source": "monitor",
            "payload": {"task_id": "ot-1"},
        },
    },
    "expected": {
        "heartbeat_wake": True,
        "wakeup_action": "WAKE",
        "material_event_detected": True,
        "notification_noise": 0,
    },
}

# ===========================================================================
# Scenario 10: QUIET_HEARTBEAT -- quiet heartbeat with no material events
# ===========================================================================

SCENARIO_QUIET_HEARTBEAT = {
    "id": "QUIET_HEARTBEAT",
    "name": "Quiet Heartbeat",
    "inputs": {
        "conditions": [
            {
                "kind": "INFO",
                "id": "info-1",
                "severity": "low",
                "material": False,
                "age_days": 1,
            },
        ],
        "event": {
            "event_id": "hb-1",
            "event_type": "AGENT_HEARTBEAT",
            "source": "system",
            "payload": {"agent": "specialist-1"},
        },
    },
    "expected": {
        "heartbeat_wake": False,
        "wakeup_action": None,
        "notification_noise": 0,
        "cost_units": 1,
    },
}

# ===========================================================================
# Scenario 11: WEEKLY_REVIEW -- weekly executive review with briefing
# ===========================================================================

SCENARIO_WEEKLY_REVIEW = {
    "id": "WEEKLY_REVIEW",
    "name": "Weekly Review",
    "inputs": {
        "review_inputs": {
            "projects": [
                {
                    "id": "p1",
                    "name": "Growth Initiative",
                    "status": "active",
                    "deadline": "2026-10-15",
                    "risk": "medium",
                    "blocked_by": [],
                },
                {
                    "id": "p2",
                    "name": "Stalled Project",
                    "status": "stalled",
                    "deadline": "2026-10-01",
                    "risk": "high",
                    "blocked_by": ["p3"],
                },
            ],
            "capacity": {"load": 80, "overload": False},
            "growth_opportunities": [
                {
                    "id": "go1",
                    "name": "New Market Entry",
                    "impact": "high",
                    "material": True,
                    "evidence": "market data",
                },
            ],
            "scholar_obligations": [
                {
                    "id": "so1",
                    "name": "Scholar Review",
                    "due_date": "2026-10-05",
                    "requirement": "submit paper",
                },
            ],
            "stalled": [
                {"id": "t1", "label": "Write report", "status": "stalled", "owner": "alice"},
            ],
            "experiments": [],
            "decisions": [],
            "risks": [
                {"id": "r1", "label": "Budget risk", "status": "new", "severity": "high"},
            ],
            "deferred": [],
        },
    },
    "expected": {
        "review_has_priorities": True,
        "briefing_lines_gt_0": True,
        "stalled_surfaced": True,
        "growth_incorporated": True,
        "scholar_deadline_detected": True,
    },
}

# ===========================================================================
# Scenario 12: IMPROVEMENT_PROPOSAL -- improvement proposal via weekly review
# ===========================================================================

SCENARIO_IMPROVEMENT_PROPOSAL = {
    "id": "IMPROVEMENT_PROPOSAL",
    "name": "Improvement Proposal",
    "inputs": {
        "observations": [
            {
                "id": f"obs-{i}",
                "kind": "DELEGATION_WEAKNESS",
                "subject": "specialist_selection",
                "evidence_refs": (f"evidence_{i}",),
                "category": "delegation:specialist_selection",
            }
            for i in range(3)
        ],
    },
    "expected": {
        "proposals_generated": True,
        "proposal_count_gt_0": True,
        "proposal_status": "CANDIDATE",
        "observations_kept": 3,
    },
}

# ===========================================================================
# Ordered tuple of all scenarios (deterministic, frozen structure)
# ===========================================================================

PILOT_SCENARIOS = (
    SCENARIO_MULTI_PROJECT,
    SCENARIO_CAPACITY_CONFLICT,
    SCENARIO_PLAN_CRITIQUE,
    SCENARIO_STALLED_TASK,
    SCENARIO_PARTIAL_OUTPUT,
    SCENARIO_USER_CORRECTION,
    SCENARIO_EXPLICIT_PREFERENCE,
    SCENARIO_REPEATED_INFERRED_PREFERENCE,
    SCENARIO_MATERIAL_EVENT,
    SCENARIO_QUIET_HEARTBEAT,
    SCENARIO_WEEKLY_REVIEW,
    SCENARIO_IMPROVEMENT_PROPOSAL,
)

# Ensure tuple is frozen (no mutation possible via construction)
_PILOT_SCENARIOS = PILOT_SCENARIOS