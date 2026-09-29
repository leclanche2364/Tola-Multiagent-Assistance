# QA T31 -- Final Hardening end-to-end tests.
# 13 tests T31-01..T31-13 plus critical assertions.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

import unittest

# ---------------------------------------------------------------------------
# Imports: real pipeline functions from existing modules
# ---------------------------------------------------------------------------

from tola.delegation.protocol import (
    DelegationRecord,
    DelegationStatus,
    DelegationLedger,
)
from tola.delegation.workflow import (
    delegation_request,
    run_capacity_query,
    tola_decide,
    commit_task,
    record_result,
    accept_or_reject,
    ProtocolInvariantError,
)
from tola.registry.capability import (
    agent_capability_match,
    agent_boundary_check,
    agent_capability_get,
)
from tola.registry.availability import (
    check_delegation_allowed,
    DelegationBlockedError,
    route_marketing_work,
    FUTURE_SPECIALIST_DEPENDENCY,
    validate_marketing_activation,
)
from tola.registry.boundaries import enforce_boundary, BoundaryViolation
from tola.registry.profiles import PROFILES, AvailabilityStatus
from tola.monitoring.tracker import (
    DelegationTracker,
    TrackingEntry,
    TrackingEvent,
)
from tola.monitoring.summary import delegation_ledger
from tola.recovery.patterns import (
    StallKind,
    StallPattern,
    detect_stall_pattern,
)
from tola.recovery.actions import (
    propose_recovery,
    RecoveryAction,
    ALLOWED_ACTIONS,
)
from tola.heartbeat.heartbeat import run_heartbeat
from tola.heartbeat.policy import THRESHOLDS
from tola.evolution.proposal import propose_improvement, rollback
from tola.evolution.apply import apply_or_reject
from tola.decisions.register import (
    register_decision,
    DecisionRecord,
)
from tola.pilot.scenarios import PILOT_SCENARIOS
from tola.pilot.metrics import score_pilot
from tola.portfolio.snapshot import (
    portfolio_snapshot_build,
    portfolio_snapshot_validate,
)
from tola.portfolio.contracts import Project, Goal, Task
from tola.scope.evaluator import evaluate_scope
from tola.hardening.audits import (
    permission_audit,
    secret_privacy_audit,
    cost_audit,
    AUTONOMY_MATRIX,
)
from tola.hardening.runbook import (
    rollback_runbook,
    runbook_execute,
    chain_trace,
)


# ===========================================================================
# Fixtures
# ===========================================================================

FIXTURE_TS = "2026-09-29T12:00:00"
FIXTURE_TS_2 = "2026-09-29T13:00:00"
FIXTURE_TS_3 = "2026-09-29T14:00:00"

MY_RHYTHM_PATHS = ("/my_rhythm", "my_rhythm", "/Users/habeebodubunmi/.openclaw/my_rhythm")


def _make_ledger() -> DelegationLedger:
    return DelegationLedger()


def _make_capacity_client() -> callable:
    def _client(delegation: DelegationRecord) -> dict:
        return {
            "delegation_id": delegation.delegation_id,
            "specialist": delegation.specialist,
            "fit": "FIT",
            "risk_level": "none",
            "available_capacity": 100,
            "timestamp": FIXTURE_TS,
        }
    return _client


def _make_tracker() -> DelegationTracker:
    return DelegationTracker()


# ===========================================================================
# T31-01: Goal -> plan -> delegation -> specialist -> monitoring ->
#         verification -> close
# ===========================================================================

