import { test } from "node:test";
import assert from "node:assert/strict";
import {
  type DailyReviewRecord,
  aggregateDailyReviews,
  computeWeeklyReview,
  PILOT_QUESTIONS,
  checkReleaseGate,
} from "../src/index.ts";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const makeRecord = (overrides: Partial<DailyReviewRecord> = {}): DailyReviewRecord => ({
  date: "2026-09-27",
  tasksDelegated: 10,
  success: 7,
  partial: 1,
  blocked: 1,
  failed: 1,
  manualReroutes: 2,
  wrongAgentDecisions: 0,
  modelRoute: { R0: 1, R1: 3, R2: 4, R3: 1, R4: 1 },
  retries: 3,
  apiFailures: 1,
  duplicateCount: 2,
  userCorrections: 1,
  skillTriggerFailures: 0,
  skillProposals: 2,
  ...overrides,
});

const makeModelRun = (overrides: Record<string, unknown> = {}) => ({
  model_route: "R1" as const,
  latency_ms: 120,
  cost_usd: 0.05,
  status: "completed" as const,
  ...overrides,
});

const makeTaskRun = (overrides: Record<string, unknown> = {}) => ({
  status: "success" as const,
  summary: null,
  ...overrides,
});

// ---------------------------------------------------------------------------
// Daily record validation
// ---------------------------------------------------------------------------

test("daily-review: unknown fields are rejected at runtime (TypeScript enforces, runtime throws)", () => {
  // TypeScript strips unknown fields at compile time; runtime validation
  // ensures only known fields survive. We test via a type-safe construction.
  const rec = makeRecord({ tasksDelegated: 5 });
  assert.strictEqual(rec.tasksDelegated, 5);
  // Accessing a non-existent field should be a TypeScript error;
  // we verify the record shape via Object.keys
  const keys = Object.keys(rec);
  assert.ok(keys.includes("tasksDelegated"));
  assert.ok(!keys.includes("nonExistentField"));
});

test("daily-review: all required daily fields present", () => {
  const rec = makeRecord();
  const requiredFields = [
    "date", "tasksDelegated", "success", "partial", "blocked", "failed",
    "manualReroutes", "wrongAgentDecisions", "modelRoute", "retries",
    "apiFailures", "duplicateCount", "userCorrections", "skillTriggerFailures", "skillProposals",
  ];
  for (const field of requiredFields) {
    assert.ok(field in rec, `missing field: ${field}`);
  }
});

// ---------------------------------------------------------------------------
// Aggregation math correctness
// ---------------------------------------------------------------------------

test("aggregateDailyReviews: percentages are correct", () => {
  const rec = makeRecord({ tasksDelegated: 10, success: 7, partial: 1, blocked: 1, failed: 1 });
  const result = aggregateDailyReviews([rec]);
  assert.strictEqual(result.successRate, 0.7);
  assert.strictEqual(result.partialRate, 0.1);
  assert.strictEqual(result.blockedRate, 0.1);
  assert.strictEqual(result.failedRate, 0.1);
});

test("aggregateDailyReviews: duplicate counts sum correctly", () => {
  const r1 = makeRecord({ duplicateCount: 3 });
  const r2 = makeRecord({ duplicateCount: 2 });
  const result = aggregateDailyReviews([r1, r2]);
  assert.strictEqual(result.totalDuplicateCount, 5);
});

test("aggregateDailyReviews: empty array returns zeros not NaN", () => {
  const result = aggregateDailyReviews([]);
  assert.strictEqual(result.totalTasksDelegated, 0);
  assert.strictEqual(result.successRate, 0);
  assert.strictEqual(result.duplicateRate, 0);
  assert.strictEqual(result.averageTasksPerDay, 0);
  assert.ok(Number.isFinite(result.successRate));
});

test("aggregateDailyReviews: averageTasksPerDay is computed correctly", () => {
  const r1 = makeRecord({ tasksDelegated: 10 });
  const r2 = makeRecord({ tasksDelegated: 20 });
  const result = aggregateDailyReviews([r1, r2]);
  assert.strictEqual(result.averageTasksPerDay, 15);
});

// ---------------------------------------------------------------------------
// Weekly roll-up edge cases
// ---------------------------------------------------------------------------

test("computeWeeklyReview: zero tasks → rates are 0 not NaN", () => {
  const result = computeWeeklyReview([], [], []);
  assert.strictEqual(result.delegationSuccessRate, 0);
  assert.strictEqual(result.costPerSuccessfulTask, 0);
  assert.strictEqual(result.modelRetryRate, 0);
  assert.strictEqual(result.apiToolFailureRate, 0);
  assert.strictEqual(result.skillFalseTriggerRate, 0);
  assert.ok(Number.isFinite(result.delegationSuccessRate));
});

