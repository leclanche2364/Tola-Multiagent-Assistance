"""QA T17 tests -- Founder Briefing and Attention Filter.

Stdlib only.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

import unittest

from tola.briefing.filter import (
    AttentionDecision,
    AttentionLevel,
    classify_attention,
    collapse_chatter,
)
from tola.briefing.brief import (
    Brief,
    founder_brief,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _routine_ack_event(index: int = 0) -> dict:
    return {
        "kind": "ack",
        "title": f"Routine ack {index}",
        "detail": "Internal heartbeat",
        "timestamp": f"2026-09-29T{10 + index:02d}:00:00Z",
    }


def _non_urgent_change_event() -> dict:
    return {
        "kind": "health_label_change",
        "title": "Health label updated",
        "detail": "Project Alpha label changed to ATTENTION",
        "timestamp": "2026-09-29T11:00:00Z",
    }


def _material_change_event() -> dict:
    return {
        "kind": "project_blocked",
        "title": "Project Alpha BLOCKED",
        "detail": "Blocked by dependency failure; 3 items affected",
        "timestamp": "2026-09-29T12:00:00Z",
    }


def _decision_request_event() -> dict:
    return {
        "kind": "decision_request",
        "title": "Choose release strategy",
        "options": ["ship_now", "delay_one_week", "ship_partial"],
        "timestamp": "2026-09-29T13:00:00Z",
    }


def _urgent_event() -> dict:
    return {
        "kind": "escalate_stop",
        "title": "Stop-rule triggered",
        "detail": "T8 ESCALATE: boundary violation count=2",
        "timestamp": "2026-09-29T14:00:00Z",
    }


def _missed_deadline_event() -> dict:
    return {
        "kind": "missed_hard_deadline",
        "title": "Hard deadline missed",
        "detail": "Milestone M3 was due 2026-09-28; status=OVERDUE",
        "timestamp": "2026-09-29T15:00:00Z",
    }


def _progress_note_event() -> dict:
    return {
        "kind": "progress_note",
        "title": "Progress update",
        "detail": "Sprint 4 completed 7 of 10 stories; status=IN_PROGRESS",
        "timestamp": "2026-09-29T16:00:00Z",
    }


def _ledger_update_event() -> dict:
    return {
        "kind": "ledger_update",
        "title": "Ledger entry",
        "detail": "Budget line B2 updated: allocated=5000, spent=3200",
        "timestamp": "2026-09-29T17:00:00Z",
    }


def _deadline_at_risk_event() -> dict:
    return {
        "kind": "deadline_at_risk",
        "title": "Deadline at risk",
        "detail": "Release R2 due 2026-10-15; 2 of 5 gates not passed",
        "timestamp": "2026-09-29T18:00:00Z",
    }


def _decision_superseded_event() -> dict:
    return {
        "kind": "decision_superseded",
        "title": "Decision superseded",
        "detail": "D-004 replaced by D-005; reason=new evidence",
        "timestamp": "2026-09-29T19:00:00Z",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestT17AttentionFilter(unittest.TestCase):
    """QA T17 -- Founder Briefing and Attention Filter."""

    # T17-01: Routine internal acknowledgement remains SILENT.
    def test_t17_01_routine_ack_silent(self):
        ev = _routine_ack_event()
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.SILENT)
        self.assertIn("Routine acknowledgement", result.reason)

    # T17-02: Non-urgent change appears in DIGEST.
    def test_t17_02_non_urgent_change_digest(self):
        ev = _non_urgent_change_event()
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.DIGEST)

    def test_t17_02_progress_note_digest(self):
        ev = _progress_note_event()
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.DIGEST)

    def test_t17_02_ledger_update_digest(self):
        ev = _ledger_update_event()
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.DIGEST)

    # T17-03: Material change becomes NOTIFY.
    def test_t17_03_project_blocked_notify(self):
        ev = _material_change_event()
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.NOTIFY)

    def test_t17_03_project_dormant_notify(self):
        ev = {
            "kind": "project_dormant",
            "title": "Project Delta DORMANT",
            "detail": "No activity for 30 days",
            "timestamp": "2026-09-29T10:00:00Z",
        }
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.NOTIFY)

    def test_t17_03_escalation_raised_notify(self):
        ev = {
            "kind": "escalation_raised",
            "title": "Escalation raised",
            "detail": "E-001: dependency chain blocked",
            "timestamp": "2026-09-29T10:00:00Z",
        }
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.NOTIFY)

    def test_t17_03_deadline_at_risk_notify(self):
        ev = _deadline_at_risk_event()
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.NOTIFY)

    def test_t17_03_decision_superseded_notify(self):
        ev = _decision_superseded_event()
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.NOTIFY)

    # T17-04: True decision request becomes DECISION_REQUIRED.
    def test_t17_04_decision_request(self):
        ev = _decision_request_event()
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.DECISION_REQUIRED)

    # T17-05: True urgent condition becomes URGENT.
    def test_t17_05_escalate_stop_urgent(self):
        ev = _urgent_event()
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.URGENT)

    def test_t17_05_missed_hard_deadline_urgent(self):
        ev = _missed_deadline_event()
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.URGENT)

    def test_t17_05_stop_rule_trigger_urgent(self):
        ev = {
            "kind": "stop_rule_trigger",
            "title": "Stop rule fired",
            "detail": "T8 stop-rule: boundary_violations>=2",
            "timestamp": "2026-09-29T10:00:00Z",
        }
        result = classify_attention(ev)
        self.assertEqual(result.level, AttentionLevel.URGENT)

    # T17-06: Brief leads with implication before details.
    def test_t17_06_implication_first_urgent(self):
        ev = _urgent_event()
        brief = founder_brief([ev], {})
        self.assertTrue(len(brief.urgent) > 0)
        first_line = brief.urgent[0]
        # First line must contain the implication keyword/action.
        self.assertIn("URGENT", first_line)
        # Detail comes after the separator.
        self.assertIn("|", first_line)

    def test_t17_06_implication_first_decision(self):
        ev = _decision_request_event()
        brief = founder_brief([ev], {})
        self.assertTrue(len(brief.decisions) > 0)
        first_line = brief.decisions[0]
        self.assertIn("DECISION REQUIRED", first_line)
        self.assertIn("|", first_line)

    def test_t17_06_implication_first_notify(self):
        ev = _material_change_event()
        brief = founder_brief([ev], {})
        self.assertTrue(len(brief.notifications) > 0)
        first_line = brief.notifications[0]
        self.assertIn("NOTIFY", first_line)
        self.assertIn("|", first_line)

    def test_t17_06_implication_first_digest(self):
        ev = _non_urgent_change_event()
        brief = founder_brief([ev], {})
        self.assertTrue(len(brief.digest) > 0)
        first_line = brief.digest[0]
        self.assertIn("UPDATE", first_line)
        self.assertIn("|", first_line)

    # T17-07: Numbers/status match sources exactly.
    def test_t17_07_exact_number_passthrough(self):
        ev = {
            "kind": "project_blocked",
            "title": "Project Alpha BLOCKED",
            "detail": "3 items affected",
            "timestamp": "2026-09-29T12:00:00Z",
        }
        brief = founder_brief([ev], {})
        self.assertTrue(len(brief.notifications) > 0)
        line = brief.notifications[0]
        # Exact string "3 items affected" must appear.
        self.assertIn("3 items affected", line)

    def test_t17_07_exact_status_passthrough(self):
        ev = {
            "kind": "progress_note",
            "title": "Progress update",
            "detail": "Sprint 4 completed 7 of 10 stories; status=IN_PROGRESS",
            "timestamp": "2026-09-29T16:00:00Z",
        }
        brief = founder_brief([ev], {})
        self.assertTrue(len(brief.digest) > 0)
        line = brief.digest[0]
        # Exact status string must appear.
        self.assertIn("status=IN_PROGRESS", line)
        # Exact count string must appear.
        self.assertIn("7 of 10", line)

    def test_t17_07_exact_budget_numbers(self):
        ev = _ledger_update_event()
        brief = founder_brief([ev], {})
        self.assertTrue(len(brief.digest) > 0)
        line = brief.digest[0]
        self.assertIn("allocated=5000", line)
        self.assertIn("spent=3200", line)

    # T17-08: Internal agent chatter does not flood user.
    def test_t17_08_chatter_collapsing(self):
        events = [_routine_ack_event(i) for i in range(10)]
        brief = founder_brief(events, {})
        # 10 routine acks -> silence_count=9, one digest line.
        self.assertEqual(brief.silence_count, 9)
        self.assertEqual(len(brief.digest), 1)
        # No urgent/decisions/notifications from chatter.
        self.assertEqual(len(brief.urgent), 0)
        self.assertEqual(len(brief.decisions), 0)
        self.assertEqual(len(brief.notifications), 0)

    def test_t17_08_chatter_collapsing_count(self):
        """10 routine acks: first becomes digest, rest collapse."""
        events = [_routine_ack_event(i) for i in range(10)]
        collapsed, silence_count = collapse_chatter(events, {})
        self.assertEqual(silence_count, 9)
        self.assertEqual(len(collapsed), 1)

    # T17-09: User can understand action/inaction required from first layer.
    def test_t17_09_action_clear_from_first_layer_urgent(self):
        ev = _urgent_event()
        brief = founder_brief([ev], {})
        self.assertTrue(len(brief.urgent) > 0)
        first_line = brief.urgent[0]
        # First layer must state what action is needed.
        self.assertIn("URGENT", first_line)
        self.assertIn("Stop-rule triggered", first_line)

    def test_t17_09_action_clear_from_first_layer_decision(self):
        ev = _decision_request_event()
        brief = founder_brief([ev], {})
        self.assertTrue(len(brief.decisions) > 0)
        first_line = brief.decisions[0]
        # First layer must state what decision is needed.
        self.assertIn("DECISION REQUIRED", first_line)
        self.assertIn("Choose release strategy", first_line)

    def test_t17_09_action_clear_from_first_layer_notify(self):
        ev = _material_change_event()
        brief = founder_brief([ev], {})
        self.assertTrue(len(brief.notifications) > 0)
        first_line = brief.notifications[0]
        self.assertIn("NOTIFY", first_line)
        self.assertIn("Project Alpha BLOCKED", first_line)

    def test_t17_09_action_clear_from_first_layer_digest(self):
        ev = _non_urgent_change_event()
        brief = founder_brief([ev], {})
        self.assertTrue(len(brief.digest) > 0)
        first_line = brief.digest[0]
        self.assertIn("UPDATE", first_line)
        self.assertIn("Health label updated", first_line)

    # Determinism: same inputs produce identical output.
    def test_t17_09_determinism_classify(self):
        ev = _material_change_event()
        d1 = classify_attention(ev)
        d2 = classify_attention(ev)
        self.assertEqual(d1.level, d2.level)
        self.assertEqual(d1.reason, d2.reason)

    def test_t17_09_determinism_brief(self):
        events = [_urgent_event(), _decision_request_event(), _non_urgent_change_event()]
        b1 = founder_brief(events, {})
        b2 = founder_brief(events, {})
        self.assertEqual(b1.urgent, b2.urgent)
        self.assertEqual(b1.decisions, b2.decisions)
        self.assertEqual(b1.notifications, b2.notifications)
        self.assertEqual(b1.digest, b2.digest)
        self.assertEqual(b1.silence_count, b2.silence_count)

    # Determinism with chatter collapsing.
    def test_t17_09_determinism_collapse(self):
        events = [_routine_ack_event(i) for i in range(5)]
        b1 = founder_brief(events, {})
        b2 = founder_brief(events, {})
        self.assertEqual(b1.silence_count, b2.silence_count)
        self.assertEqual(b1.digest, b2.digest)

    # Level -> condition mapping completeness.
    def test_t17_01_02_03_04_05_all_levels_covered(self):
        """Verify all five levels are reachable."""
        levels_found = set()
        ev_by_kind = {
            "ack": _routine_ack_event(),
            "health_label_change": _non_urgent_change_event(),
            "project_blocked": _material_change_event(),
            "decision_request": _decision_request_event(),
            "escalate_stop": _urgent_event(),
        }
        for kind, ev in ev_by_kind.items():
            result = classify_attention(ev)
            levels_found.add(result.level.value)

        expected = {"SILENT", "DIGEST", "NOTIFY", "DECISION_REQUIRED", "URGENT"}
        self.assertEqual(levels_found, expected)

    # Plain ASCII check: no non-ASCII characters in output lines.
    def test_t17_09_output_plain_ascii(self):
        events = [
            _urgent_event(),
            _decision_request_event(),
            _material_change_event(),
            _non_urgent_change_event(),
            _routine_ack_event(),
        ]
        brief = founder_brief(events, {})
        for line in brief.urgent + brief.decisions + brief.notifications + brief.digest:
            for ch in line:
                self.assertTrue(
                    ord(ch) < 128,
                    f"Non-ASCII character {ch!r} found in line: {line!r}",
                )

    # First layer of every line contains implication keyword.
    def test_t17_06_first_layer_contains_implication(self):
        """Every output line's first segment (before |) contains the action keyword."""
        events = [
            _urgent_event(),
            _decision_request_event(),
            _material_change_event(),
            _non_urgent_change_event(),
        ]
        brief = founder_brief(events, {})
        for line in brief.urgent:
            prefix = line.split(" | ")[0]
            self.assertIn("URGENT", prefix)
        for line in brief.decisions:
            prefix = line.split(" | ")[0]
            self.assertIn("DECISION REQUIRED", prefix)
        for line in brief.notifications:
            prefix = line.split(" | ")[0]
            self.assertIn("NOTIFY", prefix)
        for line in brief.digest:
            prefix = line.split(" | ")[0]
            self.assertIn("UPDATE", prefix)


if __name__ == "__main__":
    unittest.main()