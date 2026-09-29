"""Deterministic fixture tests for BlackboardClient. No network, no credentials."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from blackboard_client.client import BlackboardClient  # noqa: E402


class FakeTransport:
    """Injects canned responses in place of _request."""

    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def _request(self, method, path, body=None, params=None):
        self.calls.append((method, path, body, params))
        if self.fail:
            raise OSError("connection refused")
        return 201, ""


def make_client():
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    tmp.close()
    os.unlink(tmp.name)
    return BlackboardClient("https://example.supabase.co", "test-key", tmp.name), tmp.name


class WriteSuccessTest(unittest.TestCase):
    def test_write_success_returns_synced(self):
        client, _ = make_client()
        client._request = FakeTransport()._request
        status, detail = client.write("metrics", {"idempotency_key": "k1", "value": 1})
        self.assertEqual(status, "synced")
        self.assertEqual(detail, 201)
        self.assertEqual(client.outbox_count(), 0)

    def test_write_sends_upsert_params(self):
        client, _ = make_client()
        ft = FakeTransport()
        client._request = ft._request
        client.write("metrics", {"idempotency_key": "k1"})
        method, path, body, params = ft.calls[0]
        self.assertEqual((method, path), ("POST", "metrics"))
        self.assertEqual(params, {"on_conflict": "idempotency_key"})
        self.assertEqual(body, {"idempotency_key": "k1"})


class QueueFallbackTest(unittest.TestCase):
    def test_network_failure_queues_row(self):
        client, path = make_client()
        client._request = FakeTransport(fail=True)._request
        status, reason = client.write("tasks", {"idempotency_key": "k2", "name": "x"})
        self.assertEqual(status, "queued")
        self.assertIn("network-error", reason)
        self.assertEqual(client.outbox_count(), 1)
        self.assertEqual(client.outbox_count(synced=0), 1)

    def test_http_failure_queues_row(self):
        client, _ = make_client()
        ft = FakeTransport()

        def failing(method, path, body=None, params=None):
            return 429, "throttled"

        client._request = failing
        status, reason = client.write("goals", {"idempotency_key": "k3"})
        self.assertEqual(status, "queued")
        self.assertEqual(reason, "http-429")
        self.assertEqual(client.outbox_count(), 1)


class FlushTest(unittest.TestCase):
    def test_flush_replays_and_clears(self):
        client, _ = make_client()
        client._request = FakeTransport(fail=True)._request
        client.write("metrics", {"idempotency_key": "a", "v": 1})
        client.write("metrics", {"idempotency_key": "b", "v": 2})
        self.assertEqual(client.outbox_count(), 2)
        ft = FakeTransport()
        client._request = ft._request
        attempted, synced = client.flush()
        self.assertEqual((attempted, synced), (2, 2))
        self.assertEqual(client.outbox_count(), 0)
        self.assertEqual(len(ft.calls), 2)

    def test_flush_replay_dedup_safe(self):
        # Same key queued twice replays both times; server upsert keeps
        # one row, and each successful replay clears its outbox entry.
        client, _ = make_client()
        client._request = FakeTransport(fail=True)._request
        client.write("metrics", {"idempotency_key": "dup", "v": 1})
        client.write("metrics", {"idempotency_key": "dup", "v": 1})
        self.assertEqual(client.outbox_count(), 2)
        client._request = FakeTransport()._request
        attempted, synced = client.flush()
        self.assertEqual((attempted, synced), (2, 2))
        self.assertEqual(client.outbox_count(), 0)

    def test_flush_keeps_failed_rows(self):
        client, _ = make_client()
        client._request = FakeTransport(fail=True)._request
        client.write("metrics", {"idempotency_key": "a"})
        client.write("metrics", {"idempotency_key": "b"})

        def half_up(method, path, body=None, params=None):
            if body["idempotency_key"] == "a":
                return 201, ""
            raise OSError("still down")

        client._request = half_up
        attempted, synced = client.flush()
        self.assertEqual((attempted, synced), (2, 1))
        self.assertEqual(client.outbox_count(), 1)


class ReadTest(unittest.TestCase):
    def test_read_passthrough(self):
        client, _ = make_client()

        def fake_get(method, path, body=None, params=None):
            self.assertEqual((method, path), ("GET", "agents"))
            return 200, json.dumps([{"id": "a1"}])

        client._request = fake_get
        status, rows = client.read("agents")
        self.assertEqual(status, 200)
        self.assertEqual(rows, [{"id": "a1"}])

    def test_read_with_params(self):
        client, _ = make_client()
        ft = FakeTransport()
        ft._request_orig = ft._request

        def fake_get(method, path, body=None, params=None):
            ft.calls.append((method, path, body, params))
            return 200, "[]"

        client._request = fake_get
        client.read("metrics", params={"agent_id": "eq.growth"})
        self.assertEqual(ft.calls[0][3], {"agent_id": "eq.growth"})

    def test_read_http_error_returns_body(self):
        client, _ = make_client()

        def fake_get(method, path, body=None, params=None):
            return 404, "not found"

        client._request = fake_get
        status, body = client.read("metrics")
        self.assertEqual((status, body), (404, "not found"))


class ValidationTest(unittest.TestCase):
    def test_bad_table_rejected_on_write(self):
        client, _ = make_client()
        with self.assertRaises(ValueError):
            client.write("users", {"idempotency_key": "k"})
        self.assertEqual(client.outbox_count(), 0)

    def test_bad_table_rejected_on_read(self):
        client, _ = make_client()
        with self.assertRaises(ValueError):
            client.read("secrets")

    def test_missing_idempotency_key_rejected(self):
        client, _ = make_client()
        with self.assertRaises(ValueError):
            client.write("metrics", {"value": 1})
        self.assertEqual(client.outbox_count(), 0)

    def test_requires_base_url_and_key(self):
        with self.assertRaises(ValueError):
            BlackboardClient("", "key", ":memory:")
        with self.assertRaises(ValueError):
            BlackboardClient("https://example.supabase.co", "", ":memory:")


if __name__ == "__main__":
    unittest.main()