"""
Batch S7 -- Curriculum Registry Fixtures.
Deterministic fixtures for S7 QA: sources, nodes, outcomes,
topic links, IntenSIQ mappings, and helper builders.
Plain ASCII. Python 3 stdlib only.
"""

# ---------------------------------------------------------------------------
# Clock helper (deterministic)
# ---------------------------------------------------------------------------

def _fake_now():
    """Deterministic timestamp for testing."""
    from datetime import datetime
    return datetime(2026, 9, 30, 12, 0, 0)


# ---------------------------------------------------------------------------
# Handbook source (version 1.0)
# ---------------------------------------------------------------------------

HANDBOOK_SOURCE_V1 = {
    "source_id": "src-handbook-cc101",
    "name": "Critical Care 101 Course Handbook",
    "source_type": "handbook",
    "version": "1.0",
    "content_hash": "a1b2c3d4e5f6",
    "content": {
        "title": "Critical Care 101 Course Handbook",
        "course_id": "critical-care-101",
        "modules": [
            {
                "module_id": "mod-ventilation",
                "title": "Mechanical Ventilation",
                "sections": [
                    {
                        "section_id": "sec-vent-basics",
                        "title": "Ventilation Basics",
                        "topics": ["ventilation-basics", "ventilator-modes"],
                    },
                    {
                        "section_id": "sec-vent-advanced",
                        "title": "Advanced Ventilation Strategies",
                        "topics": ["lung-protective-ventilation", "prone-positioning"],
                    },
                ],
            },
            {
                "module_id": "mod-sepsis",
                "title": "Sepsis Management",
                "sections": [
                    {
                        "section_id": "sec-sepsis-basics",
                        "title": "Sepsis Recognition",
                        "topics": ["sepsis-basics", "qsofa"],
                    },
                    {
                        "section_id": "sec-sepsis-treatment",
                        "title": "Sepsis Treatment",
                        "topics": ["antibiotic-stewardship", "fluid-resuscitation"],
                    },
                ],
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Assignment guidance source (version 1.0)
# ---------------------------------------------------------------------------

ASSIGNMENT_GUIDANCE_SOURCE_V1 = {
    "source_id": "src-assignment-cc101",
    "name": "Critical Care 101 Assignment Guidance",
    "source_type": "assignment_guidance",
    "version": "1.0",
    "content_hash": "f6e5d4c3b2a1",
    "content": {
        "title": "Critical Care 101 Assignment Guidance",
        "course_id": "critical-care-101",
        "assignments": [
            {
                "assignment_id": "asm-vent-01",
                "title": "Ventilation Case Analysis",
                "linked_topics": ["ventilation-basics", "lung-protective-ventilation"],
                "max_words": 2000,
                "rubric": ["knowledge", "application", "rationale"],
            },
            {
                "assignment_id": "asm-sepsis-01",
                "title": "Sepsis Management Plan",
                "linked_topics": ["sepsis-basics", "antibiotic-stewardship"],
                "max_words": 1500,
                "rubric": ["knowledge", "application", "critical_analysis"],
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# IntenSIQ topic structure source (version 1.0)
# ---------------------------------------------------------------------------

INTENSIQ_TOPIC_SOURCE_V1 = {
    "source_id": "src-intensiq-cc101",
    "name": "IntenSIQ Critical Care 101 Topic Structure",
    "source_type": "intensiq_topic",
    "version": "1.0",
    "content_hash": "1a2b3c4d5e6f",
    "content": {
        "course_id": "critical-care-101",
        "topics": [
            {
                "topic_id": "intensiq-topic-vent-01",
                "title": "Ventilation Basics",
                "intenSIQ_path": "/courses/cc101/topics/ventilation-basics",
                "learning_outcomes": [
                    "outcome-vent-01",
                    "outcome-vent-02",
                ],
            },
            {
                "topic_id": "intensiq-topic-vent-02",
                "title": "Lung Protective Ventilation",
                "intenSIQ_path": "/courses/cc101/topics/lung-protective",
                "learning_outcomes": [
                    "outcome-vent-03",
                ],
            },
            {
                "topic_id": "intensiq-topic-sepsis-01",
                "title": "Sepsis Recognition",
                "intenSIQ_path": "/courses/cc101/topics/sepsis-recognition",
                "learning_outcomes": [
                    "outcome-sepsis-01",
                ],
            },
            {
                "topic_id": "intensiq-topic-sepsis-02",
                "title": "Antibiotic Stewardship",
                "intenSIQ_path": "/courses/cc101/topics/antibiotic-stewardship",
                "learning_outcomes": [
                    "outcome-sepsis-02",
                ],
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Handbook source version 2.0 (supersedes v1.0)
# ---------------------------------------------------------------------------

HANDBOOK_SOURCE_V2 = {
    "source_id": "src-handbook-cc101",
    "name": "Critical Care 101 Course Handbook",
    "source_type": "handbook",
    "version": "2.0",
    "content_hash": "z9y8x7w6v5u4",
    "content": {
        "title": "Critical Care 101 Course Handbook",
        "course_id": "critical-care-101",
        "modules": [
            {
                "module_id": "mod-ventilation",
                "title": "Mechanical Ventilation",
                "sections": [
                    {
                        "section_id": "sec-vent-basics",
                        "title": "Ventilation Basics",
                        "topics": ["ventilation-basics", "ventilator-modes", "ventilator-weaning"],
                    },
                    {
                        "section_id": "sec-vent-advanced",
                        "title": "Advanced Ventilation Strategies",
                        "topics": ["lung-protective-ventilation", "prone-positioning", "ecmo"],
                    },
                ],
            },
            {
                "module_id": "mod-sepsis",
                "title": "Sepsis Management",
                "sections": [
                    {
                        "section_id": "sec-sepsis-basics",
                        "title": "Sepsis Recognition",
                        "topics": ["sepsis-basics", "qsofa", "procalcitonin"],
                    },
                    {
                        "section_id": "sec-sepsis-treatment",
                        "title": "Sepsis Treatment",
                        "topics": ["antibiotic-stewardship", "fluid-resuscitation", "vasopressors"],
                    },
                ],
            },
            {
                "module_id": "mod-hemodynamics",
                "title": "Hemodynamics",
                "sections": [
                    {
                        "section_id": "sec-hemo-basics",
                        "title": "Hemodynamic Monitoring",
                        "topics": ["blood-pressure-monitoring", "cardiac-output"],
                    },
                ],
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Nodes (traceable to sources)
# ---------------------------------------------------------------------------

HANDBOOK_NODE_VENT_BASICS = {
    "node_id": "node-vent-basics",
    "source_id": "src-handbook-cc101",
    "source_version": "1.0",
    "provenance": {
        "source_id": "src-handbook-cc101",
        "source_version": "1.0",
        "ingested_at": "2026-09-30T12:00:00",
        "ingested_by": "scholar",
        "section": "sec-vent-basics",
    },
    "title": "Ventilation Basics",
    "kind": "section",
    "content": {
        "topics": ["ventilation-basics", "ventilator-modes"],
        "module_id": "mod-ventilation",
    },
}

HANDBOOK_NODE_SEPSIS_BASICS = {
    "node_id": "node-sepsis-basics",
    "source_id": "src-handbook-cc101",
    "source_version": "1.0",
    "provenance": {
        "source_id": "src-handbook-cc101",
        "source_version": "1.0",
        "ingested_at": "2026-09-30T12:00:00",
        "ingested_by": "scholar",
        "section": "sec-sepsis-basics",
    },
    "title": "Sepsis Recognition",
    "kind": "section",
    "content": {
        "topics": ["sepsis-basics", "qsofa"],
        "module_id": "mod-sepsis",
    },
}

ASSIGNMENT_NODE_VENT_CASE = {
    "node_id": "node-vent-case-asm",
    "source_id": "src-assignment-cc101",
    "source_version": "1.0",
    "provenance": {
        "source_id": "src-assignment-cc101",
        "source_version": "1.0",
        "ingested_at": "2026-09-30T12:00:00",
        "ingested_by": "scholar",
        "assignment_id": "asm-vent-01",
    },
    "title": "Ventilation Case Analysis",
    "kind": "unit",
    "content": {
        "assignment_id": "asm-vent-01",
        "linked_topics": ["ventilation-basics", "lung-protective-ventilation"],
        "max_words": 2000,
    },
}

# ---------------------------------------------------------------------------
# Learning outcomes
# ---------------------------------------------------------------------------

OUTCOME_VENT_01 = {
    "outcome_id": "outcome-vent-01",
    "node_id": "node-vent-basics",
    "description": "Explain the basic principles of mechanical ventilation.",
    "mastery_dimensions": ["KNOWLEDGE", "RECALL"],
}

OUTCOME_VENT_02 = {
    "outcome_id": "outcome-vent-02",
    "node_id": "node-vent-basics",
    "description": "Identify common ventilator modes and their indications.",
    "mastery_dimensions": ["KNOWLEDGE", "APPLICATION"],
}

OUTCOME_SEPSIS_01 = {
    "outcome_id": "outcome-sepsis-01",
    "node_id": "node-sepsis-basics",
    "description": "Recognize early signs of sepsis using qSOFA criteria.",
    "mastery_dimensions": ["KNOWLEDGE", "APPLICATION"],
}

# ---------------------------------------------------------------------------
# Topic links
# ---------------------------------------------------------------------------

LINK_VENT_BASICS_TO_LUNG_PROTECTIVE = {
    "link_id": "link-vent-to-lung",
    "from_node_id": "node-vent-basics",
    "to_node_id": "node-vent-basics",  # self-link for same module progression
    "link_type": "builds_on",
}

LINK_SEPSIS_TO_VENT = {
    "link_id": "link-sepsis-to-vent",
    "from_node_id": "node-sepsis-basics",
    "to_node_id": "node-vent-basics",
    "link_type": "prerequisite",
}

# ---------------------------------------------------------------------------
# IntenSIQ topic mappings
# ---------------------------------------------------------------------------

INTENSIQ_MAPPING_VENT = {
    "mapping_id": "map-intensiq-vent-01",
    "intensiq_topic_id": "intensiq-topic-vent-01",
    "curriculum_node_id": "node-vent-basics",
    "source_version": "1.0",
}

INTENSIQ_MAPPING_SEPSIS = {
    "mapping_id": "map-intensiq-sepsis-01",
    "intensiq_topic_id": "intensiq-topic-sepsis-01",
    "curriculum_node_id": "node-sepsis-basics",
    "source_version": "1.0",
}

# ---------------------------------------------------------------------------
# Malformed / edge-case fixtures
# ---------------------------------------------------------------------------

# Source with missing required fields
MALFORMED_SOURCE_MISSING_ID = {
    "source_id": "",
    "name": "Missing ID Source",
    "source_type": "handbook",
    "version": "1.0",
    "content_hash": "badhash",
    "content": {},
}

MALFORMED_SOURCE_MISSING_TYPE = {
    "source_id": "src-bad-1",
    "name": "Missing Type Source",
    "source_type": "",
    "version": "1.0",
    "content_hash": "badhash",
    "content": {},
}

MALFORMED_SOURCE_UNKNOWN_TYPE = {
    "source_id": "src-bad-2",
    "name": "Unknown Type Source",
    "source_type": "unknown_type",
    "version": "1.0",
    "content_hash": "badhash",
    "content": {},
}

MALFORMED_SOURCE_MISSING_VERSION = {
    "source_id": "src-bad-3",
    "name": "Missing Version Source",
    "source_type": "handbook",
    "version": "",
    "content_hash": "badhash",
    "content": {},
}

MALFORMED_SOURCE_MISSING_HASH = {
    "source_id": "src-bad-4",
    "name": "Missing Hash Source",
    "source_type": "handbook",
    "version": "1.0",
    "content_hash": "",
    "content": {},
}

# Node with missing provenance
MALFORMED_NODE_MISSING_PROVENANCE = {
    "node_id": "node-bad-1",
    "source_id": "src-handbook-cc101",
    "source_version": "1.0",
    "provenance": {},  # missing required keys
    "title": "Bad Node",
    "kind": "section",
    "content": {},
}

MALFORMED_NODE_MISSING_SOURCE = {
    "node_id": "node-bad-2",
    "source_id": "src-nonexistent",
    "source_version": "1.0",
    "provenance": {
        "source_id": "src-nonexistent",
        "source_version": "1.0",
        "ingested_at": "2026-09-30T12:00:00",
        "ingested_by": "scholar",
    },
    "title": "Untraceable Node",
    "kind": "section",
    "content": {},
}

MALFORMED_NODE_MISSING_PROVENANCE_KEY = {
    "node_id": "node-bad-3",
    "source_id": "src-handbook-cc101",
    "source_version": "1.0",
    "provenance": {
        "source_id": "src-handbook-cc101",
        # missing ingested_at
        "ingested_by": "scholar",
    },
    "title": "Incomplete Provenance Node",
    "kind": "section",
    "content": {},
}

# Duplicate source version attempt
DUPLICATE_SOURCE_VERSION_ATTEMPT = {
    "source_id": "src-handbook-cc101",
    "name": "Critical Care 101 Course Handbook",
    "source_type": "handbook",
    "version": "1.0",  # same version as HANDBOOK_SOURCE_V1
    "content_hash": "different-hash",
    "content": {"title": "Different content"},
}

# Duplicate node_id attempt
DUPLICATE_NODE_ATTEMPT = {
    "node_id": "node-vent-basics",  # same as HANDBOOK_NODE_VENT_BASICS
    "source_id": "src-handbook-cc101",
    "source_version": "1.0",
    "provenance": {
        "source_id": "src-handbook-cc101",
        "source_version": "1.0",
        "ingested_at": "2026-09-30T12:00:00",
        "ingested_by": "scholar",
        "section": "sec-vent-basics",
    },
    "title": "Duplicate Node",
    "kind": "section",
    "content": {},
}

# Untraceable node (source exists but version doesn't)
UNTRACEABLE_NODE_WRONG_VERSION = {
    "node_id": "node-untraceable",
    "source_id": "src-handbook-cc101",
    "source_version": "99.0",  # doesn't exist
    "provenance": {
        "source_id": "src-handbook-cc101",
        "source_version": "99.0",
        "ingested_at": "2026-09-30T12:00:00",
        "ingested_by": "scholar",
    },
    "title": "Untraceable Node",
    "kind": "section",
    "content": {},
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def make_registry(clock=None) -> "CurriculumRegistry":
    """Create a fresh CurriculumRegistry with deterministic clock."""
    from scholar.curriculum.registry import CurriculumRegistry
    return CurriculumRegistry(clock=clock or _fake_now)


def make_source(**overrides) -> dict:
    """Build a source dict with optional overrides."""
    base = dict(HANDBOOK_SOURCE_V1)
    base.update(overrides)
    return base


def make_node(**overrides) -> dict:
    """Build a node dict with optional overrides."""
    base = dict(HANDBOOK_NODE_VENT_BASICS)
    base.update(overrides)
    return base


def make_outcome(**overrides) -> dict:
    """Build an outcome dict with optional overrides."""
    base = dict(OUTCOME_VENT_01)
    base.update(overrides)
    return base


def make_topic_link(**overrides) -> dict:
    """Build a topic link dict with optional overrides."""
    base = dict(LINK_VENT_BASICS_TO_LUNG_PROTECTIVE)
    base.update(overrides)
    return base


def make_intensiq_mapping(**overrides) -> dict:
    """Build an IntenSIQ mapping dict with optional overrides."""
    base = dict(INTENSIQ_MAPPING_VENT)
    base.update(overrides)
    return base