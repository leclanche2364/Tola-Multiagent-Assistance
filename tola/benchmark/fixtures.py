"""Fixture builders for Batch T22 -- Improvement Benchmark Harness.

Each builder returns a fresh dict spec (id, name, scenario params,
expected signals). Fixtures are pure data, deterministic, no execution.

score_run(fixture, observed) -> FixtureScore compares observed dict
against expected signals using TOLERANCE for float comparisons.

Plain ASCII. Stdlib only. No I/O. No clock reads.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BENCHMARK_VERSION = "1.0.0"
TOLERANCE = 0.01

# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

FIXTURE_BUILDERS = {}  # name -> builder function


def _register(name: str):
    def decorator(fn):
        FIXTURE_BUILDERS[name] = fn
        return fn
    return decorator


@_register("simple delegation")
def simple_delegation() -> dict[str, Any]:
    return {
        "id": "fixture-01",
        "name": "simple delegation",
        "params": {"agents": 1, "tasks": 1, "ambiguity": 0.0, "capacity": 1.0},
        "expected": {
            "task_success": True,
            "delegation_correct": True,
            "criteria_completeness": 1.0,
            "escalation_correct": False,
            "plan_quality": 0.95,
            "tool_calls": 3,
            "token_cost": 1200,
            "latency_ms": 45,
            "human_correction": 0,
        },
    }


@_register("multi-agent task")
def multi_agent_task() -> dict[str, Any]:
    return {
        "id": "fixture-02",
        "name": "multi-agent task",
        "params": {"agents": 3, "tasks": 5, "ambiguity": 0.2, "capacity": 0.8},
        "expected": {
            "task_success": True,
            "delegation_correct": True,
            "criteria_completeness": 0.92,
            "escalation_correct": False,
            "plan_quality": 0.88,
            "tool_calls": 12,
            "token_cost": 4500,
            "latency_ms": 180,
            "human_correction": 0,
        },
    }


@_register("ambiguous ownership")
def ambiguous_ownership() -> dict[str, Any]:
    return {
        "id": "fixture-03",
        "name": "ambiguous ownership",
        "params": {"agents": 2, "tasks": 1, "ambiguity": 0.9, "capacity": 1.0},
        "expected": {
            "task_success": False,
            "delegation_correct": False,
            "criteria_completeness": 0.40,
            "escalation_correct": True,
            "plan_quality": 0.50,
            "tool_calls": 5,
            "token_cost": 2100,
            "latency_ms": 90,
            "human_correction": 1,
        },
    }


@_register("capacity-limited task")
def capacity_limited_task() -> dict[str, Any]:
    return {
        "id": "fixture-04",
        "name": "capacity-limited task",
        "params": {"agents": 1, "tasks": 3, "ambiguity": 0.1, "capacity": 0.3},
        "expected": {
            "task_success": False,
            "delegation_correct": True,
            "criteria_completeness": 0.55,
            "escalation_correct": True,
            "plan_quality": 0.60,
            "tool_calls": 7,
            "token_cost": 2800,
            "latency_ms": 110,
            "human_correction": 1,
        },
    }


@_register("blocked specialist")
def blocked_specialist() -> dict[str, Any]:
    return {
        "id": "fixture-05",
        "name": "blocked specialist",
        "params": {"agents": 2, "tasks": 1, "ambiguity": 0.3, "capacity": 0.5},
        "expected": {
            "task_success": False,
            "delegation_correct": True,
            "criteria_completeness": 0.30,
            "escalation_correct": True,
            "plan_quality": 0.45,
            "tool_calls": 4,
            "token_cost": 1600,
            "latency_ms": 75,
            "human_correction": 1,
        },
    }


@_register("poor specialist result")
def poor_specialist_result() -> dict[str, Any]:
    return {
        "id": "fixture-06",
        "name": "poor specialist result",
        "params": {"agents": 1, "tasks": 1, "ambiguity": 0.1, "capacity": 1.0},
        "expected": {
            "task_success": False,
            "delegation_correct": True,
            "criteria_completeness": 0.60,
            "escalation_correct": False,
            "plan_quality": 0.40,
            "tool_calls": 3,
            "token_cost": 1100,
            "latency_ms": 40,
            "human_correction": 1,
        },
    }


@_register("cross-domain conflict")
def cross_domain_conflict() -> dict[str, Any]:
    return {
        "id": "fixture-07",
        "name": "cross-domain conflict",
        "params": {"agents": 2, "tasks": 2, "ambiguity": 0.7, "capacity": 0.6},
        "expected": {
            "task_success": False,
            "delegation_correct": False,
            "criteria_completeness": 0.35,
            "escalation_correct": True,
            "plan_quality": 0.42,
            "tool_calls": 9,
            "token_cost": 3200,
            "latency_ms": 140,
            "human_correction": 2,
        },
    }


@_register("deadline-sensitive task")
def deadline_sensitive_task() -> dict[str, Any]:
    return {
        "id": "fixture-08",
        "name": "deadline-sensitive task",
        "params": {"agents": 1, "tasks": 1, "ambiguity": 0.2, "capacity": 1.0, "deadline_ms": 50},
        "expected": {
            "task_success": True,
            "delegation_correct": True,
            "criteria_completeness": 0.85,
            "escalation_correct": False,
            "plan_quality": 0.78,
            "tool_calls": 4,
            "token_cost": 1800,
            "latency_ms": 55,
            "human_correction": 0,
        },
    }


@_register("plan critique")
def plan_critique() -> dict[str, Any]:
    return {
        "id": "fixture-09",
        "name": "plan critique",
        "params": {"agents": 1, "tasks": 1, "ambiguity": 0.4, "capacity": 1.0},
        "expected": {
            "task_success": True,
            "delegation_correct": True,
            "criteria_completeness": 0.70,
            "escalation_correct": False,
            "plan_quality": 0.55,
            "tool_calls": 6,
            "token_cost": 2400,
            "latency_ms": 80,
            "human_correction": 0,
        },
    }


@_register("founder briefing")
def founder_briefing() -> dict[str, Any]:
    return {
        "id": "fixture-10",
        "name": "founder briefing",
        "params": {"agents": 1, "tasks": 1, "ambiguity": 0.0, "capacity": 1.0, "stakeholder": "founder"},
        "expected": {
            "task_success": True,
            "delegation_correct": True,
            "criteria_completeness": 0.98,
            "escalation_correct": False,
            "plan_quality": 0.92,
            "tool_calls": 2,
            "token_cost": 900,
            "latency_ms": 30,
            "human_correction": 0,
        },
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

ALL_FIXTURE_NAMES = list(FIXTURE_BUILDERS.keys())


def build_fixture(name: str) -> dict[str, Any]:
    """Return the named fixture spec (fresh dict each call)."""
    if name not in FIXTURE_BUILDERS:
        raise KeyError(f"Unknown fixture: {name!r}")
    return FIXTURE_BUILDERS[name]()


def build_all_fixtures() -> list[dict[str, Any]]:
    """Return all ten fixture specs in defined order."""
    return [build_fixture(n) for n in ALL_FIXTURE_NAMES]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FixtureScore:
    fixture_id: str
    fixture_name: str
    metric_scores: dict[str, bool]
    all_pass: bool


def score_run(fixture: dict[str, Any], observed: dict[str, Any]) -> FixtureScore:
    """Compare observed dict against fixture expected signals.

    Exact equality for bools and ints; float comparison within TOLERANCE;
    missing keys count as failures.
    """
    expected = fixture["expected"]
    metric_scores: dict[str, bool] = {}
    all_pass = True

    for key, exp_val in expected.items():
        if key not in observed:
            metric_scores[key] = False
            all_pass = False
            continue
        got = observed[key]
        if isinstance(exp_val, bool):
            ok = got is exp_val
        elif isinstance(exp_val, float):
            ok = math.isclose(got, exp_val, abs_tol=TOLERANCE)
        else:
            ok = got == exp_val
        metric_scores[key] = ok
        if not ok:
            all_pass = False

    return FixtureScore(
        fixture_id=fixture["id"],
        fixture_name=fixture["name"],
        metric_scores=metric_scores,
        all_pass=all_pass,
    )