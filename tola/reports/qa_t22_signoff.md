# QA T22 - Improvement Benchmark Harness - Sign-off

Batch: T22
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T22-01 (current Tola baseline recorded, frozen, with pinned
  version): PASS
- T22-02 (candidate tested on identical fixtures; missing fixture
  errors): PASS
- T22-03 (improvement on one metric cannot hide critical
  regression): PASS (REGRESSION_CRITICAL = task_success,
  delegation_correct, escalation_correct, human_correction; any
  per-fixture critical regression forces REJECTED)
- T22-04 (cost measured): PASS
- T22-05 (latency measured): PASS
- T22-06 (human-correction proxy measured): PASS
- T22-07 (benchmark version pinned in baseline and comparisons):
  PASS
- T22-08 (re-run reproducible; two evaluations equal; floats within
  declared TOLERANCE): PASS

Ten deterministic fixtures (simple delegation, multi-agent task,
ambiguous ownership, capacity-limited task, blocked specialist,
poor specialist result, cross-domain conflict, deadline-sensitive
task, plan critique, founder briefing). Nine comparison metrics.
Verdicts: IMPROVED | REJECTED | REVIEW. Pure data + pure functions,
no execution of the system, no I/O, deterministic.

No deviations reported. Main-session verification: 745/745 PASS
(720 T1-T21 + 25 T22), re-run by Tola main session. Plain-ASCII
check: clean after normalisation (recurring registry/profiles.py).
Boundary check: no My Rhythm write capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
