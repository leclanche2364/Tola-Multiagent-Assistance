"""
Batch S2 -- Scholar Authentication Policy.
AUTH_POLICY document-object and check_access function.
Plain ASCII. Python 3 stdlib only.
"""

from scholar.intensiq import denials
from scholar.intensiq import scopes

# ---------------------------------------------------------------------------
# AUTH_POLICY document-object describing the credential design.
# ---------------------------------------------------------------------------

AUTH_POLICY = {
    "credential_design": {
        "description": (
            "Narrow integration scopes bound to Scholar's integration contract. "
            "Credentials carry exactly the four S2 scopes and nothing else."
        ),
        "scopes": list(scopes.SCHOLAR_SCOPES),
        "scope_count": 4,
    },
    "principles": {
        "no_user_mutation": (
            "Scholar credentials must never include write/delete access to "
            "user profiles or settings. The /api/v1/users/{userId} route is "
            "forbidden regardless of scope."
        ),
        "no_delete_operations": (
            "DELETE verbs are forbidden for Scholar on all routes. "
            "Course and topic deletion is outside Scholar authority."
        ),
        "wrong_user_denial": (
            "When the requesting user_id does not match the scholar_bound_user "
            "the request is denied. Credentials are bound to a single user "
            "and cannot be reused across users."
        ),
        "no_action_approval_target_approval": (
            "Action approval (e.g. granting a scope) never includes target "
            "approval (e.g. permission to point that scope at another user's "
            "data). A credentialed scope is not permission to point it "
            "elsewhere. The scope grants access only to the bound user's "
            "own data."
        ),
    },
    "forbidden_classifications": [
        "NOT_FOR_SCHOLAR",
    ],
    "allowed_classifications": [
        "READ_EXISTING",
        "NEW_INTEGRATION_NEEDED",
    ],
}


def check_access(route, verb, user_id, scholar_bound_user):
    """Check whether a request is allowed under the S2 auth policy.

    Returns (allowed: bool, reason: str).

    Denial rules (checked in order):
    1. Wrong user: user_id != scholar_bound_user -> denied (S2-08).
    2. Forbidden route/verb: denials.is_forbidden -> denied (S2-05..S2-07).
    3. Scope check: scopes.can(route, verb, SCHOLAR_SCOPES) must be True
       for the four allowed scoped reads/writes (S2-01..S2-04).
       Every other combination is denied.
    """
    # S2-08: wrong-user denial
    if user_id != scholar_bound_user:
        return (False, "wrong_user: user_id does not match scholar_bound_user")

    # S2-05..S2-07: forbidden route/verb denial
    if denials.is_forbidden(route, verb):
        return (False, "forbidden_route_or_verb: route+verb is not permitted for Scholar")

    # S2-01..S2-04: scope-based allow; everything else denied
    if scopes.can(route, verb, scopes.SCHOLAR_SCOPES):
        return (True, "allowed: scope and route match Scholar integration contract")

    return (False, "denied: route or verb not covered by Scholar scopes")