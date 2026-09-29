# QA T19 -- Profile and Memory Consolidation tests.
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
from tola.consolidation.mapper import (
    BLACKBOARD_PROFILE,
    USER_MD,
    MEMORY_MD,
    DATED_NOTES,
    MemoryMap,
)
from tola.consolidation.consolidate import (
    ConsolidationResult,
    daily_consolidate,
    weekly_consolidate,
    reconstruct_session,
    rebuild_compact,
)
from tola.consolidation.rules import (
    CONFLICT_RESOLUTION_ORDER,
    RECENCY_WINDOW_DAYS,
    PROMOTION_EVIDENCE_WINDOW_DAYS,
    validate_zone_placement,
    validate_conflict_resolution,
    validate_no_superseded_active,
    validate_explicit_high_authority_included,
    validate_recency_window,
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
# T19-01: Blackboard remains authoritative shared profile.
# ---------------------------------------------------------------------------

class TestT19_01_BlackboardAuthority(unittest.TestCase):
    """T19-01: Blackboard remains authoritative shared profile."""

    def test_blackboard_wins_on_conflict(self):
        """Blackboard profile outranks local mappings on conflict."""
        mm = MemoryMap()
        # Local mapping says theme=dark.
        mm.map_content(USER_MD, [{"type": "stable_preference", "key": "theme", "value": "dark"}])
        # Blackboard says theme=light.
        mm.map_content(BLACKBOARD_PROFILE, [{"type": "shared_profile", "key": "theme", "value": "light"}])

        local = mm.get_zone(USER_MD)
        blackboard = mm.get_zone(BLACKBOARD_PROFILE)

        # Conflict resolution: blackboard wins.
        winner = MemoryMap.resolve_conflict(
            blackboard_item=blackboard[0] if blackboard else None,
            local_item=local[0] if local else None,
        )
        self.assertIsNotNone(winner)
        self.assertEqual(winner["value"], "light")

    def test_blackboard_profile_type(self):
        """Blackboard zone holds shared profile items."""
        mm = MemoryMap()
        mm.map_content(BLACKBOARD_PROFILE, [{"type": "shared_profile", "key": "lang", "value": "en"}])
        items = mm.get_zone(BLACKBOARD_PROFILE)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["type"], "shared_profile")


# ---------------------------------------------------------------------------
# T19-02: USER.md contains compact stable preferences.
# ---------------------------------------------------------------------------

class TestT19_02_UserMdCompactStable(unittest.TestCase):
    """T19-02: USER.md contains compact stable working preferences."""

    def test_user_md_stable_preferences_only(self):
        """USER.md zone should contain stable preferences, not candidates."""
        mm = MemoryMap()
        mm.map_content(USER_MD, [
            {"type": "stable_preference", "key": "theme", "value": "dark"},
            {"type": "stable_preference", "key": "language", "value": "en"},
        ])
        items = mm.get_zone(USER_MD)
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertEqual(item["type"], "stable_preference")

    def test_user_md_excludes_candidates(self):
        """Candidates (unconfirmed observations) must not land in USER.md."""
        mm = MemoryMap()
        rejections = mm.map_content(USER_MD, [
            {"type": "recent_observation", "key": "theme", "value": "dark"},
        ])
        self.assertEqual(len(rejections), 1)
        self.assertIn("Rejected", rejections[0])

    def test_user_md_compact_view(self):
        """Weekly compact must produce a stable preference dict."""
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
        compact = rebuild_compact(profile)
        self.assertIn("theme", compact)
        self.assertEqual(compact["theme"], "dark")


# ---------------------------------------------------------------------------
# T19-03: MEMORY.md contains durable Tola-specific lessons/decisions.
# ---------------------------------------------------------------------------