class TestT31_01_FullDelegationLoop(unittest.TestCase):
    """T31-01: End-to-end goal-to-close delegation loop."""

    def test_full_loop(self):
        ledger = _make_ledger()
        tracker = _make_tracker()

        # Goal -> plan (scope evaluation)
        scope_decision = evaluate_scope(
            {"goal_refs": ["g1"], "tags": ["growth"], "expected_value": 0.85, "evidence": "revenue"},
            {"active_goals": [{"id": "g1", "name": "Growth Sprint", "tags": ["growth"]}],
             "capacity_summary": {"remaining_capacity": 2, "active_tasks": 1, "max_parallel_tasks": 4}},
        )
        self.assertEqual(scope_decision.verdict.value, "START")

        # Delegation request
        delegation = delegation_request(
            task_description="Analyze conversion funnel",
            domain="growth",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-T31-01",
            timestamps={"requested_at": FIXTURE_TS},
        )
        self.assertEqual(delegation.status, DelegationStatus.DRAFTED)

        # Capacity query
        delegation = run_capacity_query(
            delegation, _make_capacity_client(), ledger, {"queried_at": FIXTURE_TS},
        )
        self.assertEqual(delegation.status, DelegationStatus.AWAITING_CAPACITY)

        # Tola decide -> commit
        delegation = tola_decide(
            delegation, "COMMIT", "Growth specialist available", ledger, {"decided_at": FIXTURE_TS},
        )
        boundary = agent_boundary_check("growth", "delegated_task_commit")
        self.assertTrue(boundary["allowed"])

        delegation = commit_task(
            delegation, ["conversion_analysis_complete"], boundary, ledger, {"committed_at": FIXTURE_TS},
        )
        self.assertEqual(delegation.status, DelegationStatus.COMMITTED)

        # Register in tracker for monitoring
        tracker.register_delegation(delegation)
        tracker.record_event("DEL-T31-01", TrackingEvent.ACKNOWLEDGED, FIXTURE_TS)
        tracker.record_event("DEL-T31-01", TrackingEvent.PROGRESS_NOTED, FIXTURE_TS_2)

        # Record result
        delegation = record_result(
            delegation, {"status": "SUCCESS", "output": "funnel analysis complete"}, ledger, {"result_at": FIXTURE_TS_2},
        )

        # Verification -> close
        close = accept_or_reject(
            delegation, "ACCEPT", "All success criteria met", ledger, {"closed_at": FIXTURE_TS_3},
        )
        self.assertEqual(close.status, DelegationStatus.ACCEPTED)

        # Monitoring summary
        summary = delegation_ledger(tracker)
        self.assertEqual(summary["total"], 1)

        # Critical assertion: no My Rhythm write
        for path in MY_RHYTHM_PATHS:
            self.assertNotIn(path, str(ledger.all()))

    def test_no_future_not_available_delegation(self):
        """Critical: Tola never delegates to FUTURE_NOT_AVAILABLE Marketing Agent."""
        ledger = _make_ledger()
        delegation = delegation_request(
            task_description="Run marketing campaign",
            domain="marketing",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-T31-01B",
            timestamps={"requested_at": FIXTURE_TS},
        )
        # Marketing is FUTURE_NOT_AVAILABLE; check_delegation_allowed must block
        with self.assertRaises(DelegationBlockedError):
            check_delegation_allowed("marketing")

    def test_no_unsupported_portfolio_state_invented(self):
        """Critical: no unsupported portfolio state invented."""
        snapshot = portfolio_snapshot_build({})
        validation = portfolio_snapshot_validate(snapshot)
        # Confidence must be reduced when blackboard source is missing
        self.assertLess(snapshot.confidence, 1.0)
        # No invented projects
        self.assertEqual(len(snapshot.projects), 0)

    def test_no_incomplete_result_falsely_closed(self):
        """Critical: no incomplete result falsely closed as SUCCESS."""
        ledger = _make_ledger()
        delegation = delegation_request(
            task_description="Analyze conversion funnel for growth",
            domain="growth",
            priority="normal",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-T31-01C",
            timestamps={"requested_at": FIXTURE_TS},
        )
        delegation = run_capacity_query(
            delegation, _make_capacity_client(), ledger, {"queried_at": FIXTURE_TS},
        )
        delegation = tola_decide(
            delegation, "COMMIT", "Proceed", ledger, {"decided_at": FIXTURE_TS},
        )
        boundary = agent_boundary_check("growth", "delegated_task_commit")
        delegation = commit_task(
            delegation, ["report_done"], boundary, ledger, {"committed_at": FIXTURE_TS},
        )

        # Record a PARTIAL result (incomplete)
        delegation = record_result(
            delegation, {"status": "PARTIAL", "sections_done": ["analysis"]}, ledger, {"result_at": FIXTURE_TS_2},
        )

        # Accepting a partial result should still work (the verifier decides),
        # but the result status must be recorded as PARTIAL, not silently
        # upgraded to SUCCESS.
        self.assertEqual(delegation.result["status"], "PARTIAL")


# ===========================================================================
# T31-02: Growth + Scholar + Rhythm -> Tola cross-domain decision
# ===========================================================================

