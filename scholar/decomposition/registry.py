"""
Batch S10 -- Learning-Goal Decomposition.
Map goals to curriculum nodes, proficiencies, prerequisites, mastery
dimensions, time horizon and evidence requirements.

Deterministic mapping only — no invented curriculum or proficiency
mappings (S10-05).  Missing prerequisites detected (S10-03).
Unrealistic time horizon flagged as risk (S10-04).
Multi-domain goals decompose correctly (S10-02).
Representative goal (mechanical ventilation) maps to relevant
curriculum (S10-01).

Mappings are grounded in the S7/S8 registries, not hard-coded
prompt data.

Plain ASCII. Python 3 stdlib only.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecompositionResult:
    """Result of decomposing a learning goal against curriculum/proficiency
    registries."""
    goal_id: str
    goal_title: str
    goal_state: str
    curriculum_nodes: List[Dict[str, Any]]
    proficiencies: List[Dict[str, Any]]
    prerequisites: List[Dict[str, Any]]
    missing_prerequisites: List[str]
    mastery_dimensions: List[str]
    time_horizon_days: Optional[int]
    time_horizon_risk: bool
    evidence_requirements: List[Dict[str, Any]]
    domain_count: int
    is_multi_domain: bool
    deterministic_key: str  # hash-like key proving deterministic output


@dataclass(frozen=True)
class CurriculumMapping:
    """A single curriculum-node mapping for a goal."""
    goal_id: str
    node_id: str
    node_title: str
    node_kind: str
    source_id: str
    source_version: str
    mastery_dimensions: List[str]
    learning_outcomes: List[str]


@dataclass(frozen=True)
class ProficiencyMapping:
    """A single proficiency mapping for a goal."""
    goal_id: str
    proficiency_id: str
    domain: str
    step: str
    verbatim_requirement: str
    knowledge_requirements: List[str]
    application_requirements: List[str]
    rationale_requirements: List[str]
    linked_topics: List[str]
    linked_learning_outcomes: List[str]
    linked_evidence: List[str]


@dataclass(frozen=True)
class PrerequisiteLink:
    """A prerequisite relationship between curriculum nodes."""
    from_node_id: str
    to_node_id: str
    link_type: str  # "prerequisite" | "builds_on" | "maps_to" | "supersedes"


@dataclass(frozen=True)
class EvidenceRequirement:
    """An evidence requirement derived from a proficiency or curriculum node."""
    goal_id: str
    evidence_id: str
    link_type: str  # "supports" | "contradicts" | "requires" | "informs"
    source: str  # "proficiency" | "curriculum"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _require_non_empty_string(value: Any, name: str) -> str:
    """Validate a non-empty string field. Returns the stripped value."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")
    return value.strip()


def _require_valid_state(state: str) -> str:
    """Validate a goal state is one of the known states."""
    valid = {"ACTIVE", "PAUSED", "COMPLETED", "STOPPED", "SUPERSEDED"}
    if state not in valid:
        raise ValueError(f"state must be one of {sorted(valid)}, got {state!r}")
    return state


# ---------------------------------------------------------------------------
# Deterministic key builder
# ---------------------------------------------------------------------------

def _build_deterministic_key(
    goal_id: str,
    node_ids: List[str],
    prof_ids: List[str],
    prereq_ids: List[str],
    dimensions: List[str],
    horizon: Optional[int],
) -> str:
    """Build a deterministic key from the decomposition components.

    The key is stable across calls with the same inputs, proving
    deterministic repeatability.
    """
    parts = [
        f"goal:{goal_id}",
        f"nodes:{','.join(sorted(node_ids))}",
        f"profs:{','.join(sorted(prof_ids))}",
        f"prereqs:{','.join(sorted(prereq_ids))}",
        f"dims:{','.join(sorted(dimensions))}",
        f"horizon:{horizon}",
    ]
    # Simple deterministic hash: concatenate and take a stable representation
    combined = "|".join(parts)
    # Use a simple deterministic checksum (not cryptographic — just for
    # repeatability verification)
    h = 0
    for ch in combined:
        h = ((h * 31) + ord(ch)) & 0xFFFFFFFF
    return f"{combined}::hash={h:08x}"


# ---------------------------------------------------------------------------
# Decomposition engine
# ---------------------------------------------------------------------------