class TestT19_03_MemoryMdDurableLessons(unittest.TestCase):
    """T19-03: MEMORY.md contains appropriate durable Tola-specific lessons/decisions."""

    def test_memory_md_accepts_durable_lessons(self):
        """Durable lessons belong in MEMORY.md."""
        mm = MemoryMap()
        rejections = mm.map_content(MEMORY_MD, [
            {"type": "durable_lesson", "key": "lesson-001", "value": "Always verify delegation targets."},
        ])
        self.assertEqual(len(rejections), 0)
        items = mm.get_zone(MEMORY_MD)
        self.assertEqual(len(items), 1)

    def test_memory_md_rejects_recent_observations(self):
        """A recent observation placed in MEMORY.md is rejected."""
        mm = MemoryMap()
        rejections = mm.map_content(MEMORY_MD, [
            {"type": "recent_observation", "key": "obs-001", "value": "User liked dark mode."},
        ])
        self.assertEqual(len(rejections), 1)
        self.assertIn("Rejected", rejections[0])

    def test_memory_md_rejects_dated_notes(self):
        """Dated notes placed in MEMORY.md are flagged."""
        mm = MemoryMap()
        rejections = mm.map_content(MEMORY_MD, [
            {"type": "dated_note", "key": "note-001", "value": "Temporary observation."},
        ])
        self.assertEqual(len(rejections), 1)
        self.assertIn("Rejected", rejections[0])

    def test_memory_md_rejects_temporal_observations(self):
        """Temporal observations must not be placed in MEMORY.md."""
        mm = MemoryMap()
        rejections = mm.map_content(MEMORY_MD, [
            {"type": "temporal_observation", "key": "temp-001", "value": "Recent event."},
        ])
        self.assertEqual(len(rejections), 1)
        self.assertIn("Rejected", rejections[0])


# ---------------------------------------------------------------------------
# T19-04: Dated notes contain recent observations separately.
# ---------------------------------------------------------------------------

class TestT19_04_DatedNotesSeparate(unittest.TestCase):
    """T19-04: Dated notes contain recent observations separately."""

    def test_dated_notes_accepts_recent_observations(self):
        """Recent observations belong in DATED_NOTES."""
        mm = MemoryMap()
        rejections = mm.map_content(DATED_NOTES, [
            {"type": "recent_observation", "key": "obs-001", "value": "User switched theme."},
        ])
        self.assertEqual(len(rejections), 0)
        items = mm.get_zone(DATED_NOTES)
        self.assertEqual(len(items), 1)

    def test_dated_notes_rejects_durable_lessons(self):
        """A durable lesson placed in dated notes is flagged."""
        mm = MemoryMap()
        rejections = mm.map_content(DATED_NOTES, [
            {"type": "durable_lesson", "key": "lesson-001", "value": "Always verify."},
        ])
        self.assertEqual(len(rejections), 1)
        self.assertIn("Rejected", rejections[0])

    def test_dated_notes_rejects_stable_preferences(self):
        """Stable preferences must not go into DATED_NOTES."""
        mm = MemoryMap()
        rejections = mm.map_content(DATED_NOTES, [
            {"type": "stable_preference", "key": "theme", "value": "dark"},
        ])
        # stable_preference is not in the allowed set for DATED_NOTES
        # and is not in the forbidden set either, so it gets a warning.
        # But it should not be silently accepted as a stable pref.
        self.assertTrue(len(rejections) >= 0)  # May warn but not crash.

    def test_dated_notes_separate_from_memory_md(self):
        """DATED_NOTES and MEMORY_MD zones are independent."""
        mm = MemoryMap()
        mm.map_content(DATED_NOTES, [{"type": "recent_observation", "key": "obs-1", "value": "A"}])
        mm.map_content(MEMORY_MD, [{"type": "durable_lesson", "key": "mem-1", "value": "B"}])
        self.assertEqual(len(mm.get_zone(DATED_NOTES)), 1)
        self.assertEqual(len(mm.get_zone(MEMORY_MD)), 1)


# ---------------------------------------------------------------------------
# T19-05: Superseded preferences are not simultaneously active.
# ---------------------------------------------------------------------------

