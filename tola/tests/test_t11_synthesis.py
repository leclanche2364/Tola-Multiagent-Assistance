# Batch T11 - Cross-Agent Synthesis tests.
# unittest tests covering QA T11 cases T11-01..T11-06.
# Fixture-driven, deterministic, plain ASCII. Stdlib only.

from __future__ import annotations

import ast
import unittest

from tola.synthesis.attribution import (
    EvidenceItem,
    EvidenceSource,
    attribute,
)
from tola.synthesis.synthesizer import (
    RULE_ATTRIBUTION_TRACEABLE,
    RULE_CONFLICT_SURFACED_NOT_FABRICATED,
    RULE_GROWTH_CONSTRAINED_BY_CAPACITY,
    RULE_MISSING_INPUT_GENERATES_REQUEST,
    RULE_SCHOLAR_PROTECTED_PRESERVED,
    SynthesisResult,
    synthesize_portfolio_decision,
)


# ===========================================================================
# Fixtures
# ===========================================================================

def _make_source(agent_id, kind, ref, timestamp="2026-09-29T00:00:00Z"):
    return EvidenceSource(
        agent_id=agent_id,
        kind=kind,
        ref=ref,
        timestamp=timestamp,
    )


def _make_item(agent_id, kind, ref, claim, confidence=1.0):
    return EvidenceItem(
        source=_make_source(agent_id, kind, ref),
        claim=claim,
        confidence=confidence,
    )


# --- T11-01 fixture: Growth opportunity constrained by Rhythm ---
def _fixture_growth_constrained_by_capacity():
    return {
        "growth": {
            "evidence": ["user growth up 12%"],
            "opportunities": ["expand onboarding flow"],
        },
        "rhythm": {
            "capacity_summary": {
                "available_hours": 10,
                "committed_hours": 18,
            },
            "capacity_shortfall": True,
        },
        "scholar": {
            "obligations": [],
            "protected_requirements": [],
        },
        "deadlines": {
            "active_deadlines": [],
            "deadline_conflicts": [],
        },
    }


# --- T11-02 fixture: Scholar protected requirement preserved ---
def _fixture_scholar_protected():
    return {
        "growth": {
            "evidence": [],
            "opportunities": ["cut study time by 50%"],
        },
        "rhythm": {
            "capacity_summary": {"available_hours": 40},
            "capacity_shortfall": False,
        },
        "scholar": {
            "obligations": ["complete core curriculum"],
            "protected_requirements": ["minimum 3 hours daily study"],
        },
        "deadlines": {
            "active_deadlines": [],
            "deadline_conflicts": [],
        },
    }


# --- T11-03 fixture: Growth + Scholar + Rhythm competing needs ---
def _fixture_competing_needs():
    return {
        "growth": {
            "evidence": ["conversion rate dropped 8%"],
            "opportunities": ["run retention experiment"],
        },
        "rhythm": {
            "capacity_summary": {"available_hours": 5},
            "capacity_shortfall": True,
        },
        "scholar": {
            "obligations": ["finish module 3"],
            "protected_requirements": ["daily review session"],
        },
        "deadlines": {
            "active_deadlines": ["experiment review due Friday"],
            "deadline_conflicts": [],
        },
    }


# --- T11-04 fixture: Conflicting evidence between specialists ---
def _fixture_conflicting_evidence():
    return {
        "growth": {
            "evidence": ["expand to new market now"],
            "opportunities": ["enter APAC region immediately"],
        },
        "rhythm": {
            "capacity_summary": {"available_hours": 20},
            "capacity_shortfall": False,
        },
        "scholar": {
            "obligations": ["complete current module first"],
            "protected_requirements": ["do not defer learning for growth"],
        },
        "deadlines": {
            "active_deadlines": [],
            "deadline_conflicts": [],
        },
    }


# --- T11-05 fixture: Missing specialist input ---
def _fixture_missing_input():
    return {
        "growth": {
            "evidence": ["trial signups steady"],
            "opportunities": [],
        },
        "rhythm": None,
        "scholar": {
            "obligations": [],
            "protected_requirements": [],
        },
        "deadlines": {
            "active_deadlines": [],
            "deadline_conflicts": [],
        },
    }


