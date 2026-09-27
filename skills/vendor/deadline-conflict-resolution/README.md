# deadline-conflict-resolution

## Trigger
Activated when a task deadline cannot be met given available capacity and current schedule. Fires during planTask execution when infeasibility is detected.

## Purpose
Report deadline conflicts transparently without silently changing project priority. The skill ensures that infeasible schedules are surfaced to the user as decisions, not resolved by the system.

## Behaviour Rules
1. Compare required task duration against available capacity before the deadline.
2. If capacity is insufficient, generate a `deadline-conflict` report that includes: the deadline, required minutes, available minutes, and the shortfall.
3. The report must explicitly state that project priority is NOT changed.
4. Do NOT auto-adjust deadlines, auto-change project priority, or silently drop tasks to resolve conflicts.
5. The planner's `infeasible` flag must be set to true and `infeasibleReason` must contain "REPORTED".
