# QA T18 - User Operating Profile and Persona Awareness - Sign-off

Batch: T18
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T18-01 (explicit preference gets highest authority): PASS
- T18-02 (single behavioural observation stays CANDIDATE): PASS
- T18-03 (repeated pattern promotes only at PROMOTION_THRESHOLD=3): PASS
- T18-04 (contradiction supersedes old preference; old version
  preserved in user_preference_versions history): PASS
- T18-05 (sensitive inference rejected at observation time, never
  stored): PASS
- T18-06 (repeated approval does not expand Tola capability set):
  PASS
- T18-07 (every active preference has provenance + confidence): PASS
- T18-08 (project-scoped preference does not become global without
  explicit global evidence): PASS

Preference lifecycle: EXPLICIT_PREFERENCE -> ACTIVE immediately;
BEHAVIOURAL_OBSERVATION -> CANDIDATE until threshold. Supersession
is versioned, never deleted. Frozen sensitive-category blocklist.
check_authority tracks approval counts without touching capability
set. Pure functions, deterministic, no I/O.

No deviations reported. Main-session verification: 624/624 PASS
(594 T1-T17 + 30 T18), re-run by Tola main session. Plain-ASCII
check: clean after normalisation (5 files this batch, including
recurring registry/profiles.py). Boundary check: no My Rhythm write
capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
