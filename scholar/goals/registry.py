"""
Batch S9 -- Learning Goal Contract.
Persistent scholar_goals supporting direct-user and Tola sources,
with states ACTIVE/PAUSED/COMPLETED/STOPPED/SUPERSEDED.
Goals persist beyond chat sessions (independent of chat state).
STOPPED means no further planning.
SUPERSEDED retains full history; superseded versions remain retrievable.
PAUSED retains state for later restart.
Plain ASCII. Python 3 stdlib only.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GoalSource:
    """A versioned source of learning goals."""
    source_id: str
    name: str
    source_type: str       # "direct_user" | "tola"
    version: str            # semantic version string
    content_hash: str
    content: Dict[str, Any]
    created_at: str         # ISO-8601 timestamp


@dataclass(frozen=True)
class GoalRecord:
    """A versioned learning goal record."""
    goal_id: str
    source_id: str
    source_version: str
    provenance: Dict[str, Any]
    title: str
    description: str
    source_type: str        # "direct_user" | "tola"
    state: str              # ACTIVE | PAUSED | COMPLETED | STOPPED | SUPERSEDED
    version: int            # integer version for record-level changes


@dataclass(frozen=True)
class GoalStateTransition:
    """A state transition record for a goal."""
    transition_id: str
    goal_id: str
    from_state: Optional[str]
    to_state: str
    occurred_at: str
    version: int


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _require_non_empty_string(value: Any, name: str) -> str:
    """Validate a non-empty string field. Returns the stripped value."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")
    return value.strip()


