/**
 * Weekly roll-up pure functions over injected pilot data.
 *
 * Signatures match the Batch 16 spec §9.3 quantitative review requirements.
 * All inputs are plain data; no model calls, no cron, no network.
 */

import type { DailyReviewRecord } from "./daily-review.js";

/** Model route enum, matching the blackboard R0..R4 convention */
export type ModelRoute = "R0" | "R1" | "R2" | "R3" | "R4";

/** Defect severity per spec §13 */
export type Severity = "S0" | "S1" | "S2" | "S3";

/** A single model-run record injected from the blackboard */
export type ModelRunRecord = {
  model_route: ModelRoute;
  latency_ms: number | null;
  cost_usd: number | null;
  status: "completed" | "failed" | "timeout";
};

/** A single task-run record injected from the blackboard */
export type TaskRunRecord = {
  status: "success" | "partial" | "blocked" | "failed";
  summary?: string | null;
};

/** Aggregated weekly review result */
export type WeeklyReviewResult = {
  /** Delegation success rate = successful task runs / total task runs */
  delegationSuccessRate: number;
  /** Cost per successfully completed task (USD) */
  costPerSuccessfulTask: number;
  /** Latency by route: p50 and p95 per model route */
  latencyP50ByRoute: Record<ModelRoute, number>;
  latencyP95ByRoute: Record<ModelRoute, number>;
  /** Model retry rate = retries / total model runs */
  modelRetryRate: number;
  /** API / tool failure rate */
  apiToolFailureRate: number;
  /** Duplicate-action count across the week */
  duplicateActionCount: number;
  /** Manual schedule corrections applied */
  manualScheduleCorrections: number;
  /** Growth insights accepted / actioned (injected stat, 0..1) */
  growthInsightsAccepted: number;
  /** Scholar content accepted / used (injected stat, 0..1) */
  scholarContentAccepted: number;
  /** Skill improvement vs baseline (0 = no improvement, 1 = full improvement) */
  skillImprovementVsBaseline: number;
  /** Skill false-trigger rate = false triggers / total skill firings */
  skillFalseTriggerRate: number;
};

/**
 * Compute the weekly review from daily reviews, model runs, and task runs.
 *
 * All computations are pure — no side effects, no model calls.
 */
export function computeWeeklyReview(
  dailyReviews: DailyReviewRecord[],
  modelRuns: ModelRunRecord[],
  taskRuns: TaskRunRecord[],
): WeeklyReviewResult {
  const totalTaskRuns = taskRuns.length;
  const successfulTaskRuns = taskRuns.filter((tr) => tr.status === "success").length;
  const delegationSuccessRate = totalTaskRuns > 0 ? successfulTaskRuns / totalTaskRuns : 0;

  // Cost per successful task
  const successfulModelRuns = modelRuns.filter(
    (mr) => mr.status === "completed" && mr.cost_usd !== null && mr.latency_ms !== null,
  );
  const costSum = successfulModelRuns.reduce((sum, mr) => sum + (mr.cost_usd ?? 0), 0);
  const costPerSuccessfulTask = successfulTaskRuns > 0 ? costSum / successfulTaskRuns : 0;

  // Latency by route (p50 and p95)
  const latenciesByRoute: Record<ModelRoute, number[]> = { R0: [], R1: [], R2: [], R3: [], R4: [] };
  for (const mr of modelRuns) {
    if (mr.status === "completed" && mr.latency_ms !== null) {
      latenciesByRoute[mr.model_route].push(mr.latency_ms);
    }
  }

  const sortAsc = (a: number, b: number) => a - b;
  const latencyP50ByRoute: Record<ModelRoute, number> = { R0: 0, R1: 0, R2: 0, R3: 0, R4: 0 };
  const latencyP95ByRoute: Record<ModelRoute, number> = { R0: 0, R1: 0, R2: 0, R3: 0, R4: 0 };

  for (const route of ["R0", "R1", "R2", "R3", "R4"] as ModelRoute[]) {
    const lats = latenciesByRoute[route];
    if (lats.length === 0) {
      latencyP50ByRoute[route] = 0;
      latencyP95ByRoute[route] = 0;
    } else {
      const sorted = [...lats].sort(sortAsc);
      latencyP50ByRoute[route] = sorted[Math.floor(0.5 * sorted.length)] || 0;
      latencyP95ByRoute[route] = sorted[Math.min(Math.floor(0.95 * sorted.length) - 1, sorted.length - 1)] || 0;
    }
  }

  // Model retry rate
  const totalModelRuns = modelRuns.length;
  const retriedModelRuns = modelRuns.filter((mr) => mr.status === "failed" || mr.status === "timeout").length;
  const modelRetryRate = totalModelRuns > 0 ? retriedModelRuns / totalModelRuns : 0;

  // API / tool failure rate
  const apiToolFailureRate = totalModelRuns > 0 ? retriedModelRuns / totalModelRuns : 0;

  // Duplicate-action count
  const duplicateActionCount = dailyReviews.reduce((sum, r) => sum + r.duplicateCount, 0);

  // Manual schedule corrections
  const manualScheduleCorrections = dailyReviews.reduce((sum, r) => sum + r.manualReroutes, 0);

  // Injected stats (placeholders for Growth/Scholar)
  const growthInsightsAccepted = 0;
  const scholarContentAccepted = 0;
  const skillImprovementVsBaseline = 0;

  // Skill false-trigger rate
  const totalSkillTriggerFailures = dailyReviews.reduce((sum, r) => sum + r.skillTriggerFailures, 0);
  const totalSkillProposals = dailyReviews.reduce((sum, r) => sum + r.skillProposals, 0);
  const skillFalseTriggerRate = totalSkillProposals > 0 ? totalSkillTriggerFailures / totalSkillProposals : 0;

  return {
    delegationSuccessRate,
    costPerSuccessfulTask,
    latencyP50ByRoute,
    latencyP95ByRoute,
    modelRetryRate,
    apiToolFailureRate,
    duplicateActionCount,
    manualScheduleCorrections,
    growthInsightsAccepted,
    scholarContentAccepted,
    skillImprovementVsBaseline,
    skillFalseTriggerRate,
  };
}