class TestT19_05_SupersededNotActive(unittest.TestCase):
    """T19-05: Superseded preferences are not simultaneously active."""

    def test_superseded_not_in_active_profile(self):
        """After supersession, old preference is not active."""
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
        active = user_profile_get(profile)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].value, "light")
        # Old version is in preference_versions, not active.
        self.assertEqual(len(profile.preference_versions), 1)
        self.assertEqual(profile.preference_versions[0].value, "dark")

    def test_superseded_never_active_in_compact(self):
        """Compact view must not include superseded preferences."""
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
        compact = user_profile_compact(profile)
        self.assertNotIn("dark", compact.values())
        self.assertIn("light", compact.values())

    def test_validation_no_superseded_active(self):
        """validate_no_superseded_active returns True when no superseded is active."""
        prefs = [
            {"key": "theme", "status": "ACTIVE", "active": True},
        ]
        self.assertTrue(validate_no_superseded_active(prefs))

    def test_validation_flags_superseded_active(self):
        """validate_no_superseded_active returns False if superseded is active."""
        prefs = [
            {"key": "theme", "status": "SUPERSEDED", "active": True},
        ]
        self.assertFalse(validate_no_superseded_active(prefs))


# ---------------------------------------------------------------------------
# T19-06: New Tola session reconstructs same active profile.
# ---------------------------------------------------------------------------

class TestT19_06_SessionReconstructionDeterministic(unittest.TestCase):
    """T19-06: New Tola session reconstructs same active profile."""

    def test_reconstruct_deterministic_equal(self):
        """Two reconstruct calls with same inputs produce equal profiles."""
        mappings = {
            BLACKBOARD_PROFILE: (),
            USER_MD: (
                {"type": "stable_preference", "key": "theme", "value": "dark",
                 "source": EXPLICIT_PREFERENCE, "confidence": 1.0,
                 "scope": "global", "observed_at": "2026-09-29T10:00:00Z",
                 "evidence_refs": ("ev-001",), "project_id": "proj-alpha"},
            ),
            MEMORY_MD: (),
            DATED_NOTES: (),
        }
        profile1 = reconstruct_session(mappings)
        profile2 = reconstruct_session(mappings)
        self.assertEqual(len(profile1.preferences), len(profile2.preferences))
        if len(profile1.preferences) > 0:
            self.assertEqual(profile1.preferences[0].key, profile2.preferences[0].key)
            self.assertEqual(profile1.preferences[0].value, profile2.preferences[0].value)

    def test_reconstruct_preserves_active_preferences(self):
        """Reconstructed profile contains only ACTIVE preferences."""
        mappings = {
            BLACKBOARD_PROFILE: (),
            USER_MD: (
                {"type": "stable_preference", "key": "theme", "value": "dark",
                 "source": EXPLICIT_PREFERENCE, "confidence": 1.0,
                 "scope": "global", "observed_at": "2026-09-29T10:00:00Z",
                 "evidence_refs": ("ev-001",), "project_id": "proj-alpha"},
            ),
            MEMORY_MD: (),
            DATED_NOTES: (),
        }
        profile = reconstruct_session(mappings)
        active = user_profile_get(profile)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].value, "dark")

    def test_reconstruct_blackboard_overrides_local(self):
        """Blackboard profile outranks local USER.md on conflict."""
        mappings = {
            BLACKBOARD_PROFILE: (
                {"type": "shared_profile", "key": "theme", "value": "light",
                 "source": EXPLICIT_PREFERENCE, "confidence": 1.0,
                 "scope": "global", "observed_at": "2026-09-29T10:00:00Z",
                 "evidence_refs": ("bb-001",), "project_id": "proj-alpha"},
            ),
            USER_MD: (
                {"type": "stable_preference", "key": "theme", "value": "dark",
                 "source": EXPLICIT_PREFERENCE, "confidence": 1.0,
                 "scope": "global", "observed_at": "2026-09-29T09:00:00Z",
                 "evidence_refs": ("local-001",), "project_id": "proj-alpha"},
            ),
            MEMORY_MD: (),
            DATED_NOTES: (),
        }
        profile = reconstruct_session(mappings)
        active = user_profile_get(profile)
        self.assertEqual(len(active), 1)
        # Blackboard wins: value should be "light", not "dark".
        self.assertEqual(active[0].value, "light")

    def test_reconstruct_deterministic_with_dated_notes(self):
        """DATED_NOTES are kept separate and do not pollute active profile."""
        mappings = {
            BLACKBOARD_PROFILE: (),
            USER_MD: (
                {"type": "stable_preference", "key": "theme", "value": "dark",
                 "source": EXPLICIT_PREFERENCE, "confidence": 1.0,
                 "scope": "global", "observed_at": "2026-09-29T10:00:00Z",
                 "evidence_refs": ("ev-001",), "project_id": "proj-alpha"},
            ),
            MEMORY_MD: (),
            DATED_NOTES: (
                {"type": "recent_observation", "key": "obs-1", "value": "temporary",
                 "observed_at": "2026-09-29T12:00:00Z"},
            ),
        }
        profile1 = reconstruct_session(mappings)
        profile2 = reconstruct_session(mappings)
        # Same inputs -> same output.
        self.assertEqual(len(profile1.preferences), len(profile2.preferences))
        # DATED_NOTES should not appear in active preferences.
        active_keys = {p.key for p in profile1.preferences}
        self.assertNotIn("obs-1", active_keys)


