"""
Batch S1 -- IntenSIQ Capability Registry.
Classifies every IntenSIQ route referenced in the implementation plan.
Plain ASCII. Python 3 stdlib only.
"""

CAPABILITY_REGISTRY = [
    # --- Existing IntenSIQ routes (section 8) ---
    {
        "route": "/api/v1/courses",
        "verb": "GET",
        "classification": "READ_EXISTING",
        "rationale": "Plan section 8: course/topic/content read is an existing IntenSIQ capability (handover doc).",
    },
    {
        "route": "/api/v1/courses/{courseId}/topics",
        "verb": "GET",
        "classification": "READ_EXISTING",
        "rationale": "Plan section 8: course/topic/content read is an existing IntenSIQ capability (handover doc).",
    },
    {
        "route": "/api/v1/courses/{courseId}/topics/{topicId}/content",
        "verb": "GET",
        "classification": "READ_EXISTING",
        "rationale": "Plan section 8: course/topic/content read is an existing IntenSIQ capability (handover doc).",
    },
    {
        "route": "/api/v1/goals",
        "verb": "GET",
        "classification": "READ_EXISTING",
        "rationale": "Plan section 8: goals read is an existing IntenSIQ capability (handover doc).",
    },
    {
        "route": "/api/v1/progress",
        "verb": "GET",
        "classification": "READ_EXISTING",
        "rationale": "Plan section 8: progress read is an existing IntenSIQ capability (handover doc).",
    },
    {
        "route": "/api/v1/practice",
        "verb": "GET",
        "classification": "READ_EXISTING",
        "rationale": "Plan section 8: practice read is an existing IntenSIQ capability (handover doc).",
    },
    {
        "route": "/api/v1/tests",
        "verb": "GET",
        "classification": "READ_EXISTING",
        "rationale": "Plan section 8: tests read is an existing IntenSIQ capability (handover doc).",
    },
    {
        "route": "/api/v1/cases",
        "verb": "GET",
        "classification": "READ_EXISTING",
        "rationale": "Plan section 8: cases read is an existing IntenSIQ capability (handover doc).",
    },
    {
        "route": "/api/v1/study-materials",
        "verb": "GET",
        "classification": "READ_EXISTING",
        "rationale": "Plan section 8: study materials read is an existing IntenSIQ capability (handover doc).",
    },
    {
        "route": "/api/v1/recordings",
        "verb": "GET",
        "classification": "READ_EXISTING",
        "rationale": "Plan section 8: recordings read is an existing IntenSIQ capability (handover doc).",
    },
    {
        "route": "/api/v1/reasoning",
        "verb": "GET",
        "classification": "READ_EXISTING",
        "rationale": "Plan section 8: reasoning read is an existing IntenSIQ capability (handover doc).",
    },
    # --- Forbidden writes (mutations Scholar must not perform) ---
    {
        "route": "/api/v1/progress",
        "verb": "PUT",
        "classification": "NOT_FOR_SCHOLAR",
        "rationale": "Plan section 8 + QA S1-02: progress mutation is a learner-evidence write; Scholar must never mark study complete or submit progress (plan section 3, 9, 19).",
    },
    {
        "route": "/api/v1/practice",
        "verb": "PUT",
        "classification": "NOT_FOR_SCHOLAR",
        "rationale": "Plan section 8 + QA S1-02: practice mutation is a learner-evidence write; Scholar must never submit practice (plan section 3, 9, 19).",
    },
    {
        "route": "/api/v1/assessment",
        "verb": "POST",
        "classification": "NOT_FOR_SCHOLAR",
        "rationale": "Plan section 8 + QA S1-02: assessment submit is a learner-evidence write; Scholar must never submit assessments (plan section 3, 9, 19).",
    },
    {
        "route": "/api/v1/courses/{courseId}",
        "verb": "DELETE",
        "classification": "NOT_FOR_SCHOLAR",
        "rationale": "Plan section 3 + QA S1-02: course delete is a destructive write outside Scholar authority; Scholar does not own course lifecycle.",
    },
    {
        "route": "/api/v1/courses/{courseId}/topics/{topicId}",
        "verb": "DELETE",
        "classification": "NOT_FOR_SCHOLAR",
        "rationale": "Plan section 3 + QA S1-02: topic delete is a destructive write outside Scholar authority; Scholar does not own topic lifecycle.",
    },
    {
        "route": "/api/v1/users/{userId}",
        "verb": "PUT",
        "classification": "NOT_FOR_SCHOLAR",
        "rationale": "Plan section 3 + QA S1-02: user mutation is outside Scholar authority; Scholar does not modify user profiles or settings.",
    },
    # --- Three NEW integration additions (plan sections 8.1-8.3) ---
    {
        "route": "/api/v1/integration/learner-state",
        "verb": "GET",
        "classification": "NEW_INTEGRATION_NEEDED",
        "rationale": "Plan section 8.1: learner-state read model (schema_version, state_version, as_of, course, course_goals, proficiency_context, topics with progress/next_action/practice_units/recent_assessments/recent_study_activity, reasoning_evidence, competency_evidence, revision_items, cursor).",
    },
    {
        "route": "/api/v1/integration/courses/{courseId}/learning-plan",
        "verb": "GET/PUT",
        "classification": "NEW_INTEGRATION_NEEDED",
        "rationale": "Plan section 8.2: versioned learning plan read+write (plan_id, goal_id, course_id, version, expected_previous_version, status, objective, target_date, proficiency_refs, ordered_learning_items, weekly_minutes, minimum_session_minutes, review_policy, mastery_targets, rationale, created_by, updated_at). GET/PUT are the two verbs for this single new integration route.",
    },
    {
        "route": "/api/v1/integration/events",
        "verb": "GET",
        "classification": "NEW_INTEGRATION_NEEDED",
        "rationale": "Plan section 8.3: durable learning events outbox (event_id, event_type, schema_version, occurred_at, course_id, topic_id, aggregate_id, payload; 9 event types; cursor pagination).",
    },
]

# Classification counts (derived, for reference)
CLASSIFICATION_COUNTS = {
    "READ_EXISTING": sum(1 for e in CAPABILITY_REGISTRY if e["classification"] == "READ_EXISTING"),
    "WRITE_EXISTING": sum(1 for e in CAPABILITY_REGISTRY if e["classification"] == "WRITE_EXISTING"),
    "NOT_FOR_SCHOLAR": sum(1 for e in CAPABILITY_REGISTRY if e["classification"] == "NOT_FOR_SCHOLAR"),
    "NEW_INTEGRATION_NEEDED": sum(1 for e in CAPABILITY_REGISTRY if e["classification"] == "NEW_INTEGRATION_NEEDED"),
}


def classify(route, verb):
    """Return the classification dict for a route+verb, or None if not found."""
    for entry in CAPABILITY_REGISTRY:
        if entry["route"] == route and entry["verb"] == verb:
            return entry
    return None


def list_by_classification(cls):
    """Return all registry entries matching a classification."""
    return [e for e in CAPABILITY_REGISTRY if e["classification"] == cls]
