"""
Batch S6 -- Scholar Event Consumer QA Tests (S6-01..S6-06 + edge cases).
Plain ASCII. Python 3 stdlib only.
"""

import unittest

from scholar.intensiq.event_outbox import EventOutbox
from scholar.events.consumer import (
    EventConsumer,
    RESULT_PROCESSED,
    RESULT_DUPLICATE,
    RESULT_QUARANTINED,
    RESULT_OUT_OF_ORDER,
    validate_event,
)
from scholar.fixtures.consumer import (
    CONSUMER_STUDY_SESSION,
    CONSUMER_PRACTICE_UNIT,
    CONSUMER_ASSESSMENT,
    CONSUMER_REASONING,
    DUPLICATE_CONSUMER_EVENT,
    OUT_OF_ORDER_CONSUMER_EVENT,
    MALFORMED_MISSING_EVENT_ID,
    MALFORMED_MISSING_EVENT_TYPE,
    MALFORMED_UNKNOWN_EVENT_TYPE,
    MALFORMED_EMPTY_EVENT_ID,
    MALFORMED_EMPTY_COURSE_ID,
    MALFORMED_MISSING_SCHEMA_VERSION,
    MALFORMED_NON_STRING_EVENT_ID,
    MALFORMED_MISSING_OCCURRED_AT,
    MALFORMED_NOT_A_DICT,
    INTERLEAVED_DUPLICATE_A,
    INTERLEAVED_DUPLICATE_B,
    make_consumer_event,
)


# ====================================================================== #
#  Helpers
# ====================================================================== #

def _fake_now():
    """Deterministic timestamp for testing."""
    from datetime import datetime
    return datetime(2026, 9, 30, 12, 0, 0)


def _make_outbox(*consumer_events):
    """Create an EventOutbox pre-loaded with consumer events.

    Strips event_id from each event dict before calling append(),
    since EventOutbox generates its own event_id.
    """
    outbox = EventOutbox(clock=_fake_now)
    for ev in consumer_events:
        ev_no_id = {k: v for k, v in ev.items() if k != "event_id"}
        outbox.append(**ev_no_id)
    return outbox


class _MockOutbox:
    """Minimal mock outbox for testing with specific event dicts."""

    def __init__(self, events):
        self._events = list(events)

    def replay(self, cursor=None, limit=None):
        if cursor is not None:
            start = 0
            for i, ev in enumerate(self._events):
                if ev.get("event_id") == cursor:
                    start = i + 1
                    break
            sliced = self._events[start:]
        else:
            sliced = list(self._events)

        if limit is not None:
            sliced = sliced[:limit]

        next_cursor = None
        if sliced:
            next_cursor = sliced[-1].get("event_id")

        return sliced, next_cursor


class _ProcessingTracker:
    def __init__(self):
        self.processed = []

    def __call__(self, event):
        self.processed.append(event)


# ====================================================================== #
#  S6-01 Single event: processed once
# ====================================================================== #

class TestS6_01_SingleEventProcessedOnce(unittest.TestCase):
    def test_single_event_processed_once(self):
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        result = consumer.poll_and_process()

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["poll_count"], 1)
        self.assertEqual(len(tracker.processed), 1)
        self.assertEqual(
            tracker.processed[0]["event_type"],
            "study_session.recorded",
        )

    def test_cursor_advances_after_processing(self):
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()

        self.assertIsNotNone(consumer.cursor)

    def test_subsequent_poll_returns_no_new_events(self):
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()
        result2 = consumer.poll_and_process()

        self.assertEqual(result2["poll_count"], 0)
        self.assertEqual(result2["processed"], 0)


# ====================================================================== #
#  S6-02 Duplicate: one logical update
# ====================================================================== #

