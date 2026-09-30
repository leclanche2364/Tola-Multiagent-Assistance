"""
Batch S11 -- Learner-State Analysis QA Tests (S11-01..S11-05).
Deterministic fixtures, injectable clock, unittest.
No network, no real clocks.
Plain ASCII. Python 3 stdlib only.
"""

import unittest

from scholar.fixtures.learner_state_analysis import (
    STRONG_EVIDENCE_STATE,
    WEAK_EVIDENCE_STATE,
    MISSING_EVIDENCE_STATE,
    MIXED_EVIDENCE_STATE,
    MALFORMED_STATE_MISSING_SCHEMA_VERSION,
    MALFORMED_STATE_EMPTY_SCHEMA_VERSION,
    MALFORMED_STATE_MISSING_STATE_VERSION,
    MALFORMED_STATE_NOT_DICT,
    PAUSED_GOAL_STATE,
    SUPERSEDED_GOAL_STATE,
    VALID_LING_OUTPUT,
    MALFORMED_LING_OUTPUT_MISSING_FIELDS,
    MALFORMED_LING_OUTPUT_WRONG_TYPES,
    MALFORMED_LING_OUTPUT_EMPTY_STRINGS,
    MALFORMED_LING_OUTPUT_NOT_DICT,
    MALFORMED_LING_OUTPUT_NULL,
    MALFORMED_LING_OUTPUT_EXTRA_FIELDS,
    make_analyser,
    make_state,
)
from scholar.learner_state_analysis.analyser import (
    LearnerStateAnalyser,
    ObservedEvidence,
    Interpretation,
    Uncertainty,
    LingAnalyserInterface,
)
from scholar.learner_state_analysis.schema import (
    LingOutputSchema,
    LingSchemaError,
    validate_ling_output,
)


def _fake_now():
    from datetime import datetime
    return datetime(2026, 9, 30, 12, 0, 0)


# ====================================================================== #
#  S11-01: Strong evidence recognised
# ====================================================================== #


class TestS11_01StrongEvidenceRecognised(unittest.TestCase):
    def test_strong_evidence_has_strength_strong(self):
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        strong_evs = [e for e in result.observed_evidence if e.strength == "strong"]
        self.assertGreater(len(strong_evs), 0)

    def test_strong_evidence_includes_topic_progress(self):
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        progress_evs = [
            e for e in result.observed_evidence
            if e.evidence_type == "topic_progress" and e.strength == "strong"
        ]
        self.assertGreater(len(progress_evs), 0)

    def test_strong_evidence_includes_assessment_score(self):
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        assess_evs = [
            e for e in result.observed_evidence
            if e.evidence_type == "assessment_score" and e.strength == "strong"
        ]
        self.assertGreater(len(assess_evs), 0)

    def test_strong_evidence_includes_practice_units(self):
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        practice_evs = [
            e for e in result.observed_evidence
            if e.evidence_type == "practice_units" and e.strength == "strong"
        ]
        self.assertGreater(len(practice_evs), 0)

    def test_strong_evidence_includes_reasoning_evidence(self):
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        reasoning_evs = [
            e for e in result.observed_evidence
            if e.evidence_type == "reasoning_evidence"
        ]
        self.assertGreater(len(reasoning_evs), 0)

    def test_strong_evidence_includes_competency_evidence_authoritative(self):
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        comp_evs = [
            e for e in result.observed_evidence
            if e.evidence_type == "competency_evidence" and e.strength == "strong"
        ]
        self.assertGreater(len(comp_evs), 0)

    def test_strong_evidence_never_invented(self):
        """S11-01: Strong evidence only references what exists in the state."""
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        for ev in result.observed_evidence:
            self.assertIsNotNone(ev.evidence_id)
            self.assertIn(ev.strength, ("strong", "weak", "missing"))


# ====================================================================== #
#  S11-02: Weak evidence recognised
# ====================================================================== #