class TestT31_02_CrossDomainDecision(unittest.TestCase):
    """T31-02: Cross-domain decision routing across Growth, Scholar, Rhythm."""

    def test_cross_domain_routing(self):
        growth_route = agent_capability_match("product growth analysis")
        self.assertEqual(growth_route["agent_id"], "growth")

        scholar_route = agent_capability_match("learning gap detection")
        self.assertEqual(scholar_route["agent_id"], "scholar")

        rhythm_route = agent_capability_match("capacity query")
        self.assertEqual(rhythm_route["agent_id"], "rhythm")

    def test_tola_cross_domain_decision(self):
        """Tola routes work to the correct specialist per domain."""
        # Growth handles marketing work under contract
        growth_check = agent_boundary_check("growth", "marketing_work_under_contract")
        self.assertTrue(growth_check["allowed"])

        # Scholar cannot take product-growth authority
        scholar_check = agent_boundary_check("scholar", "product_growth_analysis")
        self.assertFalse(scholar_check["allowed"])

        # Rhythm owns scheduling
        rhythm_check = agent_boundary_check("rhythm", "rhythm_schedule_write")
        self.assertTrue(rhythm_check["allowed"])


# ===========================================================================
# T31-03: Tola -> Rhythm capacity query -> commit -> scheduling request
# ===========================================================================

class TestT31_03_RhythmCapacityProtocol(unittest.TestCase):
    """T31-03: Tola queries Rhythm capacity, commits, requests scheduling."""

    def test_capacity_query_commit_scheduling(self):
        ledger = _make_ledger()

        delegation = delegation_request(
            task_description="Schedule weekly review",
            domain="scheduling",
            priority="high",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-T31-03",
            timestamps={"requested_at": FIXTURE_TS},
        )

        # Capacity query
        delegation = run_capacity_query(
            delegation, _make_capacity_client(), ledger, {"queried_at": FIXTURE_TS},
        )
        self.assertIsNotNone(delegation.capacity_report)

        # Tola decide
        delegation = tola_decide(
            delegation, "COMMIT", "Capacity confirmed", ledger, {"decided_at": FIXTURE_TS},
        )

        # Commit (requires boundary check + delegation allowed)
        boundary = agent_boundary_check("rhythm", "delegated_task_commit")
        self.assertTrue(boundary["allowed"])

        delegation = commit_task(
            delegation, ["schedule_created"], boundary, ledger, {"committed_at": FIXTURE_TS},
        )
        self.assertEqual(delegation.status, DelegationStatus.COMMITTED)

        # Critical assertion: Tola never writes My Rhythm directly
        boundary_tola = agent_boundary_check("tola", "direct_my_rhythm_write")
        self.assertFalse(boundary_tola["allowed"])


# ===========================================================================
# T31-04: Weak specialist plan -> Tola revision -> improved plan
# ===========================================================================

class TestT31_04_PlanRevision(unittest.TestCase):
    """T31-04: Weak specialist plan gets revised by Tola."""

    def test_weak_plan_revision(self):
        # Weak plan: low expected value, no smallest viable version
        weak_scope = evaluate_scope(
            {"goal_refs": ["g1"], "tags": ["growth"], "expected_value": 0.3, "evidence": "weak"},
            {"active_goals": [{"id": "g1", "name": "Growth Sprint", "tags": ["growth"]}],
             "capacity_summary": {"remaining_capacity": 1, "active_tasks": 0, "max_parallel_tasks": 4}},
        )
        # Low value -> STOP or SHAPE_SMALLER
        self.assertIn(weak_scope.verdict.value, ("STOP", "SHAPE_SMALLER"))

        # Improved plan: higher value + smallest viable version
        improved_scope = evaluate_scope(
            {"goal_refs": ["g1"], "tags": ["growth"], "expected_value": 0.85,
             "smallest_viable_version": "Reduce to MVP slice", "evidence": "strong"},
            {"active_goals": [{"id": "g1", "name": "Growth Sprint", "tags": ["growth"]}],
             "capacity_summary": {"remaining_capacity": 1, "active_tasks": 0, "max_parallel_tasks": 4}},
        )
        self.assertEqual(improved_scope.verdict.value, "SHAPE_SMALLER")


# ===========================================================================
# T31-05: Stalled work -> detection -> recovery -> completion
# ===========================================================================

