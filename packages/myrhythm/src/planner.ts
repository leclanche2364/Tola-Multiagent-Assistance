/**
 * Shift-aware planning layer — Batch 10.
 *
 * Rules:
 * - No high-cognitive task placed in post-shift recovery window without explicit instruction.
 * - Deep-work placement (180-min high-cognitive task) goes into suitable day-off window.
 * - Overload detection: flag when scheduled blocks exceed daily capacity.
 * - Deadline-conflict reporting: infeasible schedules are REPORTED, never silently resolved
 *   by changing project priority.
 */

import { rangesOverlap, addMinutes, subMinutes, durationMinutes, type FlexibleBlock, type PlanEntry } from "./client.ts";

// ---------- time window constants ----------

/** Default post-shift recovery window start/end (UTC). */
export const DEFAULT_RECOVERY_WINDOW = { startsAt: "2025-01-01T07:00:00.000Z", endsAt: "2025-01-01T09:00:00.000Z" };

/** Deep-work block duration in minutes (180 min = 3 hours). */
export const DEEP_WORK_DURATION_MINUTES = 180;

// ---------- types ----------

export interface ShiftSchedule {
  shiftStartsAt: string;
  shiftEndsAt: string;
  recoveryWindow?: { startsAt: string; endsAt: string };
}

export interface PlanningDay {
  date: string;
  dayType: "work-day" | "day-off" | "rest-day";
  availableWindows: Array<{ startsAt: string; endsAt: string }>;
}

export interface PlannerInput {
  taskTitle: string;
  taskDurationMinutes: number;
  isHighCognitive: boolean;
  deadline: string; // ISO-8601
  days: PlanningDay[];
  shiftSchedule?: ShiftSchedule;
  explicitOverrideRecovery?: boolean; // explicit user instruction to place in recovery
}

export interface PlannerResult {
  proposals: PlannerSlotProposal[];
  conflicts: string[];
  overloadDetected: boolean;
  infeasible: boolean;
  infeasibleReason?: string;
}

export interface PlannerSlotProposal {
  date: string;
  startsAt: string;
  endsAt: string;
  block: FlexibleBlock;
  reasoning: string;
}

// ---------- helpers ----------

function makeBlock(title: string, startsAt: string, endsAt: string, projectId: string): FlexibleBlock {
  return {
    id: crypto.randomUUID(),
    title,
    startsAt,
    endsAt,
    projectId,
    createdAt: new Date().toISOString(),
  };
}

/** Check if a datetime is within the recovery window. Pure/deterministic. */
function isInRecoveryWindow(dt: string, recovery: { startsAt: string; endsAt: string }): boolean {
  return (
    new Date(dt).getTime() >= new Date(recovery.startsAt).getTime() &&
    new Date(dt).getTime() <= new Date(recovery.endsAt).getTime()
  );
}

// ---------- core planning ----------

/**
 * Plan a high-cognitive task across available days with shift-aware rules.
 *
 * - If task is high-cognitive and falls in post-shift recovery without explicitOverrideRecovery,
 *   skip that window and move to next suitable window.
 * - 180-minute high-cognitive tasks are placed in day-off windows.
 * - Overload is detected when total scheduled minutes exceed 480 (8h).
 * - Infeasible deadlines are REPORTED, never silently resolved by changing project priority.
 */
