# Batch T24 -- Event-Driven Executive Proactivity
# test_t24_proactivity.py: QA T24 tests T24-01 through T24-08.

import unittest
from tola.proactivity.events import (
    WAKE_EVENTS,
    LOW_VALUE_EVENTS,
    AUTHORIZED_SOURCES,
    handle_event,
    WakeDecision,
)
from tola.proactivity.correlation import CorrelationChain


def make_event(event_id, event_type, source, payload, signature=None):
    e = {
        "event_id": event_id,
        "event_type": event_type,
        "source": source,
        "payload": payload,
    }
    if signature is not None:
        e["signature"] = signature
    return e


class TestT24Proactivity(unittest.TestCase):

    # T24-01: TASK_STALLED wakes Tola
    def test_t24_01_task_stalled_wakes(self):
        event = make_event("e01", "TASK_STALLED", "monitor", {"task": "t1"})
        decision = handle_event(event)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "WAKE")
        self.assertEqual(decision.event_type, "TASK_STALLED")

    # T24-02: EXPERIMENT_COMPLETED wakes Tola for review
    def test_t24_02_experiment_completed_wakes(self):
        event = make_event("e02", "EXPERIMENT_COMPLETED", "specialist", {"exp": "x1"})
        decision = handle_event(event)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "WAKE")
        self.assertEqual(decision.event_type, "EXPERIMENT_COMPLETED")

    # T24-03: RHYTHM_OVERLOAD wakes Tola
    def test_t24_03_rhythm_overload_wakes(self):
        event = make_event("e03", "RHYTHM_OVERLOAD", "rhythm", {"load": 0.95})
        decision = handle_event(event)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "WAKE")
        self.assertEqual(decision.event_type, "RHYTHM_OVERLOAD")

    # T24-04: USER_CORRECTION wakes and generates learning followup
    def test_t24_04_user_correction_wakes_with_learning(self):
        event = make_event("e04", "USER_CORRECTION", "user", {"correction": "fix"})
        decision = handle_event(event)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "WAKE")
        self.assertEqual(decision.followup, "LEARNING_OBSERVATION")

    # T24-05: Routine low-value event does not wake Tola
    def test_t24_05_low_value_no_wake(self):
        for etype in LOW_VALUE_EVENTS:
            event = make_event("lv-" + etype, etype, "monitor", {})
            decision = handle_event(event)
            self.assertIsNone(decision, f"Low-value {etype} should not wake")

    # T24-06: Duplicate event_id returns same decision, single logical action
    def test_t24_06_duplicate_event_dedup(self):
        registry = {}
        event = make_event("dup-01", "TASK_STALLED", "monitor", {"task": "t1"})
        d1 = handle_event(event, seen_registry=registry)
        d2 = handle_event(event, seen_registry=registry)
        self.assertIs(d1, d2)
        self.assertEqual(d1.action, "WAKE")

    # T24-07: Malformed and unauthorized events are rejected
    def test_t24_07_malformed_rejected(self):
        # Missing required fields
        for bad in [
            {},
            {"event_type": "TASK_STALLED"},
            {"event_id": "x", "source": "monitor"},
            {"event_id": "x", "event_type": "TASK_STALLED", "payload": {}},
        ]:
            d = handle_event(bad)
            self.assertIsNotNone(d)
            self.assertEqual(d.action, "REJECTED")

        # Unauthorized source
        event = make_event("unauth", "TASK_STALLED", "hacker", {})
        d = handle_event(event)
        self.assertIsNotNone(d)
        self.assertEqual(d.action, "REJECTED")

        # Invalid signature placeholder
        event = make_event("badsig", "TASK_STALLED", "monitor", {}, signature="")
        d = handle_event(event)
        self.assertIsNotNone(d)
        self.assertEqual(d.action, "REJECTED")

    # T24-08: Correlation chain remains traceable and idempotent
    def test_t24_08_correlation_chain_traceable(self):
        chain = CorrelationChain("chain-1")
        registry = {}

        e1 = make_event("c1", "TASK_STALLED", "monitor", {})
        d1 = handle_event(e1, seen_registry=registry)
        chain.attach("c1", d1)

        e2 = make_event("c2", "USER_CORRECTION", "user", {})
        d2 = handle_event(e2, seen_registry=registry)
        chain.attach("c2", d2)

        # Duplicate attach is idempotent
        chain.attach("c1", d1)

        trace = chain.trace()
        self.assertEqual(len(trace), 2)
        self.assertEqual(trace[0][0], "c1")
        self.assertEqual(trace[1][0], "c2")
        self.assertEqual(trace[0][1].action, "WAKE")
        self.assertEqual(trace[1][1].action, "WAKE")
        self.assertEqual(trace[1][1].followup, "LEARNING_OBSERVATION")

    # Determinism: same input always produces same decision
    def test_determinism(self):
        registry = {}
        event = make_event("det", "TASK_STALLED", "monitor", {"task": "t1"})
        d1 = handle_event(event, seen_registry=registry)
        d2 = handle_event(event, seen_registry=registry)
        self.assertIs(d1, d2)

    # All WAKE_EVENTS produce a decision (not None, not REJECTED)
    def test_all_wake_events_produce_decision(self):
        for etype in WAKE_EVENTS:
            event = make_event("w-" + etype, etype, "monitor", {})
            decision = handle_event(event)
            self.assertIsNotNone(decision)
            self.assertIn(decision.action, ("WAKE",))


if __name__ == "__main__":
    unittest.main()