# --- T11-06 fixture: Source attribution traceability ---
def _fixture_attribution_trace():
    return {
        "growth": {
            "evidence": ["engagement up 20%"],
            "opportunities": ["launch referral program"],
        },
        "rhythm": {
            "capacity_summary": {"available_hours": 30},
            "capacity_shortfall": False,
        },
        "scholar": {
            "obligations": [],
            "protected_requirements": ["weekly learning review"],
        },
        "deadlines": {
            "active_deadlines": [],
            "deadline_conflicts": [],
        },
    }


# ===========================================================================
# T11-01: Growth opportunity constrained by Rhythm capacity
# ===========================================================================

class T11_01_GrowthConstrainedByCapacity(unittest.TestCase):
    def test_capacity_shortfall_noted(self):
        result = synthesize_portfolio_decision(
            _fixture_growth_constrained_by_capacity()
        )
        self.assertIn("capacity shortfall", result.decision.lower())

    def test_opportunity_preserved_not_suppressed(self):
        result = synthesize_portfolio_decision(
            _fixture_growth_constrained_by_capacity()
        )
        self.assertIn("expand onboarding flow", result.decision)

    def test_rationale_includes_capacity_rule(self):
        result = synthesize_portfolio_decision(
            _fixture_growth_constrained_by_capacity()
        )
        rationale_text = " ".join(result.rationale)
        self.assertIn("capacity", rationale_text.lower())


# ===========================================================================
# T11-02: Scholar protected requirement preserved verbatim
# ===========================================================================

class T11_02_ScholarProtectedPreserved(unittest.TestCase):
    def test_protected_requirement_in_decision(self):
        result = synthesize_portfolio_decision(
            _fixture_scholar_protected()
        )
        self.assertIn("minimum 3 hours daily study", result.decision)

    def test_protected_requirement_not_removed(self):
        result = synthesize_portfolio_decision(
            _fixture_scholar_protected()
        )
        self.assertIn("minimum 3 hours daily study", result.decision)

    def test_protected_preserved_verbatim(self):
        result = synthesize_portfolio_decision(
            _fixture_scholar_protected()
        )
        for req in ["minimum 3 hours daily study"]:
            self.assertIn(req, result.decision)


# ===========================================================================
# T11-03: Growth + Scholar + Rhythm competing needs synthesized
# ===========================================================================

class T11_03_CompetingNeedsSynthesized(unittest.TestCase):
    def test_decision_mentions_growth(self):
        result = synthesize_portfolio_decision(
            _fixture_competing_needs()
        )
        self.assertIn("growth", result.decision.lower())

    def test_decision_mentions_scholar(self):
        result = synthesize_portfolio_decision(
            _fixture_competing_needs()
        )
        self.assertIn("scholar", result.decision.lower())

    def test_decision_mentions_rhythm(self):
        result = synthesize_portfolio_decision(
            _fixture_competing_needs()
        )
        self.assertIn("capacity", result.decision.lower())

    def test_rationale_lists_multiple_specialists(self):
        result = synthesize_portfolio_decision(
            _fixture_competing_needs()
        )
        rationale_text = " ".join(result.rationale).lower()
        self.assertIn("growth", rationale_text)
        self.assertIn("scholar", rationale_text)
        self.assertIn("capacity", rationale_text)


# ===========================================================================
# T11-04: Conflicting evidence surfaced not fabricated
# ===========================================================================

class T11_04_ConflictSurfacedNotFabricated(unittest.TestCase):
    def test_unresolved_conflicts_not_empty(self):
        result = synthesize_portfolio_decision(
            _fixture_conflicting_evidence()
        )
        self.assertTrue(len(result.unresolved_conflicts) > 0)

    def test_decision_says_conflict_unresolved(self):
        result = synthesize_portfolio_decision(
            _fixture_conflicting_evidence()
        )
        self.assertIn("conflict unresolved", result.decision.lower())

    def test_no_fabricated_certainty(self):
        result = synthesize_portfolio_decision(
            _fixture_conflicting_evidence()
        )
        certainty_phrases = [
            "definitely",
            "certainly",
            "will definitely",
            "guaranteed",
        ]
        decision_lower = result.decision.lower()
        for phrase in certainty_phrases:
            self.assertNotIn(phrase, decision_lower)


