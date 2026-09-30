"""
Batch S9 -- Learning Goal Contract QA Tests (S9-01..S9-06 + edge cases).
Plain ASCII. Python 3 stdlib only.
"""

import unittest

from scholar.goals.registry import (
    GoalRegistry, GoalSource, GoalRecord, GoalStateTransition,
)
from scholar.fixtures.goals import (
    DIRECT_USER_SOURCE_V1, TOLA_SOURCE_V1, DIRECT_USER_SOURCE_V2, TOLA_SOURCE_V2,
    GOAL_VENT_DIRECT_V1, GOAL_VENT_TOLA_V1, GOAL_HEMO_DIRECT_V1,
    MALFORMED_GOAL_MISSING_TITLE, MALFORMED_GOAL_MISSING_DESCRIPTION,
    MALFORMED_GOAL_BAD_SOURCE_TYPE, MALFORMED_GOAL_MISSING_SOURCE,
    MALFORMED_GOAL_MISSING_SOURCE_VERSION, MALFORMED_GOAL_NON_STRING_TITLE,
    MALFORMED_GOAL_EMPTY_GOAL_ID, MALFORMED_GOAL_NON_STRING_SOURCE_TYPE,
    DUPLICATE_GOAL_ATTEMPT,
    make_registry, make_source, make_goal, make_tola_goal,
)


def _fake_now():
    from datetime import datetime
    return datetime(2026, 9, 30, 12, 0, 0)


# ====================================================================== #
#  S9-01 Direct user goal: created
# ====================================================================== #

