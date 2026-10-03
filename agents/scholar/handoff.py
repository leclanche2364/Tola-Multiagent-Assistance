"""Scholar handoff producer for scholar_handoff.v1.

Reads the Level 7 Module 1 state file and produces validated handoff
payloads against the contract in agents/daily_synthesis/contracts.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agents.daily_synthesis.contracts import ScholarHandoff, validate_payload

STATE_PATH = Path(__file__).parent / "level7_module1_state.json"


def _load_state() -> dict[str, Any]:
    with open(STATE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _find_current_batch(state: dict[str, Any]) -> dict[str, Any] | None:
    """Return the first batch whose status is not_started or in_progress,
    or None if all batches are complete."""
    for batch in state.get("batches", []):
        if batch.get("status") in ("not_started", "in_progress"):
            return batch
    return None


def _get_completion_events(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect all completion events across batches, sorted newest first."""
    events: list[dict[str, Any]] = []
    for batch in state.get("batches", []):
        for article in batch.get("articles", []):
            for event in article.get("completion_events", []):
                events.append(event)
    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events


def _is_stale(state: dict[str, Any]) -> bool:
    """Return True if the latest completion event is newer than the handoff timestamp."""
    completion_events = _get_completion_events(state)
    if not completion_events:
        return False
    latest_completion = completion_events[0].get("timestamp", "")
    handoff_ts = state.get("last_handoff_timestamp", "")
    if not handoff_ts:
        return False
    return latest_completion > handoff_ts


def _get_reading_target(batch: dict[str, Any]) -> dict[str, Any]:
    """Build a reading_target dict from the batch's first not-started article."""
    articles = [a for a in batch.get("articles", []) if a.get("status") == "not_started"]
    if not articles:
        articles = [a for a in batch.get("articles", []) if a.get("status") == "in_progress"]
    article = articles[0] if articles else None
    return {
        "required": True,
        "article_title": article["title"] if article else "",
        "exact_sections_to_read": batch.get("sections", []),
        "extraction_goal": batch.get("extraction_goals", [])[0] if batch.get("extraction_goals") else "",
    }


def _get_writing_target(batch: dict[str, Any]) -> dict[str, Any]:
    """Build a writing_target dict from the batch."""
    return {
        "section": batch.get("title", ""),
        "word_target": batch.get("word_target", ""),
        "articles_to_draw_on": [a["title"] for a in batch.get("articles", []) if a.get("status") == "complete"],
    }


def produce_handoff(
    agent_id: str = "scholar",
    window_minutes: Optional[int] = None,
    energy_level: str = "medium",
) -> dict[str, Any]:
    """Produce a validated scholar_handoff.v1 payload for the current batch.

    Args:
        agent_id: Identifier for the calling agent.
        window_minutes: If 20-30, return a short-window quick-read atom.
        energy_level: "light", "light-medium", "medium", "high".

    Returns:
        Validated dict conforming to scholar_handoff.v1.
    """
    state = _load_state()
    current_batch = _find_current_batch(state)

    if current_batch is None:
        raise ValueError("No current batch found; all batches are complete.")

    # Short-window support: 20-30 min with light-medium energy
    if window_minutes is not None and 20 <= window_minutes <= 30 and energy_level in ("light", "light-medium"):
        return _short_window_handoff(agent_id, current_batch, state)

    # Determine action type based on batch progress
    action_type, exact_action, reading_target, writing_target = _full_task_handoff(
        agent_id, current_batch, state
    )

    handoff = ScholarHandoff(
        schema_version="scholar_handoff.v1",
        agent_id=agent_id,
        current_batch_id=current_batch["batch_id"],
        exact_action=exact_action,
        estimated_minutes=_estimate_minutes(current_batch),
        definition_of_done=_definition_of_done(current_batch),
        reading_target=reading_target,
        source_refs=[a["title"] for a in current_batch.get("articles", [])],
    )

    result = handoff.validate()
    result["freshness_status"] = "stale" if _is_stale(state) else "fresh"
    return result