# ===========================================================================
# T11-05: Missing specialist input generates request not guess
# ===========================================================================

class T11_05_MissingInputGeneratesRequest(unittest.TestCase):
    def test_missing_inputs_not_empty(self):
        result = synthesize_portfolio_decision(
            _fixture_missing_input()
        )
        self.assertTrue(len(result.missing_inputs) > 0)

    def test_missing_input_has_agent_id(self):
        result = synthesize_portfolio_decision(
            _fixture_missing_input()
        )
        for mi in result.missing_inputs:
            self.assertIn("agent_id", mi)
            self.assertEqual(mi["agent_id"], "rhythm")

    def test_missing_input_has_what_is_needed(self):
        result = synthesize_portfolio_decision(
            _fixture_missing_input()
        )
        for mi in result.missing_inputs:
            self.assertIn("what_is_needed", mi)
            self.assertTrue(len(mi["what_is_needed"]) > 0)

    def test_decision_does_not_guess_rhythm_data(self):
        result = synthesize_portfolio_decision(
            _fixture_missing_input()
        )
        self.assertNotIn("rhythm capacity is", result.decision.lower())


# ===========================================================================
# T11-06: Source attribution remains traceable
# ===========================================================================

class T11_06_SourceAttributionTraceable(unittest.TestCase):
    def test_attribution_not_empty(self):
        result = synthesize_portfolio_decision(
            _fixture_attribution_trace()
        )
        self.assertTrue(len(result.attribution) > 0)

    def test_attribution_contains_growth_tag(self):
        result = synthesize_portfolio_decision(
            _fixture_attribution_trace()
        )
        attrib_text = " ".join(result.attribution)
        self.assertIn("growth:", attrib_text)

    def test_attribution_contains_scholar_tag(self):
        result = synthesize_portfolio_decision(
            _fixture_attribution_trace()
        )
        attrib_text = " ".join(result.attribution)
        self.assertIn("scholar:", attrib_text)

    def test_attribution_contains_rhythm_tag(self):
        result = synthesize_portfolio_decision(
            _fixture_attribution_trace()
        )
        attrib_text = " ".join(result.attribution)
        self.assertIn("rhythm:", attrib_text)

    def test_decision_carries_attribution(self):
        result = synthesize_portfolio_decision(
            _fixture_attribution_trace()
        )
        self.assertTrue(len(result.attribution) > 0)
        # Check that at least one attribution line has a tag format
        found_tag = False
        for line in result.attribution:
            if ":" in line and "[" in line and "]" in line:
                found_tag = True
                break
        self.assertTrue(found_tag)

    def test_rationale_carries_attribution(self):
        result = synthesize_portfolio_decision(
            _fixture_attribution_trace()
        )
        # Rationale lines should reference specialist tags
        rationale_text = " ".join(result.rationale)
        has_tag = ("growth:" in rationale_text or
                   "scholar:" in rationale_text or
                   "rhythm:" in rationale_text or
                   "deadlines:" in rationale_text)
        self.assertTrue(has_tag)


# ===========================================================================
# Attribution module tests
# ===========================================================================

