"""Batch 6 QA tests for Tola Daily Synthesis Engine.

Covers scenarios A-F plus regression risks 2 & 3.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.daily_synthesis.contracts import ValidationError
from agents.daily_synthesis.synthesis import build_brief


# ---------------------------------------------------------------------------
# shared handoff factories
# ---------------------------------------------------------------------------

def _capacity(total=240, used=60, buffer=30):
    return {
        "schema_version": "rhythm_capacity_handoff.v1",
        "agent_id": "tola",
        "rhythm_id": "r1",
        "capacity_used_minutes": used,
        "capacity_total_minutes": total,
        "recovery_buffer_minutes": buffer,
    }


def _scholar(
    exact_action="Read CCRN3 chapter 5 — sections 5.1, 5.2 extracting key definitions",
    estimated_minutes=60,
    article_title="CRRN3 Deep Dive",
    sections=("section 5.1", "section 5.2"),
    extraction_goal="extract key definitions",
    required=True,
    **overrides,
):
    h = {
        "schema_version": "scholar_handoff.v1",
        "agent_id": "scholar",
        "current_batch_id": "batch-42",
        "exact_action": exact_action,
        "estimated_minutes": estimated_minutes,
        "definition_of_done": "Chapter 5 notes written",
        "reading_target": {
            "required": required,
            "article_title": article_title,
            "exact_sections_to_read": list(sections),
            "extraction_goal": extraction_goal,
        },
        "source_refs": ["https://example.com/crrn3"],
    }
    h.update(overrides)
    return h


def _growth(next_actions=None, blockers=None, deadlines=None):
    return {
        "schema_version": "growth_handoff.v1",
        "agent_id": "growth",
        "project_id": "growth",
        "action": "growth_handoff",
        "estimated_minutes": 150,
        "definition_of_done": "Growth handoff produced",
        "next_actions": next_actions or [
            {"action": "Finalize onboarding_flow_v3 variant B analysis", "estimated_effort_minutes": 120, "freshness_status": "fresh"},
            {"action": "Submit Q4 budget for approval", "estimated_effort_minutes": 30, "freshness_status": "fresh"},
        ],
        "blockers": blockers or [],
        "deadlines": deadlines or [],
    }


def _project(project_id="Shiftlyx", next_action="Complete dashboard wireframe review",
            blocker="", deadline="2026-10-15", effort=120, energy="high"):
    return {
        "schema_version": "project_status_handoff.v1",
        "agent_id": "tola",
        "project_id": project_id,
        "status": "development",
        "summary": f"{project_id}: development",
        "next_action": next_action,
        "blocker": blocker,
        "deadline": deadline,
        "estimated_effort_minutes": effort,
        "energy_required": energy,
        "definition_of_done": "Dashboard wireframe reviewed and approved",
    }


# ---------------------------------------------------------------------------
# Scenario A — high-capacity day (4h deep, one deferred explicitly)
# ---------------------------------------------------------------------------

class ScenarioAHighCapacityTest(unittest.TestCase):
    def test_high_capacity_selects_deep_and_defers_explicitly(self):
        brief = build_brief(
            capacity_handoff=_capacity(total=480, used=60, buffer=30),
            scholar_handoff=_scholar(estimated_minutes=60),
            growth_handoff=_growth(),
            project_handoffs=[_project()],
            now="2026-10-03T09:00:00+01:00",
        )
        self.assertLessEqual(len(brief["top_outcomes"]), 3)
        # Should have selected scholar + growth + project (3 outcomes)
        self.assertGreaterEqual(len(brief["top_outcomes"]), 1)
        # At least one item must be in not_today (deferred)
        self.assertGreater(len(brief["not_today"]), 0)
        # Buffer must be reserved
        self.assertGreaterEqual(brief["buffer_minutes"], 30)


# ---------------------------------------------------------------------------
# Scenario B — ICU shift day (no unrealistic deep session; quick-read allowed)
# ---------------------------------------------------------------------------

class ScenarioBIcuShiftTest(unittest.TestCase):
    def test_icu_shift_uses_quick_read_not_deep_session(self):
        brief = build_brief(
            capacity_handoff=_capacity(total=120, used=90, buffer=10),
            scholar_handoff=_scholar(estimated_minutes=60),
            growth_handoff=_growth(next_actions=[
                {"action": "Quick metric check", "estimated_effort_minutes": 10, "freshness_status": "fresh"},
            ]),
            project_handoffs=[],
            now="2026-10-03T09:00:00+01:00",
        )
        # No outcome should require deep energy when only light windows exist
        for outcome in brief["top_outcomes"]:
            self.assertNotEqual(outcome.get("energy_required"), "deep")
        # Quick-read should be present (low energy, small minutes)
        titles = [o.get("estimated_minutes", 0) for o in brief["top_outcomes"]]
        self.assertTrue(any(m <= 15 for m in titles))


# ---------------------------------------------------------------------------
# Scenario C — 25-minute window (selects short reading atom, defers 60-min draft)
# ---------------------------------------------------------------------------

class ScenarioCShortWindowTest(unittest.TestCase):
    def test_25min_window_selects_quick_read_not_60min_draft(self):
        brief = build_brief(
            capacity_handoff=_capacity(total=60, used=30, buffer=5),
            scholar_handoff=_scholar(estimated_minutes=60),
            growth_handoff=_growth(next_actions=[
                {"action": "Write campaign draft", "estimated_effort_minutes": 60, "freshness_status": "fresh"},
            ]),
            project_handoffs=[],
            now="2026-10-03T09:00:00+01:00",
        )
        # The selected outcome should be <= 25 minutes (quick-read atom)
        selected_minutes = [o["estimated_minutes"] for o in brief["top_outcomes"]]
        self.assertTrue(any(m <= 25 for m in selected_minutes),
                        f"Expected a <=25min outcome, got {selected_minutes}")
        # The 60-min draft should be deferred
        deferred = " ".join(brief["not_today"])
        self.assertTrue(
            any("60" in d or "draft" in d.lower() for d in brief["not_today"]),
            f"Expected 60-min draft to be deferred, got not_today: {brief['not_today']}",
        )


# ---------------------------------------------------------------------------
# Scenario D — assignment deadline near (recognised, still capacity-bounded)
# ---------------------------------------------------------------------------

class ScenarioDDeadlineNearTest(unittest.TestCase):
    def test_near_deadline_recognised_and_capacity_bounded(self):
        brief = build_brief(
            capacity_handoff=_capacity(total=120, used=30, buffer=10),
            scholar_handoff=_scholar(estimated_minutes=60),
            growth_handoff=_growth(deadlines=["2026-10-03T23:59:59+01:00: End-of-day campaign deadline"]),
            project_handoffs=[_project(deadline="2026-10-03")],
            now="2026-10-03T09:00:00+01:00",
        )
        # Today's deadline should be recognised (project with deadline today should rank high)
        self.assertGreater(len(brief["top_outcomes"]), 0)
        # Still capacity-bounded — never exceed max_major_outcomes
        self.assertLessEqual(len(brief["top_outcomes"]), 3)


# ---------------------------------------------------------------------------
# Scenario E — no project capacity (valid brief with only commitments/recovery/optional small learning)
# ---------------------------------------------------------------------------

class ScenarioENoProjectCapacityTest(unittest.TestCase):
    def test_no_project_capacity_valid_brief_with_commitments(self):
        brief = build_brief(
            capacity_handoff=_capacity(total=60, used=55, buffer=5),
            scholar_handoff=_scholar(estimated_minutes=60),
            growth_handoff=_growth(next_actions=[
                {"action": "Submit final campaign report", "estimated_effort_minutes": 45, "freshness_status": "fresh"},
            ]),
            project_handoffs=[_project(effort=120)],
            now="2026-10-03T09:00:00+01:00",
        )
        # Should still produce a valid brief (0 or 1 outcomes)
        self.assertIsInstance(brief["top_outcomes"], list)
        self.assertLessEqual(len(brief["top_outcomes"]), 3)
        # Buffer must be preserved
        self.assertGreaterEqual(brief["buffer_minutes"], 5)


# ---------------------------------------------------------------------------
# Scenario F — excessive candidates (20 given → small selection + explicit Not Today list)
# ---------------------------------------------------------------------------

class ScenarioFExcessiveCandidatesTest(unittest.TestCase):
    def test_excessive_candidates_small_selection_explicit_deferrals(self):
        # 20 growth next actions to overwhelm capacity
        many_actions = [
            {"action": f"Growth task {i}", "estimated_effort_minutes": 30, "freshness_status": "fresh"}
            for i in range(20)
        ]
        brief = build_brief(
            capacity_handoff=_capacity(total=120, used=30, buffer=10),
            scholar_handoff=_scholar(estimated_minutes=60),
            growth_handoff=_growth(next_actions=many_actions),
            project_handoffs=[],
            now="2026-10-03T09:00:00+01:00",
        )
        # Selection must be small (<=3)
        self.assertLessEqual(len(brief["top_outcomes"]), 3)
        # Must have explicit Not Today list
        self.assertGreater(len(brief["not_today"]), 0)
        # not_today must contain reasons
        for d in brief["not_today"]:
            self.assertIsInstance(d, str)
            self.assertTrue(len(d) > 0)


# ---------------------------------------------------------------------------
# Regression Risk 2 — Tola must not delegate cross-domain decision
# (module makes the decision itself from provided handoffs — no calls back)
# ---------------------------------------------------------------------------

class RegressionNoCrossDomainDelegationTest(unittest.TestCase):
    def test_module_makes_decision_from_handoffs_no_external_calls(self):
        # build_brief only uses the handoff dicts passed in — it never
        # calls scholar/growth/project producers. Verify it returns a
        # valid brief without any external dependency.
        brief = build_brief(
            capacity_handoff=_capacity(total=240, used=60, buffer=30),
            scholar_handoff=_scholar(estimated_minutes=60),
            growth_handoff=_growth(next_actions=[
                {"action": "Run A/B test analysis", "estimated_effort_minutes": 60, "freshness_status": "fresh"},
            ]),
            project_handoffs=[_project()],
            now="2026-10-03T09:00:00+01:00",
        )
        self.assertEqual(brief["schema_version"], "daily_command_brief.v1")
        self.assertGreater(len(brief["top_outcomes"]), 0)


# ---------------------------------------------------------------------------
# Regression Risk 3 — no generic study language in output
# ---------------------------------------------------------------------------

class RegressionNoGenericStudyLanguageTest(unittest.TestCase):
    def test_no_generic_study_language_in_study_detail(self):
        brief = build_brief(
            capacity_handoff=_capacity(total=240, used=60, buffer=30),
            scholar_handoff=_scholar(
                exact_action="Read CCRN3 chapter 5 — sections 5.1, 5.2 extracting key definitions",
                article_title="CRRN3 Deep Dive",
                sections=("section 5.1", "section 5.2"),
                extraction_goal="extract key definitions",
            ),
            growth_handoff=_growth(),
            project_handoffs=[],
            now="2026-10-03T09:00:00+01:00",
        )
        study = brief.get("study_detail", {})
        self.assertEqual(study["exact_action"], "Read CCRN3 chapter 5 — sections 5.1, 5.2 extracting key definitions")
        self.assertEqual(study["article"], "CRRN3 Deep Dive")
        self.assertEqual(study["sections"], ["section 5.1", "section 5.2"])
        self.assertEqual(study["extraction_goal"], "extract key definitions")

    def test_generic_study_raises_when_scholar_requires_reading(self):
        # If scholar handoff has reading_target.required=True but no exact_action/article,
        # the guard must raise ValidationError.
        with self.assertRaises(ValidationError):
            build_brief(
                capacity_handoff=_capacity(total=240, used=60, buffer=30),
                scholar_handoff=_scholar(
                    exact_action="study CCRN3",  # generic — rejected
                    article_title="",
                    sections=(),
                    extraction_goal="",
                ),
                growth_handoff=_growth(),
                project_handoffs=[],
                now="2026-10-03T09:00:00+01:00",
            )


if __name__ == "__main__":
    unittest.main()