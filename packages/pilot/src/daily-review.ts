/**
 * Daily review record types matching the Batch 16 pilot spec §9.1–§9.2.
 *
 * Record one of these per day per agent (or per system-wide aggregate).
 * All counts are non-negative integers. modelRoute counts map R0..R4 to counts.
 */
export type DailyReviewRecord = {
  /** Date in YYYY-MM-DD format */
  date: string;
  /** How many tasks were delegated (across all agents) */
  tasksDelegated: number;
  /** Counts of task outcomes */
  success: number;
  partial: number;
  blocked: number;
  failed: number;
  /** How many times a human manually rerouted a task */
  manualReroutes: number;
  /** Count of decisions made by the wrong agent */
  wrongAgentDecisions: number;
  /** Model route usage counts for the day */
  modelRoute: { R0: number; R1: number; R2: number; R3: number; R4: number };
  /** Total retries attempted */
  retries: number;
  /** API/tool call failures */
  apiFailures: number;
  /** Duplicate task-action count */
  duplicateCount: number;
  /** Count of user corrections applied */
  userCorrections: number;
  /** Skill trigger failures (a skill fired but produced no useful result) */
  skillTriggerFailures: number;
  /** Count of skill proposals generated that day */
  skillProposals: number;
};

/**
 * Pure aggregation function: combine multiple daily review records into summary stats.
 *
 * @param reviews array of DailyReviewRecord values (non-empty recommended)
 * @returns aggregated totals and rates (all pure — no model calls, no I/O)
 */
export function aggregateDailyReviews(reviews: DailyReviewRecord[]): {
  totalTasksDelegated: number;
  totalSuccess: number;
  totalPartial: number;
  totalBlocked: number;
  totalFailed: number;
  totalManualReroutes: number;
  totalWrongAgentDecisions: number;
  totalRetries: number;
  totalApiFailures: number;
  totalDuplicateCount: number;
  totalUserCorrections: number;
  totalSkillTriggerFailures: number;
  totalSkillProposals: number;
  successRate: number;
  partialRate: number;
  blockedRate: number;
  failedRate: number;
  averageTasksPerDay: number;
  duplicateRate: number;
  modelRouteTotals: { R0: number; R1: number; R2: number; R3: number; R4: number };
} {
  if (reviews.length === 0) {
    return {
      totalTasksDelegated: 0,
      totalSuccess: 0,
      totalPartial: 0,
      totalBlocked: 0,
      totalFailed: 0,
      totalManualReroutes: 0,
      totalWrongAgentDecisions: 0,
      totalRetries: 0,
      totalApiFailures: 0,
      totalDuplicateCount: 0,
      totalUserCorrections: 0,
      totalSkillTriggerFailures: 0,
      totalSkillProposals: 0,
      successRate: 0,
      partialRate: 0,
      blockedRate: 0,
      failedRate: 0,
      averageTasksPerDay: 0,
      duplicateRate: 0,
      modelRouteTotals: { R0: 0, R1: 0, R2: 0, R3: 0, R4: 0 },
    };
  }

  const totalTasksDelegated = reviews.reduce((sum, r) => sum + r.tasksDelegated, 0);
  const totalSuccess = reviews.reduce((sum, r) => sum + r.success, 0);
  const totalPartial = reviews.reduce((sum, r) => sum + r.partial, 0);
  const totalBlocked = reviews.reduce((sum, r) => sum + r.blocked, 0);
  const totalFailed = reviews.reduce((sum, r) => sum + r.failed, 0);
  const totalManualReroutes = reviews.reduce((sum, r) => sum + r.manualReroutes, 0);
  const totalWrongAgentDecisions = reviews.reduce((sum, r) => sum + r.wrongAgentDecisions, 0);
  const totalRetries = reviews.reduce((sum, r) => sum + r.retries, 0);
  const totalApiFailures = reviews.reduce((sum, r) => sum + r.apiFailures, 0);
  const totalDuplicateCount = reviews.reduce((sum, r) => sum + r.duplicateCount, 0);
  const totalUserCorrections = reviews.reduce((sum, r) => sum + r.userCorrections, 0);
  const totalSkillTriggerFailures = reviews.reduce((sum, r) => sum + r.skillTriggerFailures, 0);
  const totalSkillProposals = reviews.reduce((sum, r) => sum + r.skillProposals, 0);

  const successRate = totalTasksDelegated > 0 ? totalSuccess / totalTasksDelegated : 0;
  const partialRate = totalTasksDelegated > 0 ? totalPartial / totalTasksDelegated : 0;
  const blockedRate = totalTasksDelegated > 0 ? totalBlocked / totalTasksDelegated : 0;
  const failedRate = totalTasksDelegated > 0 ? totalFailed / totalTasksDelegated : 0;
  const averageTasksPerDay = totalTasksDelegated / reviews.length;
  const duplicateRate = totalTasksDelegated > 0 ? totalDuplicateCount / totalTasksDelegated : 0;

  const modelRouteTotals = {
    R0: reviews.reduce((sum, r) => sum + r.modelRoute.R0, 0),
    R1: reviews.reduce((sum, r) => sum + r.modelRoute.R1, 0),
    R2: reviews.reduce((sum, r) => sum + r.modelRoute.R2, 0),
    R3: reviews.reduce((sum, r) => sum + r.modelRoute.R3, 0),
    R4: reviews.reduce((sum, r) => sum + r.modelRoute.R4, 0),
  };

  return {
    totalTasksDelegated,
    totalSuccess,
    totalPartial,
    totalBlocked,
    totalFailed,
    totalManualReroutes,
    totalWrongAgentDecisions,
    totalRetries,
    totalApiFailures,
    totalDuplicateCount,
    totalUserCorrections,
    totalSkillTriggerFailures,
    totalSkillProposals,
    successRate,
    partialRate,
    blockedRate,
    failedRate,
    averageTasksPerDay,
    duplicateRate,
    modelRouteTotals,
  };
}
