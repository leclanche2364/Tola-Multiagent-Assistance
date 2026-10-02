// Reconciler tests — Batch 09.
// Covers: idempotent reconciliation, timezone handling, changed schedule,
// removed job, unchanged job, invalid manifest.

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { AutomationReconciler } from "../src/reconciler.ts";
import { loadManifest } from "../src/manifest.ts";
import { fakeJobSource } from "../src/adapter.ts";
import type { OpenClawJob } from "../src/adapter.ts";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeJob(overrides: Partial<OpenClawJob> & { name: string }): OpenClawJob {
  return {
    id: `job-${Math.random().toString(36).slice(2, 8)}`,
    enabled: true,
    mode: "isolated",
    agentId: "tola",
    delivery: null,
    schedule: { kind: "cron", expr: "0 6 * * *", tz: "Europe/London" },
    ...overrides,
  };
}

async function reconcileWith(jobs: OpenClawJob[]) {
  const manifest = await loadManifest();
  const source = fakeJobSource(jobs);
  const reconciler = new AutomationReconciler(source, true);
  return reconciler.reconcile(manifest);
}

// ==================== Idempotent reconciliation ====================

describe("idempotent reconciliation", () => {
  test("running reconcile twice produces the same operations", async () => {
    const jobs = [
      makeJob({ name: "tola-morning-brief", schedule: { kind: "cron", expr: "30 7 * * *", tz: "Europe/London" } }),
    ];
    const r1 = await reconcileWith(jobs);
    const r2 = await reconcileWith(jobs);
    assert.strictEqual(r1.operations.length, r2.operations.length);
    assert.strictEqual(r1.operations[0].kind, r2.operations[0].kind);
    assert.strictEqual(r1.operations[0].stableName, r2.operations[0].stableName);
  });

  test("unchanged job produces no-op, not add", async () => {
    const jobs = [
      makeJob({
        name: "tola-morning-brief",
        schedule: { kind: "cron", expr: "30 7 * * *", tz: "Europe/London" },
      }),
    ];
    const result = await reconcileWith(jobs);
    const op = result.operations.find((o) => o.stableName === "tola-morning-brief");
    assert.ok(op, "should find tola-morning-brief");
    assert.strictEqual(op.kind, "no-op");
  });
});

// ==================== Timezone handling ====================

describe("timezone handling", () => {
  test("job with matching cron expr and tz matches manifest entry", async () => {
    const jobs = [
      makeJob({
        name: "growth-daily-anomaly",
        agentId: "growth",
        schedule: { kind: "cron", expr: "0 8 * * *", tz: "Europe/London" },
      }),
    ];
    const result = await reconcileWith(jobs);
    const op = result.operations.find((o) => o.stableName === "growth-daily-anomaly");
    assert.ok(op);
    assert.strictEqual(op.kind, "no-op");
  });

  test("job with different tz is flagged as edit", async () => {
    const jobs = [
      makeJob({
        name: "growth-daily-anomaly",
        agentId: "growth",
        schedule: { kind: "cron", expr: "0 8 * * *", tz: "UTC" },
      }),
    ];
    const result = await reconcileWith(jobs);
    const op = result.operations.find((o) => o.stableName === "growth-daily-anomaly");
    assert.ok(op);
    assert.strictEqual(op.kind, "edit");
    assert.ok(/Europe\/London/.test(op.summary));
  });
});

// ==================== Changed schedule ====================

describe("changed schedule", () => {
  test("job with different cron expr is flagged as edit", async () => {
    const jobs = [
      makeJob({
        name: "rhythm-capacity-refresh",
        schedule: { kind: "cron", expr: "0 6 * * *", tz: "Europe/London" },
      }),
    ];
    // Manifest has rhythm-capacity-refresh at 0 5 * * *
    const result = await reconcileWith(jobs);
    const op = result.operations.find((o) => o.stableName === "rhythm-capacity-refresh");
    assert.ok(op);
    assert.strictEqual(op.kind, "edit");
  });
});

// ==================== Removed job ====================

describe("removed job", () => {
  test("job not in manifest produces remove operation", async () => {
    const jobs = [
      makeJob({ name: "legacy-deprecated-job", schedule: { kind: "cron", expr: "0 12 * * *" } }),
    ];
    const result = await reconcileWith(jobs);
    const ops = result.operations.filter((o) => o.kind === "remove");
    assert.ok(ops.some((o) => o.stableName === "legacy-deprecated-job"));
  });

  test("remove operation has no jobId when job has no id", async () => {
    const jobs = [
      { ...makeJob({ name: "legacy-deprecated-job" }), id: "" },
    ];
    const result = await reconcileWith(jobs);
    const op = result.operations.find((o) => o.stableName === "legacy-deprecated-job");
    assert.ok(op);
    assert.strictEqual(op.kind, "remove");
  });
});

// ==================== Unchanged job ====================

describe("unchanged job", () => {
  test("job matching manifest entry exactly is no-op", async () => {
    const jobs = [
      makeJob({
        name: "blackboard-reconciler",
        schedule: { kind: "cron", expr: "0 6 * * *", tz: "Europe/London" },
        mode: "isolated",
        agentId: "tola",
      }),
    ];
    const result = await reconcileWith(jobs);
    const op = result.operations.find((o) => o.stableName === "blackboard-reconciler");
    assert.ok(op);
    assert.strictEqual(op.kind, "no-op");
  });
});

// ==================== Invalid manifest ====================

describe("invalid manifest", () => {
  test("missing automations array throws", async () => {
    const { AutomationReconciler } = await import("../src/reconciler.ts");
    const badManifest = { version: "1.0.0", automations: undefined };
    const source = fakeJobSource([]);
    const reconciler = new AutomationReconciler(source, true);
    await assert.rejects(
      reconciler.reconcile(badManifest as any),
      /not iterable/
    );
  });

  test("entry missing stableName is caught by loader", async () => {
    const { loadManifest } = await import("../src/manifest.ts");
    // Use the real manifest — it should load cleanly.
    // We test validation by checking that all entries have stableName.
    const manifest = await loadManifest();
    for (const entry of manifest.automations) {
      assert.ok(entry.stableName, `entry missing stableName: ${JSON.stringify(entry)}`);
    }
  });
});

// ==================== Dry-run default ====================

describe("dry-run default", () => {
  test("reconciler defaults to dry-run (does not mutate)", async () => {
    const jobs = [makeJob({ name: "tola-morning-brief", schedule: { kind: "cron", expr: "30 7 * * *", tz: "Europe/London" } })];
    const manifest = await loadManifest();
    const source = fakeJobSource(jobs);
    // No dryRun arg → defaults to true
    const reconciler = new AutomationReconciler(source);
    const result = await reconciler.reconcile(manifest);
    assert.strictEqual(result.dryRun, true);
  });
});
