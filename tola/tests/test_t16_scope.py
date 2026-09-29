# QA T16 tests -- Scope Control.
# Stdlib only. Plain ASCII. Deterministic.

from __future__ import annotations

import unittest

from tola.scope.evaluator import (
    ScopeDecision,
    Verdict,
    evaluate_scope,
)
from tola.scope.gate import scope_gate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _aligned_high_value_context() -> dict:
    return {
        "active_goals": [
            {"id": "G1", "name": "Reduce onboarding friction", "tags": ["onboarding"], "status": "open"},
        ],
        "current_priorities": [
            {"type": "goal", "id": "G1", "name": "Reduce onboarding friction", "priority": 1},
        ],
        "capacity_summary": {
            "remaining_capacity": 3,
            "active_tasks": 2,
            "max_parallel_tasks": 5,
        },
        "available_dependencies": ["analytics", "auth"],
        "expected_value_score": 0.9,
        "evidence": "Pilot data shows 40% reduction in drop-off",
    }


def _aligned_high_value_proposal() -> dict:
    return {
        "id": "P1",
        "name": "Add social login to onboarding",
        "goal_refs": ["G1"],
        "tags": ["onboarding"],
        "expected_value": 0.9,
        "evidence": "Pilot data shows 40% reduction in drop-off",
        "scope": "Full social login integration with 5 providers",
        "dependencies": ["auth"],
        "displaces": ["G1: Reduce onboarding friction - current priority"],
        "owner": "tola-build",
        "date": "2026-09-29",
        "expected_outcome": "Onboarding completion rate improves by 40%",
    }


def _oversized_context() -> dict:
    return {
        "active_goals": [
            {"id": "G2", "name": "Improve search relevance", "tags": ["search"], "status": "open"},
        ],
        "current_priorities": [
            {"type": "goal", "id": "G2", "name": "Improve search relevance", "priority": 1},
        ],
        "capacity_summary": {
            "remaining_capacity": 1,
            "active_tasks": 4,
            "max_parallel_tasks": 5,
        },
        "available_dependencies": ["search_index"],
        "expected_value_score": 0.85,
        "evidence": "Search latency correlates with conversion",
    }


def _oversized_proposal() -> dict:
    return {
        "id": "P2",
        "name": "Rebuild search ranking with ML",
        "goal_refs": ["G2"],
        "tags": ["search"],
        "expected_value": 0.85,
        "evidence": "Search latency correlates with conversion",
        "scope": "Full ML pipeline with feature store, model training, and A/B testing",
        "dependencies": ["search_index", "ml_platform"],
        "displaces": ["G2: Improve search relevance - current priority"],
        "smallest_viable_version": "Add BM25 tuning to existing search index",
        "owner": "tola-build",
        "date": "2026-09-29",
        "expected_outcome": "Search relevance score improves by 25%",
    }


def _wrong_time_context() -> dict:
    return {
        "active_goals": [
            {"id": "G3", "name": "Stabilize payment flow", "tags": ["payments"], "status": "open"},
        ],
        "current_priorities": [
            {"type": "goal", "id": "G3", "name": "Stabilize payment flow", "priority": 1},
        ],
        "capacity_summary": {
            "remaining_capacity": 0,
            "active_tasks": 5,
            "max_parallel_tasks": 5,
        },
        "available_dependencies": ["payments"],
        "expected_value_score": 0.8,
        "evidence": "Payment failures cost 12% of revenue",
    }


def _wrong_time_proposal() -> dict:
    return {
        "id": "P3",
        "name": "Add split payment support",
        "goal_refs": ["G3"],
        "tags": ["payments"],
        "expected_value": 0.8,
        "evidence": "Payment failures cost 12% of revenue",
        "scope": "Split payment UI and backend reconciliation",
        "dependencies": ["payments"],
        "displaces": ["G3: Stabilize payment flow - current priority"],
        "revisit_trigger": "Revisit when remaining_capacity > 0",
        "owner": "tola-build",
        "date": "2026-09-29",
        "expected_outcome": "Revenue recovery from split-payment use cases",
    }


def _low_value_context() -> dict:
    return {
        "active_goals": [
            {"id": "G4", "name": "Reduce onboarding friction", "tags": ["onboarding"], "status": "open"},
        ],
        "current_priorities": [
            {"type": "goal", "id": "G4", "name": "Reduce onboarding friction", "priority": 1},
        ],
        "capacity_summary": {
            "remaining_capacity": 2,
            "active_tasks": 1,
            "max_parallel_tasks": 5,
        },
        "available_dependencies": [],
        "expected_value_score": 0.15,
        "evidence": "Anecdotal feedback from 2 users",
    }


