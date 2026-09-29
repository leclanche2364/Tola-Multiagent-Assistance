# QA T15 - Decision Register and Review Triggers - Sign-off

Batch: T15
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T15-01 (decision captures reason/evidence/tradeoff; incomplete
  rejected at registration): PASS
- T15-02 (review date surfaces exactly when due: before/at/after):
  PASS
- T15-03 (revisit trigger activates correctly on match, silent on
  no-match; unknown trigger kinds rejected at build time): PASS
- T15-04 (superseded decision keeps history; both records retrievable,
  old marked superseded; immutability enforced): PASS
- explain_decision output includes all fields. PASS
- Determinism verified.

Gate arbitration by Tola main session: child flagged that superseded
records could still surface in due_reviews/check_revisit_triggers.
Fixed: both queries now exclude superseded records; two pinning tests
added. Registered decisions immutable; supersession is the only
change. Required fields: decision, reason, evidence, alternatives,
tradeoff, owner, date, expected_outcome; optional review_date,
revisit_trigger. Known scope notes: deterministic hash IDs; register
is in-memory (persistence is a later batch concern).

Main-session verification: 543/543 PASS (518 T1-T14 + 25 T15 incl. 2
new pinning tests), re-run by Tola main session. Plain-ASCII check:
clean after normalisation (recurring registry/profiles.py). Boundary
check: no My Rhythm write capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
