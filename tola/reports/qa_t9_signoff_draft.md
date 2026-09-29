# QA T9 Sign-Off Draft — Client Report Generator

**Batch:** T9 — Client Report Generator  
**Date:** 2026-09-29  
**Status:** DRAFT — pending final sign-off

---

## Files Created

| File | Purpose |
|------|---------|
| `tola/reports_gen/__init__.py` | Package init, re-exports all three report functions |
| `tola/reports_gen/daily_brief.py` | `daily_brief(snapshot, escalations, delegations) -> str` |
| `tola/reports_gen/status_report.py` | `portfolio_status_report(snapshot, plans, risks) -> str` |
| `tola/reports_gen/weekly_digest.py` | `weekly_digest(week_inputs) -> str` |
| `tola/tests/test_t9_reports.py` | 24 unittest cases covering QA T9 requirements |
| `tola/reports/qa_t9_signoff_draft.md` | This file |

---

## Per-Case Results

### daily_brief

| Case | Result | Notes |
|------|--------|-------|
| Brief includes only material attention items (not ON_TRACK noise) | PASS | ON_TRACK projects excluded from attention section |
| Attention-level project with signal appears in brief | PASS | DEADLINE_RISK, STALLED_ACTIVITY signals rendered |
| Output sorted/stable by project_id | PASS | Projects sorted; signals sorted by type |
| No secrets/credentials in output | PASS | Fake credential in agent_state not present in output |
| Open escalations appear | PASS | STOP_AND_ESCALATE, FLAG, NOTE levels shown |
| Resolved escalations excluded | PASS | status=resolved filtered out |
| In-flight delegations shown | PASS | COMPLETED/REJECTED/CANCELLED excluded |
| Determinism (same inputs -> identical string) | PASS | 3 consecutive calls identical |
| Empty snapshot produces valid brief | PASS | Zero counts, no crash |

### portfolio_status_report

| Case | Result | Notes |
|------|--------|-------|
| Non-ON_TRACK projects include evidence lines | PASS | AT_RISK project shows DEADLINE_RISK + STALLED_ACTIVITY evidence |
| ON_TRACK projects show "no material signals" | PASS | No evidence lines for healthy projects |
| Risk highlights from snapshot | PASS | Risk ID, title, severity, status rendered |
| Critical path milestones section present | PASS | Falls back to goal-level milestones when no graph |
| Plan versions section includes metadata | PASS | plan_id, version, status shown |
| No secrets/credentials in output | PASS | Credential in agent_state not present |
| Determinism | PASS | 3 consecutive calls identical |
| Empty snapshot produces valid report | PASS | "no projects in snapshot" message |

### weekly_digest

| Case | Result | Notes |
|------|--------|-------|
| Digest counts match ledger inputs | PASS | Total, by-status counts verified |
| Closed/completed items count correct | PASS | closed_items + completed_items summed |
| Escalation raised/resolved counts match | PASS | Separate raised/resolved lists counted |
| Health transitions listed correctly | PASS | from_label -> to_label format |
| Determinism | PASS | 3 consecutive calls identical |
| No secrets/credentials in output | PASS | Credential in delegation ledger not present |
| Empty inputs produce valid digest | PASS | Zero counts for all sections |
| Sorted/stable output | PASS | Items sorted by id |

### Cross-cutting

| Case | Result | Notes |
|------|--------|-------|
| All reports plain ASCII | PASS | All chars < 128 |
| All reports deterministic roundtrip | PASS | 3 consecutive calls identical per report type |
| No file I/O in report functions | PASS | No open()/write()/print()/subprocess in source |

---

## Deviations and Concerns

1. **T9 QA scope mismatch**: The implementation plan section 17 describes Batch T9 as "Capacity-Aware Delegation with Rhythm" (QA T9-01..T9-07), but the task brief defines T9 as "Client Report Generator." The report generator build follows the task brief, not the implementation plan's T9 description. The QA T9 test cases in the testing plan (capacity-aware delegation) are not covered here — those belong to the delegation capacity layer, not report generation.

2. **Health assessment attachment**: The report functions read `project._health_assessment` as an optional attribute. This is a convention, not enforced by the PortfolioSnapshot dataclass. In production, a separate assessment pass would attach these. The `_infer_label` fallback handles projects without assessments.

3. **Critical path without graph**: `portfolio_status_report` attempts to use `snapshot._dependency_graph` for T7 critical-path analysis. If no graph is attached, it falls back to goal-level milestone listing. This is a graceful degradation, not a deviation.

4. **Test count**: 24 new T9 test cases added. Combined with existing T1-T8 suite (363 tests), total is 387. All 387 pass (0 failures, 0 errors).

5. **No Tola write capability**: All three report functions are pure (no I/O, no network, no My Rhythm writes). Confirmed by source inspection.