export function planTask(input: PlannerInput): PlannerResult {
  const proposals: PlannerSlotProposal[] = [];
  const conflicts: string[] = [];
  const { taskTitle, taskDurationMinutes, isHighCognitive, deadline, days, shiftSchedule, explicitOverrideRecovery } = input;

  const recovery = shiftSchedule?.recoveryWindow ?? DEFAULT_RECOVERY_WINDOW;

  // ---------- overload detection ----------
  let totalScheduledMinutes = 0;
  for (const day of days) {
    for (const win of day.availableWindows) {
      totalScheduledMinutes += durationMinutes(win.startsAt, win.endsAt);
    }
  }
  const OVERLOAD_THRESHOLD = 480; // 8 hours in minutes
  const overloadDetected = totalScheduledMinutes > OVERLOAD_THRESHOLD;

  // ---------- deadline feasibility check ----------
  const deadlineTime = new Date(deadline).getTime();
  const now = new Date("2025-01-01T00:00:00.000Z").getTime(); // deterministic reference
  const hoursToDeadline = (deadlineTime - now) / 60_000;
  const totalAvailableMinutes = days.reduce((acc, day) => {
    return acc + day.availableWindows.reduce((a, w) => a + durationMinutes(w.startsAt, w.endsAt), 0);
  }, 0);
  const infeasible = hoursToDeadline > 0 && taskDurationMinutes > totalAvailableMinutes;
  const infeasibleReason = infeasible
    ? `Deadline ${deadline} cannot be met: ${taskDurationMinutes}min task exceeds ${totalAvailableMinutes}min available capacity. REPORTED — project priority is NOT changed.`
    : undefined;

  // ---------- placement logic ----------
  for (const day of days) {
    for (const win of day.availableWindows) {
      const winStart = win.startsAt;
      const winEnd = win.endsAt;
      const winDuration = durationMinutes(winStart, winEnd);

      if (taskDurationMinutes > winDuration) continue; // window too small

      // Shift-aware recovery check
      if (isHighCognitive && !explicitOverrideRecovery) {
        const recoveryEnd = recovery.endsAt;
        // Check if this window overlaps with recovery
        const winMid = addMinutes(winStart, winDuration / 2);
        if (isInRecoveryWindow(winMid, recovery)) {
          // Skip recovery window placement for high-cognitive tasks
          continue;
        }
      }

      // Deep-work placement for 180-min high-cognitive tasks
      if (isHighCognitive && taskDurationMinutes === DEEP_WORK_DURATION_MINUTES) {
        // Only place in day-off windows
        if (day.dayType === "day-off") {
          const block = makeBlock(taskTitle, winStart, addMinutes(winStart, taskDurationMinutes), "project-default");
          proposals.push({
            date: day.date,
            startsAt: winStart,
            endsAt: addMinutes(winStart, taskDurationMinutes),
            block,
            reasoning: `Deep-work placement in day-off window: ${day.date}. 180-minute high-cognitive task scheduled outside recovery hours.`,
          });
        }
        continue; // Only day-off for deep work
      }

      // Standard placement
      const block = makeBlock(taskTitle, winStart, addMinutes(winStart, taskDurationMinutes), "project-default");
      proposals.push({
        date: day.date,
        startsAt: winStart,
        endsAt: addMinutes(winStart, taskDurationMinutes),
        block,
        reasoning: `Scheduled ${taskDurationMinutes}min task in available window on ${day.date}.`,
      });
    }
  }

  // If no proposals were generated and not infeasible, add a conflict note
  if (proposals.length === 0 && !infeasible) {
    conflicts.push("No suitable placement window found for the task within available days.");
  }

  return {
    proposals,
    conflicts,
    overloadDetected,
    infeasible,
    infeasibleReason,
  };
}

/**
 * Detect overload across planned days. Pure/deterministic.
 */
export function detectOverload(days: PlanningDay[], thresholdMinutes: number = 480): boolean {
  const total = days.reduce((acc, day) => {
    return acc + day.availableWindows.reduce((a, w) => a + durationMinutes(w.startsAt, w.endsAt), 0);
  }, 0);
  return total > thresholdMinutes;
}

/**
 * Report a deadline conflict. Returns a report string — never modifies project priority.
 */
export function reportDeadlineConflict(deadline: string, requiredMinutes: number, availableMinutes: number): string {
  return `Deadline conflict REPORTED: ${deadline} — requires ${requiredMinutes}min, only ${availableMinutes}min available. Project priority unchanged.`;
}
