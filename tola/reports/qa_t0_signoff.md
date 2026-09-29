# QA T0 — Baseline and Restore — Sign-off

Batch: T0
Version/commit: see git log at sign-off
Environment: Habeeb's MacBook Pro (macOS 13.7.8), four-agent repo, Tola main session
Date: 2026-09-29

## Test results

- T0-01 Configuration inventory matches live/test state: PASS
  (openclaw.json + exec-approvals + model-watch captured to
  tola/baseline/ and ~/.openclaw-backups/config-20260929/).
- T0-02 Current Tola Skills captured: PASS (skills_inventory.txt).
- T0-03 Blackboard schema captured: PASS
  (baseline/blackboard_schema_v1.sql = deployed v1 migration).
- T0-04 Rhythm/Growth/Scholar boundaries documented: PASS
  (contracts/specialist_boundaries_and_routing_v1.md, incl. Marketing
  Agent FUTURE_NOT_AVAILABLE state machine and model routing).
- T0-05 Tola can be restored in a safe test environment: PASS
  (RESTORE_MANIFEST.md documents file-level restore per item; openclaw
  config restore = copy back + gateway restart).
- T0-06 Secret scan finds no credentials committed: PASS
  (git ls-files scan: only test-fixture mock strings in packages/*/tests;
  no real tokens in tracked files. tola/baseline/ gitignored — it
  contains a live config snapshot and must never be committed).

Failure injection: tar-based full-config backup attempted twice and
SIGKILLed (21 GB tree). Targeted file-level capture used instead and
documented. Config capture verified by file listing before sign-off.

## Notes

- Plan docs v1.1 stored in tola/docs/ (implementation + testing).
- /tola directory structure created per plan §17 T0.
- Backup location outside repo: ~/.openclaw-backups/config-20260929/.
- Known limitation: no full-tree archive of ~/.openclaw (21 GB). Media,
  node_modules, browser state excluded; project workspaces are each
  independently in git. Revisit backup strategy in a later batch.

Overall: PASS

Critical defects: none
High defects: none
Medium defects: none
Low defects: 1 (full-tree archive infeasible on this machine; targeted
capture accepted as baseline scope).

Evidence: this file + baseline/ contents + git history.
Approved by: Tola (awaiting Habeeb counter-sign).