def _require_positive_int(value: Any, name: str) -> int:
    """Validate a positive integer field."""
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive int, got {value!r}")
    return value


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class GoalRegistry:
    """Persistent learning goal registry with state machine and versioning.

    Key guarantees:
    - Goals persist beyond chat sessions (independent of any session object).
    - States: ACTIVE, PAUSED, COMPLETED, STOPPED, SUPERSEDED.
    - STOPPED means no further planning.
    - SUPERSEDED retains full history; superseded versions remain retrievable.
    - PAUSED retains state for later restart.
    - Direct-user and Tola sources are supported.
    - Every record is traceable to a source (provenance).
    - Duplicate source versions are rejected.
    - Superseded versions remain retrievable.
    - Malformed ingest is rejected with clear error messages.
    - Invalid state transitions are rejected.
    - Deterministic clock injection for testing.
    """

    VALID_SOURCE_TYPES = {"direct_user", "tola"}
    VALID_STATES = {"ACTIVE", "PAUSED", "COMPLETED", "STOPPED", "SUPERSEDED"}

    VALID_TRANSITIONS = {
        "ACTIVE": {"PAUSED", "COMPLETED", "STOPPED", "SUPERSEDED"},
        "PAUSED": {"ACTIVE", "COMPLETED", "STOPPED", "SUPERSEDED"},
        "COMPLETED": set(),
        "STOPPED": set(),
        "SUPERSEDED": set(),
    }

    def __init__(self, clock: Optional[callable] = None) -> None:
        self._clock = clock or datetime.utcnow

        # source_id -> {version_str: GoalSource}
        self._sources: Dict[str, Dict[str, GoalSource]] = {}

        # goal_id -> {version_int: GoalRecord}
        self._goals: Dict[str, Dict[int, GoalRecord]] = {}

        # goal_id -> [GoalStateTransition]
        self._transitions: Dict[str, List[GoalStateTransition]] = {}

        # transition_id -> GoalStateTransition
        self._transition_index: Dict[str, GoalStateTransition] = {}

    # ------------------------------------------------------------------ #
    #  Clock helper
    # ------------------------------------------------------------------ #

    def _now(self) -> str:
        return self._clock().isoformat()

    # ------------------------------------------------------------------ #
    #  Source management
    # ------------------------------------------------------------------ #

    def add_source(
        self,
        source_id: str,
        name: str,
        source_type: str,
        version: str,
        content_hash: str,
        content: Dict[str, Any],
    ) -> GoalSource:
        """Add a new goal source.

        Raises ValueError on:
        - missing or empty required fields
        - unknown source_type (must be direct_user or tola)
        - duplicate source_id + version combination
        """
        source_id = _require_non_empty_string(source_id, "source_id")
        name = _require_non_empty_string(name, "name")
        source_type = _require_non_empty_string(source_type, "source_type")
        version = _require_non_empty_string(version, "version")
        content_hash = _require_non_empty_string(content_hash, "content_hash")

        if source_type not in self.VALID_SOURCE_TYPES:
            raise ValueError(
                f"source_type must be one of {sorted(self.VALID_SOURCE_TYPES)}, "
                f"got {source_type!r}"
            )

        # Check for duplicate source_id + version
        if source_id in self._sources:
            if version in self._sources[source_id]:
                raise ValueError(
                    f"Duplicate source version: source_id={source_id!r}, "
                    f"version={version!r}"
                )

        source = GoalSource(
            source_id=source_id,
            name=name,
            source_type=source_type,
            version=version,
            content_hash=content_hash,
            content=content,
            created_at=self._now(),
        )

        if source_id not in self._sources:
            self._sources[source_id] = {}
        self._sources[source_id][version] = source

        return source

    def get_source(
        self,
        source_id: str,
        version: Optional[str] = None,
    ) -> Optional[GoalSource]:
        """Retrieve a source by id, optionally at a specific version.

        If version is None, returns the latest version.
        Returns None if source_id or version does not exist.
        """
        if source_id not in self._sources:
            return None

        versions = self._sources[source_id]
        if version is not None:
            return versions.get(version)

        latest = max(versions.keys(), key=_version_key)
        return versions[latest]

    def get_source_history(self, source_id: str) -> List[GoalSource]:
        """Return all versions of a source in ascending version order."""
        if source_id not in self._sources:
            return []
        versions = self._sources[source_id]
        return [versions[v] for v in sorted(versions.keys(), key=_version_key)]

    def replace_source(
        self,
        source_id: str,
        new_version: str,
        new_content_hash: str,
        new_content: Dict[str, Any],
    ) -> Tuple[GoalSource, GoalSource]:
        """Replace a source with a new version, preserving history.

        Returns (old_source, new_source).

        Raises ValueError on:
        - source_id does not exist
        - new_version is identical to current version
        - missing or empty required fields
        """
        source_id = _require_non_empty_string(source_id, "source_id")
        new_version = _require_non_empty_string(new_version, "new_version")
        new_content_hash = _require_non_empty_string(new_content_hash, "new_content_hash")

        if source_id not in self._sources:
            raise ValueError(f"source_id {source_id!r} does not exist")

        current_versions = self._sources[source_id]
        current_version = max(current_versions.keys(), key=_version_key)
        current_source = current_versions[current_version]

        if new_version == current_version:
            raise ValueError(
                f"New version {new_version!r} is identical to current "
                f"version {current_version!r}"
            )

        new_source = GoalSource(
            source_id=source_id,
            name=current_source.name,
            source_type=current_source.source_type,
            version=new_version,
            content_hash=new_content_hash,
            content=new_content,
            created_at=self._now(),
        )

        self._sources[source_id][new_version] = new_source
        return current_source, new_source

    # ------------------------------------------------------------------ #
    #  Goal management
    # ------------------------------------------------------------------ #

    def create_goal(
        self,
        goal_id: str,
        source_id: str,
        source_version: str,
        title: str,
        description: str,
        source_type: str,
    ) -> GoalRecord:
        """Create a new learning goal from a source.

        The goal starts in ACTIVE state.

        Raises ValueError on:
        - missing or empty required fields
        - source_id does not exist
        - source_version does not exist for that source
        - unknown source_type
        - duplicate goal_id
        - title or description empty
        """
        goal_id = _require_non_empty_string(goal_id, "goal_id")
        source_id = _require_non_empty_string(source_id, "source_id")
        source_version = _require_non_empty_string(source_version, "source_version")
        title = _require_non_empty_string(title, "title")
        description = _require_non_empty_string(description, "description")
        source_type = _require_non_empty_string(source_type, "source_type")

        if source_type not in self.VALID_SOURCE_TYPES:
            raise ValueError(
                f"source_type must be one of {sorted(self.VALID_SOURCE_TYPES)}, "
                f"got {source_type!r}"
            )

        # Validate source exists
        source = self.get_source(source_id, version=source_version)
        if source is None:
            raise ValueError(
                f"Untraceable goal: source_id={source_id!r}, "
                f"source_version={source_version!r} does not exist"
            )

        # Check for duplicate goal_id
        if goal_id in self._goals:
            raise ValueError(
                f"Duplicate goal_id: {goal_id!r} already exists"
            )

        provenance = {
            "source_id": source_id,
            "source_version": source_version,
            "created_at": self._now(),
            "created_by": "scholar",
        }

        record = GoalRecord(
            goal_id=goal_id,
            source_id=source_id,
            source_version=source_version,
            provenance=dict(provenance),
            title=title,
            description=description,
            source_type=source_type,
            state="ACTIVE",
            version=1,
        )

        self._goals[goal_id] = {1: record}

        # Record the initial state transition
        transition = GoalStateTransition(
            transition_id=f"trans-{goal_id}-v1",
            goal_id=goal_id,
            from_state=None,
            to_state="ACTIVE",
            occurred_at=self._now(),
            version=1,
        )
        self._transitions[goal_id] = [transition]
        self._transition_index[transition.transition_id] = transition

        return record

    def get_goal(
        self,
        goal_id: str,
        version: Optional[int] = None,
    ) -> Optional[GoalRecord]:
        """Retrieve a goal by id, optionally at a specific version.

        If version is None, returns the latest version.
        Returns None if goal_id or version does not exist.
        """
        if goal_id not in self._goals:
            return None

        versions = self._goals[goal_id]
        if version is not None:
            return versions.get(version)

        latest = max(versions.keys())
        return versions[latest]

    def get_goal_history(self, goal_id: str) -> List[GoalRecord]:
        """Return all versions of a goal in ascending version order."""
        if goal_id not in self._goals:
            return []
        versions = self._goals[goal_id]
        return [versions[v] for v in sorted(versions.keys())]

    def get_transitions(self, goal_id: str) -> List[GoalStateTransition]:
        """Return all state transitions for a goal."""
        return list(self._transitions.get(goal_id, []))

    # ------------------------------------------------------------------ #
    #  State transitions
    # ------------------------------------------------------------------ #

    def pause_goal(self, goal_id: str) -> Tuple[GoalRecord, GoalRecord]:
        """Pause an ACTIVE goal. Creates a new version with state PAUSED.

        Returns (old_record, new_record).

        Raises ValueError on:
        - goal_id does not exist
        - current state is not ACTIVE
        """
        if goal_id not in self._goals:
            raise ValueError(f"goal_id {goal_id!r} does not exist")

        current = self.get_goal(goal_id)
        assert current is not None

        if current.state != "ACTIVE":
            raise ValueError(
                f"Cannot pause goal in state {current.state!r}; "
                f"only ACTIVE goals can be paused"
            )

        return self._create_new_version(current, "PAUSED")

    def resume_goal(self, goal_id: str) -> Tuple[GoalRecord, GoalRecord]:
        """Resume a PAUSED goal. Creates a new version with state ACTIVE.

        Returns (old_record, new_record).

        Raises ValueError on:
        - goal_id does not exist
        - current state is not PAUSED
        """
        if goal_id not in self._goals:
            raise ValueError(f"goal_id {goal_id!r} does not exist")

        current = self.get_goal(goal_id)
        assert current is not None

        if current.state != "PAUSED":
            raise ValueError(
                f"Cannot resume goal in state {current.state!r}; "
                f"only PAUSED goals can be resumed"
            )

        return self._create_new_version(current, "ACTIVE")

    def complete_goal(self, goal_id: str) -> Tuple[GoalRecord, GoalRecord]:
        """Complete an ACTIVE or PAUSED goal. Creates a new version with state COMPLETED.

        Returns (old_record, new_record).

        Raises ValueError on:
        - goal_id does not exist
        - current state is not ACTIVE or PAUSED
        """
        if goal_id not in self._goals:
            raise ValueError(f"goal_id {goal_id!r} does not exist")

        current = self.get_goal(goal_id)
        assert current is not None

        if current.state not in ("ACTIVE", "PAUSED"):
            raise ValueError(
                f"Cannot complete goal in state {current.state!r}; "
                f"only ACTIVE or PAUSED goals can be completed"
            )

        return self._create_new_version(current, "COMPLETED")

    def stop_goal(self, goal_id: str) -> Tuple[GoalRecord, GoalRecord]:
        """Stop an ACTIVE or PAUSED goal. Creates a new version with state STOPPED.

        STOPPED means no further planning.

        Returns (old_record, new_record).

        Raises ValueError on:
        - goal_id does not exist
        - current state is not ACTIVE or PAUSED
        """
        if goal_id not in self._goals:
            raise ValueError(f"goal_id {goal_id!r} does not exist")

        current = self.get_goal(goal_id)
        assert current is not None

        if current.state not in ("ACTIVE", "PAUSED"):
            raise ValueError(
                f"Cannot stop goal in state {current.state!r}; "
                f"only ACTIVE or PAUSED goals can be stopped"
            )

        return self._create_new_version(current, "STOPPED")

    def supersede_goal(
        self,
        goal_id: str,
        new_title: str,
        new_description: str,
        new_source_id: str,
        new_source_version: str,
        new_source_type: str,
    ) -> Tuple[GoalRecord, GoalRecord]:
        """Supersede an ACTIVE or PAUSED goal with a new version.

        The old version remains retrievable. The new version has state SUPERSEDED.

        Returns (old_record, new_record).

        Raises ValueError on:
        - goal_id does not exist
        - current state is not ACTIVE or PAUSED
        - missing or empty required fields
        - source does not exist
        - new source_type is invalid
        - new title and description are identical to current version
        """
        goal_id = _require_non_empty_string(goal_id, "goal_id")
        new_title = _require_non_empty_string(new_title, "new_title")
        new_description = _require_non_empty_string(new_description, "new_description")
        new_source_id = _require_non_empty_string(new_source_id, "new_source_id")
        new_source_version = _require_non_empty_string(new_source_version, "new_source_version")
        new_source_type = _require_non_empty_string(new_source_type, "new_source_type")

        if new_source_type not in self.VALID_SOURCE_TYPES:
            raise ValueError(
                f"source_type must be one of {sorted(self.VALID_SOURCE_TYPES)}, "
                f"got {new_source_type!r}"
            )

        if goal_id not in self._goals:
            raise ValueError(f"goal_id {goal_id!r} does not exist")

        current = self.get_goal(goal_id)
        assert current is not None

        if current.state not in ("ACTIVE", "PAUSED"):
            raise ValueError(
                f"Cannot supersede goal in state {current.state!r}; "
                f"only ACTIVE or PAUSED goals can be superseded"
            )

        # Validate new source exists
        new_source = self.get_source(new_source_id, version=new_source_version)
        if new_source is None:
            raise ValueError(
                f"Untraceable goal: source_id={new_source_id!r}, "
                f"source_version={new_source_version!r} does not exist"
            )

        # Check that the new content is actually different
        if new_title == current.title and new_description == current.description:
            raise ValueError(
                f"New title and description are identical to current version "
                f"— use create_goal for a new goal instead"
            )

        return self._create_new_version(
            current,
            "SUPERSEDED",
            title=new_title,
            description=new_description,
            source_id=new_source_id,
            source_version=new_source_version,
            source_type=new_source_type,
        )

    def _create_new_version(
        self,
        current: GoalRecord,
        new_state: str,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        source_id: Optional[str] = None,
        source_version: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> Tuple[GoalRecord, GoalRecord]:
        """Create a new version of a goal record with a new state.

        Returns (old_record, new_record).
        """
        next_version = max(self._goals[current.goal_id].keys()) + 1

        new_record = GoalRecord(
            goal_id=current.goal_id,
            source_id=source_id or current.source_id,
            source_version=source_version or current.source_version,
            provenance={
                "source_id": source_id or current.source_id,
                "source_version": source_version or current.source_version,
                "created_at": self._now(),
                "created_by": "scholar",
                "supersedes_version": current.version,
            },
            title=title or current.title,
            description=description or current.description,
            source_type=source_type or current.source_type,
            state=new_state,
            version=next_version,
        )

        self._goals[current.goal_id][next_version] = new_record

        # Record the state transition
        transition = GoalStateTransition(
            transition_id=f"trans-{current.goal_id}-v{next_version}",
            goal_id=current.goal_id,
            from_state=current.state,
            to_state=new_state,
            occurred_at=self._now(),
            version=next_version,
        )
        self._transitions[current.goal_id].append(transition)
        self._transition_index[transition.transition_id] = transition

        return current, new_record

    # ------------------------------------------------------------------ #
    #  Registry-wide validation
    # ------------------------------------------------------------------ #

    def validate(self) -> Dict[str, Any]:
        """Validate the entire registry.

        Returns a summary dict with:
        - valid: bool
        - source_count: int
        - goal_count: int
        - transition_count: int
        - untraceable_goals: list of goal_ids
        - duplicate_source_versions: list of (source_id, version) tuples
        """
        untraceable = []
        for gid, versions in self._goals.items():
            for v, record in versions.items():
                source = self.get_source(record.source_id, version=record.source_version)
                if source is None:
                    untraceable.append(f"{gid}:v{v}")

        duplicate_versions = []
        for source_id, versions in self._sources.items():
            seen = set()
            for v in versions:
                if v in seen:
                    duplicate_versions.append((source_id, v))
                seen.add(v)

        return {
            "valid": (
                len(untraceable) == 0
                and len(duplicate_versions) == 0
            ),
            "source_count": sum(len(vs) for vs in self._sources.values()),
            "goal_count": sum(len(vs) for vs in self._goals.values()),
            "transition_count": sum(len(vs) for vs in self._transitions.values()),
            "untraceable_goals": untraceable,
            "duplicate_source_versions": duplicate_versions,
        }

    # ------------------------------------------------------------------ #
    #  State serialization for recovery / inspection
    # ------------------------------------------------------------------ #

    def get_state(self) -> Dict[str, Any]:
        """Return registry state for persistence/inspection."""
        return {
            "sources": {
                sid: {v: s.__dict__ for v, s in versions.items()}
                for sid, versions in self._sources.items()
            },
            "goals": {
                gid: {v: r.__dict__ for v, r in versions.items()}
                for gid, versions in self._goals.items()
            },
            "transitions": {
                gid: [t.__dict__ for t in trans_list]
                for gid, trans_list in self._transitions.items()
            },
        }


# ---------------------------------------------------------------------------
# Version comparison helper
# ---------------------------------------------------------------------------

def _version_key(version_str: str) -> Tuple[int, ...]:
    """Convert a version string to a tuple of integers for comparison.

    Handles semantic versions like '1.0', '2.1.3', '1.0.0-beta'.
    Non-numeric segments are treated as 0.
    """
    parts = []
    for segment in version_str.split("."):
        numeric_part = ""
        for ch in segment:
            if ch.isdigit():
                numeric_part += ch
            else:
                break
        parts.append(int(numeric_part) if numeric_part else 0)
    return tuple(parts)
