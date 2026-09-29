"""QA T21 -- Improvement Ledger tests.

Covers T21-01..T21-07 as defined in tola_testing_plan_v1_1.md.
Stdlib only: unittest.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

import unittest

from tola.improvement.ledger import (
    ImprovementLedger,
    Observation,
    USER_CORRECTION,
    DELEGATION,
    BRIEFING,
)
from tola.improvement.candidates import (
    CandidateStore,
    candidate_from,
    LINK_MIN,
    MIN_PATTERN,
)


# ===========================================================================
# Fixtures
# ===========================================================================

TS = "2026-09-29T12:00:00"


def _user_correction_event(
    delegation_id: str = "d1",
    note: str = "wrong agent",
    event_id: str = "evt-uc-1",
) -> dict:
    return {
        "id": event_id,
        "kind": USER_CORRECTION,
        "subject": delegation_id,
        "note": note,
    }


def _delegation_failure_event(
    delegation_id: str = "d2",
    event_id: str = "evt-del-fail-1",
) -> dict:
    return {
        "id": event_id,
        "kind": DELEGATION,
        "subject": delegation_id,
        "delegation_id": delegation_id,
        "success": False,
        "retry_count": 1,
    }


def _delegation_success_event(
    delegation_id: str = "d3",
    event_id: str = "evt-del-ok-1",
) -> dict:
    return {
        "id": event_id,
        "kind": DELEGATION,
        "subject": delegation_id,
        "delegation_id": delegation_id,
        "success": True,
        "retry_count": 0,
    }


def _briefing_event(
    event_id: str = "evt-brief-1",
) -> dict:
    return {
        "id": event_id,
        "kind": BRIEFING,
        "subject": "standup",
    }


def _context(timestamp: str = TS) -> dict:
    return {"timestamp": timestamp, "source": "test"}


# ===========================================================================
# T21-01: User correction generates learning observation
# ===========================================================================

class TestT21_01_UserCorrectionObservation(unittest.TestCase):
    """T21-01: USER_CORRECTION event always generates an observation."""

    def test_correction_generates_observation(self):
        ledger = ImprovementLedger()
        event = _user_correction_event()
        result = ledger.observe(event, _context())
        self.assertIsInstance(result, Observation)
        self.assertEqual(result.kind, USER_CORRECTION)

    def test_correction_evidence_retained(self):
        ledger = ImprovementLedger()
        event = _user_correction_event(note="ambiguous scope")
        result = ledger.observe(event, _context())
        self.assertEqual(result.evidence["event_payload"]["note"], "ambiguous scope")

    def test_correction_has_observation_id(self):
        ledger = ImprovementLedger()
        event = _user_correction_event(event_id="uc-unique-1")
        result = ledger.observe(event, _context())
        self.assertIsNotNone(result.id)


# ===========================================================================
# T21-02: Delegation failure generates observation
# ===========================================================================

class TestT21_02_DelegationFailureObservation(unittest.TestCase):
    """T21-02: DELEGATION with success=False always generates an observation."""

    def test_failure_generates_observation(self):
        ledger = ImprovementLedger()
        event = _delegation_failure_event()
        result = ledger.observe(event, _context())
        self.assertIsInstance(result, Observation)
        self.assertEqual(result.kind, DELEGATION)

    def test_failure_evidence_retained(self):
        ledger = ImprovementLedger()
        event = _delegation_failure_event()
        result = ledger.observe(event, _context())
        self.assertEqual(result.evidence["event_payload"]["success"], False)
        self.assertEqual(result.evidence["event_payload"]["retry_count"], 1)

    def test_failure_has_root_cause_evidence(self):
        ledger = ImprovementLedger()
        event = _delegation_failure_event(delegation_id="d-fail-1")
        ctx = {"timestamp": TS, "source": "test", "agent": "specialist-a"}
        result = ledger.observe(event, ctx)
        self.assertEqual(result.evidence["context_refs"]["agent"], "specialist-a")


# ===========================================================================
# T21-03: Reusable success pattern may generate observation
# ===========================================================================

class TestT21_03_ReusableSuccessPattern(unittest.TestCase):
    """T21-03: DELEGATION success with reusable_pattern flag may generate."""

    def test_reusable_success_with_flag_generates_observation(self):
        ledger = ImprovementLedger()
        event = _delegation_success_event()
        ctx = dict(_context(), reusable_pattern=True)
        result = ledger.observe(event, ctx)
        self.assertIsInstance(result, Observation)
        self.assertEqual(result.kind, DELEGATION)

    def test_reusable_success_without_flag_returns_none(self):
        ledger = ImprovementLedger()
        event = _delegation_success_event()
        result = ledger.observe(event, _context())
        self.assertIsNone(result)

    def test_reusable_success_flag_false_returns_none(self):
        ledger = ImprovementLedger()
        event = _delegation_success_event()
        ctx = dict(_context(), reusable_pattern=False)
        result = ledger.observe(event, ctx)
        self.assertIsNone(result)


# ===========================================================================
# T21-04: One-off noise does not automatically become candidate
# ===========================================================================

class TestT21_04_OneOffNoise(unittest.TestCase):
    """T21-04: one-off noise returns None, never auto-becomes a candidate."""

    def test_briefing_no_anomaly_returns_none(self):
        ledger = ImprovementLedger()
        event = _briefing_event()
        result = ledger.observe(event, _context())
        self.assertIsNone(result)

    def test_single_success_no_pattern_flag_returns_none(self):
        ledger = ImprovementLedger()
        event = _delegation_success_event()
        result = ledger.observe(event, _context())
        self.assertIsNone(result)

    def test_noise_does_not_auto_become_candidate(self):
        store = CandidateStore()
        ledger = ImprovementLedger()
        event = _briefing_event()
        obs = ledger.observe(event, _context())
        self.assertIsNone(obs)
        self.assertEqual(store.count(), 0)

    def test_single_success_without_pattern_not_a_candidate(self):
        store = CandidateStore()
        ledger = ImprovementLedger()
        event = _delegation_success_event()
        obs = ledger.observe(event, _context())
        self.assertIsNone(obs)
        self.assertEqual(store.count(), 0)


# ===========================================================================
# T21-05: Root-cause evidence retained exactly
# ===========================================================================

class TestT21_05_RootCauseEvidenceRetained(unittest.TestCase):
    """T21-05: evidence fields equal input verbatim; never summarised."""

    def test_correction_evidence_verbatim(self):
        ledger = ImprovementLedger()
        event = _user_correction_event(note="agent was wrong for this task")
        ctx = {"timestamp": TS, "source": "user-feedback", "task": "t1"}
        result = ledger.observe(event, ctx)
        self.assertIsNotNone(result)
        self.assertEqual(result.evidence["event_payload"]["note"], "agent was wrong for this task")
        self.assertEqual(result.evidence["context_refs"]["source"], "user-feedback")
        self.assertEqual(result.evidence["context_refs"]["task"], "t1")

    def test_failure_evidence_verbatim(self):
        ledger = ImprovementLedger()
        event = _delegation_failure_event(delegation_id="d-evidence-1")
        ctx = {"timestamp": TS, "agent": "specialist-b", "reason": "timeout"}
        result = ledger.observe(event, ctx)
        self.assertIsNotNone(result)
        self.assertEqual(result.evidence["event_payload"]["delegation_id"], "d-evidence-1")
        self.assertEqual(result.evidence["context_refs"]["agent"], "specialist-b")
        self.assertEqual(result.evidence["context_refs"]["reason"], "timeout")

    def test_reusable_success_evidence_verbatim(self):
        ledger = ImprovementLedger()
        event = _delegation_success_event(delegation_id="d-pattern-1")
        ctx = dict(_context(), reusable_pattern=True, pattern_id="p-1")
        result = ledger.observe(event, ctx)
        self.assertIsNotNone(result)
        self.assertEqual(result.evidence["event_payload"]["delegation_id"], "d-pattern-1")
        self.assertEqual(result.evidence["context_refs"]["pattern_id"], "p-1")


# ===========================================================================
# T21-06: Candidate links to underlying observation ids
# ===========================================================================

class TestT21_06_CandidateLinksObservations(unittest.TestCase):
    """T21-06: candidate links to observation ids and retains evidence chain."""

    def test_correction_candidate_links_to_observation(self):
        ledger = ImprovementLedger()
        event = _user_correction_event(event_id="uc-link-1")
        obs = ledger.observe(event, _context())
        self.assertIsNotNone(obs)
        store = CandidateStore()
        cand = store.promote(obs)
        self.assertIn(obs.id, cand.observation_ids)
        self.assertEqual(cand.observation_ids, (obs.id,))

    def test_failure_candidate_links_to_observation(self):
        ledger = ImprovementLedger()
        event = _delegation_failure_event(event_id="del-fail-link-1")
        obs = ledger.observe(event, _context())
        self.assertIsNotNone(obs)
        store = CandidateStore()
        cand = store.promote(obs)
        self.assertIn(obs.id, cand.observation_ids)

    def test_candidate_retains_evidence_refs(self):
        ledger = ImprovementLedger()
        event = _user_correction_event(event_id="uc-evidence-link-1")
        obs = ledger.observe(event, _context())
        store = CandidateStore()
        cand = store.promote(obs)
        self.assertIn("primary_event_payload", cand.evidence_refs)
        self.assertIn("primary_context_refs", cand.evidence_refs)

    def test_insufficient_success_raises(self):
        ledger = ImprovementLedger()
        event = _delegation_success_event(event_id="del-ok-insuff")
        ctx = dict(_context(), reusable_pattern=True)
        obs = ledger.observe(event, ctx)
        self.assertIsNotNone(obs)
        with self.assertRaises(ValueError):
            candidate_from(obs, supporting=())

    def test_sufficient_reusable_success_creates_candidate(self):
        ledger = ImprovementLedger()
        store = CandidateStore()
        # Create 3 supporting reusable success observations
        supporting = []
        for i in range(3):
            ev = _delegation_success_event(event_id=f"del-ok-supp-{i}")
            ctx = dict(_context(), reusable_pattern=True)
            o = ledger.observe(ev, ctx)
            self.assertIsNotNone(o)
            supporting.append(o)
        # Primary also reusable success
        primary_ev = _delegation_success_event(event_id="del-ok-primary")
        primary_obs = ledger.observe(primary_ev, dict(_context(), reusable_pattern=True))
        self.assertIsNotNone(primary_obs)
        cand = store.promote(primary_obs, supporting=tuple(supporting))
        self.assertEqual(len(cand.observation_ids), 4)


# ===========================================================================
# T21-07: Duplicate observation deduplicated / idempotent
# ===========================================================================

class TestT21_07_DeduplicationIdempotency(unittest.TestCase):
    """T21-07: duplicate observe() returns same observation; ledger unchanged."""

    def test_duplicate_same_id_returns_same_observation(self):
        ledger = ImprovementLedger()
        event = _user_correction_event(event_id="dup-uc-1")
        obs1 = ledger.observe(event, _context())
        obs2 = ledger.observe(event, _context())
        self.assertIs(obs1, obs2)
        self.assertEqual(obs1.id, obs2.id)

    def test_duplicate_same_id_ledger_count_unchanged(self):
        ledger = ImprovementLedger()
        event = _user_correction_event(event_id="dup-count-1")
        ledger.observe(event, _context())
        count_before = ledger.count()
        ledger.observe(event, _context())
        self.assertEqual(ledger.count(), count_before)

    def test_duplicate_same_content_hash_returns_same(self):
        ledger = ImprovementLedger()
        event = _user_correction_event(event_id="dup-hash-1")
        obs1 = ledger.observe(event, _context())
        obs2 = ledger.observe(event, _context())
        self.assertEqual(obs1.id, obs2.id)

    def test_different_events_produce_different_observations(self):
        ledger = ImprovementLedger()
        e1 = _user_correction_event(event_id="diff-1")
        e2 = _user_correction_event(event_id="diff-2")
        o1 = ledger.observe(e1, _context())
        o2 = ledger.observe(e2, _context())
        self.assertNotEqual(o1.id, o2.id)
        self.assertEqual(ledger.count(), 2)

    def test_idempotency_across_multiple_calls(self):
        ledger = ImprovementLedger()
        event = _user_correction_event(event_id="idem-1")
        ctx = _context()
        results = [ledger.observe(event, ctx) for _ in range(5)]
        self.assertTrue(all(r is results[0] for r in results))
        self.assertEqual(ledger.count(), 1)


# ===========================================================================
# Determinism
# ===========================================================================

class TestT21_Determinism(unittest.TestCase):
    """Same inputs always produce the same outputs."""

    def test_correction_deterministic(self):
        ledger1 = ImprovementLedger()
        ledger2 = ImprovementLedger()
        event = _user_correction_event(event_id="det-uc-1")
        r1 = ledger1.observe(event, _context())
        r2 = ledger2.observe(event, _context())
        self.assertEqual(r1.id, r2.id)
        self.assertEqual(r1.kind, r2.kind)
        self.assertEqual(r1.evidence, r2.evidence)

    def test_failure_deterministic(self):
        ledger1 = ImprovementLedger()
        ledger2 = ImprovementLedger()
        event = _delegation_failure_event(event_id="det-del-fail-1")
        r1 = ledger1.observe(event, _context())
        r2 = ledger2.observe(event, _context())
        self.assertEqual(r1.id, r2.id)

    def test_candidate_promotion_deterministic(self):
        ledger = ImprovementLedger()
        event = _user_correction_event(event_id="det-cand-1")
        obs = ledger.observe(event, _context())
        store1 = CandidateStore()
        store2 = CandidateStore()
        c1 = store1.promote(obs)
        c2 = store2.promote(obs)
        self.assertEqual(c1.id, c2.id)
        self.assertEqual(c1.observation_ids, c2.observation_ids)


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    unittest.main()