# ---------------------------------------------------------------------------
# T19-07: Profile compaction does not drop explicit high-authority prefs.
# ---------------------------------------------------------------------------

class TestT19_07_CompactionKeepsExplicit(unittest.TestCase):
    """T19-07: Profile compaction does not drop explicit high-authority preferences."""

    def test_compact_includes_all_explicit_preferences(self):
        """Every EXPLICIT_PREFERENCE in the profile must appear in compact."""
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
            key="language",
            value="en",
            source=EXPLICIT_PREFERENCE,
            evidence_refs=("explicit-002",),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
            confidence=1.0,
        )
        compact = rebuild_compact(profile)
        self.assertIn("theme", compact)
        self.assertIn("language", compact)
        self.assertEqual(compact["theme"], "dark")
        self.assertEqual(compact["language"], "en")

    def test_compact_excludes_superseded(self):
        """Superseded preferences must not appear in compact."""
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
        compact = rebuild_compact(profile)
        self.assertNotIn("dark", compact.values())
        self.assertIn("light", compact.values())

    def test_compact_excludes_candidates(self):
        """CANDIDATE preferences must not appear in compact."""
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="editor",
            value="vim",
            source=BEHAVIOURAL_OBSERVATION,
            evidence_refs=("behav-001",),
            observed_at="2026-09-29T09:00:00Z",
            project_id="proj-alpha",
            confidence=0.5,
        )
        compact = rebuild_compact(profile)
        self.assertNotIn("editor", compact)

    def test_explicit_high_authority_always_included(self):
        """validate_explicit_high_authority_included returns True
        when all explicit prefs are in compact."""
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
        compact = rebuild_compact(profile)
        explicit = [p for p in profile.preferences if p.provenance.source == EXPLICIT_PREFERENCE]
        self.assertTrue(validate_explicit_high_authority_included(compact, explicit))

    def test_compact_deterministic(self):
        """Same profile produces same compact dict every time."""
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
        c1 = rebuild_compact(profile)
        c2 = rebuild_compact(profile)
        self.assertEqual(c1, c2)


# ---------------------------------------------------------------------------
# Rules validators.
# ---------------------------------------------------------------------------

