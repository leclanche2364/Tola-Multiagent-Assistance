# QA T29 Sign-Off Draft -- Monthly Operating-System Review

## Per-Case Results

| Case | Description | Status |
|------|-------------|--------|
| T29-01 | Low-value/high-time project identified as resource drain | PASS |
| T29-02 | Useful automation retained (KEEP, no removal rec) | PASS |
| T29-03 | Noisy/low-value automation flagged for removal with evidence | PASS |
| T29-04 | Agent bottleneck detected from evidence | PASS |
| T29-05 | Cost anomaly with factor and both numbers | PASS |
| T29-06 | Repeated manual process -> automation candidate | PASS |
| T29-07 | Architecture/security stays proposal | PASS |
| T29-08 | All recommendations have expected_benefit + evidence | PASS |

## Threshold / Proposal Rules

- DRAIN_RULE: value_score <= 2 AND time_spent_hours >= 10 -> REDUCE_OR_SUNSET (resource drain).
- USEFUL_AUTOMATION: kind=useful -> KEEP (no action).
- NOISY_AUTOMATION: kind=noisy -> REDUCE_OR_REMOVE (run_count + noise signals as evidence).
- BOTTLENECK_RULE: queue_depth > 10 OR wait_time_avg > 30 OR failure_rate > 0.25 -> BOTTLENECK finding citing exact evidence.
- COST_ANOMALY: monthly_cost > 2.0 x baseline_monthly_cost -> anomaly finding with both numbers and factor.
- MANUAL_PROCESS: frequency_per_month >= 5 -> AUTOMATE recommendation.
- PROTECTED_PROPOSAL: architecture/security proposals -> status=PROPOSAL, never actioned.
- Every recommendation carries expected_benefit (non-empty string) and evidence (non-empty tuple of cited values).

## Deviations or Concerns

None. All 8 QA T29 cases covered by dedicated test classes. All recommendations are immutable (frozen dataclass). No clock reads, no network, no writes outside four-agent-repo/tola.