class TestS6_02_DuplicateOneLogicalUpdate(unittest.TestCase):
    def test_duplicate_event_not_processed_twice(self):
        """Duplicate by event_id across polls produces one effect."""
        # Use process_event directly to control event_ids
        tracker = _ProcessingTracker()
        consumer = EventConsumer(
            outbox=EventOutbox(clock=_fake_now),
            processor=tracker,
        )

        r1 = consumer.process_event(dict(CONSUMER_STUDY_SESSION))
        self.assertEqual(r1, RESULT_PROCESSED)

        r2 = consumer.process_event(dict(CONSUMER_STUDY_SESSION))
        self.assertEqual(r2, RESULT_DUPLICATE)

        self.assertEqual(len(tracker.processed), 1)

    def test_duplicate_by_event_id_across_polls(self):
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()
        consumer.reset_cursor()
        consumer.poll_and_process()
        consumer.poll_and_process()

        self.assertEqual(len(tracker.processed), 1)

    def test_double_commit_no_double_effect(self):
        """If cursor is committed twice (re-poll after crash),
        duplicate events still produce exactly one logical effect."""
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()
        consumer.reset_cursor()
        consumer.poll_and_process()

        self.assertEqual(len(tracker.processed), 1)


# ====================================================================== #
#  S6-03 Crash before cursor commit: safe replay
# ====================================================================== #

class TestS6_03_CrashBeforeCursorCommitSafeReplay(unittest.TestCase):
    def test_crash_before_commit_event_replayed(self):
        """If the consumer crashes before committing the cursor,
        on restart the event is replayed and processed again."""
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        # Process event but don't commit cursor (simulate crash)
        event = outbox.replay()[0][0]
        tracker(event)
        self.assertIsNone(consumer.cursor)

        # On restart: cursor is None, replay starts from beginning
        consumer2 = EventConsumer(outbox=outbox, processor=tracker)
        r = consumer2.poll_and_process()

        self.assertEqual(r["processed"], 1)
        # Safe replay: event is processed again (no data loss)
        self.assertEqual(len(tracker.processed), 2)

    def test_no_events_lost_on_crash_replay(self):
        """All events must be retrievable after a crash replay."""
        outbox = _make_outbox(
            CONSUMER_STUDY_SESSION,
            CONSUMER_PRACTICE_UNIT,
            CONSUMER_ASSESSMENT,
        )
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()
        self.assertEqual(len(tracker.processed), 3)

        consumer.reset_cursor()

        consumer2 = EventConsumer(outbox=outbox, processor=tracker)
        consumer2.poll_and_process()

        self.assertEqual(len(tracker.processed), 6)

    def test_deduplication_prevents_double_effect_on_replay(self):
        """After crash replay with state recovery, dedup prevents
        duplicate logical effect."""
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()
        self.assertEqual(len(tracker.processed), 1)

        consumer.reset_cursor()

        consumer2 = EventConsumer(outbox=outbox, processor=tracker)
        consumer2._processed_ids = set(consumer.processed_ids)
        consumer2._last_occurred_at = consumer.last_occurred_at

        r = consumer2.poll_and_process()

        self.assertEqual(r["duplicates"], 1)
        self.assertEqual(r["processed"], 0)
        self.assertEqual(len(tracker.processed), 1)


# ====================================================================== #
#  S6-04 Crash after commit: no reprocessing
# ====================================================================== #

class TestS6_04_CrashAfterCommitNoReprocessing(unittest.TestCase):
    def test_event_committed_not_reprocessed(self):
        """If cursor is committed after processing, crash after commit
        means the event is NOT reprocessed on restart."""
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()
        committed_cursor = consumer.cursor
        self.assertEqual(len(tracker.processed), 1)

        consumer2 = EventConsumer(outbox=outbox, processor=tracker)
        consumer2._cursor = committed_cursor
        consumer2._processed_ids = set(consumer.processed_ids)
        consumer2._last_occurred_at = consumer.last_occurred_at

        r = consumer2.poll_and_process()

        self.assertEqual(r["poll_count"], 0)
        self.assertEqual(r["processed"], 0)
        self.assertEqual(len(tracker.processed), 1)

    def test_multiple_events_committed_no_reprocessing(self):
        """All committed events are skipped on restart."""
        outbox = _make_outbox(
            CONSUMER_STUDY_SESSION,
            CONSUMER_PRACTICE_UNIT,
            CONSUMER_ASSESSMENT,
        )
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()
        committed_cursor = consumer.cursor
        self.assertEqual(len(tracker.processed), 3)

        consumer2 = EventConsumer(outbox=outbox, processor=tracker)
        consumer2._cursor = committed_cursor
        consumer2._processed_ids = set(consumer.processed_ids)
        consumer2._last_occurred_at = consumer.last_occurred_at

        r = consumer2.poll_and_process()

        self.assertEqual(r["poll_count"], 0)
        self.assertEqual(len(tracker.processed), 3)


