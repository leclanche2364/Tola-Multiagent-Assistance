"""QA T8 -- Escalation Matrix and Stop Rules tests.

Covers T8-01..T8-09 as defined for Batch T8.
Stdlib only: unittest.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

import unittest

from tola.escalation.matrix import (
    EscalationLevel,
    EscalationDecision,
    TriggerContext,
    EscalationMatrix,
    BLOCKED_CHAIN_LENGTH_THRESHOLD,
    BOUNDARY_VIOLATION_REPEAT_THRESHOLD,
    MATERIALITY_THRESHOLD,
)
from tola.escalation.stop_rules import (
    StopDecision,
    should_stop,
    StopRules,
)
from tola.escalation.notify import (
    route_escalation,
    ROUTING_TABLE,
)


# ===========================================================================
# Fixtures
# ===========================================================================

def _make_context(**kwargs) -> TriggerContext:
    """Default context with no triggers active."""
    defaults = dict(
        health_label=None,
        t7_propagation_result=None,
        t5_delegation_status=None,
        t4_boundary_violations=None,
        blocked_chain_length=0,
        boundary_violation_count=0,
        materiality_score=1.0,
        explicit_user_stop=False,
        delegation_to_inactive_specialist=False,
    )
    defaults.update(kwargs)
    return TriggerContext(**defaults)


# ===========================================================================
# T8-01: Each trigger level maps correctly
# ===========================================================================

class TestT8_01_TriggerLevelMapping(unittest.TestCase):
    """T8-01: Each escalation trigger maps to the correct level."""

    def test_blocked_health_label_maps_to_stop_and_escalate(self):
        ctx = _make_context(health_label="BLOCKED")
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.STOP_AND_ESCALATE)

    def test_at_risk_health_label_maps_to_flag(self):
        ctx = _make_context(health_label="AT_RISK")
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.FLAG)

    def test_attention_health_label_maps_to_note(self):
        ctx = _make_context(health_label="ATTENTION")
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.NOTE)

    def test_on_track_health_label_maps_to_note(self):
        ctx = _make_context(health_label="ON_TRACK")
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.NOTE)

    def test_dormant_health_label_maps_to_flag(self):
        ctx = _make_context(health_label="DORMANT")
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.FLAG)

    def test_critical_propagation_maps_to_stop_and_escalate(self):
        ctx = _make_context(t7_propagation_result="CRITICAL")
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.STOP_AND_ESCALATE)

    def test_high_propagation_maps_to_flag(self):
        ctx = _make_context(t7_propagation_result="HIGH")
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.FLAG)

    def test_medium_propagation_maps_to_note(self):
        ctx = _make_context(t7_propagation_result="MEDIUM")
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.NOTE)

    def test_rejected_delegation_maps_to_flag(self):
        ctx = _make_context(t5_delegation_status="REJECTED")
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.FLAG)

    def test_stalled_delegation_maps_to_pause(self):
        ctx = _make_context(t5_delegation_status="STALLED")
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.PAUSE)


# ===========================================================================
# T8-02: Boundary violation always stops
# ===========================================================================

class TestT8_02_BoundaryViolationAlwaysStops(unittest.TestCase):
    """T8-02: Any boundary violation from T4 always produces
    STOP_AND_ESCALATE regardless of other context."""

    def test_single_boundary_violation_stops(self):
        ctx = _make_context(t4_boundary_violations=["domain_overreach"])
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.STOP_AND_ESCALATE)

    def test_boundary_violation_with_healthy_label_stops(self):
        ctx = _make_context(
            health_label="ON_TRACK",
            t4_boundary_violations=["unauthorised_tool_use"],
        )
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.STOP_AND_ESCALATE)

    def test_boundary_violation_with_explicit_user_stop_stops(self):
        ctx = _make_context(
            explicit_user_stop=True,
            t4_boundary_violations=["boundary_breach"],
        )
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.STOP_AND_ESCALATE)

    def test_boundary_violation_evidence_contains_violation(self):
        ctx = _make_context(t4_boundary_violations=["forbidden_domain"])
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertIn("forbidden_domain", str(decision.evidence))


# ===========================================================================
# T8-03: Healthy work never triggers stop (false-positive check)
# ===========================================================================

class TestT8_03_HealthyWorkNoFalseStop(unittest.TestCase):
    """T8-03: Healthy ON_TRACK work must never trigger a stop."""

    def test_on_track_no_stop(self):
        ctx = _make_context(health_label="ON_TRACK")
        decision = should_stop(ctx)
        self.assertFalse(decision.stop)

    def test_on_track_with_material_score_no_stop(self):
        ctx = _make_context(
            health_label="ON_TRACK",
            materiality_score=0.9,
        )
        decision = should_stop(ctx)
        self.assertFalse(decision.stop)

    def test_on_track_with_note_escalation_no_stop(self):
        ctx = _make_context(
            health_label="ON_TRACK",
            t5_delegation_status="IN_PROGRESS",
        )
        decision = should_stop(ctx)
        self.assertFalse(decision.stop)

    def test_attention_no_stop(self):
        ctx = _make_context(health_label="ATTENTION")
        decision = should_stop(ctx)
        self.assertFalse(decision.stop)

    def test_completed_delegation_no_stop(self):
        ctx = _make_context(t5_delegation_status="COMPLETED")
        decision = should_stop(ctx)
        self.assertFalse(decision.stop)


# ===========================================================================
# T8-04: Minor items do-not-escalate
# ===========================================================================

class TestT8_04_MinorItemsDoNotEscalate(unittest.TestCase):
    """T8-04: Cosmetic / no-material-impact items must not trigger
    escalation stop (do-not-escalate rule)."""

    def test_cosmetic_materiality_below_threshold_no_stop(self):
        ctx = _make_context(
            health_label="BLOCKED",
            materiality_score=0.1,
        )
        decision = EscalationMatrix.evaluate_escalation(ctx)
        # Materiality below threshold caps at FLAG, not STOP.
        self.assertNotEqual(
            decision.level, EscalationLevel.STOP_AND_ESCALATE
        )

    def test_cosmic_materiality_caps_at_flag(self):
        ctx = _make_context(
            t7_propagation_result="CRITICAL",
            materiality_score=0.2,
        )
        decision = EscalationMatrix.evaluate_escalation(ctx)
        # Even CRITICAL propagation is capped to FLAG for minor items.
        self.assertEqual(decision.level, EscalationLevel.FLAG)

    def test_stop_rules_do_not_fire_for_minor_items(self):
        ctx = _make_context(
            health_label="BLOCKED",
            materiality_score=0.15,
        )
        decision = should_stop(ctx)
        # Minor items should not trigger stop even if BLOCKED.
        self.assertFalse(decision.stop)

    def test_material_above_threshold_can_stop(self):
        ctx = _make_context(
            health_label="BLOCKED",
            materiality_score=0.8,
        )
        decision = should_stop(ctx)
        # Material items CAN trigger stop.
        self.assertTrue(decision.stop)


# ===========================================================================
# T8-05: Escalation routing targets correct recipient
# ===========================================================================

class TestT8_05_EscalationRouting(unittest.TestCase):
    """T8-05: Escalation routing targets the correct recipient agent/class."""

    def test_note_routes_to_owning_specialist(self):
        decision = EscalationDecision(
            level=EscalationLevel.NOTE,
            reason="test",
            evidence=[],
            recipient_class="OWNING_SPECIALIST",
        )
        result = route_escalation(decision)
        self.assertEqual(result.recipient_agent, "owning_specialist")
        self.assertEqual(result.recipient_class, "OWNING_SPECIALIST")

    def test_flag_routes_to_owning_specialist(self):
        decision = EscalationDecision(
            level=EscalationLevel.FLAG,
            reason="test",
            evidence=[],
            recipient_class="OWNING_SPECIALIST",
        )
        result = route_escalation(decision)
        self.assertEqual(result.recipient_agent, "owning_specialist")

    def test_pause_routes_to_tola(self):
        decision = EscalationDecision(
            level=EscalationLevel.PAUSE,
            reason="test",
            evidence=[],
            recipient_class="TOLA",
        )
        result = route_escalation(decision)
        self.assertEqual(result.recipient_agent, "tola")
        self.assertEqual(result.recipient_class, "TOLA")

    def test_stop_and_escalate_routes_to_habeeb(self):
        decision = EscalationDecision(
            level=EscalationLevel.STOP_AND_ESCALATE,
            reason="test",
            evidence=[],
            recipient_class="HABEEB",
        )
        result = route_escalation(decision)
        self.assertEqual(result.recipient_agent, "habeeb")
        self.assertEqual(result.recipient_class, "HABEEB")

    def test_message_skeleton_contains_reason(self):
        decision = EscalationDecision(
            level=EscalationLevel.STOP_AND_ESCALATE,
            reason="boundary violation detected",
            evidence=["violation_1"],
            recipient_class="HABEEB",
        )
        result = route_escalation(decision)
        self.assertIn("boundary violation detected", result.message_skeleton)


# ===========================================================================
# T8-06: Determinism -- same context produces same decision
# ===========================================================================

class TestT8_06_Determinism(unittest.TestCase):
    """T8-06: Same context always produces the same decision."""

    def test_escalation_decision_deterministic(self):
        ctx = _make_context(
            health_label="BLOCKED",
            t4_boundary_violations=["domain_overreach"],
            materiality_score=0.5,
        )
        d1 = EscalationMatrix.evaluate_escalation(ctx)
        d2 = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(d1.level, d2.level)
        self.assertEqual(d1.reason, d2.reason)
        self.assertEqual(d1.evidence, d2.evidence)
        self.assertEqual(d1.recipient_class, d2.recipient_class)

    def test_stop_decision_deterministic(self):
        ctx = _make_context(
            health_label="BLOCKED",
            materiality_score=0.5,
        )
        s1 = should_stop(ctx)
        s2 = should_stop(ctx)
        self.assertEqual(s1.stop, s2.stop)
        self.assertEqual(s1.rule_id, s2.rule_id)
        self.assertEqual(s1.reason, s2.reason)

    def test_routing_deterministic(self):
        ctx = _make_context(health_label="BLOCKED")
        esc = EscalationMatrix.evaluate_escalation(ctx)
        r1 = route_escalation(esc)
        r2 = route_escalation(esc)
        self.assertEqual(r1.recipient_agent, r2.recipient_agent)
        self.assertEqual(r1.message_skeleton, r2.message_skeleton)


# ===========================================================================
# T8-07: Explicit user stop honoured
# ===========================================================================

class TestT8_07_ExplicitUserStop(unittest.TestCase):
    """T8-07: An explicit user stop must always be honoured."""

    def test_explicit_stop_overrides_all(self):
        ctx = _make_context(
            explicit_user_stop=True,
            health_label="ON_TRACK",
            t4_boundary_violations=None,
        )
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.STOP_AND_ESCALATE)
        self.assertEqual(decision.recipient_class, "HABEEB")

    def test_explicit_stop_in_stop_rules(self):
        ctx = _make_context(explicit_user_stop=True)
        result = should_stop(ctx)
        self.assertTrue(result.stop)
        self.assertEqual(result.rule_id, "explicit_user_stop")

    def test_explicit_stop_with_minor_materiality(self):
        """Even minor/cosmetic items must stop when user says stop."""
        ctx = _make_context(
            explicit_user_stop=True,
            materiality_score=0.05,
        )
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.STOP_AND_ESCALATE)


# ===========================================================================
# T8-08: Delegation to non-ACTIVE specialist stops
# ===========================================================================

class TestT8_08_DelegationToInactiveSpecialist(unittest.TestCase):
    """T8-08: Delegation to a non-ACTIVE specialist triggers stop."""

    def test_delegation_to_inactive_stops(self):
        ctx = _make_context(delegation_to_inactive_specialist=True)
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.STOP_AND_ESCALATE)

    def test_delegation_to_inactive_in_stop_rules(self):
        ctx = _make_context(delegation_to_inactive_specialist=True)
        result = should_stop(ctx)
        self.assertTrue(result.stop)
        self.assertEqual(
            result.rule_id, "delegation_to_inactive_specialist"
        )

    def test_delegation_to_active_does_not_stop(self):
        ctx = _make_context(delegation_to_inactive_specialist=False)
        result = should_stop(ctx)
        # Not stopped by this rule alone.
        self.assertFalse(result.stop)


# ===========================================================================
# T8-09: Blocked dependency chain length threshold
# ===========================================================================

class TestT8_09_BlockedChainThreshold(unittest.TestCase):
    """T8-09: Blocked dependency chain length exceeding threshold
    triggers STOP_AND_ESCALATE."""

    def test_chain_below_threshold_no_stop(self):
        ctx = _make_context(blocked_chain_length=2)
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertNotEqual(
            decision.level, EscalationLevel.STOP_AND_ESCALATE
        )

    def test_chain_at_threshold_stops(self):
        ctx = _make_context(blocked_chain_length=BLOCKED_CHAIN_LENGTH_THRESHOLD)
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.STOP_AND_ESCALATE)

    def test_chain_above_threshold_stops(self):
        ctx = _make_context(blocked_chain_length=5)
        decision = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(decision.level, EscalationLevel.STOP_AND_ESCALATE)

    def test_stop_rules_fire_for_long_blocked_chain(self):
        ctx = _make_context(blocked_chain_length=4)
        result = should_stop(ctx)
        self.assertTrue(result.stop)
        self.assertEqual(
            result.rule_id, "blocked_chain_exceeds_threshold"
        )

    def test_stop_rules_do_not_fire_for_short_chain(self):
        ctx = _make_context(blocked_chain_length=1)
        result = should_stop(ctx)
        self.assertFalse(result.stop)


# ===========================================================================
# Threshold constants are accessible and valid
# ===========================================================================

class TestThresholdConstants(unittest.TestCase):
    """Verify threshold constants are named and valid."""

    def test_blocked_chain_length_threshold_is_positive_int(self):
        self.assertIsInstance(BLOCKED_CHAIN_LENGTH_THRESHOLD, int)
        self.assertGreater(BLOCKED_CHAIN_LENGTH_THRESHOLD, 0)

    def test_boundary_violation_repeat_threshold_is_positive_int(self):
        self.assertIsInstance(BOUNDARY_VIOLATION_REPEAT_THRESHOLD, int)
        self.assertGreater(BOUNDARY_VIOLATION_REPEAT_THRESHOLD, 0)

    def test_materiality_threshold_is_positive_float(self):
        self.assertIsInstance(MATERIALITY_THRESHOLD, float)
        self.assertGreater(MATERIALITY_THRESHOLD, 0.0)


# ===========================================================================
# StopRules utility methods
# ===========================================================================

class TestStopRulesUtilities(unittest.TestCase):
    """Test StopRules helper methods."""

    def test_is_do_not_stop_label_on_track(self):
        self.assertTrue(StopRules.is_do_not_stop_label("ON_TRACK"))

    def test_is_do_not_stop_label_attention(self):
        self.assertTrue(StopRules.is_do_not_stop_label("ATTENTION"))

    def test_is_do_not_stop_label_blocked(self):
        self.assertFalse(StopRules.is_do_not_stop_label("BLOCKED"))

    def test_is_do_not_stop_label_at_risk(self):
        self.assertFalse(StopRules.is_do_not_stop_label("AT_RISK"))

    def test_is_cosmetic_rule_true(self):
        self.assertTrue(StopRules.is_cosmetic_rule("cosmetic_change"))

    def test_is_cosmetic_rule_false(self):
        self.assertFalse(StopRules.is_cosmetic_rule("blocked_chain_exceeds_threshold"))


# ===========================================================================
# EscalationDecision carries required fields
# ===========================================================================

class TestEscalationDecisionFields(unittest.TestCase):
    """Verify EscalationDecision has all required fields."""

    def test_decision_has_level(self):
        d = EscalationDecision(
            level=EscalationLevel.NOTE,
            reason="test",
            evidence=[],
            recipient_class="TOLA",
        )
        self.assertIn(d.level, EscalationLevel)

    def test_decision_has_reason(self):
        d = EscalationDecision(
            level=EscalationLevel.NOTE,
            reason="test reason",
            evidence=[],
            recipient_class="TOLA",
        )
        self.assertIsInstance(d.reason, str)
        self.assertGreater(len(d.reason), 0)

    def test_decision_has_evidence_list(self):
        d = EscalationDecision(
            level=EscalationLevel.NOTE,
            reason="test",
            evidence=["e1", "e2"],
            recipient_class="TOLA",
        )
        self.assertIsInstance(d.evidence, list)

    def test_decision_has_recipient_class(self):
        d = EscalationDecision(
            level=EscalationLevel.NOTE,
            reason="test",
            evidence=[],
            recipient_class="HABEEB",
        )
        self.assertIn(d.recipient_class, ("HABEEB", "OWNING_SPECIALIST", "TOLA"))


# ===========================================================================
# No stop for healthy ON_TRACK with no other triggers
# ===========================================================================

class TestNoFalsePositive(unittest.TestCase):
    """Ensure healthy work with no triggers never stops."""

    def test_completely_clean_context_no_stop(self):
        ctx = _make_context()
        result = should_stop(ctx)
        self.assertFalse(result.stop)
        self.assertEqual(result.rule_id, "no_stop_rule_fired")

    def test_on_track_with_note_escalation_no_stop(self):
        ctx = _make_context(health_label="ON_TRACK")
        esc = EscalationMatrix.evaluate_escalation(ctx)
        self.assertEqual(esc.level, EscalationLevel.NOTE)
        result = should_stop(ctx)
        self.assertFalse(result.stop)

    def test_routing_skeleton_is_ascii(self):
        """Message skeletons must be plain ASCII."""
        for level, (_, _, skeleton) in ROUTING_TABLE.items():
            self.assertTrue(skeleton.isascii(),
                            f"Non-ASCII skeleton for {level.value}")


if __name__ == "__main__":
    unittest.main()