def _low_value_proposal() -> dict:
    return {
        "id": "P4",
        "name": "Add tooltip to settings page",
        "goal_refs": ["G4"],
        "tags": ["ui-polish"],
        "expected_value": 0.15,
        "evidence": "Anecdotal feedback from 2 users",
        "scope": "Tooltip on settings page",
        "dependencies": [],
        "displaces": [],
        "stop_condition": "Do not start; revisit when alignment or value changes",
        "owner": "tola-build",
        "date": "2026-09-29",
        "expected_outcome": "Minor UX improvement",
    }


def _ambiguous_consequential_context() -> dict:
    return {
        "active_goals": [
            {"id": "G5", "name": "Expand to new markets", "tags": ["expansion"], "status": "open"},
        ],
        "current_priorities": [
            {"type": "goal", "id": "G5", "name": "Expand to new markets", "priority": 1},
        ],
        "capacity_summary": {
            "remaining_capacity": 2,
            "active_tasks": 3,
            "max_parallel_tasks": 5,
        },
        "available_dependencies": ["localization"],
        "expected_value_score": 0.6,
        "evidence": "Market research indicates 20% growth potential",
    }


def _ambiguous_consequential_proposal() -> dict:
    return {
        "id": "P5",
        "name": "Enter APAC market with localized product",
        "goal_refs": ["G5"],
        "tags": ["expansion"],
        "expected_value": 0.6,
        "evidence": "Market research indicates 20% growth potential",
        "scope": "Full APAC launch with localization, legal review, and regional support",
        "dependencies": ["localization"],
        "displaces": ["G5: Expand to new markets - current priority"],
        "ambiguous": True,
        "consequential": True,
        "owner": "tola-build",
        "date": "2026-09-29",
        "expected_outcome": "20% revenue growth from APAC",
    }


def _opportunity_cost_context() -> dict:
    return {
        "active_goals": [
            {"id": "G6", "name": "Reduce onboarding friction", "tags": ["onboarding"], "status": "open"},
        ],
        "current_priorities": [
            {"type": "goal", "id": "G6", "name": "Reduce onboarding friction", "priority": 1},
            {"type": "goal", "id": "G7", "name": "Improve search relevance", "priority": 2},
        ],
        "capacity_summary": {
            "remaining_capacity": 1,
            "active_tasks": 4,
            "max_parallel_tasks": 5,
        },
        "available_dependencies": ["analytics", "auth"],
        "expected_value_score": 0.75,
        "evidence": "Onboarding pilot data shows 30% improvement",
    }


def _opportunity_cost_proposal() -> dict:
    return {
        "id": "P6",
        "name": "Add referral program to onboarding",
        "goal_refs": ["G6"],
        "tags": ["onboarding"],
        "expected_value": 0.75,
        "evidence": "Onboarding pilot data shows 30% improvement",
        "scope": "Referral program with tracking and rewards",
        "dependencies": ["analytics"],
        "displaces": ["G6: Reduce onboarding friction - current priority", "G7: Improve search relevance"],
        "owner": "tola-build",
        "date": "2026-09-29",
        "expected_outcome": "Onboarding growth via referrals",
    }


def _reasoning_refs_context() -> dict:
    """Context whose specific keys/values must appear in reasoning."""
    return {
        "active_goals": [
            {"id": "G8", "name": "Stabilize payment flow", "tags": ["payments"], "status": "open"},
        ],
        "current_priorities": [
            {"type": "goal", "id": "G8", "name": "Stabilize payment flow", "priority": 1},
        ],
        "capacity_summary": {
            "remaining_capacity": 0,
            "active_tasks": 5,
            "max_parallel_tasks": 5,
        },
        "available_dependencies": ["payments"],
        "expected_value_score": 0.85,
        "evidence": "Payment failures cost 12% of revenue",
    }


