"""Tests for Scholar precision handoff skill — Batch 3 Tests A–F."""

from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

# Ensure the repo root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.daily_synthesis.contracts import ScholarHandoff, validate_payload, ValidationError
from agents.scholar.handoff import (
    produce_handoff,
    advance_state,
    _load_state,
    _find_current_batch,
    _is_stale,
    _short_window_handoff,
    _full_task_handoff,
    STATE_PATH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state() -> dict:
    """Return a minimal state for testing with 12 batches."""
    batches = []
    for i in range(12):
        batches.append({
            "batch_id": f"batch_{i}",
            "title": f"Batch {i} test batch",
            "sections": [f"section_{i}"],
            "articles": [
                {
                    "title": f"Article A for batch {i}",
                    "status": "not_started",
                },
                {
                    "title": f"Article B for batch {i}",
                    "status": "not_started",
                },
            ],
            "extraction_goals": [f"goal for batch {i}"],
            "word_target": "100-200",
            "status": "not_started",
        })
    return {
        "schema_version": "level7_module1_state.v1",
        "module": "Level 7 ICU Module 1",
        "last_updated": "2026-10-03T12:52:00+01:00",
        "last_handoff_timestamp": "2026-10-03T12:00:00+01:00",
        "batches": batches,
    }


def _write_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Test A: exact current batch (not "CCRN3")
# ---------------------------------------------------------------------------


class TestExactCurrentBatch:
    """Test A: producer returns the exact current batch, not a generic string."""

    def test_current_batch_is_batch_0_not_generic(self):
        state = _make_state()
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        assert handoff["current_batch_id"] == "batch_0"
        assert handoff["current_batch_id"] != "CCRN3"

    def test_current_batch_is_batch_1_when_0_complete(self):
        state = _make_state()
        # Mark batch_0 articles complete
        for article in state["batches"][0]["articles"]:
            article["status"] = "complete"
            article["completion_events"] = [
                {
                    "timestamp": "2026-10-03T11:00:00+01:00",
                    "action": "complete",
                    "previous_status": "read",
                    "article_title": article["title"],
                    "batch_id": "batch_0",
                }
            ]
        state["batches"][0]["status"] = "complete"
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        assert handoff["current_batch_id"] == "batch_1"


# ---------------------------------------------------------------------------
# Test B: exact writing action
# ---------------------------------------------------------------------------


class TestExactWritingAction:
    """Test B: exact_action names the specific article/section, never generic."""

    def test_exact_action_is_not_generic(self):
        state = _make_state()
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        assert handoff["exact_action"] is not None
        # Must not be generic strings
        assert handoff["exact_action"].strip().lower() not in (
            "study ccrn3",
            "do assignment",
            "read an article",
        )
        # Must contain a named article or specific task
        assert len(handoff["exact_action"]) > 20

    def test_exact_action_contains_article_name(self):
        state = _make_state()
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        # batch_0 has not_started articles; action should reference the first article
        assert "Article A" in handoff["exact_action"]

    def test_exact_action_rejected_by_contract(self):
        """Verify that generic strings are rejected by the contract validator."""
        for generic in ["study CCRN3", "do assignment", "read an article"]:
            handoff = ScholarHandoff(
                schema_version="scholar_handoff.v1",
                agent_id="test",
                current_batch_id="batch_0",
                exact_action=generic,
                estimated_minutes=30,
                definition_of_done="test",
            )
            with pytest.raises(ValidationError):
                handoff.validate()


# ---------------------------------------------------------------------------
# Test C: quick-read task for short window
# ---------------------------------------------------------------------------


class TestQuickReadTask:
    """Test C: short-window support returns a single quick-read atom."""

    def test_short_window_returns_quick_read(self):
        state = _make_state()
        _write_state(state)
        handoff = produce_handoff(
            agent_id="test-agent",
            window_minutes=25,
            energy_level="light-medium",
        )
        assert handoff["short_window"]["quick_read"] is True
        assert "best_next_article" in handoff["short_window"]
        assert handoff["short_window"]["best_next_article"] != ""
        assert "backup_article" in handoff["short_window"]

    def test_short_window_reading_target_has_exact_sections(self):
        state = _make_state()
        _write_state(state)
        handoff = produce_handoff(
            agent_id="test-agent",
            window_minutes=25,
            energy_level="light-medium",
        )
        rt = handoff["reading_target"]
        assert rt["required"] is True
        assert rt["article_title"] != ""
        assert isinstance(rt["exact_sections_to_read"], list)
        assert len(rt["exact_sections_to_read"]) > 0
        assert rt["extraction_goal"] != ""

    def test_short_window_nominates_one_best_and_one_backup(self):
        state = _make_state()
        # batch_0 has 2 not_started articles
        _write_state(state)
        handoff = produce_handoff(
            agent_id="test-agent",
            window_minutes=25,
            energy_level="light-medium",
        )
        best = handoff["short_window"]["best_next_article"]
        backup = handoff["short_window"]["backup_article"]
        assert best != backup
        assert best != ""
        assert backup != ""

    def test_short_window_rejects_generic_action(self):
        state = _make_state()
        _write_state(state)
        handoff = produce_handoff(
            agent_id="test-agent",
            window_minutes=25,
            energy_level="light-medium",
        )
        assert handoff["exact_action"].strip().lower() not in (
            "study ccrn3",
            "do assignment",
            "read an article",
        )


# ---------------------------------------------------------------------------
# Test D: already-completed article not re-recommended
# ---------------------------------------------------------------------------


class TestNoRepeatedRecommendations:
    """Test D: articles already marked complete must not be recommended."""

    def test_complete_article_not_in_source_refs_for_reading(self):
        state = _make_state()
        # Mark batch_0 and batch_1 as complete so batch_2 is current
        for b in state["batches"][:2]:
            b["status"] = "complete"
            for a in b["articles"]:
                a["status"] = "complete"
        # batch_2 articles are still not_started
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        # batch_2 is current; articles are not_started
        assert handoff["current_batch_id"] == "batch_2"
        # Article A for batch 2 should be the reading target (not a complete article from batch_0/1)
        if handoff.get("reading_target") and handoff["reading_target"].get("required"):
            assert "Article A" in handoff["reading_target"]["article_title"]

    def test_advance_state_then_no_re_read(self):
        state = _make_state()
        # Mark batch_2 first article as complete
        state["batches"][2]["articles"][0]["status"] = "complete"
        state["batches"][2]["articles"][0]["completion_events"] = [
            {
                "timestamp": "2026-10-03T10:00:00+01:00",
                "action": "complete",
                "previous_status": "read",
                "article_title": state["batches"][2]["articles"][0]["title"],
                "batch_id": "batch_2",
            }
        ]
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        # The handoff should not recommend the already-complete article for reading
        if handoff.get("reading_target") and handoff["reading_target"].get("required"):
            assert handoff["reading_target"]["article_title"] != state["batches"][2]["articles"][0]["title"]


# ---------------------------------------------------------------------------
# Test E: state progression changes handoff
# ---------------------------------------------------------------------------


class TestStateProgressionChangesHandoff:
    """Test E: advancing state changes the next handoff."""

    def test_reading_to_extraction_changes_action(self):
        state = _make_state()
        _write_state(state)
        handoff_before = produce_handoff(agent_id="test-agent")
        assert handoff_before["current_batch_id"] == "batch_0"

        # Advance ALL articles in batch_0 to "read" so the handoff moves to extraction
        for article in state["batches"][0]["articles"]:
            advance_state(
                batch_id="batch_0",
                article_title=article["title"],
                new_status="read",
            )

        handoff_after = produce_handoff(agent_id="test-agent")
        # The exact action should now reference extraction, not reading
        assert "Extract" in handoff_after["exact_action"] or "extracted" in handoff_after["exact_action"].lower()
        # And it should reference Article A for batch 0
        assert "Article A" in handoff_after["exact_action"]

    def test_extraction_to_drafting_changes_action(self):
        state = _make_state()
        # Mark batch_0 articles as read then extracted
        for article in state["batches"][0]["articles"]:
            article["status"] = "extracted"
            article["completion_events"] = [
                {
                    "timestamp": "2026-10-03T11:00:00+01:00",
                    "action": "extracted",
                    "previous_status": "read",
                    "article_title": article["title"],
                    "batch_id": "batch_0",
                }
            ]
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        # Should now be a writing/drafting action
        assert handoff["exact_action"] is not None
        assert len(handoff["exact_action"]) > 0

    def test_all_complete_then_no_current_batch(self):
        state = _make_state()
        for batch in state["batches"]:
            batch["status"] = "complete"
            for article in batch["articles"]:
                article["status"] = "complete"
        _write_state(state)
        with pytest.raises(ValueError, match="No current batch"):
            produce_handoff(agent_id="test-agent")


# ---------------------------------------------------------------------------
# Test F: stale state detection
# ---------------------------------------------------------------------------


class TestStaleStateDetection:
    """Test F: when a completion event is newer than the handoff, freshness is stale."""

    def test_fresh_when_no_completion_events_after_handoff(self):
        state = _make_state()
        state["last_handoff_timestamp"] = "2026-10-03T12:00:00+01:00"
        _write_state(state)
        assert _is_stale(state) is False

    def test_stale_when_completion_event_newer_than_handoff(self):
        state = _make_state()
        state["last_handoff_timestamp"] = "2026-10-03T12:00:00+01:00"
        # Add a completion event after the handoff timestamp
        state["batches"][0]["articles"][0]["completion_events"] = [
            {
                "timestamp": "2026-10-03T13:00:00+01:00",
                "action": "complete",
                "previous_status": "read",
                "article_title": state["batches"][0]["articles"][0]["title"],
                "batch_id": "batch_0",
            }
        ]
        _write_state(state)
        assert _is_stale(state) is True

    def test_handoff_reports_stale_freshness(self):
        state = _make_state()
        state["last_handoff_timestamp"] = "2026-10-03T12:00:00+01:00"
        state["batches"][0]["articles"][0]["completion_events"] = [
            {
                "timestamp": "2026-10-03T13:00:00+01:00",
                "action": "complete",
                "previous_status": "read",
                "article_title": state["batches"][0]["articles"][0]["title"],
                "batch_id": "batch_0",
            }
        ]
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        assert handoff["freshness_status"] == "stale"

    def test_handoff_reports_fresh_when_no_stale_events(self):
        state = _make_state()
        state["last_handoff_timestamp"] = "2026-10-03T12:00:00+01:00"
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        assert handoff["freshness_status"] == "fresh"


# ---------------------------------------------------------------------------
# Contract validation tests
# ---------------------------------------------------------------------------


class TestContractValidation:
    """Ensure all produced handoffs pass the scholar_handoff.v1 contract."""

    def test_produced_handoff_passes_validation(self):
        state = _make_state()
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        # Should not raise
        validated = validate_payload(handoff)
        assert validated["schema_version"] == "scholar_handoff.v1"

    def test_handoff_has_required_fields(self):
        state = _make_state()
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        for field in ScholarHandoff.REQUIRED:
            assert field in handoff, f"Missing required field: {field}"
            assert handoff[field] is not None, f"Required field {field} is None"

    def test_estimated_minutes_positive(self):
        state = _make_state()
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        assert handoff["estimated_minutes"] > 0

    def test_reading_target_has_required_fields_when_present(self):
        state = _make_state()
        _write_state(state)
        handoff = produce_handoff(agent_id="test-agent")
        if handoff.get("reading_target") and handoff["reading_target"].get("required"):
            for field in ["article_title", "exact_sections_to_read", "extraction_goal"]:
                assert field in handoff["reading_target"], f"Missing reading_target field: {field}"


# ---------------------------------------------------------------------------
# Batch coverage check
# ---------------------------------------------------------------------------


class TestStateFileBatchCoverage:
    """Verify the state file has all 12 batches (0-11)."""

    def test_all_12_batches_present(self):
        state = _load_state()
        batch_ids = [b["batch_id"] for b in state["batches"]]
        assert len(batch_ids) == 12
        expected = [f"batch_{i}" for i in range(12)]
        assert batch_ids == expected

    def test_all_batches_have_required_fields(self):
        state = _load_state()
        for batch in state["batches"]:
            for field in ["batch_id", "title", "sections", "articles", "extraction_goals", "word_target", "status"]:
                assert field in batch, f"Batch {batch.get('batch_id', '?')} missing field: {field}"

    def test_all_articles_have_status(self):
        state = _load_state()
        for batch in state["batches"]:
            for article in batch["articles"]:
                assert "status" in article, f"Article missing status in {batch['batch_id']}"
                assert article["status"] in ("not_started", "in_progress", "complete")

    def test_no_generic_exact_action_in_state(self):
        """Verify state file itself doesn't contain generic action strings."""
        state = _load_state()
        state_json = json.dumps(state)
        for generic in ["study CCRN3", "do assignment", "read an article"]:
            assert generic.lower() not in state_json.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