# ====================================================================== #
#  S6-05 Malformed event: rejected/quarantined
# ====================================================================== #

class TestS6_05_MalformedEventRejectedQuarantined(unittest.TestCase):
    def _mock_outbox_with(self, *events):
        return _MockOutbox(list(events))

    def test_missing_event_id_quarantined(self):
        outbox = self._mock_outbox_with(MALFORMED_MISSING_EVENT_ID)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["quarantined"], 1)
        self.assertEqual(r["processed"], 0)
        self.assertEqual(len(consumer.quarantined), 1)

    def test_missing_event_type_quarantined(self):
        outbox = self._mock_outbox_with(MALFORMED_MISSING_EVENT_TYPE)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["quarantined"], 1)
        self.assertEqual(r["processed"], 0)

    def test_unknown_event_type_quarantined(self):
        outbox = self._mock_outbox_with(MALFORMED_UNKNOWN_EVENT_TYPE)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["quarantined"], 1)
        self.assertEqual(r["processed"], 0)

    def test_empty_event_id_quarantined(self):
        outbox = self._mock_outbox_with(MALFORMED_EMPTY_EVENT_ID)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["quarantined"], 1)

    def test_empty_course_id_quarantined(self):
        outbox = self._mock_outbox_with(MALFORMED_EMPTY_COURSE_ID)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["quarantined"], 1)

    def test_missing_schema_version_quarantined(self):
        outbox = self._mock_outbox_with(MALFORMED_MISSING_SCHEMA_VERSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["quarantined"], 1)

    def test_non_string_event_id_quarantined(self):
        outbox = self._mock_outbox_with(MALFORMED_NON_STRING_EVENT_ID)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["quarantined"], 1)

    def test_missing_occurred_at_quarantined(self):
        outbox = self._mock_outbox_with(MALFORMED_MISSING_OCCURRED_AT)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["quarantined"], 1)

    def test_not_a_dict_quarantined(self):
        """A non-dict event (e.g. from a deserialization error) is quarantined."""
        errors = validate_event(MALFORMED_NOT_A_DICT)
        self.assertTrue(len(errors) > 0)

    def test_quarantined_events_not_in_processed_ids(self):
        outbox = self._mock_outbox_with(MALFORMED_MISSING_EVENT_ID)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()

        self.assertEqual(len(consumer.processed_ids), 0)

    def test_valid_event_after_quarantined_event(self):
        """A quarantined event should not block subsequent valid events."""
        outbox = self._mock_outbox_with(
            MALFORMED_MISSING_EVENT_ID,
            CONSUMER_STUDY_SESSION,
        )
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["quarantined"], 1)
        self.assertEqual(r["processed"], 1)
        self.assertEqual(len(tracker.processed), 1)

    def test_quarantine_recovery_retry_still_invalid(self):
        """Quarantined events that are still invalid remain quarantined."""
        outbox = self._mock_outbox_with(MALFORMED_MISSING_EVENT_ID)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r1 = consumer.poll_and_process()
        self.assertEqual(r1["quarantined"], 1)

        r_retry = consumer.retry_quarantined()
        self.assertEqual(r_retry["still_quarantined"], 1)

    def test_quarantine_retry_with_valid_event(self):
        """If a quarantined event becomes valid, retry_quarantined can process it."""
        outbox = EventOutbox(clock=_fake_now)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer._quarantined.append(
            {"event": dict(CONSUMER_STUDY_SESSION), "errors": []}
        )

        r = consumer.retry_quarantined()
        self.assertEqual(r["processed"], 1)
        self.assertEqual(len(tracker.processed), 1)


# ====================================================================== #
#  S6-06 Out-of-order event: handled safely
# ====================================================================== #

