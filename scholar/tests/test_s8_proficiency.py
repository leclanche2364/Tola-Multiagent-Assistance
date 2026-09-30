"""
Batch S8 -- Proficiency Registry QA Tests (S8-01..S8-05 + edge cases).
Plain ASCII. Python 3 stdlib only.
"""

import unittest

from scholar.curriculum.proficiency_registry import (
    ProficiencyRegistry,
    ProficiencySource,
    ProficiencyRecord,
    TopicLink,
    EvidenceLink,
    ConflictingContext,
    ProficiencyInterpretation,
)
from scholar.fixtures.proficiency import (
    STEP2_PROFICIENCY_SOURCE_V1,
    STEP2_PROFICIENCY_SOURCE_V2,
    STEP3_PROFICIENCY_SOURCE_V1,
    FUTURE_CONTEXT_SOURCE_V1,
    PROFICIENCY_VENT_V1,
    PROFICIENCY_VENT_V2,
    PROFICIENCY_HEMO_V1,
    PROFICIENCY_FUTURE_V1,
    TOPIC_LINK_VENT_TO_LUNG,
    TOPIC_LINK_VENT_TO_WEANING,
    TOPIC_LINK_HEMO_TO_ARTERIAL,
    TOPIC_LINK_VENT_PREREQ,
    EVIDENCE_LINK_VENT_SUPPORTS,
    EVIDENCE_LINK_VENT_CONTRADICTS,
    EVIDENCE_LINK_HEMO_REQUIRES,
    EVIDENCE_LINK_VENT_INFORMS,
    CONFLICT_VENT_DOMAIN_VS_HEMO,
    CONFLICT_VENT_VERBATIM_MISMATCH,
    INTERPRETATION_VENT_V1,
    INTERPRETATION_VENT_V2,
    INTERPRETATION_HEMO_V1,
    MALFORMED_PROFICIENCY_MISSING_VERBATIM,
    MALFORMED_PROFICIENCY_MISSING_SOURCE,
    MALFORMED_PROFICIENCY_BAD_STEP,
    MALFORMED_PROFICIENCY_BAD_STATUS,
    MALFORMED_PROFICIENCY_NON_STRING_KNOWLEDGE,
    MALFORMED_PROFICIENCY_EMPTY_KNOWLEDGE,
    MALFORMED_TOPIC_LINK_MISSING_PROFICIENCY,
    MALFORMED_TOPIC_LINK_BAD_TYPE,
    MALFORMED_EVIDENCE_LINK_MISSING_PROFICIENCY,
    MALFORMED_EVIDENCE_LINK_BAD_TYPE,
    MALFORMED_CONFLICT_MISSING_PROFICIENCY,
    MALFORMED_INTERPRETATION_MISSING_PROFICIENCY,
    MALFORMED_INTERPRETATION_EMPTY_SUMMARY,
    DUPLICATE_PROFICIENCY_INGEST_ATTEMPT,
    DUPLICATE_TOPIC_LINK_ATTEMPT,
    DUPLICATE_EVIDENCE_LINK_ATTEMPT,
    DUPLICATE_CONFLICT_ATTEMPT,
    DUPLICATE_INTERPRETATION_ATTEMPT,
    make_registry,
    make_source,
    make_proficiency,
    make_topic_link,
    make_evidence_link,
    make_conflict,
    make_interpretation,
    make_supersede_payload,
)


def _fake_now():
    from datetime import datetime
    return datetime(2026, 9, 30, 12, 0, 0)


# ====================================================================== #
#  S8-01 New proficiency: ingested
# ====================================================================== #