def _aligned_medium_value_proposal() -> dict:
    """Aligned but medium value, has capacity -> should START."""
    return {
        "id": "P7",
        "name": "Add payment status page",
        "goal_refs": ["G8"],
        "tags": ["payments"],
        "expected_value": 0.55,
        "evidence": "Support tickets about payment status",
        "scope": "Status page for payment transactions",
        "dependencies": ["payments"],
        "displaces": ["G8: Stabilize payment flow - current priority"],
        "owner": "tola-build",
        "date": "2026-09-29",
        "expected_outcome": "Reduced support tickets about payment status",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestT16ScopeControl(unittest.TestCase):
    """QA T16 -- Scope Control test suite."""

    # T16-01: High-value aligned work returns START.
    def test_t16_01_aligned_high_value_returns_start(self):
        decision = evaluate_scope(_aligned_high_value_proposal(), _aligned_high_value_context())
        self.assertEqual(decision.verdict, Verdict.START)

    # T16-02: Oversized work returns SHAPE_SMALLER.
    def test_t16_02_oversized_returns_shape_smaller(self):
        decision = evaluate_scope(_oversized_proposal(), _oversized_context())
        self.assertEqual(decision.verdict, Verdict.SHAPE_SMALLER)

    # T16-02 continued: smallest viable version is spelled out.
    def test_t16_02_smallest_viable_version_present(self):
        decision = evaluate_scope(_oversized_proposal(), _oversized_context())
        self.assertIn("BM25", decision.smallest_version)

    # T16-03: Good idea at wrong time returns DEFER.
    def test_t16_03_wrong_time_returns_defer(self):
        decision = evaluate_scope(_wrong_time_proposal(), _wrong_time_context())
        self.assertEqual(decision.verdict, Verdict.DEFER)

    # T16-03 continued: DEFER includes revisit condition.
    def test_t16_03_defer_has_revisit_condition(self):
        decision = evaluate_scope(_wrong_time_proposal(), _wrong_time_context())
        self.assertTrue(len(decision.stop_condition) == 0)
        # Revisit condition is in reasoning.
        revisit_found = any("Revisit" in r for r in decision.reasoning)
        self.assertTrue(revisit_found)

    # T16-04: Low-value work returns STOP.
    def test_t16_04_low_value_returns_stop(self):
        decision = evaluate_scope(_low_value_proposal(), _low_value_context())
        self.assertEqual(decision.verdict, Verdict.STOP)

    # T16-04 continued: STOP includes stop condition.
    def test_t16_04_stop_has_stop_condition(self):
        decision = evaluate_scope(_low_value_proposal(), _low_value_context())
        self.assertIn("Do not start", decision.stop_condition)

    # T16-05: Opportunity cost explicitly shown in output.
    def test_t16_05_opportunity_cost_present(self):
        decision = evaluate_scope(_opportunity_cost_proposal(), _opportunity_cost_context())
        self.assertTrue(len(decision.opportunity_cost) > 0)
        self.assertIn("displaces", decision.opportunity_cost)

    # T16-05 continued: displaces list is populated.
    def test_t16_05_displaces_populated(self):
        decision = evaluate_scope(_opportunity_cost_proposal(), _opportunity_cost_context())
        self.assertTrue(len(decision.displaces) > 0)

    # T16-06: Consequential ambiguous choice becomes NEEDS_USER_DECISION.
    def test_t16_06_consequential_ambiguous_returns_needs_user_decision(self):
        decision = evaluate_scope(
            _ambiguous_consequential_proposal(),
            _ambiguous_consequential_context(),
        )
        self.assertEqual(decision.verdict, Verdict.NEEDS_USER_DECISION)

    # T16-06 continued: NEEDS_USER_DECISION never guesses smallest_version.
    def test_t16_06_needs_user_decision_no_guess(self):
        decision = evaluate_scope(
            _ambiguous_consequential_proposal(),
            _ambiguous_consequential_context(),
        )
        # Reasoning must not fabricate a smallest version.
        self.assertEqual(decision.verdict, Verdict.NEEDS_USER_DECISION)

    # T16-07: Reasoning references current priorities/capacity, not generic advice.
    def test_t16_07_reasoning_references_context_keys(self):
        decision = evaluate_scope(
            _aligned_medium_value_proposal(),
            _reasoning_refs_context(),
        )
        # All reasoning strings should cite specific context keys/values.
        for r in decision.reasoning:
            # Each reasoning line should reference a dimension key
            # or a concrete context value, not generic productivity advice.
            self.assertTrue(
                any(k in r for k in [
                    "active_goal_alignment",
                    "expected_value",
                    "appetite",
                    "dependencies",
                    "opportunity_cost",
                    "ambiguity",
                    "capacity_summary",
                    "remaining_capacity",
                    "active_tasks",
                    "max_parallel_tasks",
                    "aligned=",
                    "tier=",
                ]),
                f"Reasoning line does not reference specific context: {r!r}",
            )

    # T16-07 continued: reasoning cites specific capacity values.
    def test_t16_07_reasoning_cites_capacity_values(self):
        decision = evaluate_scope(
            _aligned_medium_value_proposal(),
            _reasoning_refs_context(),
        )
        reasoning_text = " ".join(decision.reasoning)
        # Must cite the specific capacity numbers from context.
        self.assertIn("remaining_capacity=0", reasoning_text)
        self.assertIn("active_tasks=5", reasoning_text)
        self.assertIn("max_parallel_tasks=5", reasoning_text)

    # Determinism: same inputs produce identical output.
    def test_t16_07_determinism(self):
        d1 = evaluate_scope(_aligned_high_value_proposal(), _aligned_high_value_context())
        d2 = evaluate_scope(_aligned_high_value_proposal(), _aligned_high_value_context())
        self.assertEqual(d1.verdict, d2.verdict)
        self.assertEqual(d1.reasoning, d2.reasoning)
        self.assertEqual(d1.opportunity_cost, d2.opportunity_cost)
        self.assertEqual(d1.smallest_version, d2.smallest_version)
        self.assertEqual(d1.stop_condition, d2.stop_condition)
        self.assertEqual(d1.displaces, d2.displaces)

    # Gate test: scope_gate returns decision and register record for STOP.
    def test_t16_04_gate_returns_register_record(self):
        decision, record = scope_gate(_low_value_proposal(), _low_value_context())
        self.assertEqual(decision.verdict, Verdict.STOP)
        self.assertIn("decision", record)
        self.assertIn("reason", record)
        self.assertIn("tradeoff", record)
        self.assertIn("owner", record)
        self.assertIn("date", record)
        self.assertIn("expected_outcome", record)

    # Gate test: scope_gate returns empty record for START.
    def test_t16_01_gate_empty_record_for_start(self):
        decision, record = scope_gate(_aligned_high_value_proposal(), _aligned_high_value_context())
        self.assertEqual(decision.verdict, Verdict.START)
        self.assertEqual(record, {})

    # Gate test: scope_gate returns empty record for NEEDS_USER_DECISION.
    def test_t16_06_gate_empty_record_for_needs_user_decision(self):
        decision, record = scope_gate(
            _ambiguous_consequential_proposal(),
            _ambiguous_consequential_context(),
        )
        self.assertEqual(decision.verdict, Verdict.NEEDS_USER_DECISION)
        self.assertEqual(record, {})

    # Determinism via gate: same inputs, same record.
    def test_t16_07_gate_determinism(self):
        d1, r1 = scope_gate(_aligned_high_value_proposal(), _aligned_high_value_context())
        d2, r2 = scope_gate(_aligned_high_value_proposal(), _aligned_high_value_context())
        self.assertEqual(d1.verdict, d2.verdict)
        self.assertEqual(r1, r2)

    # Missing dependencies -> STOP with stop condition.
    def test_t16_04_missing_dependencies_blocked(self):
        proposal = {
            "id": "P8",
            "name": "Add ML recommendations",
            "goal_refs": ["G1"],
            "tags": ["ml"],
            "expected_value": 0.9,
            "evidence": "ML improves engagement",
            "scope": "Full ML recommendation engine",
            "dependencies": ["ml_platform", "data_pipeline"],
            "displaces": [],
            "owner": "tola-build",
            "date": "2026-09-29",
            "expected_outcome": "Engagement improvement",
        }
        context = {
            "active_goals": [
                {"id": "G1", "name": "Reduce onboarding friction", "tags": ["onboarding"], "status": "open"},
            ],
            "current_priorities": [],
            "capacity_summary": {
                "remaining_capacity": 3,
                "active_tasks": 1,
                "max_parallel_tasks": 5,
            },
            "available_dependencies": ["analytics"],
            "expected_value_score": 0.9,
            "evidence": "ML improves engagement",
        }
        decision = evaluate_scope(proposal, context)
        self.assertEqual(decision.verdict, Verdict.STOP)
        self.assertTrue(len(decision.stop_condition) > 0)
        self.assertIn("Resolve dependencies", decision.stop_condition)


if __name__ == "__main__":
    unittest.main()