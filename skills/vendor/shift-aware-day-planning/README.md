# shift-aware-day-planning

## Trigger
Activated when a scheduling request involves high-cognitive tasks and the agent's shift schedule is known. Fires before any block placement suggestion is emitted.

## Purpose
Ensure high-cognitive tasks are never placed into post-shift recovery windows without explicit user instruction. The skill enforces shift-aware boundaries so that cognitive work respects human recovery periods.

## Behaviour Rules
1. If the current time falls within the configured post-shift recovery window (`shiftSchedule.recoveryWindow`), do not place high-cognitive tasks unless `explicitOverrideRecovery: true`.
2. When `explicitOverrideRecovery` is false and a recovery-window placement would be chosen, skip that window and find the next suitable non-recovery window.
3. Log the recovery avoidance in the proposal `reasoning` field for auditability.
4. Never modify project priority to resolve scheduling conflicts — report infeasibility only.
5. The skill is a planning assistant only; it has no delegation authority and no spawn capability.