class AttributionTests(unittest.TestCase):
    def test_evidence_source_fields(self):
        src = _make_source("growth", "evidence", "ref-123")
        self.assertEqual(src.agent_id, "growth")
        self.assertEqual(src.kind, "evidence")
        self.assertEqual(src.ref, "ref-123")

    def test_evidence_item_fields(self):
        src = _make_source("growth", "evidence", "ref-123")
        item = EvidenceItem(source=src, claim="test claim", confidence=0.9)
        self.assertEqual(item.claim, "test claim")
        self.assertEqual(item.confidence, 0.9)

    def test_attribute_returns_tagged_text(self):
        src = _make_source("growth", "evidence", "ref-123")
        item = EvidenceItem(source=src, claim="users grew", confidence=0.95)
        result = attribute([item])
        self.assertIn("growth:ref-123", result)
        self.assertIn("users grew", result)

    def test_attribute_multiple_items(self):
        items = [
            _make_item("growth", "evidence", "ref-1", "claim A"),
            _make_item("scholar", "obligation", "ref-2", "claim B"),
        ]
        result = attribute(items)
        self.assertIn("growth:ref-1", result)
        self.assertIn("scholar:ref-2", result)

    def test_attribute_empty_list(self):
        result = attribute([])
        self.assertEqual(result, "")

    def test_tag_survives_through_synthesis(self):
        """T11-06: tags survive through synthesis output."""
        result = synthesize_portfolio_decision(
            _fixture_attribution_trace()
        )
        attrib_text = " ".join(result.attribution)
        self.assertIn("growth:", attrib_text)
        self.assertIn("[", attrib_text)
        self.assertIn("]", attrib_text)


# ===========================================================================
# Rules constants present
# ===========================================================================

class RulesConstantsTests(unittest.TestCase):
    def test_rule_growth_constrained_by_capacity(self):
        self.assertIsInstance(RULE_GROWTH_CONSTRAINED_BY_CAPACITY, str)
        self.assertIn("Growth", RULE_GROWTH_CONSTRAINED_BY_CAPACITY)

    def test_rule_scholar_protected_preserved(self):
        self.assertIsInstance(RULE_SCHOLAR_PROTECTED_PRESERVED, str)
        self.assertIn("Scholar", RULE_SCHOLAR_PROTECTED_PRESERVED)

    def test_rule_conflict_surfaced(self):
        self.assertIsInstance(RULE_CONFLICT_SURFACED_NOT_FABRICATED, str)
        self.assertIn("Conflicting", RULE_CONFLICT_SURFACED_NOT_FABRICATED)

    def test_rule_missing_input_generates_request(self):
        self.assertIsInstance(RULE_MISSING_INPUT_GENERATES_REQUEST, str)
        self.assertIn("Missing", RULE_MISSING_INPUT_GENERATES_REQUEST)

    def test_rule_attribution_traceable(self):
        self.assertIsInstance(RULE_ATTRIBUTION_TRACEABLE, str)
        self.assertIn("attribution", RULE_ATTRIBUTION_TRACEABLE.lower())


# ===========================================================================
# SynthesisResult structure
# ===========================================================================

class SynthesisResultStructureTests(unittest.TestCase):
    def test_result_has_all_fields(self):
        result = synthesize_portfolio_decision({})
        self.assertIsInstance(result.decision, str)
        self.assertIsInstance(result.rationale, list)
        self.assertIsInstance(result.unresolved_conflicts, list)
        self.assertIsInstance(result.missing_inputs, list)
        self.assertIsInstance(result.attribution, list)

    def test_empty_inputs_returns_result(self):
        result = synthesize_portfolio_decision({})
        self.assertIsInstance(result.decision, str)
        # Empty inputs produce missing-input rationale entries
        # for each absent specialist.
        self.assertTrue(len(result.missing_inputs) > 0)
        self.assertEqual(len(result.unresolved_conflicts), 0)


# ===========================================================================
# Determinism: same inputs produce same outputs
# ===========================================================================

class DeterminismTests(unittest.TestCase):
    def test_same_inputs_same_result(self):
        fixture = _fixture_attribution_trace()
        r1 = synthesize_portfolio_decision(fixture)
        r2 = synthesize_portfolio_decision(fixture)
        self.assertEqual(r1.decision, r2.decision)
        self.assertEqual(r1.rationale, r2.rationale)
        self.assertEqual(r1.attribution, r2.attribution)


# ===========================================================================
# Parse check helper
# ===========================================================================

def load_module_ast(filepath):
    with open(filepath, "r") as f:
        source = f.read()
    return ast.parse(source)


if __name__ == "__main__":
    unittest.main()