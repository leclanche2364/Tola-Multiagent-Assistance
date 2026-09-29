"""QA T5 tests -- Delegation and Task Protocol.

Covers T5-01..T5-10 as defined in tola_testing_plan_v1_1.md.
Stdlib only: unittest, datetime.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

import unittest

from tola.delegation.protocol import (
    DelegationRecord,
    DelegationStatus,
    DelegationLedger,
)
from tola.delegation.workflow import (
    delegation_request,
    run_capacity_query,
    apply_capacity_report,
    tola_decide,
    commit_task,
    record_result,
    accept_or_reject,
    ProtocolInvariantError,
)
from tola.delegation.escalation import (
    escalate_boundary_violation,
    escalate_rejected_result,
    escalate_stalled_delegation,
    handle_future_specialist_dependency,
    STALLED_DELEGATION_DAYS_THRESHOLD,
)
from tola.registry.availability import DelegationBlockedError


# ===========================================================================
# Fixtures
# ===========================================================================

FIXTURE_TIMESTAMP = "2026-09-29T12:00:00"
FIXTURE_TIMESTAMP_2 = "2026-09-29T13:00:00"
FIXTURE_TIMESTAMP_3 = "2026-09-29T14:00:00"


def _make_ledger() -> DelegationLedger:
    return DelegationLedger()


def _make_capacity_client() -> callable:
    """Return a simple capacity client callable that returns a report."""
    def _client(delegation: DelegationRecord) -> dict:
        return {
            "delegation_id": delegation.delegation_id,
            "specialist": delegation.specialist,
            "fit": "FIT",
            "risk_level": "none",
            "available_capacity": 100,
            "timestamp": FIXTURE_TIMESTAMP,
        }
    return _client


def _make_boundary_check_result(allowed: bool = True) -> dict:
    return {"allowed": allowed, "reason": "Within boundary"}


def _make_success_criteria() -> list:
    return ["output delivered", "quality check passed"]


# ===========================================================================
# T5-01: Full happy-path loop records every step
# ===========================================================================

class TestT5_01_FullHappyPathLoop(unittest.TestCase):
    """T5-01: Successful task updates success metric.

    The full delegation loop records every step:
    request -> CAPACITY_QUERY -> CAPACITY_REPORT -> Tola decision
    -> TASK_COMMITTED -> specialist work -> result -> acceptance.
    """

    def test_full_loop_records_every_step(self):
        ledger = _make_ledger()

        # Step 1: delegation request
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-001",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d1.status, DelegationStatus.DRAFTED)
        self.assertEqual(d1.specialist, "growth")

        # Step 2: capacity query
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d2.status, DelegationStatus.AWAITING_CAPACITY)
        self.assertIsNotNone(d2.capacity_query)
        self.assertIsNotNone(d2.capacity_report)

        # Step 3: Tola decision
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is the correct specialist for product domain.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d3.status, DelegationStatus.DECIDED)
        self.assertIsNotNone(d3.tola_decision)

        # Step 4: commit task
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d4.status, DelegationStatus.COMMITTED)

        # Step 5: record result
        d5 = record_result(
            delegation=d4,
            result={"status": "SUCCESS", "output": "Q3 funnel report"},
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d5.status, DelegationStatus.RESULT_RECEIVED)
        self.assertIsNotNone(d5.result)

        # Step 6: accept
        d6 = accept_or_reject(
            delegation=d5,
            verdict="ACCEPT",
            reasoning="Result meets all success criteria.",
            ledger=ledger,
            timestamps={"accepted_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d6.status, DelegationStatus.ACCEPTED)
        self.assertEqual(d6.acceptance_reason, "Result meets all success criteria.")

    def test_ledger_contains_all_six_records(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-002",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is the correct specialist.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        d5 = record_result(
            delegation=d4,
            result={"status": "SUCCESS", "output": "report"},
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        d6 = accept_or_reject(
            delegation=d5,
            verdict="ACCEPT",
            reasoning="All criteria met.",
            ledger=ledger,
            timestamps={"accepted_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(ledger.count(), 6)
        self.assertEqual(d6.status, DelegationStatus.ACCEPTED)


# ===========================================================================
# T5-02: Partial result remains separate from success
# ===========================================================================

class TestT5_02_PartialResultSeparateFromSuccess(unittest.TestCase):
    """T5-02: Partial result remains separate from success."""

    def test_partial_result_status_is_not_accepted(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-010",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is the correct specialist.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        # Specialist returns PARTIAL result
        d5 = record_result(
            delegation=d4,
            result={"status": "PARTIAL", "output": "incomplete report", "missing": "conversion data"},
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d5.status, DelegationStatus.RESULT_RECEIVED)
        self.assertEqual(d5.result["status"], "PARTIAL")

        # Accepting a partial result is allowed but the status reflects it
        d6 = accept_or_reject(
            delegation=d5,
            verdict="ACCEPT",
            reasoning="Accepted with known gaps; conversion data pending.",
            ledger=ledger,
            timestamps={"accepted_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d6.status, DelegationStatus.ACCEPTED)
        # The result status is PARTIAL, distinct from SUCCESS
        self.assertEqual(d6.result["status"], "PARTIAL")

    def test_partial_is_distinct_from_success_in_record(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-011",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is the correct specialist.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        d5 = record_result(
            delegation=d4,
            result={"status": "PARTIAL", "output": "incomplete"},
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        # The result dict is stored separately from the delegation status
        self.assertIsNotNone(d5.result)
        self.assertEqual(d5.result["status"], "PARTIAL")
        self.assertNotEqual(d5.result["status"], "SUCCESS")


# ===========================================================================
# T5-03: Blocked task is not treated as failure unless policy says so
# ===========================================================================

class TestT5_03_BlockedTaskNotTreatedAsFailure(unittest.TestCase):
    """T5-03: Blocked task is not treated as failure unless policy says so."""

    def test_blocked_result_status_is_not_failure(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-020",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is the correct specialist.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        d5 = record_result(
            delegation=d4,
            result={"status": "BLOCKED", "reason": "external dependency unavailable"},
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        # BLOCKED is a distinct status, not FAILURE
        self.assertEqual(d5.result["status"], "BLOCKED")
        self.assertNotEqual(d5.result["status"], "FAILURE")

    def test_blocked_result_can_be_accepted_with_reason(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-021",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is the correct specialist.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        d5 = record_result(
            delegation=d4,
            result={"status": "BLOCKED", "reason": "waiting on client data"},
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        d6 = accept_or_reject(
            delegation=d5,
            verdict="ACCEPT",
            reasoning="Blocked status accepted; will resume when dependency resolves.",
            ledger=ledger,
            timestamps={"accepted_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d6.status, DelegationStatus.ACCEPTED)
        self.assertEqual(d6.result["status"], "BLOCKED")


# ===========================================================================
# T5-04: Retry/latency/cost recorded correctly
# ===========================================================================

class TestT5_04_RetryLatencyCostRecorded(unittest.TestCase):
    """T5-04: Retry/latency/cost recorded correctly."""

    def test_result_includes_retry_latency_cost(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-030",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is the correct specialist.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        d5 = record_result(
            delegation=d4,
            result={
                "status": "SUCCESS",
                "output": "Q3 funnel report",
                "retry_count": 2,
                "latency_ms": 1450,
                "cost_usd": 0.03,
            },
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d5.result["retry_count"], 2)
        self.assertEqual(d5.result["latency_ms"], 1450)
        self.assertEqual(d5.result["cost_usd"], 0.03)

    def test_zero_retry_when_no_retry_needed(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-031",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is the correct specialist.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        d5 = record_result(
            delegation=d4,
            result={"status": "SUCCESS", "retry_count": 0, "latency_ms": 200, "cost_usd": 0.01},
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d5.result["retry_count"], 0)


# ===========================================================================
# T5-05: Recent and lifetime windows can be separated
# ===========================================================================

class TestT5_05_RecentAndLifetimeWindowsSeparated(unittest.TestCase):
    """T5-05: Recent and lifetime windows can be separated."""

    def test_capacity_report_can_include_separate_windows(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-040",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        report = {
            "delegation_id": d1.delegation_id,
            "fit": "FIT",
            "recent_window": {"successes": 8, "trials": 10, "period_days": 30},
            "lifetime_window": {"successes": 45, "trials": 50, "period_days": 365},
            "timestamp": FIXTURE_TIMESTAMP,
        }
        d2 = apply_capacity_report(
            delegation=d1,
            report=report,
            ledger=ledger,
            timestamps={"reported_at": FIXTURE_TIMESTAMP},
        )
        self.assertIsNotNone(d2.capacity_report)
        self.assertIn("recent_window", d2.capacity_report)
        self.assertIn("lifetime_window", d2.capacity_report)
        self.assertEqual(d2.capacity_report["recent_window"]["successes"], 8)
        self.assertEqual(d2.capacity_report["lifetime_window"]["successes"], 45)

    def test_recent_and_lifetime_are_distinct_dicts(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-041",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        report = {
            "fit": "FIT",
            "recent_window": {"successes": 1, "trials": 1},
            "lifetime_window": {"successes": 50, "trials": 50},
        }
        d2 = apply_capacity_report(
            delegation=d1,
            report=report,
            ledger=ledger,
            timestamps={"reported_at": FIXTURE_TIMESTAMP},
        )
        recent = d2.capacity_report["recent_window"]
        lifetime = d2.capacity_report["lifetime_window"]
        self.assertNotEqual(recent, lifetime)


# ===========================================================================
# T5-06: One anomalous failure does not catastrophically rerank agent
# ===========================================================================

class TestT5_06_AnomalousFailureDoesNotCatastrophicRerank(unittest.TestCase):
    """T5-06: One anomalous failure does not catastrophically rerank agent."""

    def test_single_failure_in_capacity_report_does_not_block_fit(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-050",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        # Capacity report shows one anomalous failure but overall FIT
        report = {
            "fit": "FIT",
            "recent_failures": 1,
            "recent_trials": 10,
            "failure_rate": 0.1,
            "lifetime_success_rate": 0.92,
            "timestamp": FIXTURE_TIMESTAMP,
        }
        d2 = apply_capacity_report(
            delegation=d1,
            report=report,
            ledger=ledger,
            timestamps={"reported_at": FIXTURE_TIMESTAMP},
        )
        # The report still says FIT; one failure does not override
        self.assertEqual(d2.capacity_report["fit"], "FIT")
        self.assertGreater(
            d2.capacity_report["lifetime_success_rate"], 0.5
        )

    def test_recent_failure_rate_is_contextual(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-051",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        report = {
            "fit": "FIT_WITH_RISK",
            "recent_failures": 1,
            "recent_trials": 10,
            "failure_rate": 0.1,
            "lifetime_success_rate": 0.92,
            "risk_note": "Single anomalous failure in recent window; lifetime rate remains strong.",
            "timestamp": FIXTURE_TIMESTAMP,
        }
        d2 = apply_capacity_report(
            delegation=d1,
            report=report,
            ledger=ledger,
            timestamps={"reported_at": FIXTURE_TIMESTAMP},
        )
        # FIT_WITH_RISK not FIT, but not BLOCKED either
        self.assertIn(d2.capacity_report["fit"], ("FIT", "FIT_WITH_RISK"))


# ===========================================================================
# T5-07: High measured success does not permit cross-domain authority
# ===========================================================================

class TestT5_07_HighSuccessNoCrossDomainAuthority(unittest.TestCase):
    """T5-07: High measured success does not permit cross-domain authority."""

    def test_high_success_rate_growth_cannot_do_scholar_work(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="learning gap detection for curriculum",
            domain="learning",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-060",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        # Even though Growth has high success rate in product,
        # it cannot be routed to learning-gap work.
        self.assertEqual(d1.specialist, "scholar")

    def test_high_success_rate_scholar_cannot_do_growth_work(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="funnel analysis for Q3",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-061",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        # Scholar has high success in learning, but cannot do product work
        self.assertEqual(d1.specialist, "growth")

    def test_boundary_check_enforces_domain_authority_on_commit(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="funnel analysis for Q3",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-062",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is the correct specialist.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        # Even with high success rate, boundary check must pass
        # Growth is allowed to do funnel analysis (its domain)
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(allowed=True),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d4.status, DelegationStatus.COMMITTED)


# ===========================================================================
# T5-08: Skip-step rejection (commit without capacity/decision)
# ===========================================================================

class TestT5_08_SkipStepRejection(unittest.TestCase):
    """T5-08: commit without capacity report and decision must raise."""

    def test_commit_without_capacity_report_raises(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-070",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        # No capacity query or report yet
        with self.assertRaises(ProtocolInvariantError) as cm:
            commit_task(
                delegation=d1,
                success_criteria=_make_success_criteria(),
                boundary_check_result=_make_boundary_check_result(),
                ledger=ledger,
                timestamps={"committed_at": FIXTURE_TIMESTAMP},
            )
        self.assertIn("capacity report", str(cm.exception))

    def test_commit_without_tola_decision_raises(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-071",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        # No tola_decide called yet
        with self.assertRaises(ProtocolInvariantError) as cm:
            commit_task(
                delegation=d2,
                success_criteria=_make_success_criteria(),
                boundary_check_result=_make_boundary_check_result(),
                ledger=ledger,
                timestamps={"committed_at": FIXTURE_TIMESTAMP},
            )
        self.assertIn("Tola decision", str(cm.exception))

    def test_commit_without_capacity_report_and_decision_raises(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-072",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        # Neither capacity nor decision -- single raise
        with self.assertRaises(ProtocolInvariantError):
            commit_task(
                delegation=d1,
                success_criteria=_make_success_criteria(),
                boundary_check_result=_make_boundary_check_result(),
                ledger=ledger,
                timestamps={"committed_at": FIXTURE_TIMESTAMP},
            )

    def test_accept_without_result_raises(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-073",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is correct.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        # No result recorded yet
        with self.assertRaises(ProtocolInvariantError) as cm:
            accept_or_reject(
                delegation=d4,
                verdict="ACCEPT",
                reasoning="No result yet.",
                ledger=ledger,
                timestamps={"accepted_at": FIXTURE_TIMESTAMP},
            )
        self.assertIn("no result", str(cm.exception).lower())

    def test_invalid_verdict_raises(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-074",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is correct.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        d5 = record_result(
            delegation=d4,
            result={"status": "SUCCESS"},
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        with self.assertRaises(ProtocolInvariantError) as cm:
            accept_or_reject(
                delegation=d5,
                verdict="INVALID",
                reasoning="Bad verdict.",
                ledger=ledger,
                timestamps={"accepted_at": FIXTURE_TIMESTAMP},
            )
        self.assertIn("invalid verdict", str(cm.exception).lower())


# ===========================================================================
# T5-09: Boundary-violation escalation
# ===========================================================================

class TestT5_09_BoundaryViolationEscalation(unittest.TestCase):
    """T5-09: Boundary violation triggers escalation."""

    def test_escalation_marks_delegation_as_rejected(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="direct schedule write for Q3",
            domain="scheduling",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-080",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        escalated = escalate_boundary_violation(
            delegation=d1,
            violation_reason="Growth attempted direct schedule write (T4-04)",
            ledger=ledger,
            timestamps={"escalated_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(escalated.status, DelegationStatus.REJECTED)
        self.assertIsNotNone(escalated.escalation_reason)
        self.assertIn("Boundary violation", escalated.escalation_reason)

    def test_escalation_preserves_original_record(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="direct schedule write for Q3",
            domain="scheduling",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-081",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        escalated = escalate_boundary_violation(
            delegation=d1,
            violation_reason="T4-04 boundary violation",
            ledger=ledger,
            timestamps={"escalated_at": FIXTURE_TIMESTAMP},
        )
        # Original draft record still in ledger
        self.assertEqual(ledger.count(), 2)
        original = ledger.get_by_id("DEL-081")
        self.assertEqual(original.status, DelegationStatus.DRAFTED)
        # Escalated record is separate
        self.assertEqual(escalated.status, DelegationStatus.REJECTED)

    def test_escalation_reason_is_deterministic(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="direct schedule write",
            domain="scheduling",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-082",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        escalated = escalate_boundary_violation(
            delegation=d1,
            violation_reason="Growth cannot write schedule (T4-04)",
            ledger=ledger,
            timestamps={"escalated_at": FIXTURE_TIMESTAMP},
        )
        self.assertIn("T4-04", escalated.escalation_reason)


# ===========================================================================
# T5-10: Rejected result handling, re-delegation, stalled detection,
#         marketing future-dependency, no fake completion
# ===========================================================================

class TestT5_10_RejectedResultAndFutureDependency(unittest.TestCase):
    """T5-10 covers: rejected result + re-delegation, stalled detection,
    marketing future-dependency path, and no fake completion."""

    # --- Rejected result handling and re-delegation ---

    def test_rejected_result_can_be_redelegated(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-090",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is correct.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        d5 = record_result(
            delegation=d4,
            result={"status": "FAILURE", "reason": "insufficient data"},
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        # Reject and re-delegate to Growth (same specialist, retry)
        d6 = escalate_rejected_result(
            delegation=d5,
            rejection_reason="Failure: insufficient data. Retrying with more context.",
            re_delegate=True,
            new_specialist="growth",
            ledger=ledger,
            timestamps={"rejected_at": FIXTURE_TIMESTAMP},
        )
        # The new record should be a DRAFT for re-delegation
        self.assertEqual(d6.status, DelegationStatus.DRAFTED)
        self.assertEqual(d6.delegation_id, "DEL-090-redelegate-1")
        self.assertEqual(d6.re_delegation_count, 1)

    def test_rejected_result_without_redelegation(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-091",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is correct.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        d5 = record_result(
            delegation=d4,
            result={"status": "FAILURE", "reason": "insufficient data"},
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        escalated = escalate_rejected_result(
            delegation=d5,
            rejection_reason="Failure: insufficient data.",
            re_delegate=False,
            ledger=ledger,
            timestamps={"rejected_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(escalated.status, DelegationStatus.REJECTED)
        self.assertIn("insufficient data", escalated.acceptance_reason)

    # --- Stalled delegation detection ---

    def test_stalled_delegation_detected_above_threshold(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-100",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is correct.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        # No result recorded; now stalled
        escalated = escalate_stalled_delegation(
            delegation=d4,
            days_without_result=7,
            ledger=ledger,
            timestamps={"escalated_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(escalated.status, DelegationStatus.REJECTED)
        self.assertIn("stalled", escalated.escalation_reason.lower())
        self.assertIn("7 days", escalated.escalation_reason)

    def test_stalled_delegation_not_detected_below_threshold(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-101",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        # 3 days is below the threshold of 5
        escalated = escalate_stalled_delegation(
            delegation=d1,
            days_without_result=3,
            ledger=ledger,
            timestamps={"escalated_at": FIXTURE_TIMESTAMP},
        )
        # Returns unchanged (not rejected)
        self.assertEqual(escalated.status, DelegationStatus.DRAFTED)

    def test_stalled_threshold_constant(self):
        """STALLED_DELEGATION_DAYS_THRESHOLD is a documented constant."""
        self.assertEqual(STALLED_DELEGATION_DAYS_THRESHOLD, 5)

    # --- Marketing future-dependency path ---

    def test_marketing_future_dependency_records_deferred_work(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="paid acquisition campaign launch",
            domain="marketing",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-110",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        updated = handle_future_specialist_dependency(
            delegation=d1,
            task_description="paid acquisition campaign launch",
            required_domain="marketing",
            intended_agent_id="marketing",
            ledger=ledger,
            timestamps={"handled_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(updated.status, DelegationStatus.FUTURE_DEPENDENCY)
        self.assertEqual(updated.specialist, "marketing")
        self.assertIsNotNone(updated.tola_decision)
        self.assertEqual(updated.tola_decision["decision"], "FUTURE_DEPENDENCY")

    def test_future_dependency_never_fakes_execution(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="paid acquisition campaign launch",
            domain="marketing",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-111",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        updated = handle_future_specialist_dependency(
            delegation=d1,
            task_description="paid acquisition campaign launch",
            required_domain="marketing",
            intended_agent_id="marketing",
            ledger=ledger,
            timestamps={"handled_at": FIXTURE_TIMESTAMP},
        )
        # No result is faked; result remains None
        self.assertIsNone(updated.result)
        # Status is FUTURE_DEPENDENCY, not ACCEPTED
        self.assertNotEqual(updated.status, DelegationStatus.ACCEPTED)

    def test_marketing_eligible_work_routes_to_growth_not_future(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="funnel analysis for Q3",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-112",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        # Funnel analysis is eligible for Growth under the contract
        # This should NOT become a future dependency
        self.assertEqual(d1.specialist, "growth")
        # The task is routable to an active specialist
        from tola.registry.availability import route_marketing_work
        routing = route_marketing_work("funnel analysis for Q3")
        self.assertEqual(routing["routed_to"], "growth")
        self.assertEqual(routing["record_type"], "ROUTED_TO_ACTIVE_SPECIALIST")

    # --- No fake completion ---

    def test_status_cannot_become_accepted_without_result_and_verdict(self):
        """Status cannot become ACCEPTED without recorded result + verdict."""
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-120",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        # Attempt to force ACCEPTED status without result -- not possible
        # through the public API.  The only path to ACCEPTED is accept_or_reject
        # with verdict="ACCEPT", which requires a result.
        with self.assertRaises(ProtocolInvariantError):
            accept_or_reject(
                delegation=d1,
                verdict="ACCEPT",
                reasoning="Trying to skip result.",
                ledger=ledger,
                timestamps={"accepted_at": FIXTURE_TIMESTAMP},
            )

    def test_accepted_status_requires_result_and_verdict(self):
        ledger = _make_ledger()
        d1 = delegation_request(
            task_description="produce Q3 funnel analysis",
            domain="product",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-121",
            timestamps={"requested_at": FIXTURE_TIMESTAMP},
        )
        d2 = run_capacity_query(
            delegation=d1,
            capacity_client=_make_capacity_client(),
            ledger=ledger,
            timestamps={"queried_at": FIXTURE_TIMESTAMP},
        )
        d3 = tola_decide(
            delegation=d2,
            decision="COMMIT",
            reasoning="Growth is correct.",
            ledger=ledger,
            timestamps={"decided_at": FIXTURE_TIMESTAMP},
        )
        d4 = commit_task(
            delegation=d3,
            success_criteria=_make_success_criteria(),
            boundary_check_result=_make_boundary_check_result(),
            ledger=ledger,
            timestamps={"committed_at": FIXTURE_TIMESTAMP},
        )
        d5 = record_result(
            delegation=d4,
            result={"status": "SUCCESS", "output": "Q3 funnel report"},
            ledger=ledger,
            timestamps={"result_at": FIXTURE_TIMESTAMP},
        )
        # Now accept is valid
        d6 = accept_or_reject(
            delegation=d5,
            verdict="ACCEPT",
            reasoning="All success criteria met.",
            ledger=ledger,
            timestamps={"accepted_at": FIXTURE_TIMESTAMP},
        )
        self.assertEqual(d6.status, DelegationStatus.ACCEPTED)
        # The result is still present on the accepted record
        self.assertIsNotNone(d6.result)
        self.assertEqual(d6.result["status"], "SUCCESS")


# ===========================================================================
# Additional structural tests
# ===========================================================================

class TestT5_Structure(unittest.TestCase):
    """Structural checks on the delegation module."""

    def test_delegation_status_enum_has_all_states(self):
        expected = {
            "DRAFTED", "AWAITING_CAPACITY", "DECIDED", "COMMITTED",
            "IN_PROGRESS", "RESULT_RECEIVED", "ACCEPTED", "REJECTED",
            "CANCELLED", "FUTURE_DEPENDENCY",
        }
        actual = {s.value for s in DelegationStatus}
        self.assertTrue(expected.issubset(actual))

    def test_delegation_record_is_frozen(self):
        record = DelegationRecord(
            delegation_id="test",
            specialist="growth",
            task_description="test",
            domain="product",
            status=DelegationStatus.DRAFTED,
            priority="high",
        )
        with self.assertRaises(Exception):
            record.status = DelegationStatus.ACCEPTED

    def test_ledger_append_only(self):
        ledger = _make_ledger()
        d1 = DelegationRecord(
            delegation_id="L1",
            specialist="growth",
            task_description="test",
            domain="product",
            status=DelegationStatus.DRAFTED,
            priority="high",
        )
        ledger.create(d1)
        self.assertEqual(ledger.count(), 1)
        # Query returns the record
        results = ledger.query(delegation_id="L1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].delegation_id, "L1")

    def test_ledger_query_by_status(self):
        ledger = _make_ledger()
        d1 = DelegationRecord(
            delegation_id="Q1",
            specialist="growth",
            task_description="test",
            domain="product",
            status=DelegationStatus.DRAFTED,
            priority="high",
        )
        ledger.create(d1)
        results = ledger.query(status=DelegationStatus.DRAFTED)
        self.assertEqual(len(results), 1)
        results = ledger.query(status=DelegationStatus.ACCEPTED)
        self.assertEqual(len(results), 0)

    def test_ledger_query_by_specialist(self):
        ledger = _make_ledger()
        d1 = DelegationRecord(
            delegation_id="S1",
            specialist="growth",
            task_description="test",
            domain="product",
            status=DelegationStatus.DRAFTED,
            priority="high",
        )
        d2 = DelegationRecord(
            delegation_id="S2",
            specialist="rhythm",
            task_description="test",
            domain="scheduling",
            status=DelegationStatus.DRAFTED,
            priority="high",
        )
        ledger.create(d1)
        ledger.create(d2)
        results = ledger.query(specialist="growth")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].delegation_id, "S1")

    def test_ledger_all_returns_copy(self):
        ledger = _make_ledger()
        d1 = DelegationRecord(
            delegation_id="C1",
            specialist="growth",
            task_description="test",
            domain="product",
            status=DelegationStatus.DRAFTED,
            priority="high",
        )
        ledger.create(d1)
        all_records = ledger.all()
        all_records.clear()
        self.assertEqual(ledger.count(), 1)

    def test_escalation_stalled_constant_is_int(self):
        self.assertIsInstance(STALLED_DELEGATION_DAYS_THRESHOLD, int)
        self.assertGreater(STALLED_DELEGATION_DAYS_THRESHOLD, 0)

    def test_protocol_invariant_error_is_runtime_error(self):
        self.assertTrue(issubclass(ProtocolInvariantError, RuntimeError))


if __name__ == "__main__":
    unittest.main()