class TestS6_06_OutOfOrderEventHandledSafely(unittest.TestCase):
    def test_out_of_order_event_still_processed(self):
        """Out-of-order events are processed (safe replay) but tracked."""
        outbox = _make_outbox(
            CONSUMER_ASSESSMENT,  # occurred_at 11:00
            OUT_OF_ORDER_CONSUMER_EVENT,  # occurred_at 09:00
        )
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["processed"], 2)
        self.assertEqual(r["out_of_order"], 1)
        self.assertEqual(len(tracker.processed), 2)
        self.assertEqual(len(consumer.out_of_order), 1)

    def test_out_of_order_event_not_lost(self):
        """Out-of-order events must not be silently dropped."""
        outbox = _make_outbox(
            CONSUMER_ASSESSMENT,
            OUT_OF_ORDER_CONSUMER_EVENT,
        )
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()

        # Both events should be in processed_ids
        # (outbox generates its own event_ids, so we check
        # that the count matches rather than specific IDs)
        self.assertEqual(len(consumer.processed_ids), 2)
        # Verify the out-of-order event is tracked
        self.assertEqual(len(consumer.out_of_order), 1)
        # The out-of-order event is the one with occurred_at 09:00
        ooo_in_outbox = consumer.out_of_order[0]
        self.assertEqual(ooo_in_outbox["occurred_at"], "2026-09-30T09:00:00")

    def test_out_of_order_detection_tracks_last_occurred_at(self):
        """last_occurred_at should reflect the latest chronological time."""
        outbox = _make_outbox(
            CONSUMER_ASSESSMENT,  # 11:00
            OUT_OF_ORDER_CONSUMER_EVENT,  # 09:00
        )
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()

        self.assertEqual(consumer.last_occurred_at, "2026-09-30T11:00:00")

    def test_in_order_events_no_out_of_order_flag(self):
        """In-order events should not be flagged as out-of-order."""
        outbox = _make_outbox(
            CONSUMER_STUDY_SESSION,  # 10:00
            CONSUMER_PRACTICE_UNIT,  # 10:30
            CONSUMER_ASSESSMENT,  # 11:00
        )
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["out_of_order"], 0)
        self.assertEqual(len(consumer.out_of_order), 0)

    def test_out_of_order_with_gap(self):
        """An event significantly earlier than the last processed
        event is still handled safely."""
        outbox = _make_outbox(CONSUMER_ASSESSMENT)  # 11:00
        early_event = make_consumer_event(
            event_id="evt-early-1",
            occurred_at="2026-09-30T08:00:00",
        )
        ev_no_id = {k: v for k, v in early_event.items() if k != "event_id"}
        outbox.append(**ev_no_id)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["processed"], 2)
        self.assertEqual(r["out_of_order"], 1)


# ====================================================================== #
#  Edge cases
# ====================================================================== #

class TestEdgeCasesInterleavedDuplicates(unittest.TestCase):
    def test_interleaved_duplicate_across_polls(self):
        """Duplicate events interleaved with new events across polls."""
        # Use process_event directly to control event_ids
        tracker = _ProcessingTracker()
        consumer = EventConsumer(
            outbox=EventOutbox(clock=_fake_now),
            processor=tracker,
        )

        r1 = consumer.process_event(dict(INTERLEAVED_DUPLICATE_A))
        self.assertEqual(r1, RESULT_PROCESSED)

        r2 = consumer.process_event(dict(CONSUMER_PRACTICE_UNIT))
        self.assertEqual(r2, RESULT_PROCESSED)

        r3 = consumer.process_event(dict(INTERLEAVED_DUPLICATE_B))
        self.assertEqual(r3, RESULT_DUPLICATE)

        self.assertEqual(len(tracker.processed), 2)

    def test_interleaved_duplicate_with_cursor_reset(self):
        """After cursor reset, interleaved duplicates are still deduplicated."""
        tracker = _ProcessingTracker()
        consumer = EventConsumer(
            outbox=EventOutbox(clock=_fake_now),
            processor=tracker,
        )

        consumer.process_event(dict(INTERLEAVED_DUPLICATE_A))
        consumer.process_event(dict(CONSUMER_PRACTICE_UNIT))

        consumer.reset_cursor()

        # Simulate replay via process_event
        r1 = consumer.process_event(dict(INTERLEAVED_DUPLICATE_A))
        r2 = consumer.process_event(dict(CONSUMER_PRACTICE_UNIT))

        self.assertEqual(r1, RESULT_DUPLICATE)
        self.assertEqual(r2, RESULT_DUPLICATE)
        self.assertEqual(len(tracker.processed), 2)


