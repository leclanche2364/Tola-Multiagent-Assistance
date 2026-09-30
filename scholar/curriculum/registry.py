"""
Batch S7 -- Curriculum Registry.
Versioned curriculum sources, nodes, learning outcomes and topic links.
Every node is traceable to a source (provenance). Source replacement
preserves history. IntenSIQ topics are mapped. Handbook and assignment
guidance sources are version-correct. Curriculum state is versioned and
source-grounded, never prompt hard-coded.
Plain ASCII. Python 3 stdlib only.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CurriculumSource:
    """A versioned source of curriculum content."""
    source_id: str
    name: str
    source_type: str          # "handbook" | "assignment_guidance" | "intensiq_topic"
    version: str              # semantic version string, e.g. "1.0", "2.1"
    content_hash: str         # deterministic content fingerprint
    content: Dict[str, Any]   # structured content (never prompt hard-coded)
    created_at: str           # ISO-8601 timestamp


@dataclass(frozen=True)
class CurriculumNode:
    """A node in the curriculum, traceable to a source."""
    node_id: str
    source_id: str
    source_version: str
    provenance: Dict[str, Any]
    title: str
    kind: str                 # "topic" | "module" | "unit" | "outcome" | "section"
    content: Dict[str, Any]
    version: int              # integer version for node-level changes


@dataclass(frozen=True)
class LearningOutcome:
    """A learning outcome linked to a curriculum node."""
    outcome_id: str
    node_id: str
    description: str
    mastery_dimensions: List[str]
    version: int


@dataclass(frozen=True)
class TopicLink:
    """A link between two curriculum nodes."""
    link_id: str
    from_node_id: str
    to_node_id: str
    link_type: str            # "prerequisite" | "builds_on" | "maps_to" | "supersedes"
    version: int


@dataclass(frozen=True)
class IntenSIQTopicMapping:
    """Maps an IntenSIQ topic to a curriculum node."""
    mapping_id: str
    intensiq_topic_id: str
    curriculum_node_id: str
    source_version: str
    created_at: str


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

class CurriculumRegistry:
    """Versioned curriculum registry with source-grounded provenance.

    Key guarantees:
    - Every node is traceable to a source (provenance).
    - Source replacement preserves history (old versions remain retrievable).
    - IntenSIQ topics are mapped to curriculum nodes.
    - Handbook and assignment guidance sources are version-correct.
    - Duplicate source versions are rejected.
    - Untraceable nodes (no matching source) are rejected.
    - Curriculum state is versioned and source-grounded, never prompt hard-coded.
    """

    def __init__(self, clock: Optional[callable] = None) -> None:
        self._clock = clock or datetime.utcnow

        # source_id -> {version_str: CurriculumSource}
        self._sources: Dict[str, Dict[str, CurriculumSource]] = {}

        # node_id -> CurriculumNode
        self._nodes: Dict[str, CurriculumNode] = {}

        # outcome_id -> LearningOutcome
        self._outcomes: Dict[str, LearningOutcome] = {}

        # link_id -> TopicLink
        self._topic_links: Dict[str, TopicLink] = {}

        # mapping_id -> IntenSIQTopicMapping
        self._intensiq_mappings: Dict[str, IntenSIQTopicMapping] = {}

        # node_id -> [mapping_id]  (inverse index for IntenSIQ mappings)
        self._node_mappings: Dict[str, List[str]] = {}

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
    ) -> CurriculumSource:
        """Add a new curriculum source.

        Raises ValueError on:
        - missing or empty required fields
        - unknown source_type
        - duplicate source_id + version combination
        """
        source_id = _require_non_empty_string(source_id, "source_id")
        name = _require_non_empty_string(name, "name")
        source_type = _require_non_empty_string(source_type, "source_type")
        version = _require_non_empty_string(version, "version")
        content_hash = _require_non_empty_string(content_hash, "content_hash")

        valid_types = {"handbook", "assignment_guidance", "intensiq_topic"}
        if source_type not in valid_types:
            raise ValueError(
                f"source_type must be one of {sorted(valid_types)}, got {source_type!r}"
            )

        # Check for duplicate source_id + version
        if source_id in self._sources:
            if version in self._sources[source_id]:
                raise ValueError(
                    f"Duplicate source version: source_id={source_id!r}, "
                    f"version={version!r}"
                )

        source = CurriculumSource(
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

    def replace_source(
        self,
        source_id: str,
        new_version: str,
        new_content_hash: str,
        new_content: Dict[str, Any],
    ) -> Tuple[CurriculumSource, CurriculumSource]:
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

        # Create the new source (preserving name and type from current)
        new_source = CurriculumSource(
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

    def get_source(
        self,
        source_id: str,
        version: Optional[str] = None,
    ) -> Optional[CurriculumSource]:
        """Retrieve a source by id, optionally at a specific version.

        If version is None, returns the latest version.
        Returns None if source_id or version does not exist.
        """
        if source_id not in self._sources:
            return None

        versions = self._sources[source_id]
        if version is not None:
            return versions.get(version)

        # Return latest version
        latest = max(versions.keys(), key=_version_key)
        return versions[latest]

    def get_source_history(self, source_id: str) -> List[CurriculumSource]:
        """Return all versions of a source in ascending version order."""
        if source_id not in self._sources:
            return []
        versions = self._sources[source_id]
        return [versions[v] for v in sorted(versions.keys(), key=_version_key)]

    # ------------------------------------------------------------------ #
    #  Node management
    # ------------------------------------------------------------------ #

    def add_node(
        self,
        node_id: str,
        source_id: str,
        source_version: str,
        provenance: Dict[str, Any],
        title: str,
        kind: str,
        content: Dict[str, Any],
    ) -> CurriculumNode:
        """Add a curriculum node with provenance.

        Raises ValueError on:
        - missing or empty required fields
        - source_id does not exist
        - source_version does not exist for that source
        - duplicate node_id
        - provenance missing required keys
        """
        node_id = _require_non_empty_string(node_id, "node_id")
        source_id = _require_non_empty_string(source_id, "source_id")
        source_version = _require_non_empty_string(source_version, "source_version")
        title = _require_non_empty_string(title, "title")
        kind = _require_non_empty_string(kind, "kind")

        # Validate source exists
        source = self.get_source(source_id, version=source_version)
        if source is None:
            raise ValueError(
                f"Untraceable node: source_id={source_id!r}, "
                f"source_version={source_version!r} does not exist"
            )

        # Validate provenance has required keys
        required_provenance_keys = {"source_id", "source_version", "ingested_at"}
        missing_provenance = required_provenance_keys - set(provenance.keys())
        if missing_provenance:
            raise ValueError(
                f"Provenance missing required keys: {sorted(missing_provenance)}"
            )

        # Check for duplicate node_id
        if node_id in self._nodes:
            raise ValueError(f"Duplicate node_id: {node_id!r}")

        # Determine node version (1-based, increments per source)
        existing_for_source = [
            n for n in self._nodes.values()
            if n.source_id == source_id
        ]
        node_version = len(existing_for_source) + 1

        node = CurriculumNode(
            node_id=node_id,
            source_id=source_id,
            source_version=source_version,
            provenance=dict(provenance),
            title=title,
            kind=kind,
            content=dict(content),
            version=node_version,
        )

        self._nodes[node_id] = node
        return node

    def get_node(self, node_id: str) -> Optional[CurriculumNode]:
        """Retrieve a node by id. Returns None if not found."""
        return self._nodes.get(node_id)

    def get_nodes_by_source(self, source_id: str) -> List[CurriculumNode]:
        """Return all nodes traceable to a specific source."""
        return [
            n for n in self._nodes.values()
            if n.source_id == source_id
        ]

    def validate_node_provenance(self, node_id: str) -> bool:
        """Check that a node is traceable to an existing source.

        Returns True if the node exists and its source+version are retrievable.
        """
        node = self._nodes.get(node_id)
        if node is None:
            return False
        source = self.get_source(node.source_id, version=node.source_version)
        return source is not None

    def validate_all_nodes(self) -> List[str]:
        """Validate all nodes are traceable. Returns list of untraceable node_ids."""
        untraceable = []
        for node_id, node in self._nodes.items():
            if not self.validate_node_provenance(node_id):
                untraceable.append(node_id)
        return untraceable

    # ------------------------------------------------------------------ #
    #  Learning outcome management
    # ------------------------------------------------------------------ #

    def add_outcome(
        self,
        outcome_id: str,
        node_id: str,
        description: str,
        mastery_dimensions: List[str],
    ) -> LearningOutcome:
        """Add a learning outcome linked to a curriculum node.

        Raises ValueError on:
        - missing or empty required fields
        - node_id does not exist
        - duplicate outcome_id
        """
        outcome_id = _require_non_empty_string(outcome_id, "outcome_id")
        node_id = _require_non_empty_string(node_id, "node_id")
        description = _require_non_empty_string(description, "description")

        if node_id not in self._nodes:
            raise ValueError(f"node_id {node_id!r} does not exist")

        if outcome_id in self._outcomes:
            raise ValueError(f"Duplicate outcome_id: {outcome_id!r}")

        # Validate mastery_dimensions are non-empty strings
        if not isinstance(mastery_dimensions, list) or not mastery_dimensions:
            raise ValueError(
                "mastery_dimensions must be a non-empty list of strings"
            )
        for dim in mastery_dimensions:
            if not isinstance(dim, str) or not dim.strip():
                raise ValueError(
                    f"Each mastery_dimension must be a non-empty string, got {dim!r}"
                )

        # Determine outcome version
        existing_for_node = [
            o for o in self._outcomes.values()
            if o.node_id == node_id
        ]
        outcome_version = len(existing_for_node) + 1

        outcome = LearningOutcome(
            outcome_id=outcome_id,
            node_id=node_id,
            description=description,
            mastery_dimensions=list(mastery_dimensions),
            version=outcome_version,
        )

        self._outcomes[outcome_id] = outcome
        return outcome

    def get_outcome(self, outcome_id: str) -> Optional[LearningOutcome]:
        """Retrieve an outcome by id."""
        return self._outcomes.get(outcome_id)

    def get_outcomes_by_node(self, node_id: str) -> List[LearningOutcome]:
        """Return all outcomes linked to a node."""
        return [o for o in self._outcomes.values() if o.node_id == node_id]

    # ------------------------------------------------------------------ #
    #  Topic link management
    # ------------------------------------------------------------------ #

    def add_topic_link(
        self,
        link_id: str,
        from_node_id: str,
        to_node_id: str,
        link_type: str,
    ) -> TopicLink:
        """Add a link between two curriculum nodes.

        Raises ValueError on:
        - missing or empty required fields
        - from_node_id or to_node_id does not exist
        - unknown link_type
        - duplicate link_id
        """
        link_id = _require_non_empty_string(link_id, "link_id")
        from_node_id = _require_non_empty_string(from_node_id, "from_node_id")
        to_node_id = _require_non_empty_string(to_node_id, "to_node_id")
        link_type = _require_non_empty_string(link_type, "link_type")

        valid_link_types = {"prerequisite", "builds_on", "maps_to", "supersedes"}
        if link_type not in valid_link_types:
            raise ValueError(
                f"link_type must be one of {sorted(valid_link_types)}, got {link_type!r}"
            )

        if from_node_id not in self._nodes:
            raise ValueError(f"from_node_id {from_node_id!r} does not exist")
        if to_node_id not in self._nodes:
            raise ValueError(f"to_node_id {to_node_id!r} does not exist")

        if link_id in self._topic_links:
            raise ValueError(f"Duplicate link_id: {link_id!r}")

        # Determine link version
        existing_for_from = [
            l for l in self._topic_links.values()
            if l.from_node_id == from_node_id
        ]
        link_version = len(existing_for_from) + 1

        link = TopicLink(
            link_id=link_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            link_type=link_type,
            version=link_version,
        )

        self._topic_links[link_id] = link
        return link

    def get_topic_link(self, link_id: str) -> Optional[TopicLink]:
        """Retrieve a topic link by id."""
        return self._topic_links.get(link_id)

    def get_topic_links_for_node(self, node_id: str) -> List[TopicLink]:
        """Return all links where the given node is the from_node."""
        return [l for l in self._topic_links.values() if l.from_node_id == node_id]

    def get_topic_links_to_node(self, node_id: str) -> List[TopicLink]:
        """Return all links where the given node is the to_node."""
        return [l for l in self._topic_links.values() if l.to_node_id == node_id]

    # ------------------------------------------------------------------ #
    #  IntenSIQ topic mapping
    # ------------------------------------------------------------------ #

    def map_intensiq_topic(
        self,
        mapping_id: str,
        intensiq_topic_id: str,
        curriculum_node_id: str,
        source_version: str,
    ) -> IntenSIQTopicMapping:
        """Map an IntenSIQ topic to a curriculum node.

        Raises ValueError on:
        - missing or empty required fields
        - curriculum_node_id does not exist
        - duplicate mapping_id
        """
        mapping_id = _require_non_empty_string(mapping_id, "mapping_id")
        intensiq_topic_id = _require_non_empty_string(intensiq_topic_id, "intensiq_topic_id")
        curriculum_node_id = _require_non_empty_string(curriculum_node_id, "curriculum_node_id")
        source_version = _require_non_empty_string(source_version, "source_version")

        if curriculum_node_id not in self._nodes:
            raise ValueError(
                f"curriculum_node_id {curriculum_node_id!r} does not exist"
            )

        if mapping_id in self._intensiq_mappings:
            raise ValueError(f"Duplicate mapping_id: {mapping_id!r}")

        mapping = IntenSIQTopicMapping(
            mapping_id=mapping_id,
            intensiq_topic_id=intensiq_topic_id,
            curriculum_node_id=curriculum_node_id,
            source_version=source_version,
            created_at=self._now(),
        )

        self._intensiq_mappings[mapping_id] = mapping

        if curriculum_node_id not in self._node_mappings:
            self._node_mappings[curriculum_node_id] = []
        self._node_mappings[curriculum_node_id].append(mapping_id)

        return mapping

    def get_intensiq_mapping(self, mapping_id: str) -> Optional[IntenSIQTopicMapping]:
        """Retrieve an IntenSIQ topic mapping by id."""
        return self._intensiq_mappings.get(mapping_id)

    def get_mappings_for_node(self, node_id: str) -> List[IntenSIQTopicMapping]:
        """Return all IntenSIQ mappings for a curriculum node."""
        mapping_ids = self._node_mappings.get(node_id, [])
        return [
            self._intensiq_mappings[mid]
            for mid in mapping_ids
            if mid in self._intensiq_mappings
        ]

    def get_all_mappings(self) -> List[IntenSIQTopicMapping]:
        """Return all IntenSIQ topic mappings."""
        return list(self._intensiq_mappings.values())

    # ------------------------------------------------------------------ #
    #  Registry-wide validation
    # ------------------------------------------------------------------ #

    def validate(self) -> Dict[str, Any]:
        """Validate the entire registry.

        Returns a summary dict with:
        - valid: bool
        - source_count: int
        - node_count: int
        - outcome_count: int
        - link_count: int
        - mapping_count: int
        - untraceable_nodes: list of node_ids
        - duplicate_source_versions: list of (source_id, version) tuples
        """
        untraceable = self.validate_all_nodes()

        # Check for duplicate source versions (shouldn't happen after add_source
        # rejects them, but validate catches any inconsistency)
        duplicate_versions = []
        for source_id, versions in self._sources.items():
            seen = set()
            for v in versions:
                if v in seen:
                    duplicate_versions.append((source_id, v))
                seen.add(v)

        return {
            "valid": len(untraceable) == 0 and len(duplicate_versions) == 0,
            "source_count": sum(len(vs) for vs in self._sources.values()),
            "node_count": len(self._nodes),
            "outcome_count": len(self._outcomes),
            "link_count": len(self._topic_links),
            "mapping_count": len(self._intensiq_mappings),
            "untraceable_nodes": untraceable,
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
            "nodes": {nid: n.__dict__ for nid, n in self._nodes.items()},
            "outcomes": {oid: o.__dict__ for oid, o in self._outcomes.items()},
            "topic_links": {
                lid: l.__dict__ for lid, l in self._topic_links.items()
            },
            "intensiq_mappings": {
                mid: m.__dict__ for mid, m in self._intensiq_mappings.items()
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
        # Strip any non-numeric suffix (e.g., "-beta" -> "")
        numeric_part = ""
        for ch in segment:
            if ch.isdigit():
                numeric_part += ch
            else:
                break
        parts.append(int(numeric_part) if numeric_part else 0)
    return tuple(parts)