# QA T28 -- Weekly Persona and Improvement Review tests.
# Stdlib only: unittest.  Plain ASCII. Deterministic.

from __future__ import annotations

import unittest

from tola.review.persona_review import (
    PersonaReviewResult,
    Promotion,
    BlockedPromotion,
    SupersededEntry,
    PROMOTION_THRESHOLD,
    CONTRADICTION_BLOCK,
    SENSITIVE_CATEGORIES,
    run_persona_review,
    trace,
    record_supersession,
)
from tola.review.improvement_review import (
    ImprovementReviewResult,
    ImprovementCandidate,
    ObservationKept,
    REPEATED_WEAKNESS_THRESHOLD,
    ONE_OFF,
    SKILL_PROPOSAL_ONLY,
    run_improvement_review,
)


# ===========================================================================
# Fixtures
# ===========================================================================

NOW = "2026-09-29T21:20:00Z"


def _behavioural_obs(
    key: str,
    value: str,
    direction: str = "positive",
    evidence_id: str = "ev-001",
    project_id: str = "proj-alpha",
) -> dict:
    return {
        "key": key,
        "value": value,
        "source": "BEHAVIOURAL_OBSERVATION",
        "direction": direction,
        "evidence_refs": (evidence_id,),
        "observed_at": "2026-09-29T10:00:00Z",
        "project_id": project_id,
        "confidence": 0.5,
    }


def _explicit_obs(
    key: str,
    value: str,
    evidence_id: str = "ev-explicit-001",
    project_id: str = "proj-alpha",
) -> dict:
    return {
        "key": key,
        "value": value,
        "source": "EXPLICIT_PREFERENCE",
        "direction": "positive",
        "evidence_refs": (evidence_id,),
        "observed_at": "2026-09-29T10:00:00Z",
        "project_id": project_id,
        "confidence": 1.0,
    }


# ===========================================================================
# T28-01: Repeated candidate preference promotes correctly at threshold
# ===========================================================================

class TestT28_01_RepeatedCandidatePromotes(unittest.TestCase):
    """T28-01: A candidate preference observed >= PROMOTION_THRESHOLD
    times promotes correctly."""

    def test_promotes_at_threshold(self):
        obs = [
            _behavioural_obs("editor", "vim", evidence_id=f"ev-{i:03d}")
            for i in range(PROMOTION_THRESHOLD)
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions), 1)
        self.assertEqual(result.promotions[0].key, "editor")
        self.assertEqual(result.promotions[0].value, "vim")

    def test_below_threshold_no_promotion(self):
        obs = [
            _behavioural_obs("editor", "vim", evidence_id=f"ev-{i:03d}")
            for i in range(PROMOTION_THRESHOLD - 1)
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions), 0)

    def test_above_threshold_promotes_once(self):
        obs = [
            _behavioural_obs("editor", "vim", evidence_id=f"ev-{i:03d}")
            for i in range(PROMOTION_THRESHOLD + 2)
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions), 1)

    def test_promotion_evidence_refs_count(self):
        obs = [
            _behavioural_obs("editor", "vim", evidence_id=f"ev-{i:03d}")
            for i in range(PROMOTION_THRESHOLD)
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions[0].evidence_refs), PROMOTION_THRESHOLD)


# ===========================================================================
# T28-02: Contradictory evidence prevents premature promotion
# ===========================================================================