class TestEdgeCasesEmptyAndBoundary(unittest.TestCase):
    def test_empty_outbox_returns_zero_counts(self):
        outbox = EventOutbox(clock=_fake_now)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["poll_count"], 0)
        self.assertEqual(r["processed"], 0)
        self.assertEqual(r["duplicates"], 0)
        self.assertEqual(r["quarantined"], 0)
        self.assertEqual(r["out_of_order"], 0)

    def test_consumer_with_no_processor(self):
        """Consumer with a no-op processor should still advance cursor."""
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["processed"], 1)
        self.assertIsNotNone(consumer.cursor)

    def test_limit_parameter_respected(self):
        outbox = EventOutbox(clock=_fake_now)
        for i in range(10):
            ev = make_consumer_event(
                event_id=f"evt-limit-{i}",
                occurred_at=f"2026-09-30T10:{i:02d}:00",
            )
            ev_no_id = {k: v for k, v in ev.items() if k != "event_id"}
            outbox.append(**ev_no_id)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process(limit=3)

        self.assertEqual(r["poll_count"], 3)
        self.assertEqual(r["processed"], 3)
        self.assertEqual(len(tracker.processed), 3)

    def test_cursor_none_starts_from_beginning(self):
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        self.assertIsNone(consumer.cursor)
        r = consumer.poll_and_process()

        self.assertEqual(r["processed"], 1)


class TestEdgeCasesProcessingFailure(unittest.TestCase):
    def test_processor_exception_dead_letters_event(self):
        """If the processor raises, the event is dead-lettered
        (added to processed_ids) so it is not retried infinitely."""
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()

        def failing_processor(event):
            tracker.processed.append(event)
            raise RuntimeError("simulated processing failure")

        consumer = EventConsumer(outbox=outbox, processor=failing_processor)

        r = consumer.poll_and_process()

        self.assertEqual(r["processed"], 0)
        self.assertEqual(len(r["errors"]), 1)
        # Event is dead-lettered (in processed_ids)
        self.assertEqual(len(consumer.processed_ids), 1)

    def test_processor_failure_event_not_retried(self):
        """After a processing failure, the event is not retried
        on subsequent polls (dead-lettered)."""
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()

        def failing_processor(event):
            raise RuntimeError("simulated processing failure")

        consumer = EventConsumer(outbox=outbox, processor=failing_processor)

        r1 = consumer.poll_and_process()
        self.assertEqual(r1["processed"], 0)

        r2 = consumer.poll_and_process()
        self.assertEqual(r2["poll_count"], 0)

    def test_processor_failure_does_not_duplicate_effect(self):
        """A processor failure should not cause duplicate logical effects."""
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()

        call_count = [0]

        def counting_processor(event):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("first attempt fails")
            tracker.processed.append(event)

        consumer = EventConsumer(outbox=outbox, processor=counting_processor)

        r1 = consumer.poll_and_process()
        self.assertEqual(r1["processed"], 0)

        r2 = consumer.poll_and_process()
        self.assertEqual(r2["poll_count"], 0)
        # Tracker should NOT have received the event
        self.assertEqual(len(tracker.processed), 0)


class TestEdgeCasesQuarantineRecovery(unittest.TestCase):
    def test_quarantine_cleared_after_successful_retry(self):
        outbox = EventOutbox(clock=_fake_now)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer._quarantined.append(
            {"event": dict(CONSUMER_STUDY_SESSION), "errors": []}
        )

        r = consumer.retry_quarantined()
        self.assertEqual(r["processed"], 1)
        self.assertEqual(len(consumer.quarantined), 0)

    def test_quarantine_retry_skips_still_invalid(self):
        outbox = EventOutbox(clock=_fake_now)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer._quarantined.append(
            {"event": dict(MALFORMED_MISSING_EVENT_ID), "errors": ["missing event_id"]}
        )

        r = consumer.retry_quarantined()
        self.assertEqual(r["still_quarantined"], 1)
        self.assertEqual(r["processed"], 0)

    def test_quarantine_retry_skips_duplicates(self):
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()

        # Use the actual event_id from the processed event
        processed_event_id = next(iter(consumer.processed_ids))
        quarantined_event = dict(CONSUMER_STUDY_SESSION)
        quarantined_event["event_id"] = processed_event_id
        consumer._quarantined.append(
            {"event": quarantined_event, "errors": []}
        )

        r = consumer.retry_quarantined()
        self.assertEqual(r["duplicates"], 1)
        self.assertEqual(r["processed"], 0)


