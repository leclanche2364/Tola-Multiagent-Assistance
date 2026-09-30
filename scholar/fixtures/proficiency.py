"""
Batch S8 -- Proficiency Registry Fixtures.
Deterministic fixtures for S8 QA: sources, proficiency records,
topic links, evidence links, conflicts, interpretations, and
helper builders.
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
# Sources
# ---------------------------------------------------------------------------

STEP2_PROFICIENCY_SOURCE_V1 = {
    "source_id": "src-step2-cc101",
    "name": "Step 2 Critical Care Proficiencies v1",
    "source_type": "step2_proficiency",
    "version": "1.0",
    "content_hash": "s2v1hash001",
    "content": {
        "course_id": "critical-care-101",
        "step": "step2",
        "verbatim_requirement": "Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, and weaning criteria.",
        "domain": "mechanical_ventilation",
    },
}

STEP2_PROFICIENCY_SOURCE_V2 = {
    "source_id": "src-step2-cc101",
    "name": "Step 2 Critical Care Proficiencies v2",
    "source_type": "step2_proficiency",
    "version": "2.0",
    "content_hash": "s2v2hash002",
    "content": {
        "course_id": "critical-care-101",
        "step": "step2",
        "verbatim_requirement": "Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
        "domain": "mechanical_ventilation",
    },
}

STEP3_PROFICIENCY_SOURCE_V1 = {
    "source_id": "src-step3-cc101",
    "name": "Step 3 Critical Care Proficiencies v1",
    "source_type": "step3_proficiency",
    "version": "1.0",
    "content_hash": "s3v1hash001",
    "content": {
        "course_id": "critical-care-101",
        "step": "step3",
        "verbatim_requirement": "Apply advanced haemodynamic monitoring including arterial line interpretation, central venous pressure analysis, and cardiac output measurement.",
        "domain": "haemodynamic_monitoring",
    },
}

FUTURE_CONTEXT_SOURCE_V1 = {
    "source_id": "src-future-cc101",
    "name": "Future Step 2/3 Context Draft",
    "source_type": "future_context",
    "version": "1.0",
    "content_hash": "futurehash001",
    "content": {
        "course_id": "critical-care-101",
        "step": "future",
        "verbatim_requirement": "Emerging proficiency: Demonstrate familiarity with AI-assisted decision support tools in critical care settings.",
        "domain": "ai_decision_support",
    },
}

# ---------------------------------------------------------------------------
# Proficiency records (verbatim from sources)
# ---------------------------------------------------------------------------

PROFICIENCY_VENT_V1 = {
    "proficiency_id": "prof-vent-01",
    "source_id": "src-step2-cc101",
    "source_version": "1.0",
    "step": "step2",
    "domain": "mechanical_ventilation",
    "verbatim_requirement": "Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, and weaning criteria.",
    "knowledge_requirements": [
        "Understand ventilator modes (AC, SIMV, PSV, CPAP)",
        "Know lung-protective tidal volume targets (6-8 mL/kg IBW)",
        "Understand weaning criteria (RSBI, NIF, SBT)"
    ],
    "application_requirements": [
        "Set initial ventilator parameters for a given clinical scenario",
        "Adjust settings based on ABG and clinical response",
        "Perform a spontaneous breathing trial"
    ],
    "rationale_requirements": [
        "Explain why lung-protective ventilation reduces VILI",
        "Justify weaning readiness based on objective criteria"
    ],
    "linked_topics": ["ventilation-basics", "lung-protective-ventilation", "ventilator-weaning"],
    "linked_learning_outcomes": ["outcome-vent-01", "outcome-vent-02"],
    "linked_evidence": ["evidence-vent-01", "evidence-vent-02"],
    "status": "active",
}

PROFICIENCY_VENT_V2 = {
    "proficiency_id": "prof-vent-01",
    "source_id": "src-step2-cc101",
    "source_version": "2.0",
    "step": "step2",
    "domain": "mechanical_ventilation",
    "verbatim_requirement": "Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications.",
    "knowledge_requirements": [
        "Understand ventilator modes (AC, SIMV, PSV, CPAP)",
        "Know lung-protective tidal volume targets (6-8 mL/kg IBW)",
        "Understand weaning criteria (RSBI, NIF, SBT)",
        "Know ECMO indications and circuit basics"
    ],
    "application_requirements": [
        "Set initial ventilator parameters for a given clinical scenario",
        "Adjust settings based on ABG and clinical response",
        "Perform a spontaneous breathing trial",
        "Identify candidates for ECMO referral"
    ],
    "rationale_requirements": [
        "Explain why lung-protective ventilation reduces VILI",
        "Justify weaning readiness based on objective criteria",
        "Explain when ECMO is indicated over conventional ventilation"
    ],
    "linked_topics": ["ventilation-basics", "lung-protective-ventilation", "ventilator-weaning", "ecmo"],
    "linked_learning_outcomes": ["outcome-vent-01", "outcome-vent-02", "outcome-vent-03"],
    "linked_evidence": ["evidence-vent-01", "evidence-vent-02", "evidence-ecmo-01"],
    "status": "active",
}

PROFICIENCY_HEMO_V1 = {
    "proficiency_id": "prof-hemo-01",
    "source_id": "src-step3-cc101",
    "source_version": "1.0",
    "step": "step3",
    "domain": "haemodynamic_monitoring",
    "verbatim_requirement": "Apply advanced haemodynamic monitoring including arterial line interpretation, central venous pressure analysis, and cardiac output measurement.",
    "knowledge_requirements": [
        "Understand arterial line waveform interpretation",
        "Know normal CVP ranges and clinical significance",
        "Understand cardiac output measurement methods (Fick, thermodilution, pulse contour)"
    ],
    "application_requirements": [
        "Interpret arterial blood pressure waveforms",
        "Calculate cardiac output from Fick principle",
        "Assess fluid responsiveness using dynamic indices"
    ],
    "rationale_requirements": [
        "Explain why arterial line placement is indicated in haemodynamic instability",
        "Justify CVP interpretation in the context of fluid management"
    ],
    "linked_topics": ["haemodynamics-basics", "arterial-line", "fluid-management"],
    "linked_learning_outcomes": ["outcome-hemo-01"],
    "linked_evidence": ["evidence-hemo-01"],
    "status": "active",
}

PROFICIENCY_FUTURE_V1 = {
    "proficiency_id": "prof-ai-01",
    "source_id": "src-future-cc101",
    "source_version": "1.0",
    "step": "future",
    "domain": "ai_decision_support",
    "verbatim_requirement": "Emerging proficiency: Demonstrate familiarity with AI-assisted decision support tools in critical care settings.",
    "knowledge_requirements": [
        "Understand basic principles of AI decision support",
        "Know limitations of AI in clinical settings"
    ],
    "application_requirements": [
        "Evaluate AI-generated recommendations against clinical context"
    ],
    "rationale_requirements": [
        "Explain why AI tools require clinical validation before adoption"
    ],
    "linked_topics": ["ai-basics"],
    "linked_learning_outcomes": [],
    "linked_evidence": [],
    "status": "active",
}

# ---------------------------------------------------------------------------
# Topic links
# ---------------------------------------------------------------------------

TOPIC_LINK_VENT_TO_LUNG = {
    "link_id": "tlink-vent-to-lung",
    "proficiency_id": "prof-vent-01",
    "topic_id": "topic-lung-protective",
    "link_type": "maps_to",
}

TOPIC_LINK_VENT_TO_WEANING = {
    "link_id": "tlink-vent-to-weaning",
    "proficiency_id": "prof-vent-01",
    "topic_id": "topic-ventilator-weaning",
    "link_type": "maps_to",
}

TOPIC_LINK_HEMO_TO_ARTERIAL = {
    "link_id": "tlink-hemo-to-arterial",
    "proficiency_id": "prof-hemo-01",
    "topic_id": "topic-arterial-line",
    "link_type": "maps_to",
}

TOPIC_LINK_VENT_PREREQ = {
    "link_id": "tlink-vent-prereq",
    "proficiency_id": "prof-vent-01",
    "topic_id": "topic-basics",
    "link_type": "prerequisite",
}

# ---------------------------------------------------------------------------
# Evidence links
# ---------------------------------------------------------------------------

EVIDENCE_LINK_VENT_SUPPORTS = {
    "link_id": "elink-vent-evidence-01",
    "proficiency_id": "prof-vent-01",
    "evidence_id": "evidence-vent-01",
    "link_type": "supports",
}

EVIDENCE_LINK_VENT_CONTRADICTS = {
    "link_id": "elink-vent-evidence-02",
    "proficiency_id": "prof-vent-01",
    "evidence_id": "evidence-vent-contradict-01",
    "link_type": "contradicts",
}

EVIDENCE_LINK_HEMO_REQUIRES = {
    "link_id": "elink-hemo-evidence-01",
    "proficiency_id": "prof-hemo-01",
    "evidence_id": "evidence-hemo-01",
    "link_type": "requires",
}

EVIDENCE_LINK_VENT_INFORMS = {
    "link_id": "elink-vent-evidence-03",
    "proficiency_id": "prof-vent-01",
    "evidence_id": "evidence-vent-03",
    "link_type": "informs",
}

# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------

CONFLICT_VENT_DOMAIN_VS_HEMO = {
    "conflict_id": "conflict-vent-domain",
    "proficiency_id": "prof-vent-01",
    "source_a": "src-step2-cc101",
    "source_b": "src-step3-cc101",
    "field": "domain",
    "value_a": "mechanical_ventilation",
    "value_b": "haemodynamic_monitoring",
}

CONFLICT_VENT_VERBATIM_MISMATCH = {
    "conflict_id": "conflict-vent-verbatim",
    "proficiency_id": "prof-vent-01",
    "source_a": "src-step2-cc101",
    "source_b": "src-step2-cc101",
    "field": "verbatim_requirement",
    "value_a": "Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, and weaning criteria.",
    "value_b": "Demonstrate knowledge of mechanical ventilation principles including ventilator modes and weaning criteria only.",
}

# ---------------------------------------------------------------------------
# Interpretations
# ---------------------------------------------------------------------------

INTERPRETATION_VENT_V1 = {
    "interpretation_id": "interp-vent-01",
    "proficiency_id": "prof-vent-01",
    "source_version": "1.0",
    "knowledge_summary": "The learner must understand ventilator modes, lung-protective strategies, and weaning criteria at a theoretical level.",
    "application_summary": "The learner must be able to set and adjust ventilator parameters and perform spontaneous breathing trials in clinical scenarios.",
    "rationale_summary": "The learner must be able to explain the physiological rationale for lung-protective ventilation and weaning readiness.",
    "gap_indicators": ["limited hands-on ventilator experience", "uncertainty about weaning criteria"],
    "readiness_indicators": ["can describe ventilator modes", "understands lung-protective targets"],
}

INTERPRETATION_VENT_V2 = {
    "interpretation_id": "interp-vent-02",
    "proficiency_id": "prof-vent-01",
    "source_version": "2.0",
    "knowledge_summary": "The learner must understand ventilator modes, lung-protective strategies, weaning criteria, and ECMO indications at a theoretical level.",
    "application_summary": "The learner must be able to set and adjust ventilator parameters, perform spontaneous breathing trials, and identify candidates for ECMO referral.",
    "rationale_summary": "The learner must be able to explain the physiological rationale for lung-protective ventilation, weaning readiness, and when ECMO is indicated.",
    "gap_indicators": ["limited ECMO knowledge", "uncertainty about weaning criteria"],
    "readiness_indicators": ["can describe ventilator modes", "understands lung-protective targets", "knows ECMO indications"],
}

INTERPRETATION_HEMO_V1 = {
    "interpretation_id": "interp-hemo-01",
    "proficiency_id": "prof-hemo-01",
    "source_version": "1.0",
    "knowledge_summary": "The learner must understand arterial waveform interpretation, CVP ranges, and cardiac output measurement methods.",
    "application_summary": "The learner must be able to interpret arterial waveforms, calculate cardiac output, and assess fluid responsiveness.",
    "rationale_summary": "The learner must be able to justify arterial line placement and interpret CVP in fluid management context.",
    "gap_indicators": ["limited arterial line experience", "uncertainty about CVP interpretation"],
    "readiness_indicators": ["can describe arterial waveforms", "understands CVP ranges"],
}

# ---------------------------------------------------------------------------
# Malformed / edge-case fixtures
# ---------------------------------------------------------------------------

MALFORMED_PROFICIENCY_MISSING_VERBATIM = {
    "proficiency_id": "prof-bad-1",
    "source_id": "src-step2-cc101",
    "source_version": "1.0",
    "step": "step2",
    "domain": "mechanical_ventilation",
    "verbatim_requirement": "",  # empty — should be rejected
    "knowledge_requirements": ["Know ventilator modes"],
    "application_requirements": ["Set ventilator parameters"],
    "rationale_requirements": ["Explain lung-protective rationale"],
    "linked_topics": ["ventilation-basics"],
    "linked_learning_outcomes": ["outcome-vent-01"],
    "linked_evidence": ["evidence-vent-01"],
}

MALFORMED_PROFICIENCY_MISSING_SOURCE = {
    "proficiency_id": "prof-bad-2",
    "source_id": "src-nonexistent",
    "source_version": "1.0",
    "step": "step2",
    "domain": "mechanical_ventilation",
    "verbatim_requirement": "Some verbatim text",
    "knowledge_requirements": ["Know something"],
    "application_requirements": ["Do something"],
    "rationale_requirements": ["Explain something"],
    "linked_topics": [],
    "linked_learning_outcomes": [],
    "linked_evidence": [],
}

MALFORMED_PROFICIENCY_BAD_STEP = {
    "proficiency_id": "prof-bad-3",
    "source_id": "src-step2-cc101",
    "source_version": "1.0",
    "step": "step4",  # invalid
    "domain": "mechanical_ventilation",
    "verbatim_requirement": "Some verbatim text",
    "knowledge_requirements": ["Know something"],
    "application_requirements": ["Do something"],
    "rationale_requirements": ["Explain something"],
    "linked_topics": [],
    "linked_learning_outcomes": [],
    "linked_evidence": [],
}

MALFORMED_PROFICIENCY_BAD_STATUS = {
    "proficiency_id": "prof-bad-4",
    "source_id": "src-step2-cc101",
    "source_version": "1.0",
    "step": "step2",
    "domain": "mechanical_ventilation",
    "verbatim_requirement": "Some verbatim text",
    "knowledge_requirements": ["Know something"],
    "application_requirements": ["Do something"],
    "rationale_requirements": ["Explain something"],
    "linked_topics": [],
    "linked_learning_outcomes": [],
    "linked_evidence": [],
    "status": "invalid_status",  # invalid
}

MALFORMED_PROFICIENCY_NON_STRING_KNOWLEDGE = {
    "proficiency_id": "prof-bad-5",
    "source_id": "src-step2-cc101",
    "source_version": "1.0",
    "step": "step2",
    "domain": "mechanical_ventilation",
    "verbatim_requirement": "Some verbatim text",
    "knowledge_requirements": [123],  # non-string
    "application_requirements": ["Do something"],
    "rationale_requirements": ["Explain something"],
    "linked_topics": [],
    "linked_learning_outcomes": [],
    "linked_evidence": [],
}

MALFORMED_PROFICIENCY_EMPTY_KNOWLEDGE = {
    "proficiency_id": "prof-bad-6",
    "source_id": "src-step2-cc101",
    "source_version": "1.0",
    "step": "step2",
    "domain": "mechanical_ventilation",
    "verbatim_requirement": "Some verbatim text",
    "knowledge_requirements": [],  # empty
    "application_requirements": ["Do something"],
    "rationale_requirements": ["Explain something"],
    "linked_topics": [],
    "linked_learning_outcomes": [],
    "linked_evidence": [],
}

MALFORMED_TOPIC_LINK_MISSING_PROFICIENCY = {
    "link_id": "tlink-bad-1",
    "proficiency_id": "prof-nonexistent",
    "topic_id": "topic-basics",
    "link_type": "maps_to",
}

MALFORMED_TOPIC_LINK_BAD_TYPE = {
    "link_id": "tlink-bad-2",
    "proficiency_id": "prof-vent-01",
    "topic_id": "topic-basics",
    "link_type": "invalid_type",
}

MALFORMED_EVIDENCE_LINK_MISSING_PROFICIENCY = {
    "link_id": "elink-bad-1",
    "proficiency_id": "prof-nonexistent",
    "evidence_id": "evidence-01",
    "link_type": "supports",
}

MALFORMED_EVIDENCE_LINK_BAD_TYPE = {
    "link_id": "elink-bad-2",
    "proficiency_id": "prof-vent-01",
    "evidence_id": "evidence-01",
    "link_type": "invalid_link_type",
}

MALFORMED_CONFLICT_MISSING_PROFICIENCY = {
    "conflict_id": "conflict-bad-1",
    "proficiency_id": "prof-nonexistent",
    "source_a": "src-a",
    "source_b": "src-b",
    "field": "domain",
    "value_a": "val_a",
    "value_b": "val_b",
}

MALFORMED_INTERPRETATION_MISSING_PROFICIENCY = {
    "interpretation_id": "interp-bad-1",
    "proficiency_id": "prof-nonexistent",
    "source_version": "1.0",
    "knowledge_summary": "Summary",
    "application_summary": "Summary",
    "rationale_summary": "Summary",
    "gap_indicators": [],
    "readiness_indicators": [],
}

MALFORMED_INTERPRETATION_EMPTY_SUMMARY = {
    "interpretation_id": "interp-bad-2",
    "proficiency_id": "prof-vent-01",
    "source_version": "1.0",
    "knowledge_summary": "",  # empty
    "application_summary": "Summary",
    "rationale_summary": "Summary",
    "gap_indicators": [],
    "readiness_indicators": [],
}

# ---------------------------------------------------------------------------
# Duplicate attempt fixtures
# ---------------------------------------------------------------------------

DUPLICATE_PROFICIENCY_INGEST_ATTEMPT = {
    "proficiency_id": "prof-vent-01",
    "source_id": "src-step2-cc101",
    "source_version": "1.0",
    "step": "step2",
    "domain": "mechanical_ventilation",
    "verbatim_requirement": "Demonstrate knowledge of mechanical ventilation principles including ventilator modes, lung-protective strategies, and weaning criteria.",
    "knowledge_requirements": ["Know ventilator modes"],
    "application_requirements": ["Set ventilator parameters"],
    "rationale_requirements": ["Explain lung-protective rationale"],
    "linked_topics": ["ventilation-basics"],
    "linked_learning_outcomes": ["outcome-vent-01"],
    "linked_evidence": ["evidence-vent-01"],
}

DUPLICATE_TOPIC_LINK_ATTEMPT = {
    "link_id": "tlink-vent-to-lung",  # same as TOPIC_LINK_VENT_TO_LUNG
    "proficiency_id": "prof-vent-01",
    "topic_id": "topic-lung-protective",
    "link_type": "maps_to",
}

DUPLICATE_EVIDENCE_LINK_ATTEMPT = {
    "link_id": "elink-vent-evidence-01",  # same as EVIDENCE_LINK_VENT_SUPPORTS
    "proficiency_id": "prof-vent-01",
    "evidence_id": "evidence-vent-01",
    "link_type": "supports",
}

DUPLICATE_CONFLICT_ATTEMPT = {
    "conflict_id": "conflict-vent-domain",  # same as CONFLICT_VENT_DOMAIN_VS_HEMO
    "proficiency_id": "prof-vent-01",
    "source_a": "src-step2-cc101",
    "source_b": "src-step3-cc101",
    "field": "domain",
    "value_a": "mechanical_ventilation",
    "value_b": "haemodynamic_monitoring",
}

DUPLICATE_INTERPRETATION_ATTEMPT = {
    "interpretation_id": "interp-vent-01",  # same as INTERPRETATION_VENT_V1
    "proficiency_id": "prof-vent-01",
    "source_version": "1.0",
    "knowledge_summary": "Different summary",
    "application_summary": "Different summary",
    "rationale_summary": "Different summary",
    "gap_indicators": [],
    "readiness_indicators": [],
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def make_registry(clock=None) -> "ProficiencyRegistry":
    """Create a fresh ProficiencyRegistry with deterministic clock."""
    from scholar.curriculum.proficiency_registry import ProficiencyRegistry
    return ProficiencyRegistry(clock=clock or _fake_now)


def make_source(**overrides) -> dict:
    """Build a source dict with optional overrides."""
    base = dict(STEP2_PROFICIENCY_SOURCE_V1)
    base.update(overrides)
    return base


def make_proficiency(**overrides) -> dict:
    """Build a proficiency dict with optional overrides."""
    base = dict(PROFICIENCY_VENT_V1)
    base.update(overrides)
    return base


def make_topic_link(**overrides) -> dict:
    """Build a topic link dict with optional overrides."""
    base = dict(TOPIC_LINK_VENT_TO_LUNG)
    base.update(overrides)
    return base


def make_evidence_link(**overrides) -> dict:
    """Build an evidence link dict with optional overrides."""
    base = dict(EVIDENCE_LINK_VENT_SUPPORTS)
    base.update(overrides)
    return base


def make_conflict(**overrides) -> dict:
    """Build a conflict dict with optional overrides."""
    base = dict(CONFLICT_VENT_DOMAIN_VS_HEMO)
    base.update(overrides)
    return base


def make_interpretation(**overrides) -> dict:
    """Build an interpretation dict with optional overrides."""
    base = dict(INTERPRETATION_VENT_V1)
    base.update(overrides)
    return base


def make_supersede_payload(**overrides) -> dict:
    """Build a supersede payload dict with optional overrides."""
    base = dict(PROFICIENCY_VENT_V2)
    base.update(overrides)
    return base