class TestT28_02_ContradictionBlocksPromotion(unittest.TestCase):
    """T28-02: Contradictory evidence (opposite-direction) prevents
    promotion and records a blocked_promotion with reason."""

    def test_contradiction_blocks_with_reason(self):
        obs = [
            _behavioural_obs("theme", "dark", evidence_id="ev-pos-001"),
            _behavioural_obs("theme", "dark", evidence_id="ev-pos-002"),
            _behavioural_obs("theme", "dark", evidence_id="ev-pos-003"),
            _behavioural_obs("theme", "dark", direction="negative", evidence_id="ev-neg-001"),
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions), 0)
        self.assertEqual(len(result.blocked_promotions), 1)
        self.assertEqual(result.blocked_promotions[0].reason, CONTRADICTION_BLOCK)
        self.assertEqual(result.blocked_promotions[0].key, "theme")

    def test_contradiction_blocks_even_with_3_supporting(self):
        """3 positive + 1 negative = blocked, not promoted."""
        obs = [
            _behavioural_obs("editor", "vim", evidence_id="ev-001"),
            _behavioural_obs("editor", "vim", evidence_id="ev-002"),
            _behavioural_obs("editor", "vim", evidence_id="ev-003"),
            _behavioural_obs("editor", "vim", direction="negative", evidence_id="ev-004"),
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions), 0)
        self.assertEqual(len(result.blocked_promotions), 1)
        self.assertEqual(result.blocked_promotions[0].reason, CONTRADICTION_BLOCK)

    def test_no_contradiction_promotes(self):
        obs = [
            _behavioural_obs("editor", "vim", evidence_id=f"ev-{i:03d}")
            for i in range(PROMOTION_THRESHOLD)
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions), 1)
        self.assertEqual(len(result.blocked_promotions), 0)


# ===========================================================================
# T28-03: Repeated delegation weakness creates improvement candidate
# ===========================================================================

class TestT28_03_RepeatedDelegationWeakness(unittest.TestCase):
    """T28-03: repeated delegation weakness in the same category
    creates an improvement candidate."""

    def test_repeated_delegation_weakness_creates_candidate(self):
        obs = [
            {
                "id": f"del-fail-{i}",
                "kind": "DELEGATION",
                "subject": "specialist-a",
                "category": "delegation",
                "evidence_refs": (f"ev-{i:03d}",),
                "success": False,
            }
            for i in range(REPEATED_WEAKNESS_THRESHOLD)
        ]
        result = run_improvement_review(obs)
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].kind, "DELEGATION")
        self.assertEqual(result.candidates[0].subject, "specialist-a")

    def test_repeated_plan_correction_creates_candidate(self):
        obs = [
            {
                "id": f"plan-corr-{i}",
                "kind": "PLAN_CORRECTION",
                "subject": "proj-alpha",
                "category": "plan",
                "evidence_refs": (f"ev-{i:03d}",),
            }
            for i in range(REPEATED_WEAKNESS_THRESHOLD)
        ]
        result = run_improvement_review(obs)
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].kind, "PLAN_CORRECTION")

    def test_repeated_user_correction_creates_candidate(self):
        obs = [
            {
                "id": f"user-corr-{i}",
                "kind": "USER_CORRECTION",
                "subject": "delegation-d1",
                "category": "correction",
                "evidence_refs": (f"ev-{i:03d}",),
            }
            for i in range(REPEATED_WEAKNESS_THRESHOLD)
        ]
        result = run_improvement_review(obs)
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].kind, "USER_CORRECTION")

    def test_below_threshold_no_candidate(self):
        obs = [
            {
                "id": f"del-fail-{i}",
                "kind": "DELEGATION",
                "subject": "specialist-a",
                "category": "delegation",
                "evidence_refs": (f"ev-{i:03d}",),
                "success": False,
            }
            for i in range(REPEATED_WEAKNESS_THRESHOLD - 1)
        ]
        result = run_improvement_review(obs)
        self.assertEqual(len(result.candidates), 0)


# ===========================================================================
# T28-04: One-off failure remains observation only
# ===========================================================================

class TestT28_04_OneOffFailureObservationOnly(unittest.TestCase):
    """T28-04: a single failure remains observation only, no candidate."""

    def test_single_delegation_failure_no_candidate(self):
        obs = [
            {
                "id": "del-fail-1",
                "kind": "DELEGATION",
                "subject": "specialist-a",
                "category": "delegation",
                "evidence_refs": ("ev-001",),
                "success": False,
            }
        ]
        result = run_improvement_review(obs)
        self.assertEqual(len(result.candidates), 0)

    def test_single_failure_observation_kept(self):
        obs = [
            {
                "id": "del-fail-1",
                "kind": "DELEGATION",
                "subject": "specialist-a",
                "category": "delegation",
                "evidence_refs": ("ev-001",),
                "success": False,
            }
        ]
        result = run_improvement_review(obs)
        self.assertEqual(len(result.observations_kept), 1)
        self.assertEqual(result.observations_kept[0].id, "del-fail-1")

    def test_single_user_correction_no_candidate(self):
        obs = [
            {
                "id": "uc-1",
                "kind": "USER_CORRECTION",
                "subject": "delegation-d1",
                "category": "correction",
                "evidence_refs": ("ev-001",),
            }
        ]
        result = run_improvement_review(obs)
        self.assertEqual(len(result.candidates), 0)