class TestEdgeCasesDoubleCommit(unittest.TestCase):
    def test_double_commit_same_cursor_no_effect(self):
        """Committing the same cursor twice is a no-op."""
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()
        cursor_after_first = consumer.cursor

        consumer.commit_cursor(cursor_after_first)

        self.assertEqual(consumer.cursor, cursor_after_first)

    def test_commit_cursor_only_advances(self):
        """commit_cursor never moves the cursor backward."""
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()
        forward_cursor = consumer.cursor

        consumer.commit_cursor(None)
        self.assertEqual(consumer.cursor, forward_cursor)

    def test_commit_cursor_none_is_noop(self):
        outbox = EventOutbox(clock=_fake_now)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.commit_cursor(None)
        self.assertIsNone(consumer.cursor)


class TestEdgeCasesStateSerialization(unittest.TestCase):
    def test_get_state_returns_complete_state(self):
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()

        state = consumer.get_state()
        self.assertIn("cursor", state)
        self.assertIn("processed_event_ids", state)
        self.assertIn("last_occurred_at", state)
        self.assertIn("quarantined_count", state)
        self.assertIn("out_of_order_count", state)

    def test_restore_state_restores_cursor_and_ids(self):
        outbox = _make_outbox(CONSUMER_STUDY_SESSION)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()

        state = consumer.get_state()

        consumer2 = EventConsumer(outbox=outbox, processor=tracker)
        consumer2.restore_state(state)

        self.assertEqual(consumer2.cursor, consumer.cursor)
        self.assertEqual(consumer2.processed_ids, consumer.processed_ids)
        self.assertEqual(consumer2.last_occurred_at, consumer.last_occurred_at)

    def test_restore_state_does_not_restore_quarantine(self):
        """Quarantine log is not restored from state (operational only)."""
        outbox = _make_outbox(MALFORMED_MISSING_EVENT_ID)
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        consumer.poll_and_process()

        state = consumer.get_state()

        consumer2 = EventConsumer(outbox=outbox, processor=tracker)
        consumer2.restore_state(state)

        self.assertEqual(len(consumer2.quarantined), 0)


class TestEdgeCasesValidateEvent(unittest.TestCase):
    def test_validate_valid_event_returns_empty_list(self):
        errors = validate_event(CONSUMER_STUDY_SESSION)
        self.assertEqual(errors, [])

    def test_validate_missing_field_returns_error(self):
        errors = validate_event(MALFORMED_MISSING_EVENT_ID)
        self.assertTrue(any("event_id" in e for e in errors))

    def test_validate_unknown_event_type_returns_error(self):
        errors = validate_event(MALFORMED_UNKNOWN_EVENT_TYPE)
        self.assertTrue(any("event_type" in e for e in errors))

    def test_validate_not_a_dict_returns_error(self):
        errors = validate_event(MALFORMED_NOT_A_DICT)
        self.assertTrue(len(errors) > 0)

    def test_validate_empty_string_event_id_returns_error(self):
        errors = validate_event(MALFORMED_EMPTY_EVENT_ID)
        self.assertTrue(any("event_id" in e for e in errors))

    def test_validate_non_string_event_id_returns_error(self):
        errors = validate_event(MALFORMED_NON_STRING_EVENT_ID)
        self.assertTrue(any("event_id" in e for e in errors))

    def test_validate_empty_course_id_returns_error(self):
        errors = validate_event(MALFORMED_EMPTY_COURSE_ID)
        self.assertTrue(any("course_id" in e for e in errors))


# ====================================================================== #
#  Integration: full consumer lifecycle
# ====================================================================== #