class TestS8_01_NewProficiencyIngested(unittest.TestCase):
    def test_ingest_proficiency_returns_record(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        record = reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        self.assertIsNotNone(record)
        self.assertEqual(record.proficiency_id, "prof-vent-01")
        self.assertEqual(record.step, "step2")
        self.assertEqual(record.domain, "mechanical_ventilation")

    def test_ingest_proficiency_stores_verbatim(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        verbatim = "Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, and weaning criteria."
        record = reg.ingest_proficiency(
            proficiency_id="prof-vent-01",
            source_id="src-step2-cc101", source_version="1.0",
            step="step2", domain="mechanical_ventilation",
            verbatim_requirement=verbatim,
            knowledge_requirements=["Know ventilator modes"],
            application_requirements=["Set ventilator parameters"],
            rationale_requirements=["Explain lung-protective rationale"],
            linked_topics=["ventilation-basics"],
            linked_learning_outcomes=["outcome-vent-01"],
            linked_evidence=["evidence-vent-01"],
        )
        self.assertEqual(record.verbatim_requirement, verbatim)

    def test_ingest_proficiency_increments_version(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        v1 = reg.get_proficiency("prof-vent-01", version=1)
        self.assertIsNotNone(v1)
        self.assertEqual(v1.version, 1)

    def test_ingest_proficiency_gets_latest_version(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        latest = reg.get_proficiency("prof-vent-01")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.version, 1)

    def test_ingest_multiple_proficiencies(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.ingest_proficiency(**PROFICIENCY_HEMO_V1)
        vent = reg.get_proficiency("prof-vent-01")
        hemo = reg.get_proficiency("prof-hemo-01")
        self.assertIsNotNone(vent)
        self.assertIsNotNone(hemo)

    def test_ingest_proficiency_with_future_step(self):
        reg = make_registry()
        reg.add_source(**FUTURE_CONTEXT_SOURCE_V1)
        record = reg.ingest_proficiency(**PROFICIENCY_FUTURE_V1)
        self.assertEqual(record.step, "future")
        self.assertEqual(record.domain, "ai_decision_support")

    def test_ingest_proficiency_rejects_unknown_step(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        with self.assertRaises(ValueError) as cm:
            reg.ingest_proficiency(**MALFORMED_PROFICIENCY_BAD_STEP)
        self.assertIn("step", str(cm.exception))

    def test_ingest_proficiency_rejects_unknown_status(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        with self.assertRaises(ValueError) as cm:
            reg.ingest_proficiency(**MALFORMED_PROFICIENCY_BAD_STATUS)
        self.assertIn("status", str(cm.exception))


# ====================================================================== #
#  S8-02 Verbatim wording: preserved
# ====================================================================== #

class TestS8_02VerbatimWordingPreserved(unittest.TestCase):
    def test_verbatim_exactly_matches_source(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        source = reg.get_source("src-step2-cc101", version="1.0")
        verbatim = source.content["verbatim_requirement"]
        record = reg.ingest_proficiency(
            proficiency_id="prof-vent-01",
            source_id="src-step2-cc101", source_version="1.0",
            step="step2", domain="mechanical_ventilation",
            verbatim_requirement=verbatim,
            knowledge_requirements=["Know ventilator modes"],
            application_requirements=["Set ventilator parameters"],
            rationale_requirements=["Explain lung-protective rationale"],
            linked_topics=["ventilation-basics"],
            linked_learning_outcomes=["outcome-vent-01"],
            linked_evidence=["evidence-vent-01"],
        )
        self.assertEqual(record.verbatim_requirement, verbatim)

    def test_verbatim_preserved_across_retrieval(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        original = "Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, and weaning criteria."
        reg.ingest_proficiency(
            proficiency_id="prof-vent-01",
            source_id="src-step2-cc101", source_version="1.0",
            step="step2", domain="mechanical_ventilation",
            verbatim_requirement=original,
            knowledge_requirements=["Know ventilator modes"],
            application_requirements=["Set ventilator parameters"],
            rationale_requirements=["Explain lung-protective rationale"],
            linked_topics=["ventilation-basics"],
            linked_learning_outcomes=["outcome-vent-01"],
            linked_evidence=["evidence-vent-01"],
        )
        retrieved = reg.get_proficiency("prof-vent-01")
        self.assertEqual(retrieved.verbatim_requirement, original)

    def test_verbatim_rejected_if_mismatches_source(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        with self.assertRaises(ValueError) as cm:
            reg.ingest_proficiency(
                proficiency_id="prof-vent-01",
                source_id="src-step2-cc101", source_version="1.0",
                step="step2", domain="mechanical_ventilation",
                verbatim_requirement="Different verbatim text that does not match source",
                knowledge_requirements=["Know ventilator modes"],
                application_requirements=["Set ventilator parameters"],
                rationale_requirements=["Explain lung-protective rationale"],
                linked_topics=["ventilation-basics"],
                linked_learning_outcomes=["outcome-vent-01"],
                linked_evidence=["evidence-vent-01"],
            )
        self.assertIn("does not match", str(cm.exception))

    def test_verbatim_preserved_after_supersede(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        old_verbatim = "Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, and weaning criteria."
        reg.ingest_proficiency(
            proficiency_id="prof-vent-01",
            source_id="src-step2-cc101", source_version="1.0",
            step="step2", domain="mechanical_ventilation",
            verbatim_requirement=old_verbatim,
            knowledge_requirements=["Know ventilator modes"],
            application_requirements=["Set ventilator parameters"],
            rationale_requirements=["Explain lung-protective rationale"],
            linked_topics=["ventilation-basics"],
            linked_learning_outcomes=["outcome-vent-01"],
            linked_evidence=["evidence-vent-01"],
        )
        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )
        v1 = reg.get_proficiency("prof-vent-01", version=1)
        self.assertEqual(v1.verbatim_requirement, old_verbatim)

    def test_verbatim_non_string_rejected(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        with self.assertRaises(ValueError):
            reg.ingest_proficiency(
                proficiency_id="prof-vent-01",
                source_id="src-step2-cc101", source_version="1.0",
                step="step2", domain="mechanical_ventilation",
                verbatim_requirement=12345,
                knowledge_requirements=["Know ventilator modes"],
                application_requirements=["Set ventilator parameters"],
                rationale_requirements=["Explain lung-protective rationale"],
                linked_topics=["ventilation-basics"],
                linked_learning_outcomes=["outcome-vent-01"],
                linked_evidence=["evidence-vent-01"],
            )

    def test_verbatim_empty_rejected(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        with self.assertRaises(ValueError):
            reg.ingest_proficiency(**MALFORMED_PROFICIENCY_MISSING_VERBATIM)


# ====================================================================== #
#  S8-03 Structured interpretation: stored separately
# ====================================================================== #

class TestS8_03StructuredInterpretationSeparate(unittest.TestCase):
    def test_interpretation_stored_separately(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        interp = reg.add_interpretation(**INTERPRETATION_VENT_V1)
        self.assertEqual(interp.proficiency_id, "prof-vent-01")
        self.assertEqual(interp.interpretation_id, "interp-vent-01")

    def test_verbatim_not_in_interpretation_fields(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_interpretation(**INTERPRETATION_VENT_V1)
        self.assertTrue(reg.verify_verbatim_separation("prof-vent-01"))

    def test_interpretation_has_own_timestamp(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        interp = reg.add_interpretation(**INTERPRETATION_VENT_V1)
        self.assertIsNotNone(interp.derived_at)
        self.assertGreater(len(interp.derived_at), 0)

    def test_interpretation_contains_gap_indicators(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        interp = reg.add_interpretation(**INTERPRETATION_VENT_V1)
        self.assertIn("limited hands-on ventilator experience", interp.gap_indicators)

    def test_interpretation_contains_readiness_indicators(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        interp = reg.add_interpretation(**INTERPRETATION_VENT_V1)
        self.assertIn("can describe ventilator modes", interp.readiness_indicators)

    def test_interpretation_rejects_unknown_proficiency(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.add_interpretation(**MALFORMED_INTERPRETATION_MISSING_PROFICIENCY)
        self.assertIn("does not exist", str(cm.exception))

    def test_interpretation_rejects_empty_summary(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        with self.assertRaises(ValueError):
            reg.add_interpretation(**MALFORMED_INTERPRETATION_EMPTY_SUMMARY)

    def test_interpretation_rejects_duplicate_id(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_interpretation(**INTERPRETATION_VENT_V1)
        with self.assertRaises(ValueError) as cm:
            reg.add_interpretation(**DUPLICATE_INTERPRETATION_ATTEMPT)
        self.assertIn("Duplicate interpretation_id", str(cm.exception))

    def test_get_interpretations_for_proficiency(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_interpretation(**INTERPRETATION_VENT_V1)
        interps = reg.get_interpretations_for_proficiency("prof-vent-01")
        self.assertEqual(len(interps), 1)
        self.assertEqual(interps[0].interpretation_id, "interp-vent-01")

    def test_multiple_interpretations_for_same_proficiency(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_interpretation(**INTERPRETATION_VENT_V1)
        reg.add_interpretation(**INTERPRETATION_VENT_V2)
        interps = reg.get_interpretations_for_proficiency("prof-vent-01")
        self.assertEqual(len(interps), 2)

    def test_interpretation_separation_enforced_after_supersede(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_interpretation(**INTERPRETATION_VENT_V1)
        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )
        self.assertTrue(reg.verify_verbatim_separation("prof-vent-01"))


# ====================================================================== #
#  S8-04 Updated version: supersedes without erasing history
# ====================================================================== #

class TestS8_04SupersededVersionStillRetrievable(unittest.TestCase):
    def test_supersede_returns_old_and_new(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        old, new = reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )
        self.assertEqual(old.version, 1)
        self.assertEqual(new.version, 2)

    def test_superseded_version_still_retrievable(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )
        v1 = reg.get_proficiency("prof-vent-01", version=1)
        v2 = reg.get_proficiency("prof-vent-01", version=2)
        self.assertIsNotNone(v1)
        self.assertEqual(v1.version, 1)
        self.assertIsNotNone(v2)
        self.assertEqual(v2.version, 2)

    def test_superseded_verbatim_unchanged(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        old_verbatim = reg.get_proficiency("prof-vent-01", version=1).verbatim_requirement
        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )
        v1 = reg.get_proficiency("prof-vent-01", version=1)
        self.assertEqual(v1.verbatim_requirement, old_verbatim)

    def test_supersede_rejects_identical_verbatim(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        with self.assertRaises(ValueError) as cm:
            reg.supersede_proficiency(
                proficiency_id="prof-vent-01",
                new_source_id="src-step2-cc101", new_source_version="1.0",
                new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, and weaning criteria.",
                new_knowledge_requirements=["Know ventilator modes"],
                new_application_requirements=["Set ventilator parameters"],
                new_rationale_requirements=["Explain lung-protective rationale"],
                new_linked_topics=["ventilation-basics"],
                new_linked_learning_outcomes=["outcome-vent-01"],
                new_linked_evidence=["evidence-vent-01"],
            )
        self.assertIn("identical", str(cm.exception))

    def test_supersede_rejects_unknown_proficiency(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.supersede_proficiency(
                proficiency_id="prof-nonexistent",
                new_source_id="src-step2-cc101", new_source_version="1.0",
                new_verbatim_requirement="Some text",
                new_knowledge_requirements=["Know something"],
                new_application_requirements=["Do something"],
                new_rationale_requirements=["Explain something"],
                new_linked_topics=[],
                new_linked_learning_outcomes=[],
                new_linked_evidence=[],
            )
        self.assertIn("does not exist", str(cm.exception))

    def test_get_proficiency_history_returns_all_versions(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )
        history = reg.get_proficiency_history("prof-vent-01")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].version, 1)
        self.assertEqual(history[1].version, 2)

    def test_supersede_preserves_source_traceability(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )
        v1 = reg.get_proficiency("prof-vent-01", version=1)
        v2 = reg.get_proficiency("prof-vent-01", version=2)
        source_v1 = reg.get_source(v1.source_id, version=v1.source_version)
        source_v2 = reg.get_source(v2.source_id, version=v2.source_version)
        self.assertIsNotNone(source_v1)
        self.assertIsNotNone(source_v2)

    def test_get_proficiency_latest_after_supersede(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )
        latest = reg.get_proficiency("prof-vent-01")
        self.assertEqual(latest.version, 2)


# ====================================================================== #
#  S8-05 Conflicting context: flagged rather than silently reconciled
# ====================================================================== #

class TestS8_05ConflictingContextFlagged(unittest.TestCase):
    def test_flag_conflict_returns_conflict(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        conflict = reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)
        self.assertEqual(conflict.conflict_id, "conflict-vent-domain")
        self.assertFalse(conflict.resolved)

    def test_conflict_preserved_after_flagging(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)
        retrieved = reg.get_conflict("conflict-vent-domain")
        self.assertIsNotNone(retrieved)
        self.assertFalse(retrieved.resolved)

    def test_conflict_rejects_duplicate_id(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)
        with self.assertRaises(ValueError) as cm:
            reg.flag_conflict(**DUPLICATE_CONFLICT_ATTEMPT)
        self.assertIn("Duplicate conflict_id", str(cm.exception))

    def test_conflict_rejects_unknown_proficiency(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.flag_conflict(**MALFORMED_CONFLICT_MISSING_PROFICIENCY)
        self.assertIn("does not exist", str(cm.exception))

    def test_resolve_conflict_marks_resolved(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)
        resolved = reg.resolve_conflict("conflict-vent-domain")
        self.assertTrue(resolved.resolved)

    def test_resolve_conflict_preserves_record(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)
        reg.resolve_conflict("conflict-vent-domain")
        retrieved = reg.get_conflict("conflict-vent-domain")
        self.assertIsNotNone(retrieved)
        self.assertTrue(retrieved.resolved)

    def test_resolve_conflict_rejects_already_resolved(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)
        reg.resolve_conflict("conflict-vent-domain")
        with self.assertRaises(ValueError) as cm:
            reg.resolve_conflict("conflict-vent-domain")
        self.assertIn("already resolved", str(cm.exception))

    def test_resolve_conflict_rejects_unknown(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.resolve_conflict("conflict-unknown")
        self.assertIn("does not exist", str(cm.exception))

    def test_get_conflicts_for_proficiency(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)
        conflicts = reg.get_conflicts_for_proficiency("prof-vent-01")
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].conflict_id, "conflict-vent-domain")

    def test_validate_reports_unresolved_conflicts(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)
        result = reg.validate()
        self.assertIn("conflict-vent-domain", result["unresolved_conflicts"])

    def test_validate_clean_after_resolution(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)
        reg.resolve_conflict("conflict-vent-domain")
        result = reg.validate()
        self.assertNotIn("conflict-vent-domain", result["unresolved_conflicts"])

    def test_conflict_not_silently_reconciled(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)
        conflict = reg.get_conflict("conflict-vent-domain")
        self.assertEqual(conflict.value_a, "mechanical_ventilation")
        self.assertEqual(conflict.value_b, "haemodynamic_monitoring")
        self.assertFalse(conflict.resolved)


# ====================================================================== #
#  Topic link management
# ====================================================================== #

class TestTopicLinkManagement(unittest.TestCase):
    def test_topic_link_added_and_retrieved(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        link = reg.add_topic_link(**TOPIC_LINK_VENT_TO_LUNG)
        self.assertEqual(link.link_id, "tlink-vent-to-lung")
        self.assertEqual(link.proficiency_id, "prof-vent-01")
        self.assertEqual(link.topic_id, "topic-lung-protective")
        self.assertEqual(link.link_type, "maps_to")

    def test_topic_link_rejects_unknown_proficiency(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.add_topic_link(**MALFORMED_TOPIC_LINK_MISSING_PROFICIENCY)
        self.assertIn("does not exist", str(cm.exception))

    def test_topic_link_rejects_bad_type(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        with self.assertRaises(ValueError) as cm:
            reg.add_topic_link(**MALFORMED_TOPIC_LINK_BAD_TYPE)
        self.assertIn("link_type", str(cm.exception))

    def test_topic_link_rejects_duplicate_id(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_topic_link(**TOPIC_LINK_VENT_TO_LUNG)
        with self.assertRaises(ValueError) as cm:
            reg.add_topic_link(**DUPLICATE_TOPIC_LINK_ATTEMPT)
        self.assertIn("Duplicate link_id", str(cm.exception))

    def test_get_topic_links_for_proficiency(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_topic_link(**TOPIC_LINK_VENT_TO_LUNG)
        reg.add_topic_link(**TOPIC_LINK_VENT_TO_WEANING)
        links = reg.get_topic_links_for_proficiency("prof-vent-01")
        self.assertEqual(len(links), 2)

    def test_get_topic_links_for_topic(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_topic_link(**TOPIC_LINK_VENT_TO_LUNG)
        links = reg.get_topic_links_for_topic("topic-lung-protective")
        self.assertEqual(len(links), 1)

    def test_topic_link_version_increments(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_topic_link(**TOPIC_LINK_VENT_TO_LUNG)
        reg.add_topic_link(**TOPIC_LINK_VENT_TO_WEANING)
        link1 = reg.get_topic_link("tlink-vent-to-lung")
        link2 = reg.get_topic_link("tlink-vent-to-weaning")
        self.assertEqual(link1.version, 1)
        self.assertEqual(link2.version, 2)


# ====================================================================== #
#  Evidence link management
# ====================================================================== #

class TestEvidenceLinkManagement(unittest.TestCase):
    def test_evidence_link_added_and_retrieved(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        link = reg.add_evidence_link(**EVIDENCE_LINK_VENT_SUPPORTS)
        self.assertEqual(link.link_id, "elink-vent-evidence-01")
        self.assertEqual(link.proficiency_id, "prof-vent-01")
        self.assertEqual(link.evidence_id, "evidence-vent-01")
        self.assertEqual(link.link_type, "supports")

    def test_evidence_link_rejects_unknown_proficiency(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.add_evidence_link(**MALFORMED_EVIDENCE_LINK_MISSING_PROFICIENCY)
        self.assertIn("does not exist", str(cm.exception))

    def test_evidence_link_rejects_bad_type(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        with self.assertRaises(ValueError) as cm:
            reg.add_evidence_link(**MALFORMED_EVIDENCE_LINK_BAD_TYPE)
        self.assertIn("link_type", str(cm.exception))

    def test_evidence_link_rejects_duplicate_id(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_evidence_link(**EVIDENCE_LINK_VENT_SUPPORTS)
        with self.assertRaises(ValueError) as cm:
            reg.add_evidence_link(**DUPLICATE_EVIDENCE_LINK_ATTEMPT)
        self.assertIn("Duplicate link_id", str(cm.exception))

    def test_get_evidence_links_for_proficiency(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_evidence_link(**EVIDENCE_LINK_VENT_SUPPORTS)
        reg.add_evidence_link(**EVIDENCE_LINK_VENT_CONTRADICTS)
        links = reg.get_evidence_links_for_proficiency("prof-vent-01")
        self.assertEqual(len(links), 2)

    def test_get_evidence_links_for_evidence(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_evidence_link(**EVIDENCE_LINK_VENT_SUPPORTS)
        links = reg.get_evidence_links_for_evidence("evidence-vent-01")
        self.assertEqual(len(links), 1)

    def test_evidence_links_traceable(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_evidence_link(**EVIDENCE_LINK_VENT_SUPPORTS)
        link = reg.get_evidence_link("elink-vent-evidence-01")
        self.assertIsNotNone(link)
        self.assertEqual(link.proficiency_id, "prof-vent-01")
        self.assertEqual(link.evidence_id, "evidence-vent-01")

    def test_evidence_link_version_increments(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_evidence_link(**EVIDENCE_LINK_VENT_SUPPORTS)
        reg.add_evidence_link(**EVIDENCE_LINK_VENT_CONTRADICTS)
        link1 = reg.get_evidence_link("elink-vent-evidence-01")
        link2 = reg.get_evidence_link("elink-vent-evidence-02")
        self.assertEqual(link1.version, 1)
        self.assertEqual(link2.version, 2)


# ====================================================================== #
#  Edge cases: malformed ingest rejected
# ====================================================================== #

class TestEdgeCasesMalformedIngestRejected(unittest.TestCase):
    def test_rejects_empty_verbatim(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        with self.assertRaises(ValueError):
            reg.ingest_proficiency(**MALFORMED_PROFICIENCY_MISSING_VERBATIM)

    def test_rejects_unknown_source(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.ingest_proficiency(**MALFORMED_PROFICIENCY_MISSING_SOURCE)
        self.assertIn("does not exist", str(cm.exception))

    def test_rejects_bad_step(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        with self.assertRaises(ValueError):
            reg.ingest_proficiency(**MALFORMED_PROFICIENCY_BAD_STEP)

    def test_rejects_bad_status(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        with self.assertRaises(ValueError):
            reg.ingest_proficiency(**MALFORMED_PROFICIENCY_BAD_STATUS)

    def test_rejects_non_string_knowledge(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        with self.assertRaises(ValueError):
            reg.ingest_proficiency(**MALFORMED_PROFICIENCY_NON_STRING_KNOWLEDGE)

    def test_rejects_empty_knowledge_list(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        with self.assertRaises(ValueError):
            reg.ingest_proficiency(**MALFORMED_PROFICIENCY_EMPTY_KNOWLEDGE)

    def test_rejects_duplicate_topic_link(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_topic_link(**TOPIC_LINK_VENT_TO_LUNG)
        with self.assertRaises(ValueError) as cm:
            reg.add_topic_link(**DUPLICATE_TOPIC_LINK_ATTEMPT)
        self.assertIn("Duplicate link_id", str(cm.exception))

    def test_rejects_duplicate_evidence_link(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_evidence_link(**EVIDENCE_LINK_VENT_SUPPORTS)
        with self.assertRaises(ValueError) as cm:
            reg.add_evidence_link(**DUPLICATE_EVIDENCE_LINK_ATTEMPT)
        self.assertIn("Duplicate link_id", str(cm.exception))

    def test_rejects_duplicate_conflict(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)
        with self.assertRaises(ValueError) as cm:
            reg.flag_conflict(**DUPLICATE_CONFLICT_ATTEMPT)
        self.assertIn("Duplicate conflict_id", str(cm.exception))

    def test_rejects_duplicate_interpretation(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_interpretation(**INTERPRETATION_VENT_V1)
        with self.assertRaises(ValueError) as cm:
            reg.add_interpretation(**DUPLICATE_INTERPRETATION_ATTEMPT)
        self.assertIn("Duplicate interpretation_id", str(cm.exception))


# ====================================================================== #
#  Edge cases: superseded version still retrievable
# ====================================================================== #

class TestEdgeCasesSupersededVersionRetrievable(unittest.TestCase):
    def test_v1_retrieved_after_v2_supersede(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )
        v1 = reg.get_proficiency("prof-vent-01", version=1)
        self.assertIsNotNone(v1)
        self.assertEqual(v1.version, 1)
        self.assertEqual(v1.status, "active")

    def test_v2_is_latest_after_supersede(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )
        latest = reg.get_proficiency("prof-vent-01")
        self.assertEqual(latest.version, 2)

    def test_history_includes_both_versions(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )
        history = reg.get_proficiency_history("prof-vent-01")
        self.assertEqual(len(history), 2)

    def test_supersede_rejects_unknown_proficiency(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.supersede_proficiency(
                proficiency_id="prof-nonexistent",
                new_source_id="src-step2-cc101", new_source_version="1.0",
                new_verbatim_requirement="Some text",
                new_knowledge_requirements=["Know something"],
                new_application_requirements=["Do something"],
                new_rationale_requirements=["Explain something"],
                new_linked_topics=[],
                new_linked_learning_outcomes=[],
                new_linked_evidence=[],
            )
        self.assertIn("does not exist", str(cm.exception))


# ====================================================================== #
#  Edge cases: injectable clock / deterministic fixtures
# ====================================================================== #

class TestEdgeCasesInjectableClock(unittest.TestCase):
    def test_registry_uses_injected_clock(self):
        from datetime import datetime
        fixed_now = datetime(2026, 1, 1, 0, 0, 0)
        def fixed_clock():
            return fixed_now
        reg = make_registry(clock=fixed_clock)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        record = reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        self.assertEqual(record.provenance["ingested_at"], "2026-01-01T00:00:00")

    def test_registry_default_clock_is_utcnow(self):
        reg = ProficiencyRegistry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        record = reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        self.assertIsNotNone(record.provenance["ingested_at"])
        self.assertGreater(len(record.provenance["ingested_at"]), 0)


# ====================================================================== #
#  Edge cases: deterministic fixtures
# ====================================================================== #

class TestEdgeCasesDeterministicFixtures(unittest.TestCase):
    def test_step2_source_v1_deterministic(self):
        self.assertEqual(STEP2_PROFICIENCY_SOURCE_V1["content_hash"], "s2v1hash001")

    def test_step2_source_v2_deterministic(self):
        self.assertEqual(STEP2_PROFICIENCY_SOURCE_V2["content_hash"], "s2v2hash002")

    def test_vent_proficiency_v1_deterministic(self):
        self.assertEqual(PROFICIENCY_VENT_V1["verbatim_requirement"],
            "Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, and weaning criteria.")

    def test_vent_proficiency_v2_deterministic(self):
        self.assertEqual(PROFICIENCY_VENT_V2["verbatim_requirement"],
            "Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.")


# ====================================================================== #
#  Integration: full S8 scenario
# ====================================================================== #

class TestIntegrationFullS8Scenario(unittest.TestCase):
    def test_full_proficiency_ingestion_flow(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.add_source(**FUTURE_CONTEXT_SOURCE_V1)

        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.ingest_proficiency(**PROFICIENCY_HEMO_V1)
        reg.ingest_proficiency(**PROFICIENCY_FUTURE_V1)

        reg.add_topic_link(**TOPIC_LINK_VENT_TO_LUNG)
        reg.add_topic_link(**TOPIC_LINK_HEMO_TO_ARTERIAL)

        reg.add_evidence_link(**EVIDENCE_LINK_VENT_SUPPORTS)
        reg.add_evidence_link(**EVIDENCE_LINK_HEMO_REQUIRES)

        reg.add_interpretation(**INTERPRETATION_VENT_V1)
        reg.add_interpretation(**INTERPRETATION_HEMO_V1)

        result = reg.validate()
        self.assertTrue(result["valid"])
        self.assertEqual(result["source_count"], 3)
        self.assertEqual(result["proficiency_count"], 3)
        self.assertEqual(result["topic_link_count"], 2)
        self.assertEqual(result["evidence_link_count"], 2)
        self.assertEqual(result["interpretation_count"], 2)

    def test_supersede_then_validate(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)

        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )

        result = reg.validate()
        self.assertTrue(result["valid"])
        self.assertEqual(result["proficiency_count"], 2)

    def test_future_context_addable_without_redesign(self):
        """Future Step 2/3 context can be added without redesign."""
        reg = make_registry()
        reg.add_source(**FUTURE_CONTEXT_SOURCE_V1)
        record = reg.ingest_proficiency(**PROFICIENCY_FUTURE_V1)

        self.assertEqual(record.step, "future")
        self.assertEqual(record.domain, "ai_decision_support")
        self.assertEqual(record.status, "active")

        # Can also add topic links and evidence links for future context
        reg.add_topic_link(
            link_id="tlink-ai-to-basics",
            proficiency_id="prof-ai-01",
            topic_id="topic-ai-basics",
            link_type="maps_to",
        )
        reg.add_evidence_link(
            link_id="elink-ai-evidence-01",
            proficiency_id="prof-ai-01",
            evidence_id="evidence-ai-01",
            link_type="supports",
        )

        self.assertEqual(len(reg.get_topic_links_for_proficiency("prof-ai-01")), 1)
        self.assertEqual(len(reg.get_evidence_links_for_proficiency("prof-ai-01")), 1)

    def test_verbatim_preserved_after_multiple_supersedes(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V2)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)

        reg.supersede_proficiency(
            proficiency_id="prof-vent-01",
            new_source_id="src-step2-cc101", new_source_version="2.0",
            new_verbatim_requirement="Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
            new_knowledge_requirements=["Know ventilator modes", "Know ECMO indications"],
            new_application_requirements=["Set ventilator parameters", "Identify ECMO candidates"],
            new_rationale_requirements=["Explain lung-protective rationale", "Explain ECMO indications"],
            new_linked_topics=["ventilation-basics", "ecmo"],
            new_linked_learning_outcomes=["outcome-vent-01", "outcome-vent-03"],
            new_linked_evidence=["evidence-vent-01", "evidence-ecmo-01"],
        )

        v1 = reg.get_proficiency("prof-vent-01", version=1)
        self.assertIsNotNone(v1)
        self.assertIn("ventilator modes", v1.verbatim_requirement)
        self.assertIn("lung-protective", v1.verbatim_requirement)
        self.assertIn("weaning criteria", v1.verbatim_requirement)
        # v1 does NOT contain ECMO (that was added in v2)
        self.assertNotIn("ECMO", v1.verbatim_requirement)


# ====================================================================== #
#  Edge cases: state serialization
# ====================================================================== #

class TestEdgeCasesStateSerialization(unittest.TestCase):
    def test_get_state_returns_complete_state(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_topic_link(**TOPIC_LINK_VENT_TO_LUNG)
        reg.add_evidence_link(**EVIDENCE_LINK_VENT_SUPPORTS)
        reg.add_interpretation(**INTERPRETATION_VENT_V1)

        state = reg.get_state()
        self.assertIn("sources", state)
        self.assertIn("proficiencies", state)
        self.assertIn("topic_links", state)
        self.assertIn("evidence_links", state)
        self.assertIn("conflicts", state)
        self.assertIn("interpretations", state)

    def test_get_state_sources_preserved(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.replace_source(
            source_id="src-step2-cc101",
            new_version="2.0",
            new_content_hash="s2v2hash002",
            new_content=STEP2_PROFICIENCY_SOURCE_V2["content"],
        )
        state = reg.get_state()
        src_versions = state["sources"]["src-step2-cc101"]
        self.assertIn("1.0", src_versions)
        self.assertIn("2.0", src_versions)


# ====================================================================== #
#  Edge cases: registry validation
# ====================================================================== #

class TestEdgeCasesRegistryValidation(unittest.TestCase):
    def test_validate_returns_counts(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)
        reg.add_topic_link(**TOPIC_LINK_VENT_TO_LUNG)
        reg.add_evidence_link(**EVIDENCE_LINK_VENT_SUPPORTS)
        reg.add_interpretation(**INTERPRETATION_VENT_V1)

        result = reg.validate()
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["proficiency_count"], 1)
        self.assertEqual(result["topic_link_count"], 1)
        self.assertEqual(result["evidence_link_count"], 1)
        self.assertEqual(result["interpretation_count"], 1)

    def test_validate_rejects_untraceable_proficiency(self):
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)

        # Manually corrupt a proficiency's source_version
        profs = reg._proficiencies["prof-vent-01"]
        v1 = profs[1]
        corrupted = ProficiencyRecord(
            proficiency_id=v1.proficiency_id,
            source_id=v1.source_id,
            source_version="99.0",  # doesn't exist
            provenance=v1.provenance,
            step=v1.step,
            domain=v1.domain,
            verbatim_requirement=v1.verbatim_requirement,
            knowledge_requirements=v1.knowledge_requirements,
            application_requirements=v1.application_requirements,
            rationale_requirements=v1.rationale_requirements,
            linked_topics=v1.linked_topics,
            linked_learning_outcomes=v1.linked_learning_outcomes,
            linked_evidence=v1.linked_evidence,
            status=v1.status,
            version=v1.version,
        )
        reg._proficiencies["prof-vent-01"][1] = corrupted

        result = reg.validate()
        self.assertFalse(result["valid"])
        self.assertIn("prof-vent-01:v1", result["untraceable_proficiencies"])


# ====================================================================== #
#  Edge cases: conflicting context flagged (explicit)
# ====================================================================== #

class TestEdgeCasesConflictingContextFlagged(unittest.TestCase):
    def test_conflict_flagged_not_reconciled(self):
        """Conflicting context must be flagged, not silently reconciled."""
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)

        reg.flag_conflict(**CONFLICT_VENT_DOMAIN_VS_HEMO)

        conflict = reg.get_conflict("conflict-vent-domain")
        # Both values preserved
        self.assertEqual(conflict.value_a, "mechanical_ventilation")
        self.assertEqual(conflict.value_b, "haemodynamic_monitoring")
        # Not silently reconciled
        self.assertFalse(conflict.resolved)

    def test_conflict_with_same_source_different_field(self):
        """Conflict can be within the same source but different field."""
        reg = make_registry()
        reg.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_VENT_V1)

        reg.flag_conflict(**CONFLICT_VENT_VERBATIM_MISMATCH)

        conflict = reg.get_conflict("conflict-vent-verbatim")
        self.assertEqual(conflict.source_a, "src-step2-cc101")
        self.assertEqual(conflict.source_b, "src-step2-cc101")
        self.assertEqual(conflict.field, "verbatim_requirement")
        self.assertFalse(conflict.resolved)


# ====================================================================== #
#  Edge cases: future context addable without redesign
# ====================================================================== #

class TestEdgeCasesFutureContextAddable(unittest.TestCase):
    def test_future_context_ingested(self):
        reg = make_registry()
        reg.add_source(**FUTURE_CONTEXT_SOURCE_V1)
        record = reg.ingest_proficiency(**PROFICIENCY_FUTURE_V1)
        self.assertEqual(record.step, "future")
        self.assertEqual(record.status, "active")

    def test_future_context_has_topic_links(self):
        reg = make_registry()
        reg.add_source(**FUTURE_CONTEXT_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_FUTURE_V1)
        reg.add_topic_link(
            link_id="tlink-ai-to-basics",
            proficiency_id="prof-ai-01",
            topic_id="topic-ai-basics",
            link_type="maps_to",
        )
        links = reg.get_topic_links_for_proficiency("prof-ai-01")
        self.assertEqual(len(links), 1)

    def test_future_context_has_evidence_links(self):
        reg = make_registry()
        reg.add_source(**FUTURE_CONTEXT_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_FUTURE_V1)
        reg.add_evidence_link(
            link_id="elink-ai-evidence-01",
            proficiency_id="prof-ai-01",
            evidence_id="evidence-ai-01",
            link_type="supports",
        )
        links = reg.get_evidence_links_for_proficiency("prof-ai-01")
        self.assertEqual(len(links), 1)

    def test_future_context_has_interpretation(self):
        reg = make_registry()
        reg.add_source(**FUTURE_CONTEXT_SOURCE_V1)
        reg.ingest_proficiency(**PROFICIENCY_FUTURE_V1)
        reg.add_interpretation(
            interpretation_id="interp-ai-01",
            proficiency_id="prof-ai-01",
            source_version="1.0",
            knowledge_summary="The learner must understand basic AI principles.",
            application_summary="The learner must evaluate AI recommendations.",
            rationale_summary="The learner must explain why AI requires clinical validation.",
            gap_indicators=["limited AI knowledge"],
            readiness_indicators=["understands AI basics"],
        )
        interps = reg.get_interpretations_for_proficiency("prof-ai-01")
        self.assertEqual(len(interps), 1)


if __name__ == "__main__":
    unittest.main()