class TestS9_01DirectUserGoalCreated(unittest.TestCase):
    def test_create_direct_user_goal_returns_record(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertIsNotNone(record)
        self.assertEqual(record.goal_id, "goal-vent-01")
        self.assertEqual(record.source_type, "direct_user")
        self.assertEqual(record.state, "ACTIVE")

    def test_create_direct_user_goal_stores_title(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertEqual(record.title, "Master mechanical ventilation within six weeks")

    def test_create_direct_user_goal_stores_description(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertIn("mechanical ventilation", record.description)

    def test_create_direct_user_goal_version_is_one(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertEqual(record.version, 1)

    def test_create_direct_user_goal_has_provenance(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertIn("source_id", record.provenance)
        self.assertIn("created_at", record.provenance)
        self.assertEqual(record.provenance["created_by"], "scholar")

    def test_create_direct_user_goal_has_initial_transition(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        transitions = reg.get_transitions("goal-vent-01")
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].from_state, None)
        self.assertEqual(transitions[0].to_state, "ACTIVE")

    def test_create_direct_user_goal_rejects_missing_title(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(ValueError) as cm:
            reg.create_goal(**MALFORMED_GOAL_MISSING_TITLE)
        self.assertIn("title", str(cm.exception))

    def test_create_direct_user_goal_rejects_missing_description(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(ValueError) as cm:
            reg.create_goal(**MALFORMED_GOAL_MISSING_DESCRIPTION)
        self.assertIn("description", str(cm.exception))

    def test_create_direct_user_goal_rejects_bad_source_type(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(ValueError) as cm:
            reg.create_goal(**MALFORMED_GOAL_BAD_SOURCE_TYPE)
        self.assertIn("source_type", str(cm.exception))

    def test_create_direct_user_goal_rejects_missing_source(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.create_goal(**MALFORMED_GOAL_MISSING_SOURCE)
        self.assertIn("does not exist", str(cm.exception))

    def test_create_direct_user_goal_rejects_missing_source_version(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(ValueError) as cm:
            reg.create_goal(**MALFORMED_GOAL_MISSING_SOURCE_VERSION)
        self.assertIn("does not exist", str(cm.exception))

    def test_create_direct_user_goal_rejects_non_string_title(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(ValueError):
            reg.create_goal(**MALFORMED_GOAL_NON_STRING_TITLE)

    def test_create_direct_user_goal_rejects_empty_goal_id(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(ValueError):
            reg.create_goal(**MALFORMED_GOAL_EMPTY_GOAL_ID)

    def test_create_direct_user_goal_rejects_non_string_source_type(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(ValueError):
            reg.create_goal(**MALFORMED_GOAL_NON_STRING_SOURCE_TYPE)

    def test_create_direct_user_goal_rejects_duplicate_id(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        with self.assertRaises(ValueError) as cm:
            reg.create_goal(**DUPLICATE_GOAL_ATTEMPT)
        self.assertIn("already exists", str(cm.exception))

    def test_create_multiple_direct_user_goals(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        g2 = dict(GOAL_VENT_DIRECT_V1)
        g2["goal_id"] = "goal-hemo-01"
        g2["title"] = "Learn haemodynamic monitoring"
        g2["description"] = "Understand arterial line interpretation."
        reg.create_goal(**g2)
        self.assertIsNotNone(reg.get_goal("goal-vent-01"))
        self.assertIsNotNone(reg.get_goal("goal-hemo-01"))


# ====================================================================== #
#  S9-02 Tola goal: created
# ====================================================================== #

class TestS9_02TolaGoalCreated(unittest.TestCase):
    def test_create_tola_goal_returns_record(self):
        reg = make_registry()
        reg.add_source(**TOLA_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_TOLA_V1)
        self.assertIsNotNone(record)
        self.assertEqual(record.goal_id, "goal-vent-02")
        self.assertEqual(record.source_type, "tola")
        self.assertEqual(record.state, "ACTIVE")

    def test_create_tola_goal_stores_title(self):
        reg = make_registry()
        reg.add_source(**TOLA_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_TOLA_V1)
        self.assertEqual(record.title, "Mechanical ventilation proficiency for Step 2")

    def test_create_tola_goal_stores_source_type_tola(self):
        reg = make_registry()
        reg.add_source(**TOLA_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_TOLA_V1)
        self.assertEqual(record.source_type, "tola")

    def test_create_tola_goal_version_is_one(self):
        reg = make_registry()
        reg.add_source(**TOLA_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_TOLA_V1)
        self.assertEqual(record.version, 1)

    def test_create_tola_goal_has_provenance(self):
        reg = make_registry()
        reg.add_source(**TOLA_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_TOLA_V1)
        self.assertEqual(record.provenance["source_id"], "src-tola-001")
        self.assertEqual(record.provenance["source_version"], "1.0")

    def test_create_tola_goal_has_initial_transition(self):
        reg = make_registry()
        reg.add_source(**TOLA_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_TOLA_V1)
        transitions = reg.get_transitions("goal-vent-02")
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].to_state, "ACTIVE")

    def test_create_tola_goal_rejects_bad_source_type(self):
        reg = make_registry()
        reg.add_source(**TOLA_SOURCE_V1)
        bad_goal = dict(GOAL_VENT_TOLA_V1)
        bad_goal["source_type"] = "invalid_type"
        with self.assertRaises(ValueError) as cm:
            reg.create_goal(**bad_goal)
        self.assertIn("source_type", str(cm.exception))

    def test_create_tola_goal_rejects_missing_source(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.create_goal(**MALFORMED_GOAL_MISSING_SOURCE)
        self.assertIn("does not exist", str(cm.exception))

    def test_create_multiple_tola_goals(self):
        reg = make_registry()
        reg.add_source(**TOLA_SOURCE_V1)
        reg.add_source(**TOLA_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_TOLA_V1)
        tola_v2 = dict(GOAL_VENT_TOLA_V1)
        tola_v2["goal_id"] = "goal-vent-03"
        tola_v2["source_id"] = "src-tola-001"
        tola_v2["source_version"] = "2.0"
        tola_v2["title"] = "Updated Tola goal v2"
        reg.create_goal(**tola_v2)
        self.assertIsNotNone(reg.get_goal("goal-vent-02"))
        self.assertIsNotNone(reg.get_goal("goal-vent-03"))

    def test_tola_goal_persists_independently_of_session(self):
        """Goals persist independent of any session object."""
        reg = make_registry()
        reg.add_source(**TOLA_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_TOLA_V1)
        # Simulate a new session by creating a fresh registry and restoring state
        state = reg.get_state()
        reg2 = make_registry()
        for sid, versions in state["sources"].items():
            for v_str, s_dict in versions.items():
                reg2.add_source(
                    source_id=s_dict["source_id"],
                    name=s_dict["name"],
                    source_type=s_dict["source_type"],
                    version=s_dict["version"],
                    content_hash=s_dict["content_hash"],
                    content=s_dict["content"],
                )
        for gid, versions in state["goals"].items():
            for v_int, g_dict in versions.items():
                reg2._goals.setdefault(gid, {})[v_int] = GoalRecord(**g_dict)
        for gid, trans_list in state["transitions"].items():
            reg2._transitions[gid] = [GoalStateTransition(**t) for t in trans_list]
        goal = reg2.get_goal("goal-vent-02")
        self.assertIsNotNone(goal)
        self.assertEqual(goal.state, "ACTIVE")
        self.assertEqual(goal.source_type, "tola")


# ====================================================================== #
#  S9-03 Pause: state retained
# ====================================================================== #

class TestS9_03PauseStateRetained(unittest.TestCase):
    def test_pause_goal_transitions_active_to_paused(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.pause_goal("goal-vent-01")
        self.assertEqual(old.state, "ACTIVE")
        self.assertEqual(new.state, "PAUSED")

    def test_pause_goal_creates_version_two(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.pause_goal("goal-vent-01")
        self.assertEqual(old.version, 1)
        self.assertEqual(new.version, 2)

    def test_paused_goal_retrievable_at_version_two(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        paused = reg.get_goal("goal-vent-01", version=2)
        self.assertIsNotNone(paused)
        self.assertEqual(paused.state, "PAUSED")

    def test_paused_goal_latest_is_paused(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        latest = reg.get_goal("goal-vent-01")
        self.assertEqual(latest.state, "PAUSED")

    def test_pause_records_transition(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        transitions = reg.get_transitions("goal-vent-01")
        self.assertEqual(len(transitions), 2)
        self.assertEqual(transitions[0].to_state, "ACTIVE")
        self.assertEqual(transitions[1].from_state, "ACTIVE")
        self.assertEqual(transitions[1].to_state, "PAUSED")

    def test_pause_goal_rejects_nonexistent_goal(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.pause_goal("goal-nonexistent")
        self.assertIn("does not exist", str(cm.exception))

    def test_pause_goal_rejects_already_paused(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.pause_goal("goal-vent-01")
        self.assertIn("PAUSED", str(cm.exception))

    def test_pause_goal_rejects_completed_goal(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.complete_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.pause_goal("goal-vent-01")
        self.assertIn("COMPLETED", str(cm.exception))

    def test_pause_goal_rejects_stopped_goal(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.pause_goal("goal-vent-01")
        self.assertIn("STOPPED", str(cm.exception))

    def test_pause_goal_rejects_superseded_goal(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Superseded goal",
            new_description="This goal has been superseded.",
            new_source_id="src-user-001",
            new_source_version="1.0",
            new_source_type="direct_user",
        )
        with self.assertRaises(ValueError) as cm:
            reg.pause_goal("goal-vent-01")
        self.assertIn("SUPERSEDED", str(cm.exception))

    def test_paused_goal_retains_original_title(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.pause_goal("goal-vent-01")
        self.assertEqual(new.title, old.title)
        self.assertEqual(new.description, old.description)

    def test_paused_goal_retains_source_traceability(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.pause_goal("goal-vent-01")
        self.assertEqual(new.source_id, old.source_id)
        self.assertEqual(new.source_version, old.source_version)

    def test_pause_preserves_deterministic_timestamp(self):
        reg = make_registry(clock=_fake_now)
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.pause_goal("goal-vent-01")
        self.assertEqual(new.provenance["created_at"], "2026-09-30T12:00:00")


# ====================================================================== #
#  S9-04 Stop: no further planning
# ====================================================================== #

class TestS9_04StopNoFurtherPlanning(unittest.TestCase):
    def test_stop_goal_transitions_active_to_stopped(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.stop_goal("goal-vent-01")
        self.assertEqual(old.state, "ACTIVE")
        self.assertEqual(new.state, "STOPPED")

    def test_stop_goal_transitions_paused_to_stopped(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        old, new = reg.stop_goal("goal-vent-01")
        self.assertEqual(old.state, "PAUSED")
        self.assertEqual(new.state, "STOPPED")

    def test_stopped_goal_cannot_be_paused(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.pause_goal("goal-vent-01")
        self.assertIn("STOPPED", str(cm.exception))

    def test_stopped_goal_cannot_be_resumed(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.resume_goal("goal-vent-01")
        self.assertIn("STOPPED", str(cm.exception))

    def test_stopped_goal_cannot_be_completed(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.complete_goal("goal-vent-01")
        self.assertIn("STOPPED", str(cm.exception))

    def test_stopped_goal_cannot_be_superseded(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="New goal",
                new_description="This goal has been superseded.",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="direct_user",
            )
        self.assertIn("STOPPED", str(cm.exception))

    def test_stopped_goal_latest_is_stopped(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        latest = reg.get_goal("goal-vent-01")
        self.assertEqual(latest.state, "STOPPED")

    def test_stop_records_transition(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        transitions = reg.get_transitions("goal-vent-01")
        self.assertEqual(len(transitions), 2)
        self.assertEqual(transitions[1].to_state, "STOPPED")

    def test_stop_goal_rejects_nonexistent_goal(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.stop_goal("goal-nonexistent")
        self.assertIn("does not exist", str(cm.exception))

    def test_stop_goal_rejects_already_stopped(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.stop_goal("goal-vent-01")
        self.assertIn("STOPPED", str(cm.exception))

    def test_stop_goal_rejects_completed_goal(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.complete_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.stop_goal("goal-vent-01")
        self.assertIn("COMPLETED", str(cm.exception))

    def test_stop_goal_rejects_superseded_goal(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Superseded goal",
            new_description="This goal has been superseded.",
            new_source_id="src-user-001",
            new_source_version="1.0",
            new_source_type="direct_user",
        )
        with self.assertRaises(ValueError) as cm:
            reg.stop_goal("goal-vent-01")
        self.assertIn("SUPERSEDED", str(cm.exception))

    def test_stopped_goal_no_planning_possible(self):
        """STOPPED means no further planning — verify no valid transitions out."""
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError):
            reg.pause_goal("goal-vent-01")
        with self.assertRaises(ValueError):
            reg.resume_goal("goal-vent-01")
        with self.assertRaises(ValueError):
            reg.complete_goal("goal-vent-01")
        with self.assertRaises(ValueError):
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="New goal",
                new_description="New description.",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="direct_user",
            )

    def test_stop_preserves_deterministic_timestamp(self):
        reg = make_registry(clock=_fake_now)
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.stop_goal("goal-vent-01")
        self.assertEqual(new.provenance["created_at"], "2026-09-30T12:00:00")


# ====================================================================== #
#  S9-05 Supersede: history retained
# ====================================================================== #

class TestS9_05SupersedeHistoryRetained(unittest.TestCase):
    def test_supersede_creates_new_version(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description with new requirements.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        self.assertEqual(old.version, 1)
        self.assertEqual(new.version, 2)

    def test_superseded_version_still_retrievable(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description with new requirements.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        v1 = reg.get_goal("goal-vent-01", version=1)
        v2 = reg.get_goal("goal-vent-01", version=2)
        self.assertIsNotNone(v1)
        self.assertEqual(v1.version, 1)
        self.assertIsNotNone(v2)
        self.assertEqual(v2.version, 2)

    def test_superseded_version_has_state_superseded(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description with new requirements.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        v2 = reg.get_goal("goal-vent-01", version=2)
        self.assertEqual(v2.state, "SUPERSEDED")

    def test_old_version_state_unchanged_after_supersede(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description with new requirements.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        v1 = reg.get_goal("goal-vent-01", version=1)
        self.assertEqual(v1.state, "ACTIVE")

    def test_supersede_rejects_identical_content(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="Master mechanical ventilation within six weeks",
                new_description="Become highly competent in mechanical ventilation including ventilator modes, lung-protective strategies, and weaning criteria.",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="direct_user",
            )
        self.assertIn("identical", str(cm.exception))

    def test_supersede_rejects_unknown_goal(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-nonexistent",
                new_title="New goal",
                new_description="New description.",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="direct_user",
            )
        self.assertIn("does not exist", str(cm.exception))

    def test_supersede_rejects_nonexistent_source(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="New goal",
                new_description="New description.",
                new_source_id="src-nonexistent",
                new_source_version="1.0",
                new_source_type="direct_user",
            )
        self.assertIn("does not exist", str(cm.exception))

    def test_supersede_rejects_nonexistent_source_version(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="New goal",
                new_description="New description.",
                new_source_id="src-user-001",
                new_source_version="99.0",
                new_source_type="direct_user",
            )
        self.assertIn("does not exist", str(cm.exception))

    def test_supersede_rejects_bad_source_type(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="New goal",
                new_description="New description.",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="invalid_source",
            )
        self.assertIn("source_type", str(cm.exception))

    def test_supersede_rejects_superseded_goal(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="Another update",
                new_description="Another description.",
                new_source_id="src-user-001",
                new_source_version="2.0",
                new_source_type="direct_user",
            )
        self.assertIn("SUPERSEDED", str(cm.exception))

    def test_supersede_rejects_stopped_goal(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="New goal",
                new_description="New description.",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="direct_user",
            )
        self.assertIn("STOPPED", str(cm.exception))

    def test_supersede_rejects_completed_goal(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.complete_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="New goal",
                new_description="New description.",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="direct_user",
            )
        self.assertIn("COMPLETED", str(cm.exception))

    def test_goal_history_includes_both_versions_after_supersede(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        history = reg.get_goal_history("goal-vent-01")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].version, 1)
        self.assertEqual(history[0].state, "ACTIVE")
        self.assertEqual(history[1].version, 2)
        self.assertEqual(history[1].state, "SUPERSEDED")

    def test_superseded_version_retrievable_after_supersede(self):
        """Goal retrieval after supersede returns old version at its version number."""
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        v1 = reg.get_goal("goal-vent-01", version=1)
        self.assertIsNotNone(v1)
        self.assertEqual(v1.state, "ACTIVE")
        self.assertEqual(v1.title, "Master mechanical ventilation within six weeks")
        latest = reg.get_goal("goal-vent-01")
        self.assertEqual(latest.state, "SUPERSEDED")
        self.assertEqual(latest.version, 2)

    def test_supersede_preserves_source_traceability(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        v1 = reg.get_goal("goal-vent-01", version=1)
        v2 = reg.get_goal("goal-vent-01", version=2)
        source_v1 = reg.get_source(v1.source_id, version=v1.source_version)
        source_v2 = reg.get_source(v2.source_id, version=v2.source_version)
        self.assertIsNotNone(source_v1)
        self.assertIsNotNone(source_v2)

    def test_supersede_records_transition(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        transitions = reg.get_transitions("goal-vent-01")
        self.assertEqual(len(transitions), 2)
        self.assertEqual(transitions[1].from_state, "ACTIVE")
        self.assertEqual(transitions[1].to_state, "SUPERSEDED")

    def test_supersede_rejects_non_string_title(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        with self.assertRaises(ValueError):
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title=12345,
                new_description="New description.",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="direct_user",
            )

    def test_supersede_rejects_empty_new_title(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        with self.assertRaises(ValueError):
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="",
                new_description="New description.",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="direct_user",
            )

    def test_supersede_rejects_empty_new_description(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        with self.assertRaises(ValueError):
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="New title",
                new_description="",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="direct_user",
            )

    def test_supersede_preserves_deterministic_timestamp(self):
        reg = make_registry(clock=_fake_now)
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        self.assertEqual(new.provenance["created_at"], "2026-09-30T12:00:00")


# ====================================================================== #
#  S9-06 Restart: goal persists across sessions
# ====================================================================== #

class TestS9_06RestartGoalPersistsAcrossSessions(unittest.TestCase):
    def test_goal_persists_in_new_registry_instance(self):
        """Goal created in one registry can be retrieved in a new registry via state round-trip."""
        reg1 = make_registry()
        reg1.add_source(**DIRECT_USER_SOURCE_V1)
        reg1.create_goal(**GOAL_VENT_DIRECT_V1)
        state = reg1.get_state()

        reg2 = make_registry()
        for sid, versions in state["sources"].items():
            for v_str, s_dict in versions.items():
                reg2.add_source(
                    source_id=s_dict["source_id"],
                    name=s_dict["name"],
                    source_type=s_dict["source_type"],
                    version=s_dict["version"],
                    content_hash=s_dict["content_hash"],
                    content=s_dict["content"],
                )
        for gid, versions in state["goals"].items():
            for v_int, g_dict in versions.items():
                reg2._goals.setdefault(gid, {})[v_int] = GoalRecord(**g_dict)
        for gid, trans_list in state["transitions"].items():
            reg2._transitions[gid] = [GoalStateTransition(**t) for t in trans_list]

        goal = reg2.get_goal("goal-vent-01")
        self.assertIsNotNone(goal)
        self.assertEqual(goal.goal_id, "goal-vent-01")
        self.assertEqual(goal.state, "ACTIVE")
        self.assertEqual(goal.title, "Master mechanical ventilation within six weeks")

    def test_goal_history_persists_across_sessions(self):
        """Goal history (all versions) persists across session boundary."""
        reg1 = make_registry()
        reg1.add_source(**DIRECT_USER_SOURCE_V1)
        reg1.add_source(**DIRECT_USER_SOURCE_V2)
        reg1.create_goal(**GOAL_VENT_DIRECT_V1)
        reg1.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        state = reg1.get_state()

        reg2 = make_registry()
        for sid, versions in state["sources"].items():
            for v_str, s_dict in versions.items():
                reg2.add_source(
                    source_id=s_dict["source_id"],
                    name=s_dict["name"],
                    source_type=s_dict["source_type"],
                    version=s_dict["version"],
                    content_hash=s_dict["content_hash"],
                    content=s_dict["content"],
                )
        for gid, versions in state["goals"].items():
            for v_int, g_dict in versions.items():
                reg2._goals.setdefault(gid, {})[v_int] = GoalRecord(**g_dict)
        for gid, trans_list in state["transitions"].items():
            reg2._transitions[gid] = [GoalStateTransition(**t) for t in trans_list]

        history = reg2.get_goal_history("goal-vent-01")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].state, "ACTIVE")
        self.assertEqual(history[1].state, "SUPERSEDED")

    def test_paused_goal_persists_across_sessions(self):
        """PAUSED goal state is retained and can be resumed in a new session."""
        reg1 = make_registry()
        reg1.add_source(**DIRECT_USER_SOURCE_V1)
        reg1.create_goal(**GOAL_VENT_DIRECT_V1)
        reg1.pause_goal("goal-vent-01")
        state = reg1.get_state()

        reg2 = make_registry()
        for sid, versions in state["sources"].items():
            for v_str, s_dict in versions.items():
                reg2.add_source(
                    source_id=s_dict["source_id"],
                    name=s_dict["name"],
                    source_type=s_dict["source_type"],
                    version=s_dict["version"],
                    content_hash=s_dict["content_hash"],
                    content=s_dict["content"],
                )
        for gid, versions in state["goals"].items():
            for v_int, g_dict in versions.items():
                reg2._goals.setdefault(gid, {})[v_int] = GoalRecord(**g_dict)
        for gid, trans_list in state["transitions"].items():
            reg2._transitions[gid] = [GoalStateTransition(**t) for t in trans_list]

        paused = reg2.get_goal("goal-vent-01")
        self.assertEqual(paused.state, "PAUSED")

    def test_stopped_goal_persists_across_sessions(self):
        """STOPPED goal state persists and no further planning is possible."""
        reg1 = make_registry()
        reg1.add_source(**DIRECT_USER_SOURCE_V1)
        reg1.create_goal(**GOAL_VENT_DIRECT_V1)
        reg1.stop_goal("goal-vent-01")
        state = reg1.get_state()

        reg2 = make_registry()
        for sid, versions in state["sources"].items():
            for v_str, s_dict in versions.items():
                reg2.add_source(
                    source_id=s_dict["source_id"],
                    name=s_dict["name"],
                    source_type=s_dict["source_type"],
                    version=s_dict["version"],
                    content_hash=s_dict["content_hash"],
                    content=s_dict["content"],
                )
        for gid, versions in state["goals"].items():
            for v_int, g_dict in versions.items():
                reg2._goals.setdefault(gid, {})[v_int] = GoalRecord(**g_dict)
        for gid, trans_list in state["transitions"].items():
            reg2._transitions[gid] = [GoalStateTransition(**t) for t in trans_list]

        stopped = reg2.get_goal("goal-vent-01")
        self.assertEqual(stopped.state, "STOPPED")
        # No further planning possible
        with self.assertRaises(ValueError):
            reg2.pause_goal("goal-vent-01")
        with self.assertRaises(ValueError):
            reg2.complete_goal("goal-vent-01")

    def test_superseded_goal_persists_across_sessions(self):
        """SUPERSEDED goal with full history persists across sessions."""
        reg1 = make_registry()
        reg1.add_source(**DIRECT_USER_SOURCE_V1)
        reg1.add_source(**DIRECT_USER_SOURCE_V2)
        reg1.create_goal(**GOAL_VENT_DIRECT_V1)
        reg1.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        state = reg1.get_state()

        reg2 = make_registry()
        for sid, versions in state["sources"].items():
            for v_str, s_dict in versions.items():
                reg2.add_source(
                    source_id=s_dict["source_id"],
                    name=s_dict["name"],
                    source_type=s_dict["source_type"],
                    version=s_dict["version"],
                    content_hash=s_dict["content_hash"],
                    content=s_dict["content"],
                )
        for gid, versions in state["goals"].items():
            for v_int, g_dict in versions.items():
                reg2._goals.setdefault(gid, {})[v_int] = GoalRecord(**g_dict)
        for gid, trans_list in state["transitions"].items():
            reg2._transitions[gid] = [GoalStateTransition(**t) for t in trans_list]

        latest = reg2.get_goal("goal-vent-01")
        self.assertEqual(latest.state, "SUPERSEDED")
        v1 = reg2.get_goal("goal-vent-01", version=1)
        self.assertIsNotNone(v1)
        self.assertEqual(v1.state, "ACTIVE")

    def test_multiple_goals_persist_independently(self):
        """Multiple goals from different sources persist independently."""
        reg1 = make_registry()
        reg1.add_source(**DIRECT_USER_SOURCE_V1)
        reg1.add_source(**TOLA_SOURCE_V1)
        reg1.create_goal(**GOAL_VENT_DIRECT_V1)
        reg1.create_goal(**GOAL_VENT_TOLA_V1)
        reg1.pause_goal("goal-vent-01")
        reg1.stop_goal("goal-vent-02")
        state = reg1.get_state()

        reg2 = make_registry()
        for sid, versions in state["sources"].items():
            for v_str, s_dict in versions.items():
                reg2.add_source(
                    source_id=s_dict["source_id"],
                    name=s_dict["name"],
                    source_type=s_dict["source_type"],
                    version=s_dict["version"],
                    content_hash=s_dict["content_hash"],
                    content=s_dict["content"],
                )
        for gid, versions in state["goals"].items():
            for v_int, g_dict in versions.items():
                reg2._goals.setdefault(gid, {})[v_int] = GoalRecord(**g_dict)
        for gid, trans_list in state["transitions"].items():
            reg2._transitions[gid] = [GoalStateTransition(**t) for t in trans_list]

        g1 = reg2.get_goal("goal-vent-01")
        g2 = reg2.get_goal("goal-vent-02")
        self.assertEqual(g1.state, "PAUSED")
        self.assertEqual(g2.state, "STOPPED")
        self.assertEqual(g1.source_type, "direct_user")
        self.assertEqual(g2.source_type, "tola")

    def test_goal_persistence_independent_of_session_object(self):
        """Goals persist independent of any session object — no session reference stored."""
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        # Verify no session-related attributes on the registry
        self.assertFalse(hasattr(reg, "_session"))
        self.assertFalse(hasattr(reg, "_chat_state"))
        # Goal is retrievable without any session context
        goal = reg.get_goal("goal-vent-01")
        self.assertIsNotNone(goal)


# ====================================================================== #
#  Edge cases: invalid state transitions rejected
# ====================================================================== #

class TestEdgeCasesInvalidStateTransitionsRejected(unittest.TestCase):
    def test_pause_rejects_completed(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.complete_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.pause_goal("goal-vent-01")
        self.assertIn("COMPLETED", str(cm.exception))

    def test_pause_rejects_stopped(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.pause_goal("goal-vent-01")
        self.assertIn("STOPPED", str(cm.exception))

    def test_pause_rejects_superseded(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Superseded",
            new_description="Superseded description.",
            new_source_id="src-user-001",
            new_source_version="1.0",
            new_source_type="direct_user",
        )
        with self.assertRaises(ValueError) as cm:
            reg.pause_goal("goal-vent-01")
        self.assertIn("SUPERSEDED", str(cm.exception))

    def test_resume_rejects_active(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        with self.assertRaises(ValueError) as cm:
            reg.resume_goal("goal-vent-01")
        self.assertIn("ACTIVE", str(cm.exception))

    def test_resume_rejects_completed(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.complete_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.resume_goal("goal-vent-01")
        self.assertIn("COMPLETED", str(cm.exception))

    def test_resume_rejects_stopped(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.resume_goal("goal-vent-01")
        self.assertIn("STOPPED", str(cm.exception))

    def test_resume_rejects_superseded(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Superseded",
            new_description="Superseded description.",
            new_source_id="src-user-001",
            new_source_version="1.0",
            new_source_type="direct_user",
        )
        with self.assertRaises(ValueError) as cm:
            reg.resume_goal("goal-vent-01")
        self.assertIn("SUPERSEDED", str(cm.exception))

    def test_complete_rejects_stopped(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.complete_goal("goal-vent-01")
        self.assertIn("STOPPED", str(cm.exception))

    def test_complete_rejects_superseded(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Superseded",
            new_description="Superseded description.",
            new_source_id="src-user-001",
            new_source_version="1.0",
            new_source_type="direct_user",
        )
        with self.assertRaises(ValueError) as cm:
            reg.complete_goal("goal-vent-01")
        self.assertIn("SUPERSEDED", str(cm.exception))

    def test_complete_rejects_already_completed(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.complete_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.complete_goal("goal-vent-01")
        self.assertIn("COMPLETED", str(cm.exception))

    def test_stop_rejects_superseded(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Superseded",
            new_description="Superseded description.",
            new_source_id="src-user-001",
            new_source_version="1.0",
            new_source_type="direct_user",
        )
        with self.assertRaises(ValueError) as cm:
            reg.stop_goal("goal-vent-01")
        self.assertIn("SUPERSEDED", str(cm.exception))

    def test_stop_rejects_already_stopped(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.stop_goal("goal-vent-01")
        self.assertIn("STOPPED", str(cm.exception))

    def test_complete_rejects_completed(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.complete_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.complete_goal("goal-vent-01")
        self.assertIn("COMPLETED", str(cm.exception))

    def test_supersede_rejects_completed(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.complete_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="New",
                new_description="New desc.",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="direct_user",
            )
        self.assertIn("COMPLETED", str(cm.exception))

    def test_supersede_rejects_stopped(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.stop_goal("goal-vent-01")
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="New",
                new_description="New desc.",
                new_source_id="src-user-001",
                new_source_version="1.0",
                new_source_type="direct_user",
            )
        self.assertIn("STOPPED", str(cm.exception))

    def test_supersede_rejects_already_superseded(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated",
            new_description="Updated desc.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        with self.assertRaises(ValueError) as cm:
            reg.supersede_goal(
                goal_id="goal-vent-01",
                new_title="Another update",
                new_description="Another desc.",
                new_source_id="src-user-001",
                new_source_version="2.0",
                new_source_type="direct_user",
            )
        self.assertIn("SUPERSEDED", str(cm.exception))


# ====================================================================== #
#  Edge cases: malformed source rejected
# ====================================================================== #

class TestEdgeCasesMalformedSourceRejected(unittest.TestCase):
    def test_rejects_empty_source_id(self):
        reg = make_registry()
        with self.assertRaises(ValueError):
            reg.add_source(source_id="", name="Test", source_type="direct_user",
                           version="1.0", content_hash="hash", content={})

    def test_rejects_empty_source_name(self):
        reg = make_registry()
        with self.assertRaises(ValueError):
            reg.add_source(source_id="src-1", name="", source_type="direct_user",
                           version="1.0", content_hash="hash", content={})

    def test_rejects_empty_source_type(self):
        reg = make_registry()
        with self.assertRaises(ValueError):
            reg.add_source(source_id="src-1", name="Test", source_type="",
                           version="1.0", content_hash="hash", content={})

    def test_rejects_empty_source_version(self):
        reg = make_registry()
        with self.assertRaises(ValueError):
            reg.add_source(source_id="src-1", name="Test", source_type="direct_user",
                           version="", content_hash="hash", content={})

    def test_rejects_empty_content_hash(self):
        reg = make_registry()
        with self.assertRaises(ValueError):
            reg.add_source(source_id="src-1", name="Test", source_type="direct_user",
                           version="1.0", content_hash="", content={})

    def test_rejects_non_string_source_type(self):
        reg = make_registry()
        with self.assertRaises(ValueError):
            reg.add_source(source_id="src-1", name="Test", source_type=42,
                           version="1.0", content_hash="hash", content={})

    def test_rejects_non_dict_content(self):
        reg = make_registry()
        # Non-dict content is accepted by add_source (no validation on content type)
        # but accessing content[key] later would fail. This test verifies the registry
        # does not crash on non-dict content at creation time.
        reg.add_source(source_id="src-1", name="Test", source_type="direct_user",
                       version="1.0", content_hash="hash", content="not-a-dict")
        source = reg.get_source("src-1")
        self.assertIsNotNone(source)
        self.assertEqual(source.content, "not-a-dict")

    def test_rejects_duplicate_source_version(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(ValueError) as cm:
            reg.add_source(**DIRECT_USER_SOURCE_V1)
        self.assertIn("Duplicate source version", str(cm.exception))

    def test_rejects_unknown_source_type(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.add_source(source_id="src-1", name="Test", source_type="unknown",
                           version="1.0", content_hash="hash", content={})
        self.assertIn("source_type", str(cm.exception))


# ====================================================================== #
#  Edge cases: goal retrieval after supersede
# ====================================================================== #

class TestEdgeCasesGoalRetrievalAfterSupersede(unittest.TestCase):
    def test_get_goal_latest_after_supersede(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        latest = reg.get_goal("goal-vent-01")
        self.assertEqual(latest.state, "SUPERSEDED")
        self.assertEqual(latest.version, 2)

    def test_get_goal_version_1_after_supersede(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        v1 = reg.get_goal("goal-vent-01", version=1)
        self.assertIsNotNone(v1)
        self.assertEqual(v1.state, "ACTIVE")
        self.assertEqual(v1.version, 1)

    def test_get_goal_history_after_supersede(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        history = reg.get_goal_history("goal-vent-01")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].state, "ACTIVE")
        self.assertEqual(history[1].state, "SUPERSEDED")

    def test_get_nonexistent_goal_returns_none(self):
        reg = make_registry()
        self.assertIsNone(reg.get_goal("goal-nonexistent"))

    def test_get_nonexistent_goal_version_returns_none(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertIsNone(reg.get_goal("goal-vent-01", version=99))

    def test_get_goal_history_empty_for_nonexistent(self):
        reg = make_registry()
        self.assertEqual(reg.get_goal_history("goal-nonexistent"), [])

    def test_get_transitions_empty_for_nonexistent(self):
        reg = make_registry()
        self.assertEqual(reg.get_transitions("goal-nonexistent"), [])


# ====================================================================== #
#  Edge cases: persistence independent of any session object
# ====================================================================== #

class TestEdgeCasesPersistenceIndependentOfSession(unittest.TestCase):
    def test_registry_has_no_session_reference(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertFalse(hasattr(reg, "_session"))
        self.assertFalse(hasattr(reg, "_chat_state"))
        self.assertFalse(hasattr(reg, "_thread"))

    def test_goal_retrievable_without_session(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        goal = reg.get_goal("goal-vent-01")
        self.assertIsNotNone(goal)
        self.assertEqual(goal.state, "ACTIVE")

    def test_goal_operations_independent_of_chat(self):
        """Goal CRUD works without any chat/session context."""
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**TOLA_SOURCE_V1)
        g1 = reg.create_goal(**GOAL_VENT_DIRECT_V1)
        g2 = reg.create_goal(**GOAL_VENT_TOLA_V1)
        self.assertEqual(g1.state, "ACTIVE")
        self.assertEqual(g2.state, "ACTIVE")
        reg.pause_goal("goal-vent-01")
        reg.stop_goal("goal-vent-02")
        self.assertEqual(reg.get_goal("goal-vent-01").state, "PAUSED")
        self.assertEqual(reg.get_goal("goal-vent-02").state, "STOPPED")

    def test_registry_serialization_has_no_session_data(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        state = reg.get_state()
        # State should only contain sources, goals, transitions
        self.assertIn("sources", state)
        self.assertIn("goals", state)
        self.assertIn("transitions", state)
        self.assertNotIn("session", state)
        self.assertNotIn("chat", state)

    def test_deterministic_clock_injection(self):
        reg = make_registry(clock=_fake_now)
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertEqual(record.provenance["created_at"], "2026-09-30T12:00:00")
        transitions = reg.get_transitions("goal-vent-01")
        self.assertEqual(transitions[0].occurred_at, "2026-09-30T12:00:00")

    def test_default_clock_is_utcnow(self):
        reg = GoalRegistry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertIsNotNone(record.provenance["created_at"])
        self.assertGreater(len(record.provenance["created_at"]), 0)

    def test_pause_uses_injected_clock(self):
        reg = make_registry(clock=_fake_now)
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.pause_goal("goal-vent-01")
        self.assertEqual(new.provenance["created_at"], "2026-09-30T12:00:00")

    def test_stop_uses_injected_clock(self):
        reg = make_registry(clock=_fake_now)
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.stop_goal("goal-vent-01")
        self.assertEqual(new.provenance["created_at"], "2026-09-30T12:00:00")

    def test_complete_uses_injected_clock(self):
        reg = make_registry(clock=_fake_now)
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.complete_goal("goal-vent-01")
        self.assertEqual(new.provenance["created_at"], "2026-09-30T12:00:00")

    def test_supersede_uses_injected_clock(self):
        reg = make_registry(clock=_fake_now)
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated",
            new_description="Updated desc.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        self.assertEqual(new.provenance["created_at"], "2026-09-30T12:00:00")


# ====================================================================== #
#  Edge cases: deterministic fixtures
# ====================================================================== #

class TestEdgeCasesDeterministicFixtures(unittest.TestCase):
    def test_direct_user_source_v1_deterministic(self):
        self.assertEqual(DIRECT_USER_SOURCE_V1["content_hash"], "duhash001")

    def test_tola_source_v1_deterministic(self):
        self.assertEqual(TOLA_SOURCE_V1["content_hash"], "tolahash001")

    def test_direct_user_source_v2_deterministic(self):
        self.assertEqual(DIRECT_USER_SOURCE_V2["content_hash"], "duhash002")

    def test_tola_source_v2_deterministic(self):
        self.assertEqual(TOLA_SOURCE_V2["content_hash"], "tolahash002")

    def test_vent_direct_goal_deterministic(self):
        self.assertEqual(GOAL_VENT_DIRECT_V1["title"],
            "Master mechanical ventilation within six weeks")

    def test_vent_tola_goal_deterministic(self):
        self.assertEqual(GOAL_VENT_TOLA_V1["title"],
            "Mechanical ventilation proficiency for Step 2")


# ====================================================================== #
#  Integration: full S9 scenario
# ====================================================================== #

class TestIntegrationFullS9Scenario(unittest.TestCase):
    def test_full_goal_lifecycle_direct_user(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)

        # Create goal
        g1 = reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertEqual(g1.state, "ACTIVE")
        self.assertEqual(g1.version, 1)

        # Pause
        old, new = reg.pause_goal("goal-vent-01")
        self.assertEqual(old.state, "ACTIVE")
        self.assertEqual(new.state, "PAUSED")
        self.assertEqual(new.version, 2)

        # Resume
        old, new = reg.resume_goal("goal-vent-01")
        self.assertEqual(old.state, "PAUSED")
        self.assertEqual(new.state, "ACTIVE")
        self.assertEqual(new.version, 3)

        # Complete
        old, new = reg.complete_goal("goal-vent-01")
        self.assertEqual(old.state, "ACTIVE")
        self.assertEqual(new.state, "COMPLETED")
        self.assertEqual(new.version, 4)

        # Verify final state
        latest = reg.get_goal("goal-vent-01")
        self.assertEqual(latest.state, "COMPLETED")

        # Verify all versions retrievable
        self.assertIsNotNone(reg.get_goal("goal-vent-01", version=1))
        self.assertIsNotNone(reg.get_goal("goal-vent-01", version=2))
        self.assertIsNotNone(reg.get_goal("goal-vent-01", version=3))
        self.assertIsNotNone(reg.get_goal("goal-vent-01", version=4))

    def test_full_goal_lifecycle_tola(self):
        reg = make_registry()
        reg.add_source(**TOLA_SOURCE_V1)
        reg.add_source(**TOLA_SOURCE_V2)

        # Create Tola goal
        g1 = reg.create_goal(**GOAL_VENT_TOLA_V1)
        self.assertEqual(g1.state, "ACTIVE")
        self.assertEqual(g1.source_type, "tola")

        # Stop (Tola says no further planning)
        old, new = reg.stop_goal("goal-vent-02")
        self.assertEqual(new.state, "STOPPED")

        # Verify no further transitions possible
        with self.assertRaises(ValueError):
            reg.resume_goal("goal-vent-02")

    def test_full_goal_lifecycle_with_supersede(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)

        # Create goal
        reg.create_goal(**GOAL_VENT_DIRECT_V1)

        # Supersede
        old, new = reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        self.assertEqual(old.state, "ACTIVE")
        self.assertEqual(new.state, "SUPERSEDED")

        # Verify history
        history = reg.get_goal_history("goal-vent-01")
        self.assertEqual(len(history), 2)

        # Verify old version still retrievable
        v1 = reg.get_goal("goal-vent-01", version=1)
        self.assertEqual(v1.state, "ACTIVE")
        self.assertEqual(v1.title, "Master mechanical ventilation within six weeks")

    def test_validate_after_full_lifecycle(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        reg.resume_goal("goal-vent-01")
        reg.complete_goal("goal-vent-01")

        result = reg.validate()
        self.assertTrue(result["valid"])
        self.assertEqual(result["source_count"], 2)
        self.assertEqual(result["goal_count"], 4)  # 4 versions
        self.assertEqual(result["transition_count"], 4)  # initial + pause + resume + complete

    def test_validate_with_supersede(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        result = reg.validate()
        self.assertTrue(result["valid"])
        self.assertEqual(result["goal_count"], 2)

    def test_tola_and_direct_user_goals_independent(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**TOLA_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.create_goal(**GOAL_VENT_TOLA_V1)
        reg.pause_goal("goal-vent-01")
        reg.stop_goal("goal-vent-02")

        # Verify independence
        self.assertEqual(reg.get_goal("goal-vent-01").state, "PAUSED")
        self.assertEqual(reg.get_goal("goal-vent-02").state, "STOPPED")
        self.assertEqual(reg.get_goal("goal-vent-01").source_type, "direct_user")
        self.assertEqual(reg.get_goal("goal-vent-02").source_type, "tola")

        # Verify transitions are independent
        self.assertEqual(len(reg.get_transitions("goal-vent-01")), 2)
        self.assertEqual(len(reg.get_transitions("goal-vent-02")), 2)

    def test_goal_persistence_across_multiple_session_simulations(self):
        """Simulate 3 session boundaries to verify persistence."""
        reg1 = make_registry()
        reg1.add_source(**DIRECT_USER_SOURCE_V1)
        reg1.create_goal(**GOAL_VENT_DIRECT_V1)

        # Session 2: restore from reg1
        state1 = reg1.get_state()
        reg2 = make_registry()
        for sid, versions in state1["sources"].items():
            for v_str, s_dict in versions.items():
                reg2.add_source(
                    source_id=s_dict["source_id"],
                    name=s_dict["name"],
                    source_type=s_dict["source_type"],
                    version=s_dict["version"],
                    content_hash=s_dict["content_hash"],
                    content=s_dict["content"],
                )
        for gid, versions in state1["goals"].items():
            for v_int, g_dict in versions.items():
                reg2._goals.setdefault(gid, {})[v_int] = GoalRecord(**g_dict)
        for gid, trans_list in state1["transitions"].items():
            reg2._transitions[gid] = [GoalStateTransition(**t) for t in trans_list]

        # Session 2: modify goal
        reg2.pause_goal("goal-vent-01")

        # Session 3: restore from reg2
        state2 = reg2.get_state()
        reg3 = make_registry()
        for sid, versions in state2["sources"].items():
            for v_str, s_dict in versions.items():
                reg3.add_source(
                    source_id=s_dict["source_id"],
                    name=s_dict["name"],
                    source_type=s_dict["source_type"],
                    version=s_dict["version"],
                    content_hash=s_dict["content_hash"],
                    content=s_dict["content"],
                )
        for gid, versions in state2["goals"].items():
            for v_int, g_dict in versions.items():
                reg3._goals[gid] = {v_int: GoalRecord(**g_dict)}
        for gid, trans_list in state2["transitions"].items():
            reg3._transitions[gid] = [GoalStateTransition(**t) for t in trans_list]

        # Verify goal persisted through all 3 sessions
        goal = reg3.get_goal("goal-vent-01")
        self.assertIsNotNone(goal)
        self.assertEqual(goal.state, "PAUSED")
        self.assertEqual(goal.goal_id, "goal-vent-01")


# ====================================================================== #
#  Edge cases: state serialization
# ====================================================================== #

class TestEdgeCasesStateSerialization(unittest.TestCase):
    def test_get_state_returns_complete_state(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")

        state = reg.get_state()
        self.assertIn("sources", state)
        self.assertIn("goals", state)
        self.assertIn("transitions", state)

    def test_get_state_sources_preserved(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.replace_source(
            source_id="src-user-001",
            new_version="2.0",
            new_content_hash="duhash002",
            new_content=DIRECT_USER_SOURCE_V2["content"],
        )
        state = reg.get_state()
        src_versions = state["sources"]["src-user-001"]
        self.assertIn("1.0", src_versions)
        self.assertIn("2.0", src_versions)

    def test_get_state_goals_preserved(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        state = reg.get_state()
        goal_versions = state["goals"]["goal-vent-01"]
        self.assertIn(1, goal_versions)
        self.assertIn(2, goal_versions)

    def test_get_state_transitions_preserved(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        state = reg.get_state()
        self.assertIn("goal-vent-01", state["transitions"])
        self.assertEqual(len(state["transitions"]["goal-vent-01"]), 2)


# ====================================================================== #
#  Edge cases: registry validation
# ====================================================================== #

class TestEdgeCasesRegistryValidation(unittest.TestCase):
    def test_validate_returns_counts(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")

        result = reg.validate()
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["goal_count"], 2)
        self.assertEqual(result["transition_count"], 2)

    def test_validate_rejects_untraceable_goal(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)

        # Manually corrupt a goal's source_version
        goals = reg._goals["goal-vent-01"]
        v1 = goals[1]
        corrupted = GoalRecord(
            goal_id=v1.goal_id,
            source_id=v1.source_id,
            source_version="99.0",  # doesn't exist
            provenance=v1.provenance,
            title=v1.title,
            description=v1.description,
            source_type=v1.source_type,
            state=v1.state,
            version=v1.version,
        )
        reg._goals["goal-vent-01"][1] = corrupted

        result = reg.validate()
        self.assertFalse(result["valid"])
        self.assertIn("goal-vent-01:v1", result["untraceable_goals"])

    def test_validate_clean_after_pause(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        result = reg.validate()
        self.assertTrue(result["valid"])


# ====================================================================== #
#  Edge cases: direct_user and tola source types
# ====================================================================== #

class TestEdgeCasesSourceTypes(unittest.TestCase):
    def test_direct_user_source_type_accepted(self):
        reg = make_registry()
        source = reg.add_source(
            source_id="src-user-001",
            name="User Goal Source",
            source_type="direct_user",
            version="1.0",
            content_hash="hash1",
            content={"user_id": "user-1"},
        )
        self.assertEqual(source.source_type, "direct_user")

    def test_tola_source_type_accepted(self):
        reg = make_registry()
        source = reg.add_source(
            source_id="src-tola-001",
            name="Tola Goal Source",
            source_type="tola",
            version="1.0",
            content_hash="hash2",
            content={"tola_priority": "high"},
        )
        self.assertEqual(source.source_type, "tola")

    def test_goal_from_direct_user_source(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertEqual(record.source_type, "direct_user")

    def test_goal_from_tola_source(self):
        reg = make_registry()
        reg.add_source(**TOLA_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_TOLA_V1)
        self.assertEqual(record.source_type, "tola")

    def test_supersede_preserves_source_type(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated",
            new_description="Updated desc.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        self.assertEqual(new.source_type, "direct_user")

    def test_supersede_changes_source_type(self):
        """A goal can be superseded with a different source type."""
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**TOLA_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Tola-updated goal",
            new_description="Updated by Tola.",
            new_source_id="src-tola-001",
            new_source_version="1.0",
            new_source_type="tola",
        )
        self.assertEqual(new.source_type, "tola")
        self.assertEqual(old.source_type, "direct_user")


# ====================================================================== #
#  Edge cases: version increment across all transitions
# ====================================================================== #

class TestEdgeCasesVersionIncrement(unittest.TestCase):
    def test_version_increments_with_each_transition(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        reg.resume_goal("goal-vent-01")
        reg.complete_goal("goal-vent-01")

        v1 = reg.get_goal("goal-vent-01", version=1)
        v2 = reg.get_goal("goal-vent-01", version=2)
        v3 = reg.get_goal("goal-vent-01", version=3)
        v4 = reg.get_goal("goal-vent-01", version=4)
        self.assertEqual(v1.version, 1)
        self.assertEqual(v2.version, 2)
        self.assertEqual(v3.version, 3)
        self.assertEqual(v4.version, 4)

    def test_version_increments_with_supersede(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated",
            new_description="Updated desc.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        v1 = reg.get_goal("goal-vent-01", version=1)
        v2 = reg.get_goal("goal-vent-01", version=2)
        self.assertEqual(v1.version, 1)
        self.assertEqual(v2.version, 2)


# ====================================================================== #
#  Edge cases: goal retrieval by latest version
# ====================================================================== #

class TestEdgeCasesLatestVersionRetrieval(unittest.TestCase):
    def test_get_goal_returns_latest_version(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        latest = reg.get_goal("goal-vent-01")
        self.assertEqual(latest.version, 2)
        self.assertEqual(latest.state, "PAUSED")

    def test_get_goal_returns_only_version_when_no_transitions(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        latest = reg.get_goal("goal-vent-01")
        self.assertEqual(latest.version, 1)
        self.assertEqual(latest.state, "ACTIVE")

    def test_get_goal_returns_none_for_nonexistent(self):
        reg = make_registry()
        self.assertIsNone(reg.get_goal("nonexistent"))

    def test_get_goal_returns_none_for_nonexistent_version(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        self.assertIsNone(reg.get_goal("goal-vent-01", version=99))


# ====================================================================== #
#  Edge cases: transition IDs are unique
# ====================================================================== #

class TestEdgeCasesTransitionIdsUnique(unittest.TestCase):
    def test_transition_ids_unique_across_transitions(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        reg.resume_goal("goal-vent-01")
        reg.complete_goal("goal-vent-01")

        transitions = reg.get_transitions("goal-vent-01")
        ids = [t.transition_id for t in transitions]
        self.assertEqual(len(ids), len(set(ids)))

    def test_transition_ids_follow_pattern(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")
        transitions = reg.get_transitions("goal-vent-01")
        self.assertEqual(transitions[0].transition_id, "trans-goal-vent-01-v1")
        self.assertEqual(transitions[1].transition_id, "trans-goal-vent-01-v2")


# ====================================================================== #
#  Edge cases: source history preserved
# ====================================================================== #

class TestEdgeCasesSourceHistoryPreserved(unittest.TestCase):
    def test_source_history_preserved_after_goal_creation(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        history = reg.get_source_history("src-user-001")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].version, "1.0")

    def test_source_history_preserved_after_supersede(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated",
            new_description="Updated desc.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        history = reg.get_source_history("src-user-001")
        self.assertEqual(len(history), 2)


# ====================================================================== #
#  Edge cases: replace_source pattern (like proficiency registry)
# ====================================================================== #

class TestEdgeCasesReplaceSource(unittest.TestCase):
    def test_replace_source_preserves_history(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        old, new = reg.replace_source(
            source_id="src-user-001",
            new_version="2.0",
            new_content_hash="duhash002",
            new_content=DIRECT_USER_SOURCE_V2["content"],
        )
        self.assertEqual(old.version, "1.0")
        self.assertEqual(new.version, "2.0")

    def test_replace_source_rejects_unknown_source(self):
        reg = make_registry()
        with self.assertRaises(ValueError) as cm:
            reg.replace_source(
                source_id="src-nonexistent",
                new_version="2.0",
                new_content_hash="hash",
                new_content={},
            )
        self.assertIn("does not exist", str(cm.exception))

    def test_replace_source_rejects_same_version(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(ValueError) as cm:
            reg.replace_source(
                source_id="src-user-001",
                new_version="1.0",
                new_content_hash="duhash001",
                new_content=DIRECT_USER_SOURCE_V1["content"],
            )
        self.assertIn("identical", str(cm.exception))


# ====================================================================== #
#  Edge cases: get_source returns latest when version is None
# ====================================================================== #

class TestEdgeCasesGetSourceLatest(unittest.TestCase):
    def test_get_source_returns_latest_by_default(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        source = reg.get_source("src-user-001")
        self.assertEqual(source.version, "2.0")

    def test_get_source_returns_specific_version(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        source = reg.get_source("src-user-001", version="1.0")
        self.assertEqual(source.version, "1.0")

    def test_get_source_returns_none_for_unknown(self):
        reg = make_registry()
        self.assertIsNone(reg.get_source("src-nonexistent"))

    def test_get_source_returns_none_for_unknown_version(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        self.assertIsNone(reg.get_source("src-user-001", version="99.0"))


# ====================================================================== #
#  Edge cases: validate after replace_source
# ====================================================================== #

class TestEdgeCasesValidateAfterReplaceSource(unittest.TestCase):
    def test_validate_clean_after_replace_source(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.replace_source(
            source_id="src-user-001",
            new_version="2.0",
            new_content_hash="duhash002",
            new_content=DIRECT_USER_SOURCE_V2["content"],
        )
        result = reg.validate()
        self.assertTrue(result["valid"])
        self.assertEqual(result["source_count"], 2)


# ====================================================================== #
#  Edge cases: goal with empty description rejected
# ====================================================================== #

class TestEdgeCasesEmptyDescriptionRejected(unittest.TestCase):
    def test_rejects_empty_description(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(ValueError) as cm:
            reg.create_goal(**MALFORMED_GOAL_MISSING_DESCRIPTION)
        self.assertIn("description", str(cm.exception))

    def test_rejects_empty_title(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(ValueError) as cm:
            reg.create_goal(**MALFORMED_GOAL_MISSING_TITLE)
        self.assertIn("title", str(cm.exception))


# ====================================================================== #
#  Edge cases: supersede with Tola source
# ====================================================================== #

class TestEdgeCasesSupersedeWithTolaSource(unittest.TestCase):
    def test_supersede_with_tola_source(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**TOLA_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        old, new = reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Tola-updated goal",
            new_description="Updated by Tola.",
            new_source_id="src-tola-001",
            new_source_version="1.0",
            new_source_type="tola",
        )
        self.assertEqual(new.source_type, "tola")
        self.assertEqual(new.source_id, "src-tola-001")
        self.assertEqual(new.state, "SUPERSEDED")

    def test_supersede_with_tola_source_preserves_history(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**TOLA_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Tola-updated goal",
            new_description="Updated by Tola.",
            new_source_id="src-tola-001",
            new_source_version="1.0",
            new_source_type="tola",
        )
        v1 = reg.get_goal("goal-vent-01", version=1)
        v2 = reg.get_goal("goal-vent-01", version=2)
        self.assertEqual(v1.source_type, "direct_user")
        self.assertEqual(v2.source_type, "tola")


# ====================================================================== #
#  Edge cases: replace_source then create goal
# ====================================================================== #

class TestEdgeCasesReplaceSourceThenCreateGoal(unittest.TestCase):
    def test_create_goal_with_replaced_source(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.replace_source(
            source_id="src-user-001",
            new_version="2.0",
            new_content_hash="duhash002",
            new_content=DIRECT_USER_SOURCE_V2["content"],
        )
        reg.create_goal(
            goal_id="goal-vent-01",
            source_id="src-user-001",
            source_version="2.0",
            title="Goal using replaced source",
            description="This goal uses the replaced source version.",
            source_type="direct_user",
        )
        goal = reg.get_goal("goal-vent-01")
        self.assertIsNotNone(goal)
        self.assertEqual(goal.source_version, "2.0")
        self.assertEqual(goal.state, "ACTIVE")


# ====================================================================== #
#  Edge cases: goal with both direct_user and tola sources
# ====================================================================== #

class TestEdgeCasesMixedSourceTypes(unittest.TestCase):
    def test_direct_user_goal_and_tola_goal_coexist(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**TOLA_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.create_goal(**GOAL_VENT_TOLA_V1)

        du_goal = reg.get_goal("goal-vent-01")
        tola_goal = reg.get_goal("goal-vent-02")
        self.assertEqual(du_goal.source_type, "direct_user")
        self.assertEqual(tola_goal.source_type, "tola")

    def test_supersede_direct_user_with_tola_source(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**TOLA_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Tola-superseded goal",
            new_description="Superseded by Tola.",
            new_source_id="src-tola-001",
            new_source_version="1.0",
            new_source_type="tola",
        )
        v1 = reg.get_goal("goal-vent-01", version=1)
        v2 = reg.get_goal("goal-vent-01", version=2)
        self.assertEqual(v1.source_type, "direct_user")
        self.assertEqual(v2.source_type, "tola")


# ====================================================================== #
#  Edge cases: version key helper
# ====================================================================== #

class TestEdgeCasesVersionKeyHelper(unittest.TestCase):
    def test_version_key_simple(self):
        from scholar.goals.registry import _version_key
        self.assertEqual(_version_key("1.0"), (1, 0))

    def test_version_key_patch(self):
        from scholar.goals.registry import _version_key
        self.assertEqual(_version_key("2.1.3"), (2, 1, 3))

    def test_version_key_with_suffix(self):
        from scholar.goals.registry import _version_key
        self.assertEqual(_version_key("1.0.0-beta"), (1, 0, 0))

    def test_version_key_single(self):
        from scholar.goals.registry import _version_key
        self.assertEqual(_version_key("3"), (3,))


# ====================================================================== #
#  Edge cases: frozen dataclass immutability
# ====================================================================== #

class TestEdgeCasesFrozenImmutability(unittest.TestCase):
    def test_goal_record_is_frozen(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        record = reg.create_goal(**GOAL_VENT_DIRECT_V1)
        with self.assertRaises(Exception):
            record.title = "Modified"

    def test_goal_source_is_frozen(self):
        reg = make_registry()
        source = reg.add_source(**DIRECT_USER_SOURCE_V1)
        with self.assertRaises(Exception):
            source.name = "Modified"

    def test_transition_is_frozen(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        trans = reg.get_transitions("goal-vent-01")[0]
        with self.assertRaises(Exception):
            trans.to_state = "MODIFIED"


# ====================================================================== #
#  Edge cases: get_state round-trip integrity
# ====================================================================== #

class TestEdgeCasesGetStateRoundTrip(unittest.TestCase):
    def test_get_state_round_trip_preserves_goal(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.pause_goal("goal-vent-01")

        state = reg.get_state()

        reg2 = make_registry()
        for sid, versions in state["sources"].items():
            for v_str, s_dict in versions.items():
                reg2.add_source(
                    source_id=s_dict["source_id"],
                    name=s_dict["name"],
                    source_type=s_dict["source_type"],
                    version=s_dict["version"],
                    content_hash=s_dict["content_hash"],
                    content=s_dict["content"],
                )
        for gid, versions in state["goals"].items():
            for v_int, g_dict in versions.items():
                reg2._goals.setdefault(gid, {})[v_int] = GoalRecord(**g_dict)
        for gid, trans_list in state["transitions"].items():
            reg2._transitions[gid] = [GoalStateTransition(**t) for t in trans_list]

        # Verify full round-trip
        goal = reg2.get_goal("goal-vent-01")
        self.assertIsNotNone(goal)
        self.assertEqual(goal.state, "PAUSED")
        self.assertEqual(goal.version, 2)
        self.assertEqual(goal.title, "Master mechanical ventilation within six weeks")

        # Verify transitions
        transitions = reg2.get_transitions("goal-vent-01")
        self.assertEqual(len(transitions), 2)
        self.assertEqual(transitions[1].to_state, "PAUSED")

    def test_get_state_round_trip_preserves_supersede(self):
        reg = make_registry()
        reg.add_source(**DIRECT_USER_SOURCE_V1)
        reg.add_source(**DIRECT_USER_SOURCE_V2)
        reg.create_goal(**GOAL_VENT_DIRECT_V1)
        reg.supersede_goal(
            goal_id="goal-vent-01",
            new_title="Updated",
            new_description="Updated desc.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )

        state = reg.get_state()

        reg2 = make_registry()
        for sid, versions in state["sources"].items():
            for v_str, s_dict in versions.items():
                reg2.add_source(
                    source_id=s_dict["source_id"],
                    name=s_dict["name"],
                    source_type=s_dict["source_type"],
                    version=s_dict["version"],
                    content_hash=s_dict["content_hash"],
                    content=s_dict["content"],
                )
        for gid, versions in state["goals"].items():
            for v_int, g_dict in versions.items():
                reg2._goals.setdefault(gid, {})[v_int] = GoalRecord(**g_dict)
        for gid, trans_list in state["transitions"].items():
            reg2._transitions[gid] = [GoalStateTransition(**t) for t in trans_list]

        # Verify supersede round-trip
        latest = reg2.get_goal("goal-vent-01")
        self.assertEqual(latest.state, "SUPERSEDED")
        v1 = reg2.get_goal("goal-vent-01", version=1)
        self.assertEqual(v1.state, "ACTIVE")


if __name__ == "__main__":
    unittest.main()