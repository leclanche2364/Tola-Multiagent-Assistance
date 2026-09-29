"""
Batch S2 -- Scholar Scope Definitions.
SCHOLAR_SCOPES frozenset and ScopeCheck helper.
Plain ASCII. Python 3 stdlib only.
"""

from scholar.intensiq import capability_registry
from scholar.intensiq import denials

# ---------------------------------------------------------------------------
# S2 scopes: exactly four narrow integration scopes, nothing else.
# ---------------------------------------------------------------------------

SCHOLAR_SCOPES = frozenset({
    "learner-state:read",
    "learning-plan:read",
    "learning-plan:write",
    "events:read",
})


# ---------------------------------------------------------------------------
# Route-to-scope mapping for NEW_INTEGRATION_NEEDED routes.
# READ_EXISTING routes are implicitly scoped to their verb (read-only).
# ---------------------------------------------------------------------------

_SCOPE_FOR_ROUTE = {
    "/api/v1/integration/learner-state": "learner-state:read",
    "/api/v1/integration/courses/{courseId}/learning-plan": "learning-plan:read",
    "/api/v1/integration/courses/{courseId}/learning-plan:PUT": "learning-plan:write",
    "/api/v1/integration/events": "events:read",
}


def _route_exists(route):
    """Return True if route appears in the registry under any verb."""
    for entry in capability_registry.CAPABILITY_REGISTRY:
        if entry["route"] == route:
            return True
    return False


def _classification_for_route(route):
    """Return the classification for a route (any verb), or None."""
    for entry in capability_registry.CAPABILITY_REGISTRY:
        if entry["route"] == route:
            return entry["classification"]
    return None


def can(route, verb, scopes):
    """Return True iff the given scopes permit (route, verb).

    Rules (all must hold):
    1. route exists in the capability registry (any verb).
    2. route is READ_EXISTING or NEW_INTEGRATION_NEEDED.
    3. verb is not forbidden (denials.is_forbidden).
    4. learning-plan:write applies ONLY to the learning-plan PUT route.
    5. The required scope for the route is present in *scopes*.
    6. Every other combination is denied.
    """
    # Guard: scopes must be a non-empty iterable of strings
    if not scopes:
        return False

    # Denied routes/verbs are always rejected
    if denials.is_forbidden(route, verb):
        return False

    # Route must exist in the registry
    classification = _classification_for_route(route)
    if classification is None:
        return False

    # Only READ_EXISTING and NEW_INTEGRATION_NEEDED are permitted
    if classification not in ("READ_EXISTING", "NEW_INTEGRATION_NEEDED"):
        return False

    # Determine required scope based on route + verb
    required_scope = None

    if route == "/api/v1/integration/learner-state" and verb == "GET":
        required_scope = "learner-state:read"

    elif route == "/api/v1/integration/events" and verb == "GET":
        required_scope = "events:read"

    elif route == "/api/v1/integration/courses/{courseId}/learning-plan":
        if verb == "GET":
            required_scope = "learning-plan:read"
        elif verb == "PUT":
            required_scope = "learning-plan:write"
        else:
            return False

    # Any other route/verb combination is denied
    return required_scope is not None and required_scope in scopes