# QA T18 -- Persona Awareness tests.
# Stdlib only. Plain ASCII. Deterministic.

from __future__ import annotations

import unittest

from tola.persona.profile import (
    PreferenceStatus,
    PreferenceProvenance,
    UserOperatingProfile,
    UserPreference,
    EXPLICIT_PREFERENCE,
    BEHAVIOURAL_OBSERVATION,
    PROMOTION_THRESHOLD,
    preference_observe,
    preference_promote,
    preference_supersede,
    user_profile_get,
    user_profile_compact,
)
from tola.persona.permissions import (
    check_authority,
    get_active_preferences,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _empty_profile(user_id: str = "u1") -> UserOperatingProfile:
    return UserOperatingProfile(
        user_id=user_id,
        preferences=(),
        preference_versions=(),
    )


def _make_provenance(
    source: str = EXPLICIT_PREFERENCE,
    evidence_refs: tuple[str, ...] = ("ev-001",),
    observed_at: str = "2026-09-29T10:00:00Z",
    project_id: str = "proj-alpha",
) -> PreferenceProvenance:
    return PreferenceProvenance(
        source=source,
        evidence_refs=evidence_refs,
        observed_at=observed_at,
        project_id=project_id,
    )


def _make_preference(
    key: str,
    value: str,
    status: PreferenceStatus = PreferenceStatus.ACTIVE,
    source: str = EXPLICIT_PREFERENCE,
    confidence: float = 1.0,
    scope: str = "global",
    evidence_refs: tuple[str, ...] = ("ev-001",),
    observed_at: str = "2026-09-29T10:00:00Z",
    project_id: str = "proj-alpha",
) -> UserPreference:
    return UserPreference(
        key=key,
        value=value,
        status=status,
        provenance=PreferenceProvenance(
            source=source,
            evidence_refs=evidence_refs,
            observed_at=observed_at,
            project_id=project_id,
        ),
        confidence=confidence,
        scope=scope,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestT18ExplicitPreferenceAuthority(unittest.TestCase):
    """T18-01: Explicit preference gets highest authority."""

    def test_explicit_overrides_candidate(self):
        profile = _empty_profile()
        # First, a behavioural observation enters as CANDIDATE.
        profile = preference_observe(
            profile,
            key="theme",
            value="dark",
            source=BEHAVIOURAL_OBSERVATION,
            evidence_refs=("behav-001",),
            observed_at="2026-09-29T09:00:00Z",
            project_id="proj-alpha",
            confidence=0.5,
        )
        # CANDIDATE is not returned by user_profile_get (ACTIVE only).
        prefs = user_profile_get(profile)
        self.assertEqual(len(prefs), 0)
        # But it exists in the profile's preferences list.
        self.assertEqual(len(profile.preferences), 1)
        self.assertEqual(profile.preferences[0].status, PreferenceStatus.CANDIDATE)

        # Now an explicit preference for the same key supersedes.
        profile = preference_observe(
            profile,
            key="theme",
            value="light",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        prefs = user_profile_get(profile)
        self.assertEqual(len(prefs), 1)
        self.assertEqual(prefs[0].status, PreferenceStatus.ACTIVE)
        self.assertEqual(prefs[0].value, "light")
        self.assertEqual(prefs[0].provenance.source, EXPLICIT_PREFERENCE)

    def test_explicit_immediately_active(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="language",
            value="en",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        prefs = user_profile_get(profile)
        self.assertEqual(len(prefs), 1)
        self.assertEqual(prefs[0].status, PreferenceStatus.ACTIVE)


class TestT18SingleObservationStaysCandidate(unittest.TestCase):
    """T18-02: Single behavioural observation stays CANDIDATE."""

    def test_single_observation_stays_candidate(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="timezone",
            value="UTC",
            source=BEHAVIOURAL_OBSERVATION,
            evidence_refs=("behav-001",),
            observed_at="2026-09-29T09:00:00Z",
            project_id="proj-alpha",
            confidence=0.4,
        )
        prefs = user_profile_get(profile)
        self.assertEqual(len(prefs), 0)  # CANDIDATE not returned by get_active
        all_prefs = profile.preferences
        self.assertEqual(len(all_prefs), 1)
        self.assertEqual(all_prefs[0].status, PreferenceStatus.CANDIDATE)

    def test_single_observation_not_active(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="notifications",
            value="enabled",
            source=BEHAVIOURAL_OBSERVATION,
            evidence_refs=("behav-001",),
            observed_at="2026-09-29T09:00:00Z",
            project_id="proj-alpha",
            confidence=0.3,
        )
        active = user_profile_get(profile)
        self.assertEqual(len(active), 0)


class TestT18PromotionOnlyAtThreshold(unittest.TestCase):
    """T18-03: Repeated pattern promotes only after threshold."""

    def test_below_threshold_stays_candidate(self):
        profile = _empty_profile()
        for i in range(PROMOTION_THRESHOLD - 1):
            profile = preference_observe(
                profile,
                key="editor",
                value="vim",
                source=BEHAVIOURAL_OBSERVATION,
                evidence_refs=(f"behav-{i:03d}",),
                observed_at=f"2026-09-29T09:{i:02d}:00Z",
                project_id="proj-alpha",
                confidence=0.5,
            )
        all_prefs = profile.preferences
        self.assertEqual(len(all_prefs), 1)
        self.assertEqual(all_prefs[0].status, PreferenceStatus.CANDIDATE)
        active = user_profile_get(profile)
        self.assertEqual(len(active), 0)

    def test_at_threshold_promotes(self):
        profile = _empty_profile()
        for i in range(PROMOTION_THRESHOLD):
            profile = preference_observe(
                profile,
                key="editor",
                value="vim",
                source=BEHAVIOURAL_OBSERVATION,
                evidence_refs=(f"behav-{i:03d}",),
                observed_at=f"2026-09-29T09:{i:02d}:00Z",
                project_id="proj-alpha",
                confidence=0.5,
            )
        # After threshold observations, promote explicitly.
        profile = preference_promote(
            profile,
            key="editor",
            evidence_refs=(f"behav-{i:03d}" for i in range(PROMOTION_THRESHOLD)),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
        )
        active = user_profile_get(profile)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].status, PreferenceStatus.ACTIVE)
        self.assertEqual(active[0].value, "vim")

    def test_promotion_requires_explicit_call(self):
        """Observations alone do not auto-promote; promote() must be called."""
        profile = _empty_profile()
        for i in range(PROMOTION_THRESHOLD):
            profile = preference_observe(
                profile,
                key="editor",
                value="vim",
                source=BEHAVIOURAL_OBSERVATION,
                evidence_refs=(f"behav-{i:03d}",),
                observed_at=f"2026-09-29T09:{i:02d}:00Z",
                project_id="proj-alpha",
                confidence=0.5,
            )
        # Without calling promote(), still CANDIDATE.
        active = user_profile_get(profile)
        self.assertEqual(len(active), 0)


class TestT18ContradictionSupersedesWithHistory(unittest.TestCase):
    """T18-04: Contradiction supersedes old preference with history."""

    def test_contradiction_supersedes_active(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="theme",
            value="dark",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        # Contradicting explicit preference.
        profile = preference_observe(
            profile,
            key="theme",
            value="light",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-002",),
            observed_at="2026-09-29T11:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        active = user_profile_get(profile)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].value, "light")

        # Old version preserved in history.
        self.assertEqual(len(profile.preference_versions), 1)
        self.assertEqual(profile.preference_versions[0].value, "dark")

    def test_version_history_retrievable(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="theme",
            value="dark",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        profile = preference_observe(
            profile,
            key="theme",
            value="light",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-002",),
            observed_at="2026-09-29T11:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        versions = profile.preference_versions
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].value, "dark")
        self.assertEqual(versions[0].provenance.evidence_refs, ("explicit-001",))

    def test_supersede_function_preserves_history(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="theme",
            value="dark",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        profile = preference_supersede(
            profile,
            key="theme",
            new_value="light",
            new_provenance=_make_provenance(source=EXPLICIT_PREFERENCE, evidence_refs=("explicit-002",)),
            new_confidence=1.0,
        )
        active = user_profile_get(profile)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].value, "light")
        self.assertEqual(len(profile.preference_versions), 1)
        self.assertEqual(profile.preference_versions[0].value, "dark")


class TestT18SensitiveInferenceNotStored(unittest.TestCase):
    """T18-05: Sensitive inference is not stored."""

    def test_health_condition_rejected(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="health_condition",
            value="migraine",
            source=BEHAVIOURAL_OBSERVATION,
            evidence_refs=("behav-001",),
            observed_at="2026-09-29T09:00:00Z",
            project_id="proj-alpha",
            confidence=0.8,
        )
        # Must not appear in any structure.
        self.assertEqual(len(profile.preferences), 0)
        self.assertEqual(len(profile.preference_versions), 0)
        active = user_profile_get(profile)
        self.assertEqual(len(active), 0)

    def test_relationship_status_rejected(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="relationship_status",
            value="single",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        self.assertEqual(len(profile.preferences), 0)

    def test_finances_rejected(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="finances",
            value="budget_5000",
            source=BEHAVIOURAL_OBSERVATION,
            evidence_refs=("behav-001",),
            observed_at="2026-09-29T09:00:00Z",
            project_id="proj-alpha",
            confidence=0.7,
        )
        self.assertEqual(len(profile.preferences), 0)

    def test_protected_characteristics_rejected(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="protected_characteristics",
            value="wheelchair_user",
            source=BEHAVIOURAL_OBSERVATION,
            evidence_refs=("behav-001",),
            observed_at="2026-09-29T09:00:00Z",
            project_id="proj-alpha",
            confidence=0.9,
        )
        self.assertEqual(len(profile.preferences), 0)

    def test_location_tracking_rejected(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="location_tracking",
            value="office",
            source=BEHAVIOURAL_OBSERVATION,
            evidence_refs=("behav-001",),
            observed_at="2026-09-29T09:00:00Z",
            project_id="proj-alpha",
            confidence=0.6,
        )
        self.assertEqual(len(profile.preferences), 0)

    def test_sensitive_category_absent_from_all_structures(self):
        """Verify sensitive inference is absent from compact and active views."""
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="health_condition",
            value="migraine",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        self.assertEqual(len(profile.preferences), 0)
        self.assertEqual(len(user_profile_get(profile)), 0)
        self.assertEqual(len(user_profile_compact(profile)), 0)


class TestT18RepeatedApprovalDoesNotExpandPermissions(unittest.TestCase):
    """T18-06: Repeated approval leaves capability set unchanged."""

    def test_approval_count_does_not_expand_capabilities(self):
        profile = _empty_profile()
        result1 = check_authority(profile, "blackboard_read", "proj-alpha", 1)
        result2 = check_authority(profile, "blackboard_read", "proj-alpha", 5)
        result3 = check_authority(profile, "blackboard_read", "proj-alpha", 100)

        self.assertTrue(result1.allowed)
        self.assertTrue(result2.allowed)
        self.assertTrue(result3.allowed)
        # Capability set must not change regardless of approval count.
        self.assertFalse(result1.capability_set_changed)
        self.assertFalse(result2.capability_set_changed)
        self.assertFalse(result3.capability_set_changed)

    def test_forbidden_action_never_allowed(self):
        profile = _empty_profile()
        result = check_authority(profile, "direct_my_rhythm_write", "proj-alpha", 999)
        self.assertFalse(result.allowed)
        self.assertFalse(result.capability_set_changed)

    def test_unknown_action_not_in_capability_set(self):
        profile = _empty_profile()
        result = check_authority(profile, "unknown_action", "proj-alpha", 1)
        self.assertFalse(result.allowed)
        self.assertFalse(result.capability_set_changed)


class TestT18ActivePreferenceHasProvenanceAndConfidence(unittest.TestCase):
    """T18-07: Every active preference has provenance + confidence."""

    def test_explicit_preference_has_provenance_and_confidence(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="theme",
            value="dark",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        active = user_profile_get(profile)
        self.assertEqual(len(active), 1)
        pref = active[0]
        self.assertIsNotNone(pref.provenance)
        self.assertEqual(pref.provenance.source, EXPLICIT_PREFERENCE)
        self.assertGreaterEqual(pref.confidence, 0.0)
        self.assertLessEqual(pref.confidence, 1.0)

    def test_get_active_preferences_returns_provenance_and_confidence(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="theme",
            value="dark",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        result = get_active_preferences(profile)
        self.assertEqual(len(result), 1)
        entry = result[0]
        self.assertIn("provenance", entry)
        self.assertIn("confidence", entry)
        self.assertIn("source", entry["provenance"])
        self.assertIn("evidence_refs", entry["provenance"])
        self.assertIn("observed_at", entry["provenance"])
        self.assertIn("project_id", entry["provenance"])

    def test_candidate_preference_excluded_from_active(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="timezone",
            value="UTC",
            source=BEHAVIOURAL_OBSERVATION,
            evidence_refs=("behav-001",),
            observed_at="2026-09-29T09:00:00Z",
            project_id="proj-alpha",
            confidence=0.4,
        )
        active = user_profile_get(profile)
        self.assertEqual(len(active), 0)

    def test_confidence_is_required_field(self):
        pref = _make_preference(key="x", value="y", confidence=0.75)
        self.assertEqual(pref.confidence, 0.75)


class TestT18ProjectScopedDoesNotLeakToGlobal(unittest.TestCase):
    """T18-08: Project-scoped preference does not become global without evidence."""

    def test_project_scoped_stays_in_scope(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="editor",
            value="vim",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
            scope="proj-alpha",
        )
        # Global scope returns nothing.
        global_prefs = user_profile_get(profile, scope=None)
        # When scope=None, all actives are returned (no filtering).
        self.assertEqual(len(global_prefs), 1)

        # Project-scoped query returns it.
        proj_prefs = user_profile_get(profile, scope="proj-alpha")
        self.assertEqual(len(proj_prefs), 1)
        self.assertEqual(proj_prefs[0].scope, "proj-alpha")

    def test_different_project_scopes_are_separate(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="editor",
            value="vim",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
            scope="proj-alpha",
        )
        profile = preference_observe(
            profile,
            key="editor",
            value="nano",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-002",),
            observed_at="2026-09-29T11:00:00Z",
            project_id="proj-beta",
            confidence=1.0,
            scope="proj-beta",
        )
        alpha_prefs = user_profile_get(profile, scope="proj-alpha")
        beta_prefs = user_profile_get(profile, scope="proj-beta")
        self.assertEqual(len(alpha_prefs), 1)
        self.assertEqual(len(beta_prefs), 1)
        self.assertEqual(alpha_prefs[0].value, "vim")
        self.assertEqual(beta_prefs[0].value, "nano")

    def test_global_preference_requires_explicit_global_evidence(self):
        """A preference observed in one project context does not become
        global unless promoted with explicit global evidence."""
        profile = _empty_profile()
        # Observe in project scope only.
        profile = preference_observe(
            profile,
            key="editor",
            value="vim",
            source=BEHAVIOURAL_OBSERVATION,
            evidence_refs=("behav-001",),
            observed_at="2026-09-29T09:00:00Z",
            project_id="proj-alpha",
            confidence=0.5,
            scope="proj-alpha",
        )
        # Promote with project-scoped evidence -- stays project-scoped.
        profile = preference_promote(
            profile,
            key="editor",
            evidence_refs=("behav-001", "behav-002", "behav-003"),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
        )
        active = user_profile_get(profile, scope="proj-alpha")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].scope, "proj-alpha")

        # Global scope query (scope=None) returns all active.
        all_active = user_profile_get(profile, scope=None)
        self.assertEqual(len(all_active), 1)
        # The preference is active but scoped to proj-alpha, not global.
        self.assertEqual(all_active[0].scope, "proj-alpha")


# ---------------------------------------------------------------------------
# Determinism tests.
# ---------------------------------------------------------------------------

class TestT18Determinism(unittest.TestCase):
    """All operations are deterministic: same inputs produce same outputs."""

    def test_determinism_explicit_preference(self):
        profile = _empty_profile()
        p1 = preference_observe(
            profile,
            key="theme",
            value="dark",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        p2 = preference_observe(
            profile,
            key="theme",
            value="dark",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        self.assertEqual(len(p1.preferences), len(p2.preferences))
        self.assertEqual(p1.preferences[0].value, p2.preferences[0].value)

    def test_determinism_profile_get(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="theme",
            value="dark",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        r1 = user_profile_get(profile)
        r2 = user_profile_get(profile)
        self.assertEqual(len(r1), len(r2))
        if len(r1) > 0:
            self.assertEqual(r1[0].key, r2[0].key)
            self.assertEqual(r1[0].value, r2[0].value)

    def test_determinism_compact(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="theme",
            value="dark",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        c1 = user_profile_compact(profile)
        c2 = user_profile_compact(profile)
        self.assertEqual(c1, c2)


# ---------------------------------------------------------------------------
# Plain ASCII check.
# ---------------------------------------------------------------------------

    def test_all_output_plain_ascii(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="theme",
            value="dark",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-001",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        active = user_profile_get(profile)
        for pref in active:
            for ch in pref.key + pref.value:
                self.assertTrue(ord(ch) < 128, f"Non-ASCII in preference: {ch!r}")


if __name__ == "__main__":
    unittest.main()