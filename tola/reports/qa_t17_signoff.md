# QA T17 - Founder Briefing and Attention Filter - Sign-off

Batch: T17
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T17-01 (routine internal acknowledgement -> SILENT): PASS
- T17-02 (non-urgent change -> DIGEST): PASS
- T17-03 (material change -> NOTIFY): PASS
- T17-04 (true decision request -> DECISION_REQUIRED): PASS
- T17-05 (true urgent condition -> URGENT): PASS
- T17-06 (brief leads with implication before details): PASS
- T17-07 (numbers/status match sources exactly): PASS
- T17-08 (internal agent chatter does not flood user; repeated
  chatter collapses to one digest line with count): PASS
- T17-09 (action/inaction required clear from first layer): PASS

Attention levels frozen: SILENT | DIGEST | NOTIFY |
DECISION_REQUIRED | URGENT. founder_brief partitions events into
urgent/decisions/notifications/digest plus silence_count. Pure
functions, no I/O, deterministic; numbers are copied verbatim from
source events (pinned by exact-string tests).

No deviations reported. Main-session verification: 594/594 PASS
(562 T1-T16 + 32 T17), re-run by Tola main session. Plain-ASCII
check: clean after normalisation (recurring registry/profiles.py).
Boundary check: no My Rhythm write capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