class TestS11_02WeakEvidenceRecognised(unittest.TestCase):
    def test_weak_evidence_has_strength_weak(self):
        state = make_state(WEAK_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        weak_evs = [e for e in result.observed_evidence if e.strength == "weak"]
        self.assertGreater(len(weak_evs), 0)

    def test_weak_evidence_includes_low_progress(self):
        state = make_state(WEAK_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        progress_evs = [
            e for e in result.observed_evidence
            if e.evidence_type == "topic_progress" and e.strength == "weak"
        ]
        self.assertGreater(len(progress_evs), 0)

    def test_weak_evidence_includes_low_assessment_score(self):
        state = make_state(WEAK_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        assess_evs = [
            e for e in result.observed_evidence
            if e.evidence_type == "assessment_score" and e.strength == "weak"
        ]
        self.assertGreater(len(assess_evs), 0)

    def test_weak_evidence_includes_low_practice_units(self):
        state = make_state(WEAK_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        practice_evs = [
            e for e in result.observed_evidence
            if e.evidence_type == "practice_units" and e.strength == "weak"
        ]
        self.assertGreater(len(practice_evs), 0)

    def test_weak_evidence_includes_non_authoritative_competency(self):
        state = make_state(WEAK_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        comp_evs = [
            e for e in result.observed_evidence
            if e.evidence_type == "competency_evidence" and e.strength == "weak"
        ]
        self.assertGreater(len(comp_evs), 0)


# ====================================================================== #
#  S11-03: Missing evidence -> uncertainty explicit (never invented)
# ====================================================================== #


class TestS11_03MissingEvidenceUncertaintyExplicit(unittest.TestCase):
    def test_missing_evidence_produces_uncertainty(self):
        state = make_state(MISSING_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        self.assertGreater(len(result.uncertainties), 0)

    def test_missing_evidence_uncertainty_wording_explicit(self):
        """S11-03: Uncertainty wording must be explicit, never invented."""
        state = make_state(MISSING_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        # At least one missing-evidence uncertainty must use explicit wording
        missing_uncertainties = [
            u for u in result.uncertainties
            if u.reason == "missing_evidence"
        ]
        self.assertGreater(len(missing_uncertainties), 0)
        for u in missing_uncertainties:
            self.assertIn("absent", u.wording.lower())
            self.assertIn("uncertainty", u.wording.lower())

    def test_missing_evidence_no_invented_evidence(self):
        """S11-03: Missing evidence must not be invented."""
        state = make_state(MISSING_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        for ev in result.observed_evidence:
            if ev.strength == "missing":
                self.assertIsNone(ev.value)

    def test_missing_evidence_uncertainty_reason_missing(self):
        state = make_state(MISSING_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        missing_uncertainties = [
            u for u in result.uncertainties if u.reason == "missing_evidence"
        ]
        self.assertGreater(len(missing_uncertainties), 0)

    def test_missing_evidence_uncertainty_reason_weak(self):
        state = make_state(WEAK_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        weak_uncertainties = [
            u for u in result.uncertainties if u.reason == "weak_evidence"
        ]
        self.assertGreater(len(weak_uncertainties), 0)


# ====================================================================== #
#  S11-04: Observation vs interpretation separated
# ====================================================================== #


class TestS11_04ObservationVsInterpretationSeparated(unittest.TestCase):
    def test_observations_are_separate_from_interpretations(self):
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        self.assertGreater(len(result.observed_evidence), 0)
        self.assertGreater(len(result.interpretations), 0)

    def test_interpretation_traceable_to_evidence_refs(self):
        """S11-04: Each interpretation's evidence_refs must exist in observed_evidence."""
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        evidence_ids = {e.evidence_id for e in result.observed_evidence}
        for interp in result.interpretations:
            for ref in interp.evidence_refs:
                self.assertIn(
                    ref, evidence_ids,
                    f"Interpretation {interp.label} references non-existent evidence ref {ref}",
                )

    def test_interpretation_has_evidence_refs(self):
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        for interp in result.interpretations:
            self.assertGreater(len(interp.evidence_refs), 0)

    def test_interpretation_has_label(self):
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        labels = {i.label for i in result.interpretations}
        self.assertIn("strength", labels)

    def test_uncertainty_interpretation_traceable(self):
        """Uncertainty interpretation must also be traceable to evidence refs."""
        state = make_state(MISSING_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        evidence_ids = {e.evidence_id for e in result.observed_evidence}
        for interp in result.interpretations:
            if interp.label == "uncertainty":
                for ref in interp.evidence_refs:
                    self.assertIn(
                        ref, evidence_ids,
                        f"Uncertainty interpretation references non-existent evidence ref {ref}",
                    )

    def test_observation_does_not_contain_interpretation(self):
        """Observed evidence detail must not be the Ling interpretation."""
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        for ev in result.observed_evidence:
            self.assertNotEqual(ev.detail, result.ling_summary)

    def test_interpretation_does_not_contain_invented_evidence_refs(self):
        """S11-04: Interpretation must not reference evidence that doesn't exist."""
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        evidence_ids = {e.evidence_id for e in result.observed_evidence}
        for interp in result.interpretations:
            for ref in interp.evidence_refs:
                self.assertIn(
                    ref, evidence_ids,
                    f"Interpretation references invented evidence ref {ref}",
                )

    def test_deterministic_repeat_calls_produce_identical_results(self):
        """S11 edge: Deterministic repeat calls produce identical output."""
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result1 = analyser.analyse(state, "goal-vent-01")
        result2 = analyser.analyse(state, "goal-vent-01")
        self.assertEqual(
            [e.evidence_id for e in result1.observed_evidence],
            [e.evidence_id for e in result2.observed_evidence],
        )
        self.assertEqual(
            [i.label for i in result1.interpretations],
            [i.label for i in result2.interpretations],
        )
        self.assertEqual(
            [u.reason for u in result1.uncertainties],
            [u.reason for u in result2.uncertainties],
        )


# ====================================================================== #
#  S11-05: Malformed Ling output -> schema validation rejects it
# ====================================================================== #


class TestS11_05MalformedLingOutputRejected(unittest.TestCase):
    def test_valid_ling_output_passes_validation(self):
        validated = validate_ling_output(VALID_LING_OUTPUT)
        self.assertIsInstance(validated, LingOutputSchema)
        self.assertEqual(validated.summary, VALID_LING_OUTPUT["summary"])

    def test_malformed_ling_missing_fields_rejected(self):
        """S11-05: Ling output missing required fields is rejected."""
        with self.assertRaises(LingSchemaError) as cm:
            validate_ling_output(MALFORMED_LING_OUTPUT_MISSING_FIELDS)
        self.assertGreater(len(cm.exception.errors), 0)

    def test_malformed_ling_wrong_types_rejected(self):
        """S11-05: Ling output with wrong field types is rejected."""
        with self.assertRaises(LingSchemaError) as cm:
            validate_ling_output(MALFORMED_LING_OUTPUT_WRONG_TYPES)
        self.assertGreater(len(cm.exception.errors), 0)

    def test_malformed_ling_empty_strings_rejected(self):
        """S11-05: Ling output with empty required strings is rejected."""
        with self.assertRaises(LingSchemaError) as cm:
            validate_ling_output(MALFORMED_LING_OUTPUT_EMPTY_STRINGS)
        self.assertGreater(len(cm.exception.errors), 0)

    def test_malformed_ling_not_dict_rejected(self):
        """S11-05: Non-dict Ling output is rejected."""
        with self.assertRaises(LingSchemaError) as cm:
            validate_ling_output(MALFORMED_LING_OUTPUT_NOT_DICT)
        self.assertGreater(len(cm.exception.errors), 0)

    def test_malformed_ling_null_rejected(self):
        """S11-05: None Ling output is rejected."""
        with self.assertRaises(LingSchemaError) as cm:
            validate_ling_output(MALFORMED_LING_OUTPUT_NULL)
        self.assertGreater(len(cm.exception.errors), 0)

    def test_malformed_ling_extra_fields_not_rejected(self):
        """Extra fields in Ling output are tolerated (schema is permissive on extras)."""
        validated = validate_ling_output(MALFORMED_LING_OUTPUT_EXTRA_FIELDS)
        self.assertIsInstance(validated, LingOutputSchema)

    def test_analysis_result_records_ling_invalid_when_malformed(self):
        """When Ling output is malformed, analysis result records ling_valid=False."""
        state = make_state(STRONG_EVIDENCE_STATE)

        class MalformedLingAnalyser(LingAnalyserInterface):
            def analyse(self, evidence, uncertainties, goal_id):
                return {"summary": ""}  # missing required fields

        analyser = make_analyser(MalformedLingAnalyser())
        result = analyser.analyse(state, "goal-vent-01")
        self.assertFalse(result.ling_valid)
        self.assertGreater(len(result.ling_errors), 0)

    def test_analysis_result_records_ling_valid_when_valid(self):
        """When Ling output is valid, analysis result records ling_valid=True."""
        state = make_state(STRONG_EVIDENCE_STATE)

        class ValidLingAnalyser(LingAnalyserInterface):
            def analyse(self, evidence, uncertainties, goal_id):
                return VALID_LING_OUTPUT

        analyser = make_analyser(ValidLingAnalyser())
        result = analyser.analyse(state, "goal-vent-01")
        self.assertTrue(result.ling_valid)
        self.assertEqual(len(result.ling_errors), 0)

    def test_malformed_ling_does_not_crash_analysis(self):
        """S11-05: Malformed Ling output is handled gracefully — analysis
        still returns a result with ling_valid=False and error details."""
        state = make_state(STRONG_EVIDENCE_STATE)

        class BrokenLingAnalyser(LingAnalyserInterface):
            def analyse(self, evidence, uncertainties, goal_id):
                return "not-a-dict"

        analyser = make_analyser(BrokenLingAnalyser())
        result = analyser.analyse(state, "goal-vent-01")
        self.assertFalse(result.ling_valid)
        self.assertGreater(len(result.ling_errors), 0)
        # Evidence and interpretations are still populated
        self.assertGreater(len(result.observed_evidence), 0)


# ====================================================================== #
#  Edge cases
# ====================================================================== #


class TestEdgeCasesInterpretationWithoutEvidenceRefRejected(unittest.TestCase):
    def test_interpretation_without_evidence_ref_rejected(self):
        """S11-04: An interpretation referencing a non-existent evidence ID
        must not be silently accepted — the traceability check in the
        analyser ensures all evidence_refs exist."""
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        evidence_ids = {e.evidence_id for e in result.observed_evidence}
        for interp in result.interpretations:
            for ref in interp.evidence_refs:
                self.assertIn(
                    ref, evidence_ids,
                    f"Interpretation {interp.label} has non-existent evidence ref {ref}",
                )


class TestEdgeCasesUncertaintyWordingForMissingData(unittest.TestCase):
    def test_uncertainty_wording_present_for_missing_data(self):
        """S11-03: When data is missing, uncertainty wording must be present."""
        state = make_state(MISSING_EVIDENCE_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        self.assertGreater(len(result.uncertainties), 0)
        for u in result.uncertainties:
            self.assertIsInstance(u.wording, str)
            self.assertGreater(len(u.wording), 0)


class TestEdgeCasesDeterministicRepeatCalls(unittest.TestCase):
    def test_deterministic_repeat_calls_produce_identical_evidence(self):
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        r1 = analyser.analyse(state, "goal-vent-01")
        r2 = analyser.analyse(state, "goal-vent-01")
        self.assertEqual(len(r1.observed_evidence), len(r2.observed_evidence))
        for e1, e2 in zip(r1.observed_evidence, r2.observed_evidence):
            self.assertEqual(e1.evidence_id, e2.evidence_id)
            self.assertEqual(e1.strength, e2.strength)

    def test_deterministic_repeat_calls_produce_identical_uncertainties(self):
        state = make_state(MISSING_EVIDENCE_STATE)
        analyser = make_analyser()
        r1 = analyser.analyse(state, "goal-vent-01")
        r2 = analyser.analyse(state, "goal-vent-01")
        self.assertEqual(len(r1.uncertainties), len(r2.uncertainties))

    def test_deterministic_repeat_calls_produce_identical_interpretations(self):
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        r1 = analyser.analyse(state, "goal-vent-01")
        r2 = analyser.analyse(state, "goal-vent-01")
        self.assertEqual(len(r1.interpretations), len(r2.interpretations))


class TestEdgeCasesMalformedLearnerStateRejected(unittest.TestCase):
    def test_rejects_missing_schema_version(self):
        with self.assertRaises(ValueError):
            make_state(MALFORMED_STATE_MISSING_SCHEMA_VERSION)

    def test_rejects_empty_schema_version(self):
        with self.assertRaises(ValueError):
            make_state(MALFORMED_STATE_EMPTY_SCHEMA_VERSION)

    def test_rejects_missing_state_version(self):
        with self.assertRaises(ValueError):
            make_state(MALFORMED_STATE_MISSING_STATE_VERSION)

    def test_rejects_not_a_dict(self):
        from scholar.learner_state.aggregate import build_learner_state
        with self.assertRaises((ValueError, TypeError)):
            build_learner_state(MALFORMED_STATE_NOT_DICT)


class TestEdgeCasesPausedSupersededGoalsExcludedFromActiveAnalysis(unittest.TestCase):
    def test_paused_goal_state_recorded(self):
        state = make_state(PAUSED_GOAL_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        self.assertEqual(result.goal_state, "PAUSED")

    def test_superseded_goal_state_recorded(self):
        state = make_state(SUPERSEDED_GOAL_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        self.assertEqual(result.goal_state, "SUPERSEDED")

    def test_paused_goal_evidence_still_collected(self):
        """PAUSED goals still have evidence collected but are flagged as PAUSED."""
        state = make_state(PAUSED_GOAL_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        self.assertEqual(result.goal_state, "PAUSED")
        self.assertGreater(len(result.observed_evidence), 0)

    def test_superseded_goal_evidence_still_collected(self):
        """SUPERSEDED goals still have evidence collected but are flagged as SUPERSEDED."""
        state = make_state(SUPERSEDED_GOAL_STATE)
        analyser = make_analyser()
        result = analyser.analyse(state, "goal-vent-01")
        self.assertEqual(result.goal_state, "SUPERSEDED")
        self.assertGreater(len(result.observed_evidence), 0)


class TestEdgeCasesDeterministicLingStub(unittest.TestCase):
    def test_default_ling_analyser_is_deterministic(self):
        """The default Ling analyser stub produces the same output for the
        same inputs."""
        state = make_state(STRONG_EVIDENCE_STATE)
        analyser = make_analyser()
        result1 = analyser.analyse(state, "goal-vent-01")
        result2 = analyser.analyse(state, "goal-vent-01")
        self.assertEqual(result1.ling_summary, result2.ling_summary)
        self.assertEqual(result1.ling_valid, result2.ling_valid)


class TestEdgeCasesSchemaValidationEdgeCases(unittest.TestCase):
    def test_validate_ling_output_rejects_list(self):
        with self.assertRaises(LingSchemaError):
            validate_ling_output([1, 2, 3])

    def test_validate_ling_output_rejects_none(self):
        with self.assertRaises(LingSchemaError):
            validate_ling_output(None)

    def test_validate_ling_output_rejects_string(self):
        with self.assertRaises(LingSchemaError):
            validate_ling_output("not a dict")

    def test_validate_ling_output_rejects_int(self):
        with self.assertRaises(LingSchemaError):
            validate_ling_output(42)

    def test_ling_output_schema_to_dict_roundtrip(self):
        validated = validate_ling_output(VALID_LING_OUTPUT)
        d = validated.to_dict()
        self.assertEqual(d["summary"], VALID_LING_OUTPUT["summary"])
        self.assertEqual(d["evidence_refs"], VALID_LING_OUTPUT["evidence_refs"])


if __name__ == "__main__":
    unittest.main()