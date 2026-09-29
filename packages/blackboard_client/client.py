"""BlackboardClient: Supabase-first upsert, SQLite outbox fallback.

Design (agreed with Habeeb 2026-09-29):
- Supabase is the source of truth. Local SQLite is a backup/outbox only.
- write(): single attempt against PostgREST; on any failure the row is
  queued locally with its idempotency key and marked unsynced.
- flush(): replays queued rows through the same upsert path. Safe on
  replay because upsert is keyed on idempotency_key.
- read(): simple REST GET with query params.
- No background threads, no blocking retry loops.

Credentials are passed in by the caller (base_url, api_key). This module
never reads env files or secrets stores. Table names are restricted to
the 15 Blackboard tables defined in the v1 migration.
"""

import json
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

ALLOWED_TABLES = frozenset(
    [
        "agents",
        "projects",
        "goals",
        "tasks",
        "task_dependencies",
        "task_runs",
        "decisions",
        "approvals",
        "metrics",
        "schedule_constraints",
        "agent_events",
        "model_runs",
        "external_refs",
        "skill_registry",
        "skill_evaluations",
    ]
)

_OUTBOX_SCHEMA = """
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    synced INTEGER NOT NULL DEFAULT 0
)
"""


class BlackboardClient:
    def __init__(self, base_url, api_key, outbox_path):
        if not base_url or not api_key:
            raise ValueError("base_url and api_key are required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.outbox_path = outbox_path
        self._init_outbox()

    # -- transport ------------------------------------------------------

    def _request(self, method, path, body=None, params=None):
        """Single HTTP attempt. Returns (status, body_text).

        Overridden in tests by patching this method.
        """
        url = "{0}/rest/v1/{1}".format(self.base_url, path)
        if params:
            url = url + "?" + urllib.parse.urlencode(params)
        data = None
        headers = {
            "apikey": self.api_key,
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Prefer"] = "resolution=merge-duplicates"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")
        # urllib.error.URLError and socket errors propagate: connection
        # failure means Supabase is unreachable, which callers treat as
        # a queue trigger via the exception handler in write().

    # -- outbox ---------------------------------------------------------

    def _init_outbox(self):
        conn = sqlite3.connect(self.outbox_path)
        try:
            conn.executescript(_OUTBOX_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def _queue(self, table, idempotency_key, row):
        conn = sqlite3.connect(self.outbox_path)
        try:
            conn.execute(
                "INSERT INTO outbox (table_name, idempotency_key, payload)"
                " VALUES (?, ?, ?)",
                (table, idempotency_key, json.dumps(row, sort_keys=True)),
            )
            conn.commit()
        finally:
            conn.close()

    def outbox_count(self, synced=None):
        conn = sqlite3.connect(self.outbox_path)
        try:
            if synced is None:
                cur = conn.execute("SELECT COUNT(*) FROM outbox")
            else:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM outbox WHERE synced = ?", (synced,)
                )
            return cur.fetchone()[0]
        finally:
            conn.close()

    # -- public API -----------------------------------------------------

    def write(self, table, row):
        """Upsert one row. Returns ("synced", status) or ("queued", reason).

        The row must carry an idempotency_key field.
        """
        if table not in ALLOWED_TABLES:
            raise ValueError("unknown table: {0}".format(table))
        key = row.get("idempotency_key")
        if not key:
            raise ValueError("row must contain idempotency_key")
        params = {"on_conflict": "idempotency_key"}
        try:
            status, _ = self._request(
                "POST", table, body=row, params=params
            )
        except Exception as exc:  # network unreachable
            self._queue(table, key, row)
            return ("queued", "network-error: {0}".format(type(exc).__name__))
        if 200 <= status < 300:
            return ("synced", status)
        self._queue(table, key, row)
        return ("queued", "http-{0}".format(status))

    def flush(self, limit=None):
        """Replay queued rows. Returns (attempted, synced) counts.

        Successful rows are removed from the outbox. Failed rows stay
        queued for the next flush. Replay-safe: upsert semantics mean
        a row already applied has no duplicate effect.
        """
        conn = sqlite3.connect(self.outbox_path)
        try:
            rows = conn.execute(
                "SELECT id, table_name, idempotency_key, payload FROM outbox"
                " WHERE synced = 0 ORDER BY id"
            ).fetchall()
        finally:
            conn.close()
        if limit is not None:
            rows = rows[:limit]
        attempted = len(rows)
        synced = 0
        for row_id, table, _key, payload in rows:
            try:
                status, _ = self._request(
                    "POST", table, body=json.loads(payload),
                    params={"on_conflict": "idempotency_key"},
                )
            except Exception:
                continue
            if 200 <= status < 300:
                conn = sqlite3.connect(self.outbox_path)
                try:
                    conn.execute("DELETE FROM outbox WHERE id = ?", (row_id,))
                    conn.commit()
                finally:
                    conn.close()
                synced += 1
        return (attempted, synced)

    def read(self, table, params=None):
        """GET rows from a Blackboard table. Returns (status, rows)."""
        if table not in ALLOWED_TABLES:
            raise ValueError("unknown table: {0}".format(table))
        status, body = self._request("GET", table, params=params)
        if 200 <= status < 300:
            return (status, json.loads(body) if body else [])
        return (status, body)