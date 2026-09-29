"""
Batch S1 -- IntenSIQ Denial Structure.
Forbidden verbs/endpoints and helper to check whether a route+verb is denied.
Plain ASCII. Python 3 stdlib only.
"""

FORBIDDEN_VERBS = frozenset({
    "PUT",
    "POST",
    "DELETE",
    "PATCH",
})

ENDPOINTS = frozenset({
    "/api/v1/progress",
    "/api/v1/practice",
    "/api/v1/assessment",
    "/api/v1/courses/{courseId}",
    "/api/v1/courses/{courseId}/topics/{topicId}",
    "/api/v1/users/{userId}",
})

# Canonicalised route patterns for matching
_FORBIDDEN_PATTERNS = frozenset({
    "/api/v1/progress",
    "/api/v1/practice",
    "/api/v1/assessment",
    "/api/v1/courses/",  # prefix match for course/topic delete
    "/api/v1/users/",    # prefix match for user mutation
})


def _matches_forbidden(route):
    """Check if route matches any forbidden endpoint pattern."""
    if route in ENDPOINTS:
        return True
    # Prefix matches
    for pattern in _FORBIDDEN_PATTERNS:
        if route.startswith(pattern) and pattern.endswith("/"):
            return True
    return False


def is_forbidden(route, verb):
    """Return True if the route+verb combination is forbidden for Scholar.

    Forbidden: progress write, practice write, assessment submit,
    course/topic delete, user mutation.
    """
    if verb not in FORBIDDEN_VERBS:
        return False
    return _matches_forbidden(route)
