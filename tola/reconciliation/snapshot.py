# Batch T26 -- Daily Executive Reconciliation
# tola/reconciliation/snapshot.py: reconcile_snapshot + SnapshotReport.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_SOURCE_AGE = 3  # days; mirrors THRESHOLDS["SNAPSHOT_MAX_AGE"]

STALE_SOURCE = "STALE_SOURCE"
DISCREPANCY = "DISCREPANCY"


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SnapshotReport:
    changed: bool
    deltas: list[dict] = field(default_factory=list)
    sources_fresh: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _field_deltas(
    prev: dict, curr: dict, oid: str
) -> list[dict]:
    """Field-wise diff between two dicts. Returns list of delta dicts."""
    deltas: list[dict] = []
    all_keys = set(prev.keys()) | set(curr.keys())
    for key in sorted(all_keys):
        pv = prev.get(key)
        cv = curr.get(key)
        if pv != cv:
            deltas.append(
                {
                    "id": oid,
                    "field": key,
                    "before": pv,
                    "after": cv,
                }
            )
    return deltas


def _sort_deltas(deltas: list[dict]) -> list[dict]:
    """Deterministic sort: by id then field."""
    return sorted(deltas, key=lambda d: (d["id"], d["field"]))


def _parse_iso_date(s: str) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD or full ISO)."""
    if not s:
        return None
    try:
        # Try full ISO first
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        pass
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _check_source_freshness(
    sources: list[dict],
    reference_date: date,
) -> tuple[bool, list[dict]]:
    """Check fetched_at age of each source entry.

    Returns (sources_fresh, stale_actions).
    A source missing fetched_at or older than MAX_SOURCE_AGE days
    marks sources_fresh=False and yields a STALE_SOURCE action.
    """
    stale_actions: list[dict] = []
    fresh = True
    for src in sources:
        name = src.get("name", "unknown")
        fetched_at = src.get("fetched_at", "")
        if not fetched_at:
            fresh = False
            stale_actions.append(
                {
                    "action": STALE_SOURCE,
                    "source": name,
                    "reason": "missing_fetched_at",
                }
            )
            continue
        fetched_date = _parse_iso_date(fetched_at)
        if fetched_date is None:
            fresh = False
            stale_actions.append(
                {
                    "action": STALE_SOURCE,
                    "source": name,
                    "reason": "invalid_fetched_at",
                }
            )
            continue
        age_days = (reference_date - fetched_date).days
        if age_days > MAX_SOURCE_AGE:
            fresh = False
            stale_actions.append(
                {
                    "action": STALE_SOURCE,
                    "source": name,
                    "reason": f"age_{age_days}_days_exceeds_max_{MAX_SOURCE_AGE}",
                }
            )
    return fresh, stale_actions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def reconcile_snapshot(
    previous: dict,
    current: dict,
    reference_date: date | None = None,
) -> SnapshotReport:
    """Compare previous and current PortfolioSnapshot dicts field-wise.

    Parameters
    ----------
    previous : dict
        The previous snapshot state (dict with entity lists keyed by
        field name, plus optional source metadata).
    current : dict
        The current snapshot state in the same shape.
    reference_date : date | None
        Reference date for source freshness checks. If None,
        freshness is not checked (sources_fresh defaults True).

    Returns
    -------
    SnapshotReport
        changed: True if any delta found or stale sources.
        deltas: list of {id, field, before, after} dicts, sorted
                deterministically by id then field.
        sources_fresh: True if all source entries are within MAX_SOURCE_AGE.
    """
    # Check source freshness from current["_sources"] if present.
    sources = current.get("_sources", [])
    sources_fresh = True
    stale_actions: list[dict] = []

    if reference_date is not None and sources:
        sources_fresh, stale_actions = _check_source_freshness(
            sources, reference_date
        )

    # Compute field-wise deltas for each entity list.
    all_deltas: list[dict] = []

    # Collect all entity-list keys (exclude _sources and other metadata).
    skip_keys = {"_sources", "_meta", "generated_at", "snapshot_version"}

    # Gather all keys from both prev and curr.
    prev_keys = set(previous.keys()) - skip_keys
    curr_keys = set(current.keys()) - skip_keys
    all_keys = prev_keys | curr_keys

    for key in sorted(all_keys):
        prev_items = previous.get(key, [])
        curr_items = current.get(key, [])

        # Index by id
        prev_by_id: dict[str, dict] = {}
        for item in prev_items:
            if isinstance(item, dict):
                oid = item.get("id", "")
                prev_by_id[oid] = item

        curr_by_id: dict[str, dict] = {}
        for item in curr_items:
            if isinstance(item, dict):
                oid = item.get("id", "")
                curr_by_id[oid] = item

        all_ids = set(prev_by_id.keys()) | set(curr_by_id.keys())
        for oid in sorted(all_ids):
            pv = prev_by_id.get(oid)
            cv = curr_by_id.get(oid)
            if pv is None:
                # Added item
                for fk in sorted(cv.keys()):
                    all_deltas.append(
                        {
                            "id": oid,
                            "field": fk,
                            "before": None,
                            "after": cv.get(fk),
                        }
                    )
            elif cv is None:
                # Removed item
                for fk in sorted(pv.keys()):
                    all_deltas.append(
                        {
                            "id": oid,
                            "field": fk,
                            "before": pv.get(fk),
                            "after": None,
                        }
                    )
            else:
                # Item exists in both: field-wise diff
                fd = _field_deltas(pv, cv, oid)
                all_deltas.extend(fd)

    # Append stale-source deltas if any.
    if stale_actions:
        for sa in stale_actions:
            all_deltas.append(
                {
                    "id": sa["source"],
                    "field": "_source_freshness",
                    "before": "fresh",
                    "after": "stale",
                    "action": STALE_SOURCE,
                }
            )

    all_deltas = _sort_deltas(all_deltas)
    changed = len(all_deltas) > 0

    return SnapshotReport(
        changed=changed,
        deltas=all_deltas,
        sources_fresh=sources_fresh,
    )