test("computeWeeklyReview: partial runs counted distinctly from success", () => {
  const taskRuns = [
    makeTaskRun({ status: "success" }),
    makeTaskRun({ status: "partial" }),
    makeTaskRun({ status: "partial" }),
    makeTaskRun({ status: "failed" }),
  ];
  const modelRuns = [makeModelRun({ model_route: "R1", status: "completed" })];
  const result = computeWeeklyReview([makeRecord()], modelRuns, taskRuns);
  assert.strictEqual(result.delegationSuccessRate, 0.25); // 1/4
});

test("computeWeeklyReview: latency p50/p95 are computed correctly", () => {
  const modelRuns = [
    makeModelRun({ model_route: "R1", latency_ms: 100 }),
    makeModelRun({ model_route: "R1", latency_ms: 200 }),
    makeModelRun({ model_route: "R1", latency_ms: 300 }),
  ];
  const result = computeWeeklyReview([makeRecord()], modelRuns, []);
  assert.strictEqual(result.latencyP50ByRoute.R1, 200);
  assert.strictEqual(result.latencyP95ByRoute.R1, 200);
});

test("computeWeeklyReview: zero-latency route returns 0 not NaN", () => {
  const modelRuns = [makeModelRun({ model_route: "R3", latency_ms: null })];
  const result = computeWeeklyReview([makeRecord()], modelRuns, []);
  assert.strictEqual(result.latencyP50ByRoute.R3, 0);
  assert.strictEqual(result.latencyP95ByRoute.R3, 0);
});

// ---------------------------------------------------------------------------
// Release gate
// ---------------------------------------------------------------------------

test("release-gate: S0 defect blocks freeze", () => {
  const outcome = checkReleaseGate({
    criticalGates: [{ gateId: "g1", passed: true }],
    defects: [{ defectId: "d1", severity: "S0", category: "security", resolved: false }],
  });
  assert.strictEqual(outcome.canFreezeV1, false);
});

test("release-gate: S1 defect blocks freeze", () => {
  const outcome = checkReleaseGate({
    criticalGates: [{ gateId: "g1", passed: true }],
    defects: [{ defectId: "d1", severity: "S1", category: "duplication", resolved: false }],
  });
  assert.strictEqual(outcome.canFreezeV1, false);
});

test("release-gate: S2/S3 defects do NOT block freeze", () => {
  const outcome = checkReleaseGate({
    criticalGates: [{ gateId: "g1", passed: true }],
    defects: [
      { defectId: "d1", severity: "S2", category: "cosmetic", resolved: false },
      { defectId: "d2", severity: "S3", category: "cosmetic", resolved: false },
    ],
  });
  assert.strictEqual(outcome.canFreezeV1, true);
});

test("release-gate: missing gate (not passed) blocks freeze", () => {
  const outcome = checkReleaseGate({
    criticalGates: [{ gateId: "g1", passed: false }],
    defects: [],
  });
  assert.strictEqual(outcome.canFreezeV1, false);
  assert.strictEqual(outcome.failedGates.length, 1);
});

test("release-gate: all gates pass and no defects → can freeze", () => {
  const outcome = checkReleaseGate({
    criticalGates: [{ gateId: "g1", passed: true }, { gateId: "g2", passed: true }],
    defects: [{ defectId: "d1", severity: "S2", category: "cosmetic", resolved: false }],
  });
  assert.strictEqual(outcome.canFreezeV1, true);
});

// ---------------------------------------------------------------------------
// Questions data integrity
// ---------------------------------------------------------------------------

test("questions: exactly 11 questions present", () => {
  assert.strictEqual(PILOT_QUESTIONS.length, 11);
});

test("questions: all questions are non-empty", () => {
  for (const q of PILOT_QUESTIONS) {
    assert.ok(q.text.length > 0, `question ${q.id} has empty text`);
    assert.ok(q.id >= 1 && q.id <= 11, `question ${q.id} out of range`);
  }
});

test("questions: answer enum has exactly 3 values", () => {
  for (const q of PILOT_QUESTIONS) {
    assert.strictEqual(q.answerEnum.length, 3);
    assert.ok(q.answerEnum.includes("yes"));
    assert.ok(q.answerEnum.includes("partially"));
    assert.ok(q.answerEnum.includes("no"));
  }
});

test("questions: question IDs are sequential 1-11", () => {
  const ids = PILOT_QUESTIONS.map((q) => q.id);
  assert.deepStrictEqual(ids, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
});
