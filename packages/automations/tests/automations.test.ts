// Automations — Batch 14
// T14.1–T14.6: proactive automation idempotency, no-change suppression, outage handling, restart persistence
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/automations.test.ts

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import {
  AutomationRunner,
  type RunResult,
  type WorkflowResult,
  AUTOMATIONS,
  InMemoryAutomationStateStore,
} from "../src/index.ts";

// ---------------------------------------------------------------------------
// Minimal mock BlackboardRepository (only the methods the runner needs)
// ---------------------------------------------------------------------------

type TaskRunRow = {
  run_id: string;
  task_id: string;
  idempotency_key: string;
  attempt: number;
  status: "running" | "success" | "partial" | "blocked" | "needs_approval" | "failed";
  summary: string | null;
  outputs: unknown[];
  evidence_refs: unknown[];
  tool_actions: unknown[];
  blockers: unknown[];
  verification: Record<string, unknown>;
  started_at: string;
  finished_at: string | null;
};

class MinimalBlackboardRepository {
  private runs: Map<string, TaskRunRow> = new Map(); // run_id → row
  private nextRunId = 1;

  async startTaskRun(input: {
    task_id: string;
    idempotency_key: string;
    attempt?: number;
    summary?: string | null;
  }): Promise<TaskRunRow> {
    const runId = `run-${this.nextRunId++}`;
    const row: TaskRunRow = {
      run_id: runId,
      task_id: input.task_id,
      idempotency_key: input.idempotency_key,
      attempt: input.attempt ?? 1,
      status: "running",
      summary: input.summary ?? null,
      outputs: [],
      evidence_refs: [],
      tool_actions: [],
      blockers: [],
      verification: {},
      started_at: new Date().toISOString(),
      finished_at: null,
    };
    this.runs.set(runId, row);
    return row;
  }

  async completeTaskRun(input: {
    run_id: string;
    status: TaskRunRow["status"];
    summary?: string | null;
  }): Promise<TaskRunRow> {
    const row = this.runs.get(input.run_id);
    if (!row) throw new Error(`run ${input.run_id} not found`);
    row.status = input.status;
    row.summary = input.summary ?? row.summary;
    row.finished_at = new Date().toISOString();
    return row;
  }

  getRunsMap(): Map<string, TaskRunRow> {
    return this.runs;
  }
}

// ---------------------------------------------------------------------------
// Helper: fixed clock for deterministic tests
// ---------------------------------------------------------------------------

function fixedClock(year: number, month: number, day: number): () => Date {
  // Use UTC to avoid timezone skew (the workspace TZ is Europe/London,
  // where new Date(2026, 8, 27) maps to 2026-09-26T23:00:00.000Z).
  const date = new Date(Date.UTC(year, month - 1, day));
  return () => new Date(date.getTime());
}

// Helper: compute period strings matching the runner logic
function periodFor(now: Date, automationId: string): string {
  if (/daily/i.test(automationId)) {
    return now.toISOString().split("T")[0];
  }
  const y = now.getFullYear();
  const jan1 = new Date(y, 0, 1);
  const dayOfYear = Math.floor((now.getTime() - jan1.getTime()) / 86400000);
  const jan4 = new Date(y, 0, 4);
  const offsetToJan4 = (jan4.getDay() + 6) % 7;
  const weekNum = Math.ceil((dayOfYear + offsetToJan4) / 7);
  return `2026-W${String(weekNum).padStart(2, "0")}`;
}

// ==================== T14.1 ====================
describe("T14.1 Growth anomaly idempotence", () => {
  test("second run same period returns {skipped:'already-run'}, no duplicate task run", async () => {
    const repo = new MinimalBlackboardRepository();
    const clock = fixedClock(2026, 9, 27);
    const store = new InMemoryAutomationStateStore();
    const workflows: any = {
      "growth-daily-anomaly": async () => ({ changed: true, summary: "anomaly detected" }),
    };
    const runner = new AutomationRunner(repo, clock, store, workflows);

    const result1 = await runner.runDue("growth-daily-anomaly");
    assert.strictEqual(result1.status, "ok");
    assert.ok(result1.taskRunId !== undefined);

    const result2 = await runner.runDue("growth-daily-anomaly");
    assert.strictEqual(result2.status, "skipped");
    assert.strictEqual(result2.reason, "already-run");

    const runKeys: string[] = Array.from(repo.getRunsMap().keys());
    assert.strictEqual(runKeys.length, 1);
  });
});

// ==================== T14.2 ====================
describe("T14.2 Weekly growth review date range", () => {
  test("workflow produces exactly one summary per period", async () => {
    const repo = new MinimalBlackboardRepository();
    const clock = fixedClock(2026, 9, 27);
    const store = new InMemoryAutomationStateStore();
    const workflows: any = {
      "growth-weekly-review": async () => ({ changed: true, summary: "weekly review summary" }),
    };
    const runner = new AutomationRunner(repo, clock, store, workflows);

    await runner.runDue("growth-weekly-review");

    const runs = repo.getRunsMap();
    const runKeys = Array.from(runs.keys());
    assert.strictEqual(runKeys.length, 1, "exactly one task run should be recorded");
    const completed = runs.get(runKeys[0])!;
    assert.strictEqual(completed.summary, "weekly review summary");
  });
});

