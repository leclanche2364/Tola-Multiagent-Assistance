"""Daily Synthesis persistence — blackboard-style REST POST with idempotency keys.

Follows the same pattern as packages/blackboard_client:
- Credentials passed by caller, never read from env inside the module.
- Supabase is the primary target; degraded mode returns persistence_unavailable.
- No SQLite fallback (per Batch 1 spec).
- Idempotency via uuid5 namespace "daily-synthesis".
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid as _uuid
from typing import Any, Optional

from agents.daily_synthesis.contracts import validate_payload

NAMESPACE = _uuid.UUID("b5a0e8a0-1a2b-3c4d-5e6f-7a8b9c0d1e2f")  # daily-synthesis namespace


class PersistenceUnavailable(RuntimeError):
    """Raised when Supabase is unreachable and no fallback is available."""


class DailySynthesisPersistence:
    """Blackboard-style persistence for Daily Synthesis v1.2 payloads."""

    ALLOWED_TABLES = frozenset([
        "handoffs",
        "briefs",
        "conflicts",
        "outcomes",
    ])

    def __init__(self, base_url: str, api_key: str):
        if not base_url or not api_key:
            raise ValueError("base_url and api_key are required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._available = True

    # -- transport ------------------------------------------------------

    def _request(self, method: str, path: str, body: Any = None, params: Optional[dict] = None) -> tuple[int, str]:
        """Single HTTP attempt. Returns (status, body_text)."""
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
        except Exception as exc:
            self._available = False
            raise PersistenceUnavailable(str(exc)) from exc

    # -- idempotency key ------------------------------------------------

    @staticmethod
    def idempotency_key(payload: dict[str, Any]) -> str:
        """Generate a deterministic uuid5 idempotency key from payload content."""
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return str(_uuid.uuid5(NAMESPACE, canonical))

    # -- public API -----------------------------------------------------

    def write(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Write a validated payload. Returns {"status": "synced"|"queued"|"persistence_unavailable", ...}."""
        if table not in self.ALLOWED_TABLES:
            raise ValueError("unknown table: {0}".format(table))
        validated = validate_payload(payload)
        key = self.idempotency_key(validated)
        validated["idempotency_key"] = key

        try:
            status, body = self._request("POST", table, body=validated)
        except PersistenceUnavailable:
            return {"status": "persistence_unavailable", "table": table, "idempotency_key": key}

        if 200 <= status < 300:
            return {"status": "synced", "table": table, "idempotency_key": key, "http_status": status}
        return {"status": "queued", "table": table, "idempotency_key": key, "http_status": status}

    def read(self, table: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Read rows from a table. Returns {"status": "ok"|"persistence_unavailable", "rows": [...]}."""
        if table not in self.ALLOWED_TABLES:
            raise ValueError("unknown table: {0}".format(table))
        try:
            status, body = self._request("GET", table, params=params)
        except PersistenceUnavailable:
            return {"status": "persistence_unavailable", "table": table, "rows": []}
        if 200 <= status < 300:
            return {"status": "ok", "table": table, "rows": json.loads(body) if body else []}
        return {"status": "error", "table": table, "http_status": status, "body": body}

    @property
    def available(self) -> bool:
        return self._available