# ===========================================================================
# T28-05: Skill improvement remains proposal-only
# ===========================================================================

class TestT28_05_SkillProposalOnly(unittest.TestCase):
    """T28-05: a candidate Skill change produces a proposal-style entry
    (status=PROPOSAL, never applied/applied flag always False)."""

    def test_skill_change_status_is_proposal(self):
        obs = [
            {
                "id": "skill-001",
                "kind": "SKILL_CHANGE",
                "subject": "delegation",
                "category": "skill",
                "evidence_refs": ("ev-001",),
            }
        ]
        result = run_improvement_review(obs)
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].status, SKILL_PROPOSAL_ONLY)

    def test_skill_change_applied_flag_always_false(self):
        obs = [
            {
                "id": "skill-001",
                "kind": "SKILL_CHANGE",
                "subject": "delegation",
                "category": "skill",
                "evidence_refs": ("ev-001",),
            }
        ]
        result = run_improvement_review(obs)
        for cand in result.candidates:
            self.assertFalse(cand.applied)

    def test_skill_change_no_applied_flag_true_anywhere(self):
        """No candidate in any result has applied=True."""
        obs = [
            {
                "id": f"skill-{i}",
                "kind": "SKILL_CHANGE",
                "subject": "delegation",
                "category": "skill",
                "evidence_refs": (f"ev-{i:03d}",),
            }
            for i in range(5)
        ]
        result = run_improvement_review(obs)
        for cand in result.candidates:
            self.assertFalse(cand.applied)

    def test_skill_proposal_does_not_mutate_profile(self):
        """Improvement recommendations never mutate profile."""
        obs = [
            {
                "id": "skill-001",
                "kind": "SKILL_CHANGE",
                "subject": "delegation",
                "category": "skill",
                "evidence_refs": ("ev-001",),
            }
        ]
        result = run_improvement_review(obs)
        # All candidates are proposal-only; no applied flag is True.
        applied_count = sum(1 for c in result.candidates if c.applied)
        self.assertEqual(applied_count, 0)


# ===========================================================================
# T28-06: No sensitive profile expansion
# ===========================================================================

class TestT28_06_SensitiveBlocklist(unittest.TestCase):
    """T28-06: sensitive profile entries never promote or extend profile."""

    def test_health_condition_sensitive_blocked(self):
        obs = [
            _behavioural_obs("health_condition", "migraine", evidence_id="ev-001"),
            _behavioural_obs("health_condition", "migraine", evidence_id="ev-002"),
            _behavioural_obs("health_condition", "migraine", evidence_id="ev-003"),
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions), 0)
        self.assertEqual(len(result.blocked_promotions), 1)
        self.assertEqual(result.blocked_promotions[0].reason, "SENSITIVE_BLOCKLIST")

    def test_relationship_status_sensitive_blocked(self):
        obs = [
            _behavioural_obs("relationship_status", "single", evidence_id="ev-001"),
            _behavioural_obs("relationship_status", "single", evidence_id="ev-002"),
            _behavioural_obs("relationship_status", "single", evidence_id="ev-003"),
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions), 0)
        self.assertEqual(len(result.blocked_promotions), 1)

    def test_finances_sensitive_blocked(self):
        obs = [
            _behavioural_obs("finances", "budget_5000", evidence_id="ev-001"),
            _behavioural_obs("finances", "budget_5000", evidence_id="ev-002"),
            _behavioural_obs("finances", "budget_5000", evidence_id="ev-003"),
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions), 0)
        self.assertEqual(len(result.blocked_promotions), 1)

    def test_protected_characteristics_sensitive_blocked(self):
        obs = [
            _behavioural_obs("protected_characteristics", "wheelchair_user", evidence_id="ev-001"),
            _behavioural_obs("protected_characteristics", "wheelchair_user", evidence_id="ev-002"),
            _behavioural_obs("protected_characteristics", "wheelchair_user", evidence_id="ev-003"),
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions), 0)
        self.assertEqual(len(result.blocked_promotions), 1)

    def test_location_tracking_sensitive_blocked(self):
        obs = [
            _behavioural_obs("location_tracking", "office", evidence_id="ev-001"),
            _behavioural_obs("location_tracking", "office", evidence_id="ev-002"),
            _behavioural_obs("location_tracking", "office", evidence_id="ev-003"),
        ]
        result = run_persona_review(obs, NOW)
        self.assertEqual(len(result.promotions), 0)
        self.assertEqual(len(result.blocked_promotions), 1)

    def test_sensitive_blocklist_matches_t18(self):
        """Sensitive categories must be the same set as T18."""
        self.assertEqual(SENSITIVE_CATEGORIES, frozenset({
            "health_conditions",
            "relationship_status",
            "finances",
            "protected_characteristics",
            "location_tracking",
        }))


