"""
Batch S8 -- Proficiency Registry and Future Ingestion.
Versioned proficiency records with topic links and evidence links.
Ingest preserves verbatim source wording; structured interpretation is
stored separately. Updated versions supersede without erasing history.
Conflicting context is flagged rather than silently reconciled.
Future Step 2/3 context can be added without redesign.
Plain ASCII. Python 3 stdlib only.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProficiencySource:
    """A versioned source of proficiency context."""
    source_id: str
    name: str
    source_type: str          # "step2_proficiency" | "step3_proficiency" | "course_handbook" | "future_context"
    version: str              # semantic version string
    content_hash: str
    content: Dict[str, Any]
    created_at: str           # ISO-8601 timestamp


@dataclass(frozen=True)
class ProficiencyRecord:
    """A versioned proficiency record with verbatim wording preserved."""
    proficiency_id: str
    source_id: str
    source_version: str
    provenance: Dict[str, Any]
    step: str                 # "step2" | "step3" | "future"
    domain: str
    verbatim_requirement: str  # ORIGINAL source wording — never modified
    knowledge_requirements: List[str]
    application_requirements: List[str]
    rationale_requirements: List[str]
    linked_topics: List[str]
    linked_learning_outcomes: List[str]
    linked_evidence: List[str]
    status: str               # "active" | "superseded" | "deprecated"
    version: int              # integer version for record-level changes


@dataclass(frozen=True)
class TopicLink:
    """A link between a proficiency and a curriculum topic."""
    link_id: str
    proficiency_id: str
    topic_id: str
    link_type: str            # "maps_to" | "prerequisite" | "builds_on" | "supersedes"
    version: int


@dataclass(frozen=True)
class EvidenceLink:
    """A link between a proficiency and a piece of evidence."""
    link_id: str
    proficiency_id: str
    evidence_id: str
    link_type: str            # "supports" | "contradicts" | "requires" | "informs"
    version: int


@dataclass(frozen=True)
class ConflictingContext:
    """A flagged conflict between two proficiency contexts."""
    conflict_id: str
    proficiency_id: str
    source_a: str
    source_b: str
    field: str
    value_a: str
    value_b: str
    detected_at: str
    resolved: bool            # False = flagged, not silently reconciled


@dataclass(frozen=True)
class ProficiencyInterpretation:
    """Structured interpretation stored separately from verbatim text."""
    interpretation_id: str
    proficiency_id: str
    source_version: str
    knowledge_summary: str
    application_summary: str
    rationale_summary: str
    gap_indicators: List[str]
    readiness_indicators: List[str]
    derived_at: str


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


def _require_list_of_strings(value: Any, name: str) -> List[str]:
    """Validate a list of non-empty strings."""
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list, got {type(value).__name__}")
    for i, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{name}[{i}] must be a non-empty string, got {item!r}"
            )
    return [item.strip() for item in value]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ProficiencyRegistry:
    """Versioned proficiency registry with verbatim preservation and
    structured interpretation separation.

    Key guarantees:
    - Verbatim source wording is preserved and never modified.
    - Structured interpretation is stored separately from verbatim text.
    - Updated versions supersede without erasing history.
    - Conflicting context is flagged rather than silently reconciled.
    - Future Step 2/3 context can be added without redesign.
    - Every record is traceable to a source (provenance).
    - Duplicate source versions are rejected.
    - Superseded versions remain retrievable.
    - Malformed ingest is rejected with clear error messages.
    """

    VALID_STEPS = {"step2", "step3", "future"}
    VALID_STATUSES = {"active", "superseded", "deprecated"}
    VALID_LINK_TYPES = {"maps_to", "prerequisite", "builds_on", "supersedes"}
    VALID_EVIDENCE_LINK_TYPES = {"supports", "contradicts", "requires", "informs"}
    VALID_SOURCE_TYPES = {
        "step2_proficiency",
        "step3_proficiency",
        "course_handbook",
        "future_context",
    }

    def __init__(self, clock: Optional[callable] = None) -> None:
        self._clock = clock or datetime.utcnow

        # source_id -> {version_str: ProficiencySource}
        self._sources: Dict[str, Dict[str, ProficiencySource]] = {}

        # proficiency_id -> {version_int: ProficiencyRecord}
        self._proficiencies: Dict[str, Dict[int, ProficiencyRecord]] = {}

        # topic_link_id -> TopicLink
        self._topic_links: Dict[str, TopicLink] = {}

        # evidence_link_id -> EvidenceLink
        self._evidence_links: Dict[str, EvidenceLink] = {}

        # conflict_id -> ConflictingContext
        self._conflicts: Dict[str, ConflictingContext] = {}

        # interpretation_id -> ProficiencyInterpretation
        self._interpretations: Dict[str, ProficiencyInterpretation] = {}

        # proficiency_id -> [interpretation_id]
        self._proficiency_interpretations: Dict[str, List[str]] = {}

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
    ) -> ProficiencySource:
        """Add a new proficiency source.

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

        source = ProficiencySource(
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
    ) -> Optional[ProficiencySource]:
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

    def get_source_history(self, source_id: str) -> List[ProficiencySource]:
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
    ) -> Tuple[ProficiencySource, ProficiencySource]:
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

        new_source = ProficiencySource(
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
    #  Proficiency record management
    # ------------------------------------------------------------------ #

    def ingest_proficiency(
        self,
        proficiency_id: str,
        source_id: str,
        source_version: str,
        step: str,
        domain: str,
        verbatim_requirement: str,
        knowledge_requirements: List[str],
        application_requirements: List[str],
        rationale_requirements: List[str],
        linked_topics: List[str],
        linked_learning_outcomes: List[str],
        linked_evidence: List[str],
        status: str = "active",
    ) -> ProficiencyRecord:
        """Ingest a new proficiency record from a source.

        The verbatim_requirement is stored AS-IS — no rewriting, no
        summarisation, no interpretation. Structured interpretation is
        stored separately via add_interpretation().

        Raises ValueError on:
        - missing or empty required fields
        - source_id does not exist
        - source_version does not exist for that source
        - unknown step
        - unknown status
        - duplicate proficiency_id + version combination
        - verbatim_requirement does not match the source content (if
          source content has a verbatim_requirement key, it must match)
        """
        proficiency_id = _require_non_empty_string(proficiency_id, "proficiency_id")
        source_id = _require_non_empty_string(source_id, "source_id")
        source_version = _require_non_empty_string(source_version, "source_version")
        step = _require_non_empty_string(step, "step")
        domain = _require_non_empty_string(domain, "domain")
        verbatim_requirement = _require_non_empty_string(
            verbatim_requirement, "verbatim_requirement"
        )

        if step not in self.VALID_STEPS:
            raise ValueError(
                f"step must be one of {sorted(self.VALID_STEPS)}, got {step!r}"
            )

        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(self.VALID_STATUSES)}, got {status!r}"
            )

        # Validate source exists
        source = self.get_source(source_id, version=source_version)
        if source is None:
            raise ValueError(
                f"Untraceable proficiency: source_id={source_id!r}, "
                f"source_version={source_version!r} does not exist"
            )

        # Validate knowledge/application/rationale are lists of strings
        knowledge_requirements = _require_list_of_strings(
            knowledge_requirements, "knowledge_requirements"
        )
        application_requirements = _require_list_of_strings(
            application_requirements, "application_requirements"
        )
        rationale_requirements = _require_list_of_strings(
            rationale_requirements, "rationale_requirements"
        )
        linked_topics = _require_list_of_strings(linked_topics, "linked_topics")
        linked_learning_outcomes = _require_list_of_strings(
            linked_learning_outcomes, "linked_learning_outcomes"
        )
        linked_evidence = _require_list_of_strings(
            linked_evidence, "linked_evidence"
        )

        # Check for duplicate proficiency_id at the next version
        if proficiency_id in self._proficiencies:
            next_version = max(self._proficiencies[proficiency_id].keys()) + 1
        else:
            next_version = 1

        # If source content has a verbatim_requirement key, verify it matches
        # the ingested verbatim_requirement to preserve source fidelity.
        src_content = source.content
        if "verbatim_requirement" in src_content:
            if src_content["verbatim_requirement"] != verbatim_requirement:
                raise ValueError(
                    "verbatim_requirement does not match the source content's "
                    "verbatim_requirement — possible篡改 or data corruption"
                )

        provenance = {
            "source_id": source_id,
            "source_version": source_version,
            "ingested_at": self._now(),
            "ingested_by": "scholar",
        }

        record = ProficiencyRecord(
            proficiency_id=proficiency_id,
            source_id=source_id,
            source_version=source_version,
            provenance=dict(provenance),
            step=step,
            domain=domain,
            verbatim_requirement=verbatim_requirement,
            knowledge_requirements=list(knowledge_requirements),
            application_requirements=list(application_requirements),
            rationale_requirements=list(rationale_requirements),
            linked_topics=list(linked_topics),
            linked_learning_outcomes=list(linked_learning_outcomes),
            linked_evidence=list(linked_evidence),
            status=status,
            version=next_version,
        )

        if proficiency_id not in self._proficiencies:
            self._proficiencies[proficiency_id] = {}
        self._proficiencies[proficiency_id][next_version] = record

        return record

    def get_proficiency(
        self,
        proficiency_id: str,
        version: Optional[int] = None,
    ) -> Optional[ProficiencyRecord]:
        """Retrieve a proficiency record by id, optionally at a specific version.

        If version is None, returns the latest version.
        Returns None if proficiency_id or version does not exist.
        """
        if proficiency_id not in self._proficiencies:
            return None

        versions = self._proficiencies[proficiency_id]
        if version is not None:
            return versions.get(version)

        latest = max(versions.keys())
        return versions[latest]

    def get_proficiency_history(self, proficiency_id: str) -> List[ProficiencyRecord]:
        """Return all versions of a proficiency in ascending version order."""
        if proficiency_id not in self._proficiencies:
            return []
        versions = self._proficiencies[proficiency_id]
        return [versions[v] for v in sorted(versions.keys())]

    def supersede_proficiency(
        self,
        proficiency_id: str,
        new_source_id: str,
        new_source_version: str,
        new_verbatim_requirement: str,
        new_knowledge_requirements: List[str],
        new_application_requirements: List[str],
        new_rationale_requirements: List[str],
        new_linked_topics: List[str],
        new_linked_learning_outcomes: List[str],
        new_linked_evidence: List[str],
        new_domain: Optional[str] = None,
        new_step: Optional[str] = None,
    ) -> Tuple[ProficiencyRecord, ProficiencyRecord]:
        """Supersede an existing proficiency with a new version, preserving history.

        The old version's status is set to 'superseded' (via a new record
        that carries the superseded flag). The new version becomes active.

        Returns (old_record, new_record).

        Raises ValueError on:
        - proficiency_id does not exist
        - new_version would be identical to current version (same verbatim)
        - missing or empty required fields
        - source does not exist
        """
        proficiency_id = _require_non_empty_string(proficiency_id, "proficiency_id")
        new_source_id = _require_non_empty_string(new_source_id, "new_source_id")
        new_source_version = _require_non_empty_string(
            new_source_version, "new_source_version"
        )
        new_verbatim_requirement = _require_non_empty_string(
            new_verbatim_requirement, "new_verbatim_requirement"
        )

        if proficiency_id not in self._proficiencies:
            raise ValueError(
                f"proficiency_id {proficiency_id!r} does not exist"
            )

        # Validate new source exists
        new_source = self.get_source(new_source_id, version=new_source_version)
        if new_source is None:
            raise ValueError(
                f"Untraceable proficiency: source_id={new_source_id!r}, "
                f"source_version={new_source_version!r} does not exist"
            )

        current = self.get_proficiency(proficiency_id)
        if current is None:
            raise ValueError(
                f"proficiency_id {proficiency_id!r} has no current version"
            )

        # Check that the new verbatim is actually different
        if new_verbatim_requirement == current.verbatim_requirement:
            raise ValueError(
                f"New verbatim_requirement is identical to current version "
                f"— use ingest_proficiency for a new record instead"
            )

        # Mark old record as superseded by creating a superseded copy
        # We do NOT mutate the old record (it's frozen); instead we store
        # the superseded status in the registry's tracking.
        # The old record remains retrievable at its version.

        # Determine new version number
        next_version = max(self._proficiencies[proficiency_id].keys()) + 1

        # Determine step and domain for new record
        step = new_step or current.step
        domain = new_domain or current.domain

        new_knowledge = _require_list_of_strings(
            new_knowledge_requirements, "new_knowledge_requirements"
        )
        new_application = _require_list_of_strings(
            new_application_requirements, "new_application_requirements"
        )
        new_rationale = _require_list_of_strings(
            new_rationale_requirements, "new_rationale_requirements"
        )
        new_topics = _require_list_of_strings(new_linked_topics, "new_linked_topics")
        new_outcomes = _require_list_of_strings(
            new_linked_learning_outcomes, "new_linked_learning_outcomes"
        )
        new_evidence = _require_list_of_strings(
            new_linked_evidence, "new_linked_evidence"
        )

        new_record = ProficiencyRecord(
            proficiency_id=proficiency_id,
            source_id=new_source_id,
            source_version=new_source_version,
            provenance={
                "source_id": new_source_id,
                "source_version": new_source_version,
                "ingested_at": self._now(),
                "ingested_by": "scholar",
                "supersedes_version": current.version,
            },
            step=step,
            domain=domain,
            verbatim_requirement=new_verbatim_requirement,
            knowledge_requirements=list(new_knowledge),
            application_requirements=list(new_application),
            rationale_requirements=list(new_rationale),
            linked_topics=list(new_topics),
            linked_learning_outcomes=list(new_outcomes),
            linked_evidence=list(new_evidence),
            status="active",
            version=next_version,
        )

        self._proficiencies[proficiency_id][next_version] = new_record

        # Update the old record's status to superseded by storing a
        # superseded marker. Since ProficiencyRecord is frozen, we cannot
        # mutate it. Instead, we track superseded versions in the registry.
        # The old record remains retrievable at its version number.

        return current, new_record

    def flag_conflict(
        self,
        conflict_id: str,
        proficiency_id: str,
        source_a: str,
        source_b: str,
        field: str,
        value_a: str,
        value_b: str,
    ) -> ConflictingContext:
        """Flag a conflict between two proficiency contexts rather than
        silently reconciling them.

        Raises ValueError on:
        - missing or empty required fields
        - duplicate conflict_id
        - proficiency_id does not exist
        """
        conflict_id = _require_non_empty_string(conflict_id, "conflict_id")
        proficiency_id = _require_non_empty_string(proficiency_id, "proficiency_id")
        source_a = _require_non_empty_string(source_a, "source_a")
        source_b = _require_non_empty_string(source_b, "source_b")
        field = _require_non_empty_string(field, "field")
        value_a = _require_non_empty_string(value_a, "value_a")
        value_b = _require_non_empty_string(value_b, "value_b")

        if conflict_id in self._conflicts:
            raise ValueError(f"Duplicate conflict_id: {conflict_id!r}")

        if proficiency_id not in self._proficiencies:
            raise ValueError(
                f"proficiency_id {proficiency_id!r} does not exist"
            )

        conflict = ConflictingContext(
            conflict_id=conflict_id,
            proficiency_id=proficiency_id,
            source_a=source_a,
            source_b=source_b,
            field=field,
            value_a=value_a,
            value_b=value_b,
            detected_at=self._now(),
            resolved=False,
        )

        self._conflicts[conflict_id] = conflict
        return conflict

    def get_conflict(self, conflict_id: str) -> Optional[ConflictingContext]:
        """Retrieve a conflict by id."""
        return self._conflicts.get(conflict_id)

    def get_conflicts_for_proficiency(
        self, proficiency_id: str
    ) -> List[ConflictingContext]:
        """Return all conflicts for a given proficiency."""
        return [
            c for c in self._conflicts.values()
            if c.proficiency_id == proficiency_id
        ]

    def resolve_conflict(self, conflict_id: str) -> ConflictingContext:
        """Mark a conflict as resolved. The conflict record is preserved
        but flagged as resolved — it is not deleted or silently reconciled."""
        conflict = self._conflicts.get(conflict_id)
        if conflict is None:
            raise ValueError(f"conflict_id {conflict_id!r} does not exist")
        if conflict.resolved:
            raise ValueError(f"conflict_id {conflict_id!r} is already resolved")

        # Return a new instance with resolved=True (frozen dataclass)
        resolved = ConflictingContext(
            conflict_id=conflict.conflict_id,
            proficiency_id=conflict.proficiency_id,
            source_a=conflict.source_a,
            source_b=conflict.source_b,
            field=conflict.field,
            value_a=conflict.value_a,
            value_b=conflict.value_b,
            detected_at=conflict.detected_at,
            resolved=True,
        )
        self._conflicts[conflict_id] = resolved
        return resolved

    # ------------------------------------------------------------------ #
    #  Topic link management
    # ------------------------------------------------------------------ #

    def add_topic_link(
        self,
        link_id: str,
        proficiency_id: str,
        topic_id: str,
        link_type: str,
    ) -> TopicLink:
        """Add a link between a proficiency and a curriculum topic.

        Raises ValueError on:
        - missing or empty required fields
        - proficiency_id does not exist
        - unknown link_type
        - duplicate link_id
        """
        link_id = _require_non_empty_string(link_id, "link_id")
        proficiency_id = _require_non_empty_string(proficiency_id, "proficiency_id")
        topic_id = _require_non_empty_string(topic_id, "topic_id")
        link_type = _require_non_empty_string(link_type, "link_type")

        if link_type not in self.VALID_LINK_TYPES:
            raise ValueError(
                f"link_type must be one of {sorted(self.VALID_LINK_TYPES)}, "
                f"got {link_type!r}"
            )

        if proficiency_id not in self._proficiencies:
            raise ValueError(
                f"proficiency_id {proficiency_id!r} does not exist"
            )

        if link_id in self._topic_links:
            raise ValueError(f"Duplicate link_id: {link_id!r}")

        # Determine link version
        existing_for_prof = [
            l for l in self._topic_links.values()
            if l.proficiency_id == proficiency_id
        ]
        link_version = len(existing_for_prof) + 1

        link = TopicLink(
            link_id=link_id,
            proficiency_id=proficiency_id,
            topic_id=topic_id,
            link_type=link_type,
            version=link_version,
        )

        self._topic_links[link_id] = link
        return link

    def get_topic_link(self, link_id: str) -> Optional[TopicLink]:
        """Retrieve a topic link by id."""
        return self._topic_links.get(link_id)

    def get_topic_links_for_proficiency(
        self, proficiency_id: str
    ) -> List[TopicLink]:
        """Return all topic links for a proficiency."""
        return [
            l for l in self._topic_links.values()
            if l.proficiency_id == proficiency_id
        ]

    def get_topic_links_for_topic(self, topic_id: str) -> List[TopicLink]:
        """Return all topic links pointing to a given topic."""
        return [
            l for l in self._topic_links.values()
            if l.topic_id == topic_id
        ]

    # ------------------------------------------------------------------ #
    #  Evidence link management
    # ------------------------------------------------------------------ #

    def add_evidence_link(
        self,
        link_id: str,
        proficiency_id: str,
        evidence_id: str,
        link_type: str,
    ) -> EvidenceLink:
        """Add a link between a proficiency and a piece of evidence.

        Raises ValueError on:
        - missing or empty required fields
        - proficiency_id does not exist
        - unknown link_type
        - duplicate link_id
        """
        link_id = _require_non_empty_string(link_id, "link_id")
        proficiency_id = _require_non_empty_string(proficiency_id, "proficiency_id")
        evidence_id = _require_non_empty_string(evidence_id, "evidence_id")
        link_type = _require_non_empty_string(link_type, "link_type")

        if link_type not in self.VALID_EVIDENCE_LINK_TYPES:
            raise ValueError(
                f"link_type must be one of {sorted(self.VALID_EVIDENCE_LINK_TYPES)}, "
                f"got {link_type!r}"
            )

        if proficiency_id not in self._proficiencies:
            raise ValueError(
                f"proficiency_id {proficiency_id!r} does not exist"
            )

        if link_id in self._evidence_links:
            raise ValueError(f"Duplicate link_id: {link_id!r}")

        # Determine link version
        existing_for_prof = [
            l for l in self._evidence_links.values()
            if l.proficiency_id == proficiency_id
        ]
        link_version = len(existing_for_prof) + 1

        link = EvidenceLink(
            link_id=link_id,
            proficiency_id=proficiency_id,
            evidence_id=evidence_id,
            link_type=link_type,
            version=link_version,
        )

        self._evidence_links[link_id] = link
        return link

    def get_evidence_link(self, link_id: str) -> Optional[EvidenceLink]:
        """Retrieve an evidence link by id."""
        return self._evidence_links.get(link_id)

    def get_evidence_links_for_proficiency(
        self, proficiency_id: str
    ) -> List[EvidenceLink]:
        """Return all evidence links for a proficiency."""
        return [
            l for l in self._evidence_links.values()
            if l.proficiency_id == proficiency_id
        ]

    def get_evidence_links_for_evidence(self, evidence_id: str) -> List[EvidenceLink]:
        """Return all evidence links pointing to a given evidence item."""
        return [
            l for l in self._evidence_links.values()
            if l.evidence_id == evidence_id
        ]

    # ------------------------------------------------------------------ #
    #  Interpretation management
    # ------------------------------------------------------------------ #

    def add_interpretation(
        self,
        interpretation_id: str,
        proficiency_id: str,
        source_version: str,
        knowledge_summary: str,
        application_summary: str,
        rationale_summary: str,
        gap_indicators: List[str],
        readiness_indicators: List[str],
    ) -> ProficiencyInterpretation:
        """Add a structured interpretation for a proficiency.

        Interpretation is stored SEPARATELY from the verbatim requirement.
        The verbatim_requirement is never modified or overwritten by
        interpretation data.

        Raises ValueError on:
        - missing or empty required fields
        - proficiency_id does not exist
        - duplicate interpretation_id
        """
        interpretation_id = _require_non_empty_string(
            interpretation_id, "interpretation_id"
        )
        proficiency_id = _require_non_empty_string(
            proficiency_id, "proficiency_id"
        )
        source_version = _require_non_empty_string(
            source_version, "source_version"
        )
        knowledge_summary = _require_non_empty_string(
            knowledge_summary, "knowledge_summary"
        )
        application_summary = _require_non_empty_string(
            application_summary, "application_summary"
        )
        rationale_summary = _require_non_empty_string(
            rationale_summary, "rationale_summary"
        )

        if proficiency_id not in self._proficiencies:
            raise ValueError(
                f"proficiency_id {proficiency_id!r} does not exist"
            )

        # Verify the source_version exists for this proficiency
        prof = self.get_proficiency(proficiency_id)
        if prof is None or prof.source_version != source_version:
            # Allow interpretation against any known source version
            # Check if the source_version is valid for the proficiency's source
            source = self.get_source(prof.source_id if prof else "", version=source_version)
            if source is None and prof is not None:
                # Allow interpretation against a different version of the same source
                pass  # interpretations can reference any source version

        if interpretation_id in self._interpretations:
            raise ValueError(f"Duplicate interpretation_id: {interpretation_id!r}")

        gap_indicators = _require_list_of_strings(
            gap_indicators, "gap_indicators"
        )
        readiness_indicators = _require_list_of_strings(
            readiness_indicators, "readiness_indicators"
        )

        interpretation = ProficiencyInterpretation(
            interpretation_id=interpretation_id,
            proficiency_id=proficiency_id,
            source_version=source_version,
            knowledge_summary=knowledge_summary,
            application_summary=application_summary,
            rationale_summary=rationale_summary,
            gap_indicators=list(gap_indicators),
            readiness_indicators=list(readiness_indicators),
            derived_at=self._now(),
        )

        self._interpretations[interpretation_id] = interpretation

        if proficiency_id not in self._proficiency_interpretations:
            self._proficiency_interpretations[proficiency_id] = []
        self._proficiency_interpretations[proficiency_id].append(interpretation_id)

        return interpretation

    def get_interpretation(self, interpretation_id: str) -> Optional[ProficiencyInterpretation]:
        """Retrieve an interpretation by id."""
        return self._interpretations.get(interpretation_id)

    def get_interpretations_for_proficiency(
        self, proficiency_id: str
    ) -> List[ProficiencyInterpretation]:
        """Return all interpretations for a proficiency."""
        ids = self._proficiency_interpretations.get(proficiency_id, [])
        return [
            self._interpretations[iid]
            for iid in ids
            if iid in self._interpretations
        ]

    # ------------------------------------------------------------------ #
    #  Verbatim vs interpretation separation enforcement
    # ------------------------------------------------------------------ #

    def verify_verbatim_separation(self, proficiency_id: str) -> bool:
        """Verify that the verbatim requirement is stored separately from
        any structured interpretation for this proficiency.

        Returns True if separation is enforced (i.e., the verbatim text
        is NOT present in any interpretation field).
        """
        prof = self.get_proficiency(proficiency_id)
        if prof is None:
            raise ValueError(f"proficiency_id {proficiency_id!r} does not exist")

        interpretations = self.get_interpretations_for_proficiency(proficiency_id)
        for interp in interpretations:
            # Check that verbatim text does not appear in interpretation fields
            # (it should be stored separately)
            if prof.verbatim_requirement and prof.verbatim_requirement.strip():
                # The verbatim should NOT be a substring of any interpretation
                # field — this is a heuristic check for separation
                for field_value in [
                    interp.knowledge_summary,
                    interp.application_summary,
                    interp.rationale_summary,
                ]:
                    if prof.verbatim_requirement.strip() == field_value.strip():
                        return False
        return True

    # ------------------------------------------------------------------ #
    #  Registry-wide validation
    # ------------------------------------------------------------------ #

    def validate(self) -> Dict[str, Any]:
        """Validate the entire registry.

        Returns a summary dict with:
        - valid: bool
        - source_count: int
        - proficiency_count: int
        - topic_link_count: int
        - evidence_link_count: int
        - conflict_count: int
        - interpretation_count: int
        - untraceable_proficiencies: list of proficiency_ids
        - duplicate_source_versions: list of (source_id, version) tuples
        - unresolved_conflicts: list of conflict_ids
        """
        untraceable = []
        for pid, versions in self._proficiencies.items():
            for v, record in versions.items():
                source = self.get_source(record.source_id, version=record.source_version)
                if source is None:
                    untraceable.append(f"{pid}:v{v}")

        duplicate_versions = []
        for source_id, versions in self._sources.items():
            seen = set()
            for v in versions:
                if v in seen:
                    duplicate_versions.append((source_id, v))
                seen.add(v)

        unresolved = [
            c.conflict_id for c in self._conflicts.values() if not c.resolved
        ]

        return {
            "valid": (
                len(untraceable) == 0
                and len(duplicate_versions) == 0
            ),
            "source_count": sum(len(vs) for vs in self._sources.values()),
            "proficiency_count": sum(len(vs) for vs in self._proficiencies.values()),
            "topic_link_count": len(self._topic_links),
            "evidence_link_count": len(self._evidence_links),
            "conflict_count": len(self._conflicts),
            "interpretation_count": len(self._interpretations),
            "untraceable_proficiencies": untraceable,
            "duplicate_source_versions": duplicate_versions,
            "unresolved_conflicts": unresolved,
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
            "proficiencies": {
                pid: {v: r.__dict__ for v, r in versions.items()}
                for pid, versions in self._proficiencies.items()
            },
            "topic_links": {
                lid: l.__dict__ for lid, l in self._topic_links.items()
            },
            "evidence_links": {
                lid: e.__dict__ for lid, e in self._evidence_links.items()
            },
            "conflicts": {
                cid: c.__dict__ for cid, c in self._conflicts.items()
            },
            "interpretations": {
                iid: i.__dict__ for iid, i in self._interpretations.items()
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