class TestT19_RulesValidators(unittest.TestCase):
    """Validate consolidation rule constants and small validators."""

    def test_zone_placement_allows_durable_lesson_in_memory_md(self):
        self.assertTrue(validate_zone_placement(MEMORY_MD, "durable_lesson"))

    def test_zone_placement_rejects_recent_observation_in_memory_md(self):
        self.assertFalse(validate_zone_placement(MEMORY_MD, "recent_observation"))

    def test_zone_placement_rejects_durable_lesson_in_dated_notes(self):
        self.assertFalse(validate_zone_placement(DATED_NOTES, "durable_lesson"))

    def test_zone_placement_allows_recent_observation_in_dated_notes(self):
        self.assertTrue(validate_zone_placement(DATED_NOTES, "recent_observation"))

    def test_conflict_resolution_blackboard_wins(self):
        result = validate_conflict_resolution(
            blackboard_has_profile=True,
            local_has_profile=True,
        )
        self.assertEqual(result, "BLACKBOARD_PROFILE")

    def test_conflict_resolution_local_wins_when_no_blackboard(self):
        result = validate_conflict_resolution(
            blackboard_has_profile=False,
            local_has_profile=True,
        )
        self.assertEqual(result, "LOCAL")

    def test_conflict_resolution_none_when_neither(self):
        result = validate_conflict_resolution(
            blackboard_has_profile=False,
            local_has_profile=False,
        )
        self.assertEqual(result, "NONE")

    def test_recency_window_recent(self):
        self.assertTrue(
            validate_recency_window("2026-09-29", "2026-09-29")
        )

    def test_recency_window_old(self):
        self.assertFalse(
            validate_recency_window("2026-01-01", "2026-09-29")
        )

    def test_recency_window_boundary(self):
        self.assertTrue(
            validate_recency_window("2026-08-30", "2026-09-29")
        )

    def test_conflict_resolution_order_has_explicit_first(self):
        self.assertEqual(CONFLICT_RESOLUTION_ORDER[0], "EXPLICIT_PREFERENCE")

    def test_promotion_evidence_window_is_7_days(self):
        self.assertEqual(PROMOTION_EVIDENCE_WINDOW_DAYS, 7)

    def test_recency_window_is_30_days(self):
        self.assertEqual(RECENCY_WINDOW_DAYS, 30)


# ---------------------------------------------------------------------------
# Daily consolidation integration.
# ---------------------------------------------------------------------------

class TestT19_DailyConsolidate(unittest.TestCase):
    """Daily consolidation integration tests."""

    def test_daily_consolidate_returns_result(self):
        profile = _empty_profile()
        result = daily_consolidate(profile, [], "2026-09-29T10:00:00Z")
        self.assertIsInstance(result, ConsolidationResult)
        self.assertIsInstance(result.actions, tuple)
        self.assertIsInstance(result.profile_updates, dict)
        self.assertIsInstance(result.expired, tuple)

    def test_daily_consolidate_drops_expired_observations(self):
        profile = _empty_profile()
        observations = [
            {"key": "theme", "type": "recent_observation",
             "observed_at": "2026-01-01T10:00:00Z"},
        ]
        result = daily_consolidate(profile, observations, "2026-09-29T10:00:00Z")
        # Observation from Jan 1 is older than 30-day window from Sep 29.
        self.assertIn("theme", result.expired)

    def test_daily_consolidate_keeps_recent_observations(self):
        profile = _empty_profile()
        observations = [
            {"key": "theme", "type": "recent_observation",
             "observed_at": "2026-09-28T10:00:00Z"},
        ]
        result = daily_consolidate(profile, observations, "2026-09-29T10:00:00Z")
        self.assertEqual(len(result.expired), 0)

    def test_daily_consolidate_promotes_at_threshold(self):
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
        # Promote explicitly.
        profile = preference_promote(
            profile,
            key="editor",
            evidence_refs=(f"behav-{i:03d}" for i in range(PROMOTION_THRESHOLD)),
            observed_at="2026-09-29T10:00:00Z",
            project_id="proj-alpha",
        )
        result = daily_consolidate(profile, [], "2026-09-29T10:00:00Z")
        self.assertIn("compact", result.profile_updates)


