# QA T23 - Proposal-First Self-Improvement - Sign-off

Batch: T23
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T23-01 (better candidate creates proposal, not auto-apply): PASS
- T23-02 (worse candidate rejected, propose_improvement -> None):
  PASS
- T23-03 (permission/security change cannot self-apply):
  PASS (PROTECTED_CATEGORIES requires explicit protected-approval
  token suffix)
- T23-04 (core skill mutation remains pending until approval):
  PASS
- T23-05 (proposal bound to evaluated version + sha256 of canonical
  JSON, asserted exact): PASS
- T23-06 (approved proposal applies correct version, token must
  match proposal hash and version be current): PASS
- T23-07 (unapproved proposal leaves production unchanged -> None):
  PASS
- T23-08 (rollback path tested; apply-then-rollback restores prior
  version/hash): PASS

Apply outcomes: APPLY | SKIP_UNAPPROVED | SKIP_STALE |
BLOCK_PROTECTED. Protected categories: core_skills, permissions,
security, architecture. Pure functions, hashlib sha256, no I/O,
deterministic, no clock reads.

No deviations reported. Main-session verification: 775/775 PASS
(745 T1-T22 + 30 T23), re-run by Tola main session. Plain-ASCII
check: clean after normalisation (2 files this batch, including
recurring registry/profiles.py). Boundary check: no My Rhythm write
capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