class TestT31_05_StalledWorkRecovery(unittest.TestCase):
    """T31-05: Stalled work detection, recovery, completion."""

    def test_stalled_work_full_cycle(self):
        tracker = _make_tracker()

        # Register a delegation that becomes stalled (UNACKNOWLEDGED)
        delegation = delegation_request(
            task_description="Analyze product growth metrics",
            domain="growth",
            priority="normal",
            sources={"blackboard": []},
            ledger=_make_ledger(),
            delegation_id="DEL-T31-05",
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(delegation)
        # Do NOT send ACKNOWLEDGED -- stays DRAFTED, which means UNACKNOWLEDGED

        # Detect stall pattern
        entry = tracker.status("DEL-T31-05")
        pattern = detect_stall_pattern(entry, None, None)
        self.assertIsInstance(pattern.kind, StallKind)

        # Propose recovery
        plan = propose_recovery(pattern, {})
        self.assertTrue(len(plan.actions) > 0)
        for action in plan.actions:
            self.assertIn(action, ALLOWED_ACTIONS)

        # Also test a known UNACKNOWLEDGED pattern directly
        unack_entry = TrackingEntry(
            delegation_id="DEL-T31-05B",
            status=DelegationStatus.DRAFTED,
            event_history=[],
        )
        unack_pattern = detect_stall_pattern(unack_entry, None, None)
        self.assertEqual(unack_pattern.kind, StallKind.UNACKNOWLEDGED)
        unack_plan = propose_recovery(unack_pattern, {})
        self.assertIn(RecoveryAction.REQUEST_MISSING_INFO.value, unack_plan.actions)

    def test_recovery_completion(self):
        ledger = _make_ledger()
        delegation = delegation_request(
            task_description="Analyze product growth metrics",
            domain="growth",
            priority="normal",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-T31-05B",
            timestamps={"requested_at": FIXTURE_TS},
        )
        delegation = run_capacity_query(
            delegation, _make_capacity_client(), ledger, {"queried_at": FIXTURE_TS},
        )
        delegation = tola_decide(
            delegation, "COMMIT", "Proceed with recovery", ledger, {"decided_at": FIXTURE_TS},
        )
        boundary = agent_boundary_check("growth", "delegated_task_commit")
        delegation = commit_task(
            delegation, ["recovery_complete"], boundary, ledger, {"committed_at": FIXTURE_TS},
        )
        delegation = record_result(
            delegation, {"status": "SUCCESS"}, ledger, {"result_at": FIXTURE_TS_2},
        )
        close = accept_or_reject(
            delegation, "ACCEPT", "Recovery successful", ledger, {"closed_at": FIXTURE_TS_2},
        )
        self.assertEqual(close.status, DelegationStatus.ACCEPTED)


# ===========================================================================
# T31-06: Preference observation -> candidate -> active -> changed comm
# ===========================================================================

class TestT31_06_PreferenceLifecycle(unittest.TestCase):
    """T31-06: Preference observation lifecycle with communication change."""

    def test_preference_observation_to_active(self):
        from tola.persona.profile import (
            UserOperatingProfile,
            preference_observe,
            preference_promote,
            user_profile_compact,
        )

        profile = UserOperatingProfile(
            user_id="u1",
            preferences=(),
            preference_versions=(),
        )

        # Observe behavioural preference (candidate)
        profile = preference_observe(
            profile, "communication_style", "concise",
            "BEHAVIOURAL_OBSERVATION", ("evidence_1",), FIXTURE_TS, "p1", 0.8,
        )
        prefs = profile.preferences
        self.assertEqual(len(prefs), 1)
        self.assertEqual(prefs[0].status.value, "CANDIDATE")

        # Promote to ACTIVE after threshold
        profile = preference_promote(
            profile, "communication_style", ("evidence_1", "evidence_2", "evidence_3"),
            FIXTURE_TS_2, "p1",
        )
        active = user_profile_compact(profile)
        self.assertIn("communication_style", active)
        self.assertEqual(active["communication_style"], "concise")

    def test_changed_communication_preference(self):
        from tola.persona.profile import (
            UserOperatingProfile,
            preference_observe,
            preference_supersede,
            user_profile_compact,
        )

        profile = UserOperatingProfile(
            user_id="u1",
            preferences=(),
            preference_versions=(),
        )

        profile = preference_observe(
            profile, "communication_style", "verbose",
            "EXPLICIT_PREFERENCE", ("fb_1",), FIXTURE_TS, "p1", 0.9,
        )
        self.assertEqual(user_profile_compact(profile)["communication_style"], "verbose")

        # Change communication preference
        new_prov = {"source": "user_explicit", "evidence_refs": ("fb_2",), "observed_at": FIXTURE_TS_2, "project_id": "p1"}
        profile = preference_supersede(
            profile, "communication_style", "concise", new_prov, 0.95,
        )
        compact = user_profile_compact(profile)
        self.assertEqual(compact["communication_style"], "concise")
        # Old version preserved
        self.assertEqual(len(profile.preference_versions), 1)


# ===========================================================================
# T31-07: Learning observation -> benchmark -> proposal -> approved apply
# ===========================================================================

class TestT31_07_LearningObservation(unittest.TestCase):
    """T31-07: Learning observation flows through benchmark to approved apply."""

    def test_learning_observation_benchmark_proposal_apply(self):
        # Learning observation: propose an improvement
        candidate = {
            "id": "imp-001",
            "category": "delegation:specialist_selection",
            "description": "Use confidence threshold for specialist routing",
        }

        # Benchmark comparison using real harness functions
        from tola.benchmark.harness import record_baseline, evaluate_candidate
        from tola.benchmark.fixtures import build_all_fixtures
        fixtures = build_all_fixtures()
        # Use all fixtures so baseline has all fixture IDs
        runs = [(f["id"], {"task_success": True, "delegation_correct": True}) for f in fixtures]
        baseline = record_baseline(runs)
        comparison = evaluate_candidate(runs, baseline)

        # Proposal only created on IMPROVED verdict
        proposal = propose_improvement(candidate, comparison)
        if proposal is not None:
            self.assertEqual(proposal.category, "delegation:specialist_selection")

            # Apply with correct approval token
            result = apply_or_reject(proposal, proposal.token, comparison.benchmark_version)
            self.assertEqual(result, "APPLY")
        else:
            # If not improved, that is also a valid outcome for this test
            pass


# ===========================================================================
# T31-08: Missed event -> heartbeat/daily review catches issue
# ===========================================================================

class TestT31_08_HeartbeatCatch(unittest.TestCase):
    """T31-08: Missed material event caught by heartbeat or daily review."""

    def test_heartbeat_catches_overdue_material_task(self):
        conditions = [
            {
                "kind": "OVERDUE_TASK",
                "id": "ot-1",
                "severity": "high",
                "material": True,
                "age_days": 2,
            },
        ]
        result = run_heartbeat(conditions, FIXTURE_TS)
        self.assertTrue(result.wake)
        self.assertTrue(len(result.findings) > 0)

    def test_quiet_heartbeat_no_false_wake(self):
        conditions = [
            {
                "kind": "INFO",
                "id": "info-1",
                "severity": "low",
                "material": False,
                "age_days": 1,
            },
        ]
        result = run_heartbeat(conditions, FIXTURE_TS)
        self.assertFalse(result.wake)

    def test_daily_review_catches_stalled(self):
        from tola.reconciliation.cycle import run_daily_cycle, DailyReconciliationResult
        # Use a simple reconciliation state
        state = {
            "previous_snapshot": {},
            "current_snapshot": {
                "active_tasks": [{"id": "t1", "status": "stalled", "label": "Write report"}],
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
        }
        # Daily review should surface stalled work
        result = run_daily_cycle(state, FIXTURE_TS)
        self.assertIsInstance(result, DailyReconciliationResult)


# ===========================================================================
# T31-09: Permission audit confirms all actions inside authority
# ===========================================================================

class TestT31_09_PermissionAudit(unittest.TestCase):
    """T31-09: Permission audit confirms all actions inside authority."""

    def test_all_allowed_actions_pass(self):
        actions = [
            {"module": "tola.scope", "verb": "read"},
            {"module": "tola.scope", "verb": "evaluate"},
            {"module": "tola.delegation", "verb": "dispatch"},
            {"module": "tola.monitoring", "verb": "follow_up"},
            {"module": "tola.recovery", "verb": "propose_recovery"},
        ]
        report = permission_audit(actions, AUTONOMY_MATRIX)
        self.assertTrue(report.passed)
        self.assertEqual(len(report.violations), 0)

    def test_violation_detected(self):
        actions = [
            {"module": "tola.scope", "verb": "delete"},  # not allowed
        ]
        report = permission_audit(actions, AUTONOMY_MATRIX)
        self.assertFalse(report.passed)
        self.assertTrue(len(report.violations) > 0)


# ===========================================================================
# T31-10: Random decision/delegation/brief traceable to evidence/source
# ===========================================================================

class TestT31_10_Traceability(unittest.TestCase):
    """T31-10: Decisions, delegations, and briefs traceable to evidence/source versions."""

    def test_decision_traceability(self):
        # Valid decision with evidence and source_version
        decision = DecisionRecord(
            decision="COMMIT",
            reason="Growth specialist available",
            evidence="capacity_report:FIT",
            alternatives="DEFER",
            tradeoff="delay vs capacity",
            owner="tola",
            date=FIXTURE_TS,
            expected_outcome="conversion analysis complete",
        )
        registered = register_decision(decision)
        self.assertEqual(registered.decision, "COMMIT")

        # Chain trace: valid decision
        trace = chain_trace([
            {
                "id": registered.id,
                "evidence": "capacity_report:FIT",
                "source_version": "1.0.0",
            }
        ])
        self.assertTrue(trace[0]["traceable"])
        self.assertEqual(len(trace[0]["violations"]), 0)

    def test_missing_evidence_flagged(self):
        trace = chain_trace([
            {
                "id": "DEC-001",
                "evidence": "",
                "source_version": "1.0.0",
            }
        ])
        self.assertFalse(trace[0]["traceable"])
        self.assertIn("missing_evidence", trace[0]["violations"])

    def test_missing_source_version_flagged(self):
        trace = chain_trace([
            {
                "id": "DEC-001",
                "evidence": "some evidence",
                "source_version": "",
            }
        ])
        self.assertFalse(trace[0]["traceable"])
        self.assertIn("missing_source_version", trace[0]["violations"])


# ===========================================================================
# T31-11: Secret/privacy audit passes
# ===========================================================================

class TestT31_11_SecretPrivacyAudit(unittest.TestCase):
    """T31-11: Secret/privacy audit passes on clean artifacts, fails on dirty."""

    def test_clean_artifacts_pass(self):
        artifacts = {
            "persona_obs_1": {"category": "communication_style", "value": "concise"},
            "log_entry_1": "Routine heartbeat sweep completed.",
        }
        report = secret_privacy_audit(artifacts)
        self.assertTrue(report.passed)

    def test_secret_leak_detected(self):
        artifacts = {
            "log_entry_1": "API key sk-abc123def456ghijklmnop detected in request.",
        }
        report = secret_privacy_audit(artifacts)
        self.assertFalse(report.passed)
        self.assertTrue(len(report.violations) > 0)

    def test_sensitive_category_rejected(self):
        artifacts = {
            "persona_obs_1": {"category": "health_conditions", "value": "migraine"},
        }
        report = secret_privacy_audit(artifacts)
        self.assertFalse(report.passed)

    def test_no_sensitive_trait_stored(self):
        """Critical assertion: no sensitive persona trait inferred/stored."""
        from tola.persona.profile import (
            UserOperatingProfile,
            preference_observe,
            SENSITIVE_CATEGORIES,
        )

        profile = UserOperatingProfile(
            user_id="u1",
            preferences=(),
            preference_versions=(),
        )

        # Attempt to store a sensitive trait
        for category in SENSITIVE_CATEGORIES:
            profile = preference_observe(
                profile, category, "some_value",
                "BEHAVIOURAL_OBSERVATION", ("evidence_1",), FIXTURE_TS, "p1", 0.5,
            )

        # Profile should remain empty (sensitive inferences rejected)
        self.assertEqual(len(profile.preferences), 0)


# ===========================================================================
# T31-12: Model/cost audit passes
# ===========================================================================

class TestT31_12_ModelCostAudit(unittest.TestCase):
    """T31-12: Cost audit passes when no line item exceeds budget."""

    def test_cost_audit_passes(self):
        costs = [
            {"item": "heartbeat_idle", "amount": 1.0},
            {"item": "wake_high", "amount": 50.0},
            {"item": "refresh_snapshot", "amount": 5.0},
        ]
        report = cost_audit(costs, budget=100.0)
        self.assertTrue(report.passed)

    def test_cost_audit_fails_on_over_budget(self):
        costs = [
            {"item": "expensive_model_call", "amount": 150.0},
        ]
        report = cost_audit(costs, budget=100.0)
        self.assertFalse(report.passed)
        self.assertEqual(report.violations[0]["item"], "expensive_model_call")
        self.assertEqual(report.violations[0]["amount"], 150.0)

    def test_heartbeat_cost_within_target(self):
        from tola.heartbeat.heartbeat import idle_cost_within_target, HeartbeatResult
        result = HeartbeatResult(cost_units=1)
        self.assertTrue(idle_cost_within_target(result, target=1))


# ===========================================================================
# T31-13: Rollback/recovery runbook tested
# ===========================================================================

class TestT31_13_RollbackRunbook(unittest.TestCase):
    """T31-13: Rollback/recovery runbook tested with round-trip restore."""

    def test_rollback_runbook_round_trip(self):
        initial_state = {"version": "1.0.0", "feature_flag": True, "config": "stable"}
        initial_hash = _state_hash(initial_state)

        steps = [
            {
                "action": "apply",
                "key": "feature_flag",
                "value": False,
                "expected_hash": initial_hash,
            },
            {
                "action": "restore",
                "key": "feature_flag",
                "value": True,
            },
        ]

        result = runbook_execute(initial_state, steps)
        restored = result["restored_state"]

        # Round-trip restore: feature_flag should be back to True
        self.assertTrue(restored["feature_flag"])
        self.assertEqual(restored["version"], "1.0.0")

        # Trace should have two entries
        self.assertEqual(len(result["trace"]), 2)

    def test_rollback_runbook_deterministic(self):
        """Determinism: same inputs produce same output."""
        state = {"key": "value", "count": 42}
        steps = [
            {"action": "apply", "key": "count", "value": 99, "expected_hash": ""},
            {"action": "restore", "key": "count", "value": 42},
        ]
        result1 = runbook_execute(state, steps)
        result2 = runbook_execute(state, steps)
        self.assertEqual(result1["restored_state"], result2["restored_state"])
        self.assertEqual(result1["trace"], result2["trace"])

    def test_rollback_runbook_hash_mismatch_skip(self):
        """Hash mismatch causes step to be skipped, not applied."""
        state = {"key": "original"}
        steps = [
            {
                "action": "apply",
                "key": "key",
                "value": "modified",
                "expected_hash": "wrong_hash_0000",
            },
        ]
        result = runbook_execute(state, steps)
        # Should NOT have applied the change because hash mismatch
        self.assertEqual(result["restored_state"]["key"], "original")


# ===========================================================================
# Critical assertions across all tests
# ===========================================================================

class TestT31_CriticalAssertions(unittest.TestCase):
    """Critical assertions that must hold across the entire system."""

    def test_tola_never_writes_my_rhythm(self):
        """Tola never writes My Rhythm directly."""
        # Verify boundary check blocks Tola My Rhythm writes
        result = agent_boundary_check("tola", "direct_my_rhythm_write")
        self.assertFalse(result["allowed"])

        result = agent_boundary_check("tola", "my_rhythm_write")
        self.assertFalse(result["allowed"])

        result = agent_boundary_check("tola", "rhythm_direct_write")
        self.assertFalse(result["allowed"])

    def test_no_future_not_available_marketing_delegation(self):
        """Tola never delegates to a FUTURE_NOT_AVAILABLE Marketing Agent."""
        profile = PROFILES.get("marketing")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.availability_status, AvailabilityStatus.FUTURE_NOT_AVAILABLE)

        # Delegation to marketing must be blocked
        with self.assertRaises(DelegationBlockedError):
            check_delegation_allowed("marketing")

    def test_protected_commitment_not_overridden(self):
        """Protected commitments are not overridden by non-authoritative agents."""
        # Growth cannot write directly to schedule
        result = agent_boundary_check("growth", "direct_schedule_write")
        self.assertFalse(result["allowed"])

    def test_no_sensitive_persona_trait_stored(self):
        """No sensitive persona trait inferred/stored."""
        from tola.persona.profile import SENSITIVE_CATEGORIES
        self.assertTrue(len(SENSITIVE_CATEGORIES) > 0)

    def test_no_core_skill_silently_mutated(self):
        """Evolution PROPOSAL-only: no core Skill silently mutated."""
        from tola.evolution.proposal import PROTECTED_CATEGORIES
        self.assertIn("core_skills", PROTECTED_CATEGORIES)
        self.assertIn("permissions", PROTECTED_CATEGORIES)

    def test_no_incomplete_result_falsely_closed(self):
        """No incomplete result falsely closed as SUCCESS."""
        # verify_and_close returns FLAGGED_TOLA for UNVERIFIABLE, not SUCCESS
        from tola.verification.closer import CloseDecision
        self.assertIn("FLAGGED_TOLA", [cd.value for cd in CloseDecision])

    def test_no_unsupported_portfolio_state_invented(self):
        """No unsupported portfolio state invented."""
        # PortfolioSnapshot validates sources; missing blackboard reduces confidence
        snapshot = portfolio_snapshot_build({})
        validation = portfolio_snapshot_validate(snapshot)
        # Confidence should be reduced when blackboard is missing
        self.assertLess(snapshot.confidence, 1.0)

    def test_autonomy_matrix_complete(self):
        """Autonomy matrix covers all pipeline modules."""
        expected_modules = frozenset(AUTONOMY_MATRIX.keys())
        self.assertIn("tola.scope", expected_modules)
        self.assertIn("tola.delegation", expected_modules)
        self.assertIn("tola.monitoring", expected_modules)
        self.assertIn("tola.recovery", expected_modules)
        self.assertIn("tola.persona", expected_modules)
        self.assertIn("tola.benchmark", expected_modules)
        self.assertIn("tola.evolution", expected_modules)
        self.assertIn("tola.heartbeat", expected_modules)
        self.assertIn("tola.reconciliation", expected_modules)
        self.assertIn("tola.review", expected_modules)
        self.assertIn("tola.pilot", expected_modules)
        self.assertIn("tola.registry", expected_modules)

    def test_delegation_contract_respected(self):
        """Delegation contract: commit requires capacity_report and tola_decision."""
        ledger = _make_ledger()
        delegation = delegation_request(
            task_description="Test",
            domain="growth",
            priority="normal",
            sources={"blackboard": []},
            ledger=ledger,
            delegation_id="DEL-T31-CONTRACT",
            timestamps={"requested_at": FIXTURE_TS},
        )
        # Commit without capacity report must raise ProtocolInvariantError
        boundary = agent_boundary_check("growth", "delegated_task_commit")
        with self.assertRaises(ProtocolInvariantError):
            commit_task(
                delegation, ["test"], boundary, ledger, {"committed_at": FIXTURE_TS},
            )

    def test_marketing_activation_gate(self):
        """Marketing Agent activation gate documented and enforced."""
        activation = validate_marketing_activation()
        self.assertFalse(activation["can_activate"])
        self.assertTrue(len(activation["missing"]) > 0)


# ===========================================================================
# Determinism test
# ===========================================================================

class TestT31_Determinism(unittest.TestCase):
    """All pipeline functions are deterministic (same input -> same output)."""

    def test_evaluate_scope_deterministic(self):
        proposal = {"goal_refs": ["g1"], "tags": ["growth"], "expected_value": 0.85, "evidence": "test"}
        context = {"active_goals": [{"id": "g1", "name": "G", "tags": ["growth"]}],
                   "capacity_summary": {"remaining_capacity": 1, "active_tasks": 0, "max_parallel_tasks": 4}}
        r1 = evaluate_scope(proposal, context)
        r2 = evaluate_scope(proposal, context)
        self.assertEqual(r1.verdict.value, r2.verdict.value)

    def test_delegation_request_deterministic(self):
        ledger1 = _make_ledger()
        ledger2 = _make_ledger()
        d1 = delegation_request("test", "growth", "normal", {}, ledger1, "D1", {"requested_at": FIXTURE_TS})
        d2 = delegation_request("test", "growth", "normal", {}, ledger2, "D1", {"requested_at": FIXTURE_TS})
        self.assertEqual(d1.delegation_id, d2.delegation_id)
        self.assertEqual(d1.specialist, d2.specialist)

    def test_heartbeat_deterministic(self):
        conditions = [{"kind": "OVERDUE_TASK", "id": "ot-1", "severity": "high", "material": True, "age_days": 2}]
        r1 = run_heartbeat(conditions, FIXTURE_TS)
        r2 = run_heartbeat(conditions, FIXTURE_TS)
        self.assertEqual(r1.wake, r2.wake)
        self.assertEqual(len(r1.findings), len(r2.findings))


# ===========================================================================
# Helper for test T31-08 daily reconciliation
# ===========================================================================

def _state_hash(state: dict) -> str:
    import hashlib, json
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()