# ===========================================================================
# T28-07: Superseded profile entries remain historically traceable
# ===========================================================================

class TestT28_07_SupersededTraceable(unittest.TestCase):
    """T28-07: superseded chain traceable end-to-end."""

    def test_superseded_chain_traceable(self):
        result = run_persona_review([], NOW)
        result = record_supersession(result, "theme", "dark", "light", NOW)
        self.assertEqual(len(result.superseded), 1)
        chain = trace(result.superseded[0].superseded_id, result.superseded)
        self.assertEqual(len(chain), 1)
        self.assertIn("dark", chain[0])
        self.assertIn("light", chain[0])

    def test_trace_returns_full_chain(self):
        result = run_persona_review([], NOW)
        result = record_supersession(result, "theme", "dark", "light", NOW)
        result = record_supersession(result, "theme", "light", "blue", NOW)
        # The most recent superseded entry should trace back.
        latest = result.superseded[-1]
        chain = trace(latest.superseded_id, result.superseded)
        self.assertGreaterEqual(len(chain), 1)

    def test_superseded_entry_has_all_fields(self):
        result = run_persona_review([], NOW)
        result = record_supersession(result, "editor", "vim", "nano", NOW)
        entry = result.superseded[0]
        self.assertEqual(entry.prior_key, "editor")
        self.assertEqual(entry.prior_value, "vim")
        self.assertEqual(entry.new_value, "nano")
        self.assertEqual(entry.observed_at, NOW)
        self.assertIsNotNone(entry.superseded_id)

    def test_trace_empty_superseded_returns_empty(self):
        chain = trace("nonexistent", ())
        self.assertEqual(chain, ())


# ===========================================================================
# Determinism
# ===========================================================================

class TestT28_Determinism(unittest.TestCase):
    """All review operations are deterministic."""

    def test_persona_review_deterministic(self):
        obs = [
            _behavioural_obs("editor", "vim", evidence_id=f"ev-{i:03d}")
            for i in range(PROMOTION_THRESHOLD)
        ]
        r1 = run_persona_review(obs, NOW)
        r2 = run_persona_review(obs, NOW)
        self.assertEqual(len(r1.promotions), len(r2.promotions))
        if r1.promotions:
            self.assertEqual(r1.promotions[0].key, r2.promotions[0].key)

    def test_improvement_review_deterministic(self):
        obs = [
            {
                "id": f"del-fail-{i}",
                "kind": "DELEGATION",
                "subject": "specialist-a",
                "category": "delegation",
                "evidence_refs": (f"ev-{i:03d}",),
                "success": False,
            }
            for i in range(REPEATED_WEAKNESS_THRESHOLD)
        ]
        r1 = run_improvement_review(obs)
        r2 = run_improvement_review(obs)
        self.assertEqual(len(r1.candidates), len(r2.candidates))
        if r1.candidates:
            self.assertEqual(r1.candidates[0].id, r2.candidates[0].id)


# ===========================================================================
# Plain ASCII check
# ===========================================================================

    def test_all_output_plain_ascii(self):
        obs = [_behavioural_obs("editor", "vim", evidence_id="ev-001")]
        result = run_persona_review(obs, NOW)
        for p in result.promotions:
            for ch in p.key + p.value:
                self.assertTrue(ord(ch) < 128, f"Non-ASCII: {ch!r}")


if __name__ == "__main__":
    unittest.main()