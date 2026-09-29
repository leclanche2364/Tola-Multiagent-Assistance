"""Tola Agent Capability and Boundary Registry -- Batch T4.

Provides agent operating profiles, capability routing, boundary
enforcement, and availability/delegation checks.  Stdlib only.
Plain ASCII.  Deterministic: no clock reads inside logic.
"""

from tola.registry.profiles import (
    AVAILABLE,
    DISABLED,
    DEGRADED,
    FUTURE_NOT_AVAILABLE,
    ACTIVE,
    AgentProfile,
    PROFILES,
    PROFILE_VERSION_HISTORY,
    update_profile_version,
)
from tola.registry.capability import (
    agent_capability_get,
    agent_capability_match,
    agent_boundary_check,
    agent_current_load_get,
    ROUTING_TABLE,
)
from tola.registry.boundaries import (
    enforce_boundary,
    record_profile_version_change,
)
from tola.registry.availability import (
    DelegationBlockedError,
    check_delegation_allowed,
    FUTURE_SPECIALIST_DEPENDENCY,
    record_future_specialist_dependency,
    validate_marketing_activation,
)

__all__ = [
    "ACTIVE",
    "FUTURE_NOT_AVAILABLE",
    "DISABLED",
    "DEGRADED",
    "AVAILABLE",
    "AgentProfile",
    "PROFILES",
    "PROFILE_VERSION_HISTORY",
    "update_profile_version",
    "agent_capability_get",
    "agent_capability_match",
    "agent_boundary_check",
    "agent_current_load_get",
    "ROUTING_TABLE",
    "enforce_boundary",
    "record_profile_version_change",
    "DelegationBlockedError",
    "check_delegation_allowed",
    "FUTURE_SPECIALIST_DEPENDENCY",
    "record_future_specialist_dependency",
    "validate_marketing_activation",
]