// ==================== T14.3 ====================
describe("T14.3 Tola weekly review necessary tasks only", () => {
  test("workflow only runs once per period due to idempotency", async () => {
    const repo = new MinimalBlackboardRepository();
    const clock = fixedClock(2026, 9, 27);
    const store = new InMemoryAutomationStateStore();
    let workflowCallCount = 0;
    const workflows: any = {
      "tola-weekly-review": async () => {
        workflowCallCount++;
        return { changed: true, summary: `task-created-${workflowCallCount}` };
      },
    };
    const runner = new AutomationRunner(repo, clock, store, workflows);

    const result1 = await runner.runDue("tola-weekly-review");
    assert.strictEqual(result1.status, "ok");
    assert.strictEqual(workflowCallCount, 1);

    const result2 = await runner.runDue("tola-weekly-review");
    assert.strictEqual(result2.status, "skipped");
    assert.strictEqual(workflowCallCount, 1);

    const runKeys: string[] = Array.from(repo.getRunsMap().keys());
    assert.strictEqual(runKeys.length, 1);
  });
});

// ==================== T14.4 ====================
describe("T14.4 Scholar no-change state", () => {
  test("workflow returns {changed:false} → run recorded no-change", async () => {
    const repo = new MinimalBlackboardRepository();
    const clock = fixedClock(2026, 9, 27);
    const store = new InMemoryAutomationStateStore();
    const workflows: any = {
      "scholar-weekly-progress": async () => ({ changed: false, summary: "no changes, state current" }),
    };
    const runner = new AutomationRunner(repo, clock, store, workflows);

    const result = await runner.runDue("scholar-weekly-progress");
    assert.strictEqual(result.status, "no-change");
    assert.strictEqual(result.summary, "no changes, state current");

    const runs = repo.getRunsMap();
    const runKeys = Array.from(runs.keys());
    const completed = runs.get(runKeys[0])!;
    assert.strictEqual(completed.status, "success");
  });

  test("scholar no-change run recorded without duplicate notification", async () => {
    const repo = new MinimalBlackboardRepository();
    const clock = fixedClock(2026, 9, 27);
    const store = new InMemoryAutomationStateStore();
    const workflows: any = {
      "scholar-weekly-progress": async () => ({ changed: false }),
    };
    const runner = new AutomationRunner(repo, clock, store, workflows);

    const result = await runner.runDue("scholar-weekly-progress");
    assert.strictEqual(result.status, "no-change");

    const runs = repo.getRunsMap();
    const runKeys = Array.from(runs.keys());
    assert.strictEqual(runKeys.length, 1);
  });
});

// ==================== T14.5 ====================
describe("T14.5 Restart persistence", () => {
  test("new runner instance with same store skips already-run period", async () => {
    const repo = new MinimalBlackboardRepository();
    const clock = fixedClock(2026, 9, 27);

    const store1 = new InMemoryAutomationStateStore();
    const workflows: any = {
      "growth-daily-anomaly": async () => ({ changed: true, summary: "anomaly" }),
    };
    const runner1 = new AutomationRunner(repo, clock, store1, workflows);
    const firstResult = await runner1.runDue("growth-daily-anomaly");
    assert.strictEqual(firstResult.status, "ok");

    const store2 = new InMemoryAutomationStateStore();
    await store2.markRun("growth-daily-anomaly", "2026-09-27");
    const runner2 = new AutomationRunner(repo, clock, store2, workflows);
    const restartResult = await runner2.runDue("growth-daily-anomaly");
    assert.strictEqual(restartResult.status, "skipped");
    assert.strictEqual(restartResult.reason, "already-run");
  });
});

// ==================== T14.6 ====================
describe("T14.6 API outage handling", () => {
  test("workflow throws → run recorded failed/partial with error gist", async () => {
    const repo = new MinimalBlackboardRepository();
    const clock = fixedClock(2026, 9, 27);
    const store = new InMemoryAutomationStateStore();
    const workflows: any = {
      "growth-daily-anomaly": async () => {
        throw new Error("API timeout");
      },
    };
    const runner = new AutomationRunner(repo, clock, store, workflows);

    const result = await runner.runDue("growth-daily-anomaly");
    assert.strictEqual(result.status, "failed");

    const runs = repo.getRunsMap();
    const runKeys = Array.from(runs.keys());
    const completed = runs.get(runKeys[0])!;
    assert.strictEqual(completed.status, "partial");
    assert.ok(/API timeout/.test(completed.summary || ""));
  });

  test("immediate re-run same period does not re-execute workflow (no noisy repeat loop)", async () => {
    const repo = new MinimalBlackboardRepository();
    const clock = fixedClock(2026, 9, 27);
    const store = new InMemoryAutomationStateStore();
    const workflows: any = {
      "growth-daily-anomaly": async () => {
        throw new Error("API timeout");
      },
    };
    const runner = new AutomationRunner(repo, clock, store, workflows);

    const result1 = await runner.runDue("growth-daily-anomaly");
    assert.strictEqual(result1.status, "failed");

    const result2 = await runner.runDue("growth-daily-anomaly");
    assert.strictEqual(result2.status, "skipped");
    assert.strictEqual(result2.reason, "already-run");
  });
});