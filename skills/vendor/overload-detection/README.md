# overload-detection

## Trigger
Activated when scheduling exceeds daily or weekly capacity thresholds. Fires after block placement and before plan finalization.

## Purpose
Detect when scheduled blocks exceed available capacity (default: 480 minutes/day) and report overload conditions to the planner rather than silently compressing or dropping tasks.

## Behaviour Rules
1. Sum all scheduled block durations for each day; compare against the configurable daily threshold (default 480 minutes).
2. If total exceeds threshold, set `overloadDetected: true` and report the excess minutes.
3. Overload is informational — it does not auto-reschedule or auto-cancel tasks.
4. Weekly overload is also tracked: flag when weekly total exceeds 30 hours.
5. Overload reports must not change project priority or silently resolve conflicts.
