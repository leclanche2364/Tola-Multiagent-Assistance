# QA T1 - Portfolio Data Contract - Sign-off

Batch: T1
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T1-01..T1-05 (authoritative source resolution per entity): PASS
- T1-06 (missing ownership flagged/rejected): PASS (MissingOwnershipError)
- T1-07 (ambiguous duplicate source detected): PASS (defensive AmbiguousSourceError guard; noted deviation)
- T1-08 (conversation-only facts rejected as authoritative): PASS (guards.py)

Main-session verification: python3 -m unittest discover -s tola/tests -t .
Result: 30/30 PASS (re-run by Tola main session; not trusting child report alone).

Fixes applied at gate: non-ASCII em-dashes replaced in 3 files to meet
plain-ASCII constraint; __pycache__ removed and gitignored.

Overall: PASS
Approved by: Tola main session
