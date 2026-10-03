"""Batch 1 QA tests for Daily Synthesis contracts.

Covers: valid payloads, missing fields, wrong enums, bad schema version,
invalid timestamps, generic-study rejection, persistence reload, duplicate handling.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.daily_synthesis.contracts import (
    ConflictReason,
    DailyCommandBrief,
    DailyPlanToRhythm,
    GrowthHandoff,
    ProjectStatusHandoff,
    RhythmCapacityHandoff,
    RhythmScheduleConflict,
    ScholarHandoff,
    ValidationError,
    handle_duplicate,
    validate_payload,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _valid_scholar(**overrides):
    defaults = dict(
        agent_id="agent-1",
        current_batch_id="batch-42",
        exact_action="review CCRN3 chapter 5",
        estimated_minutes=30,
        definition_of_done="chapter 5 notes written",
        reading_target={
            "required": True,
            "article_title": "CRRN3 Deep Dive",
            "exact_sections_to_read": ["section 5.1", "section 5.2"],
            "extraction_goal": "extract key definitions",
        },
        source_refs=["https://example.com/crrn3"],
    )
    defaults.update(overrides)
    return ScholarHandoff(**defaults)


def _valid_brief(**overrides):
    defaults = dict(
        agent_id="agent-1",
        date="2026-10-03",
        top_outcomes=[
            {
                "definition_of_done": "outcome 1 done",
                "source_refs": ["ref1"],
            }
        ],
        capacity_used_minutes=60,
        buffer_minutes=15,
    )
    defaults.update(overrides)
    return DailyCommandBrief(**defaults)


def _valid_handoff(schema_version, **overrides):
    defaults = dict(
        agent_id="agent-1",
        schema_version=schema_version,
    )
    defaults.update(overrides)
    return SCHEMA_DEFAULTS[schema_version](**defaults)


SCHEMA_DEFAULTS = {
    "rhythm_capacity_handoff.v1": RhythmCapacityHandoff,
    "scholar_handoff.v1": ScholarHandoff,
    "growth_handoff.v1": GrowthHandoff,
    "project_status_handoff.v1": ProjectStatusHandoff,
    "daily_command_brief.v1": DailyCommandBrief,
    "rhythm_schedule_conflict.v1": RhythmScheduleConflict,
    "daily_plan_to_rhythm.v1": DailyPlanToRhythm,
}


# ---------------------------------------------------------------------------
# valid payloads
# ---------------------------------------------------------------------------

class ValidPayloadsTest(unittest.TestCase):
    def test_rhythm_capacity_handoff_valid(self):
        h = RhythmCapacityHandoff(
            agent_id="agent-1", rhythm_id="r1",
            capacity_used_minutes=45, capacity_total_minutes=120,
            recovery_buffer_minutes=10,
        )
        result = h.validate()
        self.assertEqual(result["agent_id"], "agent-1")
        self.assertEqual(result["recovery_buffer_minutes"], 10)

    def test_scholar_handoff_valid_full(self):
        s = _valid_scholar()
        result = s.validate()
        self.assertEqual(result["current_batch_id"], "batch-42")
        self.assertEqual(result["estimated_minutes"], 30)

    def test_growth_handoff_valid(self):
        g = GrowthHandoff(
            agent_id="agent-1", project_id="p1",
            action="optimize", estimated_minutes=45,
            definition_of_done="metrics improved",
        )
        result = g.validate()
        self.assertEqual(result["project_id"], "p1")

    def test_project_status_handoff_valid(self):
        p = ProjectStatusHandoff(
            agent_id="agent-1", project_id="p1",
            status="on_track", summary="good progress",
            next_action="continue",
        )
        result = p.validate()
        self.assertEqual(result["status"], "on_track")

    def test_daily_command_brief_valid(self):
        b = _valid_brief()
        result = b.validate()
        self.assertEqual(len(result["top_outcomes"]), 1)

    def test_rhythm_schedule_conflict_valid(self):
        c = RhythmScheduleConflict(
            agent_id="agent-1", outcome_id="o1",
            reason=ConflictReason.OVERLAP.value,
            required_minutes=30, available_minutes=15,
            possible_alternatives=["reschedule", "shorten"],
        )
        result = c.validate()
        self.assertEqual(result["reason"], ConflictReason.OVERLAP.value)

    def test_daily_plan_to_rhythm_valid(self):
        p = DailyPlanToRhythm(
            agent_id="agent-1", plan_id="plan-1", rhythm_id="r1",
            learning_detail={"exact_action": "review CCRN3 chapter 5"},
        )
        result = p.validate()
        self.assertEqual(result["learning_detail"]["exact_action"], "review CCRN3 chapter 5")


# ---------------------------------------------------------------------------
# missing fields
# ---------------------------------------------------------------------------

class MissingFieldsTest(unittest.TestCase):
    def test_scholar_missing_current_batch_id(self):
        s = ScholarHandoff(
            agent_id="agent-1", exact_action="review CCRN3",
            estimated_minutes=30, definition_of_done="done",
        )
        with self.assertRaises(ValidationError):
            s.validate()

    def test_scholar_missing_exact_action(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            estimated_minutes=30, definition_of_done="done",
        )
        with self.assertRaises(ValidationError):
            s.validate()

    def test_scholar_missing_estimated_minutes(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            exact_action="review CCRN3", definition_of_done="done",
        )
        with self.assertRaises(ValidationError):
            s.validate()

    def test_scholar_missing_definition_of_done(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            exact_action="review CCRN3", estimated_minutes=30,
        )
        with self.assertRaises(ValidationError):
            s.validate()

    def test_rhythm_capacity_missing_recovery_buffer(self):
        h = RhythmCapacityHandoff(
            agent_id="agent-1", rhythm_id="r1",
            capacity_used_minutes=45, capacity_total_minutes=120,
        )
        # recovery_buffer_minutes is required and defaults to None
        with self.assertRaises(ValidationError):
            h.validate()

    def test_brief_missing_capacity_used(self):
        b = DailyCommandBrief(
            agent_id="agent-1", date="2026-10-03",
            top_outcomes=[{"definition_of_done": "d", "source_refs": ["r"]}],
            buffer_minutes=10,
        )
        with self.assertRaises(ValidationError):
            b.validate()

    def test_brief_missing_buffer(self):
        b = DailyCommandBrief(
            agent_id="agent-1", date="2026-10-03",
            top_outcomes=[{"definition_of_done": "d", "source_refs": ["r"]}],
            capacity_used_minutes=60,
        )
        with self.assertRaises(ValidationError):
            b.validate()


# ---------------------------------------------------------------------------
# wrong enums
# ---------------------------------------------------------------------------

class WrongEnumTest(unittest.TestCase):
    def test_conflict_bad_reason(self):
        c = RhythmScheduleConflict(
            agent_id="agent-1", outcome_id="o1",
            reason="not_a_real_reason",
            required_minutes=30, available_minutes=15,
        )
        with self.assertRaises(ValidationError):
            c.validate()

    def test_conflict_valid_reason_overlap(self):
        c = RhythmScheduleConflict(
            agent_id="agent-1", outcome_id="o1",
            reason=ConflictReason.OVERLAP.value,
            required_minutes=30, available_minutes=15,
        )
        result = c.validate()
        self.assertEqual(result["reason"], ConflictReason.OVERLAP.value)


# ---------------------------------------------------------------------------
# bad schema version
# ---------------------------------------------------------------------------

class BadSchemaVersionTest(unittest.TestCase):
    def test_unknown_schema_version(self):
        with self.assertRaises(ValidationError):
            validate_payload({"schema_version": "unknown.v99", "agent_id": "a1"})

    def test_missing_schema_version(self):
        with self.assertRaises(ValidationError):
            validate_payload({"agent_id": "a1"})


# ---------------------------------------------------------------------------
# invalid timestamps
# ---------------------------------------------------------------------------

class InvalidTimestampTest(unittest.TestCase):
    def test_bad_timestamp_scholar(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            exact_action="review CCRN3", estimated_minutes=30,
            definition_of_done="done",
            timestamp="not-a-timestamp",
        )
        with self.assertRaises(ValidationError):
            s.validate()

    def test_bad_timestamp_capacity(self):
        h = RhythmCapacityHandoff(
            agent_id="agent-1", rhythm_id="r1",
            capacity_used_minutes=45, capacity_total_minutes=120,
            recovery_buffer_minutes=10,
            timestamp="not-a-timestamp",
        )
        with self.assertRaises(ValidationError):
            h.validate()


# ---------------------------------------------------------------------------
# generic-study rejection (QA plan failing examples)
# ---------------------------------------------------------------------------

class GenericStudyRejectionTest(unittest.TestCase):
    def test_reject_study_ccrn3(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            exact_action="study CCRN3", estimated_minutes=30,
            definition_of_done="done",
        )
        with self.assertRaises(ValidationError) as cm:
            s.validate()
        self.assertIn("generic learning task rejected", str(cm.exception))

    def test_reject_do_assignment(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            exact_action="do assignment", estimated_minutes=30,
            definition_of_done="done",
        )
        with self.assertRaises(ValidationError) as cm:
            s.validate()
        self.assertIn("generic learning task rejected", str(cm.exception))

    def test_reject_read_an_article(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            exact_action="read an article", estimated_minutes=30,
            definition_of_done="done",
        )
        with self.assertRaises(ValidationError) as cm:
            s.validate()
        self.assertIn("generic learning task rejected", str(cm.exception))

    def test_accept_named_article(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            exact_action="read article 'CRRN3 Deep Dive' section 5",
            estimated_minutes=30, definition_of_done="done",
        )
        result = s.validate()
        self.assertEqual(result["exact_action"], "read article 'CRRN3 Deep Dive' section 5")


# ---------------------------------------------------------------------------
# passing full examples
# ---------------------------------------------------------------------------

class FullExamplesTest(unittest.TestCase):
    def test_full_scholar_example(self):
        s = ScholarHandoff(
            agent_id="agent-1",
            current_batch_id="batch-2026-10-03",
            exact_action="review CCRN3 chapter 5 and annotate key definitions",
            estimated_minutes=45,
            definition_of_done="annotations saved to shared doc",
            reading_target={
                "required": True,
                "article_title": "CRRN3 Deep Dive",
                "exact_sections_to_read": ["section 5.1", "section 5.2"],
                "extraction_goal": "extract key definitions",
            },
            source_refs=["https://example.com/crrn3"],
        )
        result = s.validate()
        self.assertEqual(result["current_batch_id"], "batch-2026-10-03")
        self.assertEqual(len(result["source_refs"]), 1)

    def test_full_rhythm_capacity_example(self):
        h = RhythmCapacityHandoff(
            agent_id="agent-1",
            rhythm_id="rhythm-2026-10-03",
            capacity_used_minutes=90,
            capacity_total_minutes=180,
            recovery_buffer_minutes=20,
            notes="morning block full",
        )
        result = h.validate()
        self.assertEqual(result["capacity_used_minutes"], 90)
        self.assertEqual(result["recovery_buffer_minutes"], 20)


# ---------------------------------------------------------------------------
# reading_target required=true validation
# ---------------------------------------------------------------------------

class ReadingTargetTest(unittest.TestCase):
    def test_reading_target_required_missing_article_title(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            exact_action="review CCRN3 chapter 5",
            estimated_minutes=30, definition_of_done="done",
            reading_target={
                "required": True,
                "exact_sections_to_read": ["section 5.1"],
                "extraction_goal": "extract",
            },
        )
        with self.assertRaises(ValidationError):
            s.validate()

    def test_reading_target_required_missing_sections(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            exact_action="review CCRN3 chapter 5",
            estimated_minutes=30, definition_of_done="done",
            reading_target={
                "required": True,
                "article_title": "CRRN3 Deep Dive",
                "extraction_goal": "extract",
            },
        )
        with self.assertRaises(ValidationError):
            s.validate()

    def test_reading_target_required_missing_goal(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            exact_action="review CCRN3 chapter 5",
            estimated_minutes=30, definition_of_done="done",
            reading_target={
                "required": True,
                "article_title": "CRRN3 Deep Dive",
                "exact_sections_to_read": ["section 5.1"],
            },
        )
        with self.assertRaises(ValidationError):
            s.validate()

    def test_reading_target_optional_not_required(self):
        s = ScholarHandoff(
            agent_id="agent-1", current_batch_id="b1",
            exact_action="review CCRN3 chapter 5",
            estimated_minutes=30, definition_of_done="done",
            reading_target={"required": False},
        )
        result = s.validate()
        self.assertIsNotNone(result["reading_target"])


# ---------------------------------------------------------------------------
# persistence reload (schema re-validation on read-back)
# ---------------------------------------------------------------------------

class PersistenceReloadTest(unittest.TestCase):
    def test_validate_payload_roundtrip(self):
        original = _valid_scholar()
        payload = original.validate()
        # reload through validate_payload (simulates read-back from persistence)
        result = validate_payload(payload)
        self.assertEqual(result["current_batch_id"], "batch-42")

    def test_validate_payload_roundtrip_capacity(self):
        original = RhythmCapacityHandoff(
            agent_id="agent-1", rhythm_id="r1",
            capacity_used_minutes=45, capacity_total_minutes=120,
            recovery_buffer_minutes=10,
        )
        payload = original.validate()
        result = validate_payload(payload)
        self.assertEqual(result["rhythm_id"], "r1")


# ---------------------------------------------------------------------------
# duplicate/version handling
# ---------------------------------------------------------------------------

class DuplicateHandlingTest(unittest.TestCase):
    def test_latest_wins_newer_incoming(self):
        existing = {"timestamp": "2026-10-03T10:00:00+00:00"}
        incoming = {"timestamp": "2026-10-03T11:00:00+00:00"}
        result = handle_duplicate(existing, incoming, "latest_wins")
        self.assertEqual(result["action"], "replace")
        self.assertEqual(result["record"], incoming)

    def test_latest_wins_older_incoming(self):
        existing = {"timestamp": "2026-10-03T11:00:00+00:00"}
        incoming = {"timestamp": "2026-10-03T10:00:00+00:00"}
        result = handle_duplicate(existing, incoming, "latest_wins")
        self.assertEqual(result["action"], "keep_existing")
        self.assertEqual(result["record"], existing)

    def test_keep_history_both(self):
        existing = {"timestamp": "2026-10-03T10:00:00+00:00"}
        incoming = {"timestamp": "2026-10-03T11:00:00+00:00"}
        result = handle_duplicate(existing, incoming, "keep_history")
        self.assertEqual(result["action"], "keep_both")
        self.assertIn("existing", result)
        self.assertIn("incoming", result)

    def test_default_strategy_latest_wins(self):
        existing = {"timestamp": "2026-10-03T10:00:00+00:00"}
        incoming = {"timestamp": "2026-10-03T11:00:00+00:00"}
        result = handle_duplicate(existing, incoming)
        self.assertEqual(result["action"], "replace")


# ---------------------------------------------------------------------------
# idempotency key generation
# ---------------------------------------------------------------------------

class IdempotencyKeyTest(unittest.TestCase):
    def test_same_payload_same_key(self):
        from agents.daily_synthesis.persistence import DailySynthesisPersistence
        p1 = {"agent_id": "a1", "exact_action": "review CCRN3"}
        p2 = {"agent_id": "a1", "exact_action": "review CCRN3"}
        k1 = DailySynthesisPersistence.idempotency_key(p1)
        k2 = DailySynthesisPersistence.idempotency_key(p2)
        self.assertEqual(k1, k2)

    def test_different_payloads_different_keys(self):
        from agents.daily_synthesis.persistence import DailySynthesisPersistence
        p1 = {"agent_id": "a1", "exact_action": "review CCRN3"}
        p2 = {"agent_id": "a1", "exact_action": "do assignment"}
        k1 = DailySynthesisPersistence.idempotency_key(p1)
        k2 = DailySynthesisPersistence.idempotency_key(p2)
        self.assertNotEqual(k1, k2)


# ---------------------------------------------------------------------------
# degraded mode
# ---------------------------------------------------------------------------

class DegradedModeTest(unittest.TestCase):
    def test_persistence_unavailable_on_bad_url(self):
        from agents.daily_synthesis.persistence import DailySynthesisPersistence
        p = DailySynthesisPersistence("http://localhost:1", "bad-key")
        result = p.write("handoffs", {
            "schema_version": "scholar_handoff.v1",
            "agent_id": "a1",
            "current_batch_id": "b1",
            "exact_action": "review CCRN3 chapter 5",
            "estimated_minutes": 30,
            "definition_of_done": "done",
        })
        self.assertEqual(result["status"], "persistence_unavailable")

    def test_persistence_unavailable_on_read(self):
        from agents.daily_synthesis.persistence import DailySynthesisPersistence
        p = DailySynthesisPersistence("http://localhost:1", "bad-key")
        result = p.read("handoffs")
        self.assertEqual(result["status"], "persistence_unavailable")

    def test_no_sqlite_fallback(self):
        # Degraded mode must NOT silently write to SQLite
        from agents.daily_synthesis.persistence import DailySynthesisPersistence
        p = DailySynthesisPersistence("http://localhost:1", "bad-key")
        result = p.write("handoffs", {
            "schema_version": "scholar_handoff.v1",
            "agent_id": "a1",
            "current_batch_id": "b1",
            "exact_action": "review CCRN3 chapter 5",
            "estimated_minutes": 30,
            "definition_of_done": "done",
        })
        self.assertNotEqual(result["status"], "synced")
        # No outbox/queue created — degraded mode returns persistence_unavailable only


if __name__ == "__main__":
    unittest.main()