def _short_window_handoff(
    agent_id: str,
    batch: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Return a quick-read atom for a 20-30 min light-medium energy window."""
    # Nominate the best next article (first not_started) and a backup
    not_started = [a for a in batch.get("articles", []) if a.get("status") == "not_started"]
    in_progress = [a for a in batch.get("articles", []) if a.get("status") == "in_progress"]
    all_available = not_started + in_progress

    best = all_available[0] if all_available else None
    backup = all_available[1] if len(all_available) > 1 else None

    if best is None:
        raise ValueError("No articles available for short-window handoff.")

    # Pick the first section of the batch for the quick read
    sections = batch.get("sections", [])
    exact_sections = [sections[0]] if sections else []

    handoff = ScholarHandoff(
        schema_version="scholar_handoff.v1",
        agent_id=agent_id,
        current_batch_id=batch["batch_id"],
        exact_action=f"Quick-read {best['title']} — extract {batch.get('extraction_goals', [''])[0]}",
        estimated_minutes=15,
        definition_of_done=f"Read {best['title']} sections {exact_sections} and extract one key claim relevant to {batch['title']}.",
        reading_target={
            "required": True,
            "article_title": best["title"],
            "exact_sections_to_read": exact_sections,
            "extraction_goal": batch.get("extraction_goals", [""])[0],
        },
        source_refs=[best["title"]],
    )

    result = handoff.validate()
    result["freshness_status"] = "stale" if _is_stale(state) else "fresh"
    result["short_window"] = {
        "best_next_article": best["title"],
        "backup_article": backup["title"] if backup else None,
        "quick_read": True,
    }
    return result


def _full_task_handoff(
    agent_id: str,
    batch: dict[str, Any],
    state: dict[str, Any],
) -> tuple[str, str, Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """Determine the full drafting task for the current batch.

    Progression: not_started → read → extracted → drafted → revised → complete
    """
    articles = batch.get("articles", [])

    # Categorise by progression status
    not_started = [a for a in articles if a.get("status") == "not_started"]
    read = [a for a in articles if a.get("status") == "read"]
    extracted = [a for a in articles if a.get("status") == "extracted"]
    drafted = [a for a in articles if a.get("status") == "drafted"]
    revised = [a for a in articles if a.get("status") == "revised"]
    complete = [a for a in articles if a.get("status") == "complete"]

    # If there are not_started articles, the action is reading the first one
    if not_started:
        article = not_started[0]
        action_type = "read"
        exact_action = (
            f"Read {article['title']} — sections {batch.get('sections', [])} "
            f"extracting {batch.get('extraction_goals', [''])[0]}"
        )
        reading_target = _get_reading_target(batch)
        writing_target = None
    elif read:
        # Articles have been read; move to extraction
        article = read[0]
        action_type = "extract"
        exact_action = (
            f"Extract from {article['title']} — sections {batch.get('sections', [])} "
            f"goal: {batch.get('extraction_goals', [''])[0]}"
        )
        reading_target = None
        writing_target = None
    elif extracted:
        # Articles have been extracted; move to drafting
        action_type = "write"
        exact_action = (
            f"Draft {batch['title']} — {batch.get('word_target', '')} words "
            f"using {len(extracted)} extracted articles"
        )
        reading_target = None
        writing_target = _get_writing_target(batch)
    elif drafted:
        # Articles have been drafted; move to revision
        action_type = "revise"
        exact_action = (
            f"Revise {batch['title']} — review and refine {batch.get('word_target', '')} words"
        )
        reading_target = None
        writing_target = None
    elif revised or complete:
        # All articles done; final review
        action_type = "review"
        exact_action = (
            f"Review {batch['title']} — final distinction edit and self-check"
        )
        reading_target = None
        writing_target = _get_writing_target(batch)
    else:
        # No articles at all (e.g., batch_11 final synthesis)
        action_type = "write"
        exact_action = f"Draft {batch['title']} — {batch.get('word_target', '')}"
        reading_target = None
        writing_target = _get_writing_target(batch)

    return action_type, exact_action, reading_target, writing_target


def _estimate_minutes(batch: dict[str, Any]) -> int:
    """Estimate minutes based on word target."""
    word_target = batch.get("word_target", "0")
    if "No assessed words" in word_target or "0" in word_target:
        return 30
    # Extract numeric range
    import re
    nums = re.findall(r"\d+", word_target)
    if nums:
        avg = sum(int(n) for n in nums) / len(nums)
        return max(15, int(avg / 100))
    return 30


def _definition_of_done(batch: dict[str, Any]) -> str:
    """Build a definition-of-done string for the batch."""
    word_target = batch.get("word_target", "")
    sections = batch.get("sections", [])
    return (
        f"Completed {batch['title']}: all {len(batch.get('articles', []))} articles read/extracted, "
        f"{word_target} words drafted for sections {sections}, "
        f"distinction criteria self-checked."
    )


def advance_state(
    batch_id: str,
    article_title: str,
    new_status: str,
    event: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Advance the state of a batch article and record a completion event.

    Args:
        batch_id: The batch containing the article.
        article_title: The exact title of the article to advance.
        new_status: One of "read", "extracted", "drafted", "revised", "complete".
        event: Optional completion event dict; if omitted, one is generated.

    Returns:
        The updated state dict.
    """
    state = _load_state()

    for batch in state.get("batches", []):
        if batch["batch_id"] == batch_id:
            for article in batch.get("articles", []):
                if article["title"] == article_title:
                    old_status = article.get("status", "not_started")
                    article["status"] = new_status
                    if "completion_events" not in article:
                        article["completion_events"] = []
                    article["completion_events"].append(
                        event
                        or {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "action": new_status,
                            "previous_status": old_status,
                            "article_title": article_title,
                            "batch_id": batch_id,
                        }
                    )
                    break
            break

    # Write back to file
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)

    return state


def get_handoff_freshness() -> str:
    """Return freshness_status for the current handoff without producing it."""
    state = _load_state()
    return "stale" if _is_stale(state) else "fresh"