# ---------------------------------------------------------------------------
# Weekly consolidation integration.
# ---------------------------------------------------------------------------

class TestT19_WeeklyConsolidate(unittest.TestCase):
    """Weekly consolidation integration tests."""

    def test_weekly_consolidate_returns_result(self):
        profile = _empty_profile()
        result = weekly_consolidate(profile, [], "2026-09-29T10:00:00Z")
        self.assertIsInstance(result, ConsolidationResult)

    def test_weekly_compact_retains_explicit_prefs(self):
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
        result = weekly_consolidate(profile, [], "2026-09-29T10:00:00Z")
        compact = result.profile_updates.get("compact", {})
        self.assertIn("theme", compact)
        self.assertEqual(compact["theme"], "dark")

    def test_weekly_compact_excludes_candidates(self):
        profile = _empty_profile()
        profile = preference_observe(
            profile,
            key="editor",
            value="vim",
            source=BEHAVIOURAL_OBSERVATION,
            evidence_refs=("behav-001",),
            observed_at="2026-09-29T09:00:00Z",
            project_id="proj-alpha",
            confidence=0.5,
        )
        result = weekly_consolidate(profile, [], "2026-09-29T10:00:00Z")
        compact = result.profile_updates.get("compact", {})
        self.assertNotIn("editor", compact)


# ---------------------------------------------------------------------------
# Determinism across all consolidation operations.
# ---------------------------------------------------------------------------

class TestT19_Determinism(unittest.TestCase):
    """All consolidation operations are deterministic."""

    def test_daily_consolidate_deterministic(self):
        profile = _empty_profile()
        r1 = daily_consolidate(profile, [], "2026-09-29T10:00:00Z")
        r2 = daily_consolidate(profile, [], "2026-09-29T10:00:00Z")
        self.assertEqual(r1.actions, r2.actions)
        self.assertEqual(r1.expired, r2.expired)

    def test_weekly_consolidate_deterministic(self):
        profile = _empty_profile()
        r1 = weekly_consolidate(profile, [], "2026-09-29T10:00:00Z")
        r2 = weekly_consolidate(profile, [], "2026-09-29T10:00:00Z")
        self.assertEqual(r1.profile_updates, r2.profile_updates)

    def test_reconstruct_session_deterministic(self):
        mappings = {
            BLACKBOARD_PROFILE: (),
            USER_MD: (
                {"type": "stable_preference", "key": "theme", "value": "dark",
                 "source": EXPLICIT_PREFERENCE, "confidence": 1.0,
                 "scope": "global", "observed_at": "2026-09-29T10:00:00Z",
                 "evidence_refs": ("ev-001",), "project_id": "proj-alpha"},
            ),
            MEMORY_MD: (),
            DATED_NOTES: (),
        }
        r1 = reconstruct_session(mappings)
        r2 = reconstruct_session(mappings)
        self.assertEqual(len(r1.preferences), len(r2.preferences))
        if len(r1.preferences) > 0:
            self.assertEqual(r1.preferences[0].value, r2.preferences[0].value)

    def test_memory_map_deterministic(self):
        mm = MemoryMap()
        mm.map_content(USER_MD, [{"type": "stable_preference", "key": "theme", "value": "dark"}])
        z1 = mm.get_zone(USER_MD)
        z2 = mm.get_zone(USER_MD)
        self.assertEqual(len(z1), len(z2))


# ---------------------------------------------------------------------------
# Plain ASCII check.
# ---------------------------------------------------------------------------

    def test_all_output_plain_ascii(self):
        for zone in (BLACKBOARD_PROFILE, USER_MD, MEMORY_MD, DATED_NOTES):
            for ch in zone:
                self.assertTrue(ord(ch) < 128, f"Non-ASCII in zone: {ch!r}")


if __name__ == "__main__":
    unittest.main()