class LearningGoalDecomposer:
    """Decompose learning goals against curriculum and proficiency registries.

    Key guarantees:
    - Deterministic: same inputs always produce the same output.
    - No invented mappings: only uses curriculum/proficiency data that
      actually exists in the registries.
    - Missing prerequisites are detected and reported.
    - Unrealistic time horizons are flagged as risk.
    - Multi-domain goals are correctly identified.
    - PAUSED/SUPERSEDED goals are handled (decomposition still works;
      state is recorded but no new planning is implied for STOPPED goals).
    - All mappings are grounded in the S7/S8 registries.
    - Clock injection for deterministic testing.
    """

    # Maximum reasonable time horizon in days before risk flag is raised.
    # Six weeks = 42 days is the example from the implementation plan.
    MAX_REASONABLE_HORIZON_DAYS = 42

    # Known mastery dimensions from the S6 mastery model.
    KNOWN_MASTERY_DIMENSIONS = {
        "KNOWLEDGE",
        "RATIONALE",
        "APPLICATION",
        "CRITICAL_ANALYSIS",
        "RECALL",
        "TRANSFER",
        "PRACTICAL_READINESS",
        "FORMAL_COMPETENCE",
    }

    # Stop words filtered out during keyword matching to avoid
    # false positives from single-character or very common tokens.
    STOP_WORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at",
        "to", "for", "of", "with", "by", "from", "is", "are", "was",
        "were", "be", "been", "being", "have", "has", "had", "do",
        "does", "did", "will", "would", "could", "should", "may",
        "might", "shall", "can", "need", "dare", "ought", "used",
        "it", "its", "this", "that", "these", "those", "i", "me",
        "my", "myself", "we", "our", "ours", "ourselves", "you",
        "your", "yours", "yourself", "yourselves", "he", "him", "his",
        "himself", "she", "her", "hers", "herself", "they", "them",
        "their", "theirs", "themselves", "what", "which", "who",
        "whom", "when", "where", "why", "how", "all", "each", "every",
        "both", "few", "more", "most", "other", "some", "such",
        "no", "nor", "not", "only", "own", "same", "so", "than",
        "too", "very", "s", "t", "just", "don", "now",
    }

    def __init__(
        self,
        curriculum_registry: "CurriculumRegistry",
        proficiency_registry: "ProficiencyRegistry",
        goal_registry: "GoalRegistry",
        clock: Optional[callable] = None,
    ) -> None:
        self._curriculum = curriculum_registry
        self._proficiency = proficiency_registry
        self._goals = goal_registry
        self._clock = clock or datetime.utcnow

    # ------------------------------------------------------------------ #
    #  Main decomposition
    # ------------------------------------------------------------------ #

    def decompose(
        self,
        goal_id: str,
        goal_version: Optional[int] = None,
    ) -> DecompositionResult:
        """Decompose a learning goal against curriculum and proficiency
        registries.

        Returns a DecompositionResult with all mappings, prerequisites,
        missing prerequisites, mastery dimensions, time horizon, risk
        flags, and evidence requirements.

        Raises ValueError on:
        - goal_id does not exist
        - goal_id is not a string
        """
        goal_id = _require_non_empty_string(goal_id, "goal_id")

        goal = self._goals.get_goal(goal_id, version=goal_version)
        if goal is None:
            raise ValueError(f"goal_id {goal_id!r} does not exist")

        # Decompose the goal title and description into domain keywords
        # and map them to curriculum nodes and proficiencies.
        domain_keywords = self._extract_domain_keywords(goal)

        # Map to curriculum nodes
        curriculum_mappings = self._map_to_curriculum(domain_keywords, goal)

        # Map to proficiencies
        proficiency_mappings = self._map_to_proficiencies(domain_keywords, goal)

        # Resolve prerequisites from curriculum topic links
        prerequisites, missing_prerequisites = self._resolve_prerequisites(
            curriculum_mappings
        )

        # Collect mastery dimensions from outcomes and proficiencies
        mastery_dimensions = self._collect_mastery_dimensions(
            curriculum_mappings, proficiency_mappings
        )

        # Determine time horizon from goal title/description
        time_horizon_days = self._extract_time_horizon(goal)
        time_horizon_risk = (
            time_horizon_days is not None
            and time_horizon_days > self.MAX_REASONABLE_HORIZON_DAYS
        )

        # Collect evidence requirements from proficiencies
        evidence_requirements = self._collect_evidence_requirements(
            proficiency_mappings
        )

        # Determine domain count and multi-domain flag.
        # Domains come from proficiency mappings only; curriculum
        # nodes do not carry a separate domain field.
        domains = set()
        for pm in proficiency_mappings:
            domains.add(pm.domain)

        domain_count = len(domains)
        is_multi_domain = domain_count > 1

        # Build deterministic key
        deterministic_key = _build_deterministic_key(
            goal_id=goal_id,
            node_ids=[cm.node_id for cm in curriculum_mappings],
            prof_ids=[pm.proficiency_id for pm in proficiency_mappings],
            prereq_ids=[pl.from_node_id for pl in prerequisites],
            dimensions=mastery_dimensions,
            horizon=time_horizon_days,
        )

        return DecompositionResult(
            goal_id=goal_id,
            goal_title=goal.title,
            goal_state=goal.state,
            curriculum_nodes=[
                {
                    "node_id": cm.node_id,
                    "node_title": cm.node_title,
                    "node_kind": cm.node_kind,
                    "source_id": cm.source_id,
                    "source_version": cm.source_version,
                    "mastery_dimensions": cm.mastery_dimensions,
                    "learning_outcomes": cm.learning_outcomes,
                }
                for cm in curriculum_mappings
            ],
            proficiencies=[
                {
                    "proficiency_id": pm.proficiency_id,
                    "domain": pm.domain,
                    "step": pm.step,
                    "verbatim_requirement": pm.verbatim_requirement,
                    "knowledge_requirements": pm.knowledge_requirements,
                    "application_requirements": pm.application_requirements,
                    "rationale_requirements": pm.rationale_requirements,
                    "linked_topics": pm.linked_topics,
                    "linked_learning_outcomes": pm.linked_learning_outcomes,
                    "linked_evidence": pm.linked_evidence,
                }
                for pm in proficiency_mappings
            ],
            prerequisites=[
                {
                    "from_node_id": pl.from_node_id,
                    "to_node_id": pl.to_node_id,
                    "link_type": pl.link_type,
                }
                for pl in prerequisites
            ],
            missing_prerequisites=missing_prerequisites,
            mastery_dimensions=mastery_dimensions,
            time_horizon_days=time_horizon_days,
            time_horizon_risk=time_horizon_risk,
            evidence_requirements=[
                {
                    "evidence_id": er.evidence_id,
                    "link_type": er.link_type,
                    "source": er.source,
                }
                for er in evidence_requirements
            ],
            domain_count=domain_count,
            is_multi_domain=is_multi_domain,
            deterministic_key=deterministic_key,
        )

    # ------------------------------------------------------------------ #
    #  Domain keyword extraction
    # ------------------------------------------------------------------ #

    # Word-number mapping for deterministic time-horizon parsing.
    WORD_NUMBERS = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20,
        "thirty": 30, "forty": 40, "fifty": 50,
        "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
        "hundred": 100,
    }

    def _extract_domain_keywords(self, goal) -> Dict[str, List[str]]:
        """Extract domain keywords from goal title and description.

        Returns a dict with 'domains' (set of domain strings) and
        'keywords' (list of lowercase tokens).  This is a deterministic,
        text-based extraction — no invented mappings.

        Tokens are filtered to exclude stop words and single-character
        tokens to avoid false-positive substring matches.
        """
        text = f"{goal.title} {goal.description}".lower()
        import re
        raw_tokens = re.findall(r"[a-z][a-z0-9_-]*", text)

        # Filter stop words and tokens shorter than 2 characters
        tokens = [
            t for t in raw_tokens
            if t not in self.STOP_WORDS and len(t) >= 2
        ]

        domain_keywords: Dict[str, List[str]] = {
            "domains": [],
            "keywords": tokens,
        }

        return domain_keywords

    # ------------------------------------------------------------------ #
    #  Curriculum mapping
    # ------------------------------------------------------------------ #

    def _map_to_curriculum(
        self,
        domain_keywords: Dict[str, List[str]],
        goal,
    ) -> List[CurriculumMapping]:
        """Map goal keywords to curriculum nodes.

        Only returns nodes that actually exist in the curriculum registry.
        No invented mappings.

        Uses word-boundary matching: a token must appear as a complete
        word (or hyphenated component) within the node text, not as a
        substring of an unrelated word.
        """
        mappings: List[CurriculumMapping] = []
        seen_node_ids: set = set()

        tokens = domain_keywords.get("keywords", [])

        for node in self._curriculum._nodes.values():
            if node.node_id in seen_node_ids:
                continue

            # Build searchable text from node title, kind, content keys,
            # and content values (excluding internal IDs like module_id).
            searchable_parts = [node.title, node.kind]
            for v in node.content.values():
                if isinstance(v, str):
                    searchable_parts.append(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            searchable_parts.append(item)
            node_text = " ".join(searchable_parts).lower()

            matched = False
            for token in tokens:
                # Word-boundary match: token must appear as a whole word
                # within the node text, not as a substring of another word.
                if re.search(rf"\b{re.escape(token)}\b", node_text):
                    matched = True
                    break

            if not matched:
                continue

            outcomes = self._curriculum.get_outcomes_by_node(node.node_id)
            outcome_ids = [o.outcome_id for o in outcomes]
            dims = set()
            for o in outcomes:
                for d in o.mastery_dimensions:
                    if d in self.KNOWN_MASTERY_DIMENSIONS:
                        dims.add(d)

            mappings.append(
                CurriculumMapping(
                    goal_id=goal.goal_id,
                    node_id=node.node_id,
                    node_title=node.title,
                    node_kind=node.kind,
                    source_id=node.source_id,
                    source_version=node.source_version,
                    mastery_dimensions=sorted(dims),
                    learning_outcomes=outcome_ids,
                )
            )
            seen_node_ids.add(node.node_id)

        return mappings

    # ------------------------------------------------------------------ #
    #  Proficiency mapping
    # ------------------------------------------------------------------ #

    def _map_to_proficiencies(
        self,
        domain_keywords: Dict[str, List[str]],
        goal,
    ) -> List[ProficiencyMapping]:
        """Map goal keywords to proficiency records.

        S10-05: If a proficiency is unknown (not in the registry), no
        invented mapping is created.  Only existing proficiencies are
        returned.

        Uses word-boundary matching: a token must appear as a complete
        word within the proficiency text, not as a substring of an
        unrelated word.
        """
        mappings: List[ProficiencyMapping] = []
        seen_prof_ids: set = set()

        tokens = domain_keywords.get("keywords", [])

        for prof in self._proficiency._proficiencies.values():
            for version, record in prof.items():
                if record.proficiency_id in seen_prof_ids:
                    continue

                # Build searchable text from domain, verbatim requirement,
                # and linked topics.
                searchable_parts = [
                    record.domain,
                    record.verbatim_requirement,
                ] + record.linked_topics
                prof_text = " ".join(searchable_parts).lower()

                matched = False
                for token in tokens:
                    if re.search(rf"\b{re.escape(token)}\b", prof_text):
                        matched = True
                        break

                if matched:
                    mappings.append(
                        ProficiencyMapping(
                            goal_id=goal.goal_id,
                            proficiency_id=record.proficiency_id,
                            domain=record.domain,
                            step=record.step,
                            verbatim_requirement=record.verbatim_requirement,
                            knowledge_requirements=record.knowledge_requirements,
                            application_requirements=record.application_requirements,
                            rationale_requirements=record.rationale_requirements,
                            linked_topics=record.linked_topics,
                            linked_learning_outcomes=record.linked_learning_outcomes,
                            linked_evidence=record.linked_evidence,
                        )
                    )
                    seen_prof_ids.add(record.proficiency_id)
                    break

        return mappings

    # ------------------------------------------------------------------ #
    #  Prerequisite resolution
    # ------------------------------------------------------------------ #

    def _resolve_prerequisites(
        self,
        curriculum_mappings: List[CurriculumMapping],
    ) -> Tuple[List[PrerequisiteLink], List[str]]:
        """Resolve prerequisite links for mapped curriculum nodes.

        Returns (prerequisites, missing_prerequisites).

        S10-03: Missing prerequisites are detected — a prerequisite
        is "missing" when the from_node of a prerequisite link is not
        in the mapped curriculum nodes.
        """
        prerequisites: List[PrerequisiteLink] = []
        missing_prerequisites: List[str] = []

        mapped_node_ids = {cm.node_id for cm in curriculum_mappings}

        for cm in curriculum_mappings:
            # Look at all links where this node is the from_node
            links = self._curriculum.get_topic_links_for_node(cm.node_id)
            for link in links:
                if link.link_type == "prerequisite":
                    prereq_node = self._curriculum.get_node(link.to_node_id)
                    if prereq_node is None:
                        # The prerequisite target node doesn't exist in
                        # the registry — this is a missing prerequisite
                        missing_prerequisites.append(
                            f"prerequisite node {link.to_node_id!r} "
                            f"for {cm.node_id!r} does not exist in registry"
                        )
                    else:
                        prerequisites.append(
                            PrerequisiteLink(
                                from_node_id=cm.node_id,
                                to_node_id=link.to_node_id,
                                link_type=link.link_type,
                            )
                        )
                        # If the prerequisite node is not in our mapped
                        # set, it is a missing prerequisite for this goal
                        if link.to_node_id not in mapped_node_ids:
                            missing_prerequisites.append(
                                f"prerequisite node {link.to_node_id!r} "
                                f"({prereq_node.title}) is not covered by "
                                f"the goal decomposition"
                            )

        return prerequisites, missing_prerequisites

    # ------------------------------------------------------------------ #
    #  Mastery dimensions
    # ------------------------------------------------------------------ #

    def _collect_mastery_dimensions(
        self,
        curriculum_mappings: List[CurriculumMapping],
        proficiency_mappings: List[ProficiencyMapping],
    ) -> List[str]:
        """Collect all mastery dimensions from curriculum outcomes and
        proficiency records."""
        dims: set = set()
        for cm in curriculum_mappings:
            for d in cm.mastery_dimensions:
                if d in self.KNOWN_MASTERY_DIMENSIONS:
                    dims.add(d)
        # Proficiency records don't carry mastery_dimensions directly,
        # but their linked_learning_outcomes may reference outcomes that
        # do.  We already collect dimensions from curriculum outcomes.
        return sorted(dims)

    # ------------------------------------------------------------------ #
    #  Time horizon extraction
    # ------------------------------------------------------------------ #

    def _extract_time_horizon(self, goal) -> Optional[int]:
        """Extract time horizon in days from goal title and description.

        Looks for patterns like 'within N weeks', 'N weeks', 'N days',
        'N months', and also word-number variants like 'within six weeks'.
        Returns None if no time horizon is stated.
        Flags horizons > MAX_REASONABLE_HORIZON_DAYS as risk (S10-04).
        """
        import re

        text = f"{goal.title} {goal.description}"

        # Try digit-based patterns first: "within 6 weeks", "42 days", etc.
        weeks_match = re.search(
            r"(?:within\s+)?(\d+)\s+weeks?", text, re.IGNORECASE
        )
        if weeks_match:
            return int(weeks_match.group(1)) * 7

        days_match = re.search(
            r"(?:within\s+)?(\d+)\s+days?", text, re.IGNORECASE
        )
        if days_match:
            return int(days_match.group(1))

        months_match = re.search(
            r"(?:within\s+)?(\d+)\s+months?", text, re.IGNORECASE
        )
        if months_match:
            return int(months_match.group(1)) * 30

        # Try word-number patterns: "within six weeks", "three months", etc.
        weeks_word_match = re.search(
            r"(?:within\s+)?(" + "|".join(self.WORD_NUMBERS.keys()) + r")\s+weeks?",
            text,
            re.IGNORECASE,
        )
        if weeks_word_match:
            word = weeks_word_match.group(1).lower()
            return self.WORD_NUMBERS[word] * 7

        days_word_match = re.search(
            r"(?:within\s+)?(" + "|".join(self.WORD_NUMBERS.keys()) + r")\s+days?",
            text,
            re.IGNORECASE,
        )
        if days_word_match:
            word = days_word_match.group(1).lower()
            return self.WORD_NUMBERS[word]

        months_word_match = re.search(
            r"(?:within\s+)?(" + "|".join(self.WORD_NUMBERS.keys()) + r")\s+months?",
            text,
            re.IGNORECASE,
        )
        if months_word_match:
            word = months_word_match.group(1).lower()
            return self.WORD_NUMBERS[word] * 30

        return None

    # ------------------------------------------------------------------ #
    #  Evidence requirements
    # ------------------------------------------------------------------ #

    def _collect_evidence_requirements(
        self,
        proficiency_mappings: List[ProficiencyMapping],
    ) -> List[EvidenceRequirement]:
        """Collect evidence requirements from proficiency records."""
        requirements: List[EvidenceRequirement] = []

        for pm in proficiency_mappings:
            for evidence_id in pm.linked_evidence:
                requirements.append(
                    EvidenceRequirement(
                        goal_id=pm.goal_id,
                        evidence_id=evidence_id,
                        link_type="supports",
                        source="proficiency",
                    )
                )

        return requirements

    # ------------------------------------------------------------------ #
    #  Public helpers
    # ------------------------------------------------------------------ #

    def decompose_goal(
        self,
        goal_id: str,
        goal_version: Optional[int] = None,
    ) -> DecompositionResult:
        """Public alias for decompose() — kept for API compatibility."""
        return self.decompose(goal_id, goal_version=goal_version)
