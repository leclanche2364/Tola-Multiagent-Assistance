# recovery-aware-week-planning

## Trigger
Activated when weekly scheduling involves multi-day planning with known shift patterns and recovery requirements. Fires during week-level plan generation.

## Purpose
Ensure recovery periods are respected across an entire work week, preventing cumulative cognitive overload by distributing high-cognitive tasks away from recovery windows on each day.

## Behaviour Rules
1. For each day in the planning horizon, check `shiftSchedule.recoveryWindow` and exclude it from high-cognitive task placement.
2. Distribute deep-work blocks (180-minute high-cognitive tasks) across day-off windows to maximize recovery and focus.
3. Track cumulative cognitive load per week; flag when weekly total exceeds 30 hours of high-cognitive work.
4. If a week-level plan would violate recovery constraints, generate a proposal with explicit reasoning rather than silently adjusting.
5. No project priority changes are permitted — infeasible weeks are reported, not resolved by re-prioritization.