class TestIntegrationFullConsumerLifecycle(unittest.TestCase):
    def test_full_lifecycle_poll_process_commit(self):
        """Simulate a full consumer lifecycle: poll, process, commit,
        crash, replay, dedup, complete."""
        outbox = _make_outbox(
            CONSUMER_STUDY_SESSION,
            CONSUMER_PRACTICE_UNIT,
            CONSUMER_ASSESSMENT,
        )
        tracker = _ProcessingTracker()
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r1 = consumer.poll_and_process()
        self.assertEqual(r1["processed"], 3)
        self.assertEqual(len(tracker.processed), 3)
        self.assertIsNotNone(consumer.cursor)

        # Simulate crash and restart with state recovery
        consumer2 = EventConsumer(outbox=outbox, processor=tracker)
        consumer2.restore_state(consumer.get_state())

        r2 = consumer2.poll_and_process()
        self.assertEqual(r2["poll_count"], 0)
        self.assertEqual(len(tracker.processed), 3)

        # New event arrives
        new_event = make_consumer_event(
            event_id="evt-new-1",
            occurred_at="2026-09-30T12:00:00",
        )
        ev_no_id = {k: v for k, v in new_event.items() if k != "event_id"}
        outbox.append(**ev_no_id)

        r3 = consumer2.poll_and_process()
        self.assertEqual(r3["processed"], 1)
        self.assertEqual(len(tracker.processed), 4)

    def test_mixed_valid_and_malformed_events(self):
        """A poll containing both valid and malformed events."""
        tracker = _ProcessingTracker()
        # Use mock outbox since malformed events can't go into EventOutbox
        events = [
            dict(CONSUMER_STUDY_SESSION),
            dict(MALFORMED_MISSING_EVENT_ID),
            dict(CONSUMER_PRACTICE_UNIT),
            dict(MALFORMED_UNKNOWN_EVENT_TYPE),
        ]
        outbox = _MockOutbox(events)
        consumer = EventConsumer(outbox=outbox, processor=tracker)

        r = consumer.poll_and_process()

        self.assertEqual(r["processed"], 2)
        self.assertEqual(r["quarantined"], 2)
        self.assertEqual(len(tracker.processed), 2)
        self.assertEqual(len(consumer.quarantined), 2)

    def test_all_s6_scenarios_together(self):
        """Comprehensive integration: exercise all S6 scenarios in one test."""
        tracker = _ProcessingTracker()
        consumer = EventConsumer(
            outbox=EventOutbox(clock=_fake_now),
            processor=tracker,
        )

        # 1. Process a single event (S6-01)
        r1 = consumer.process_event(dict(CONSUMER_STUDY_SESSION))
        self.assertEqual(r1, RESULT_PROCESSED)

        # 2. Replay: duplicate detected (S6-02)
        r2 = consumer.process_event(dict(CONSUMER_STUDY_SESSION))
        self.assertEqual(r2, RESULT_DUPLICATE)
        self.assertEqual(len(tracker.processed), 1)

        # 3. Add more events
        r3 = consumer.process_event(dict(CONSUMER_PRACTICE_UNIT))
        r4 = consumer.process_event(dict(CONSUMER_ASSESSMENT))
        self.assertEqual(r3, RESULT_PROCESSED)
        self.assertEqual(r4, RESULT_PROCESSED)
        self.assertEqual(len(tracker.processed), 3)

        # 4. Add malformed event (S6-05)
        r5 = consumer.process_event(dict(MALFORMED_MISSING_EVENT_ID))
        self.assertEqual(r5, RESULT_QUARANTINED)

        # 5. Add out-of-order event (S6-06)
        # Set last_occurred_at to a later time so the
        # out-of-order detection triggers
        consumer._last_occurred_at = "2026-09-30T12:00:00"
        ooo = dict(OUT_OF_ORDER_CONSUMER_EVENT)
        r6 = consumer.process_event(ooo)
        # process_event returns RESULT_PROCESSED even for
        # out-of-order events — they are still processed
        self.assertEqual(r6, RESULT_PROCESSED)
        # But the out-of-order flag is set
        self.assertEqual(len(consumer.out_of_order), 1)
        self.assertEqual(len(tracker.processed), 4)

        # 6. Verify dedup still works after all this
        r7 = consumer.process_event(dict(CONSUMER_STUDY_SESSION))
        self.assertEqual(r7, RESULT_DUPLICATE)
        self.assertEqual(len(tracker.processed), 4)


if __name__ == "__main__":
    unittest.main()