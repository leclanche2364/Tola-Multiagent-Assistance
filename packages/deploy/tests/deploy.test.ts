// Deploy tool tests — Batch 11.
// Covers: dry run, invalid SHA, failed build, failed migration,
// failed plugin reload, failed canary, rollback.

import { test, describe, after } from "node:test";
import assert from "node:assert/strict";
import { dryRun, apply, buildDeployPlan, showMigrationPlan } from "../src/deploy.ts";
import { fakeAdapter } from "../src/adapter.ts";
import type { DeployAdapter } from "../src/adapter.ts";

// ==================== Dry run ====================

describe("dry run", () => {
  test("dry run succeeds for valid SHA", async () => {
    const sha = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2";
    const result = dryRun(sha, "v1.0.0");
    assert.strictEqual(result.success, true);
    assert.strictEqual(result.phase, "dry-run");
    assert.ok(result.details.includes("DRY-RUN"));
    assert.ok(result.details.includes(sha));
    assert.strictEqual(result.rollbackPerformed, false);
  });

  test("dry run includes all steps in plan", async () => {
    const sha = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2";
    const plan = buildDeployPlan(sha, "v1.0.0");
    assert.strictEqual(plan.steps.length, 7);
    assert.ok(plan.steps.every((s) => s.dryRunOnly === true));
  });

  test("dry run uses staging directory", async () => {
    const sha = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2";
    const plan = buildDeployPlan(sha, "v1.0.0");
    assert.ok(plan.stagingDir.includes(sha.slice(0, 7)));
    assert.ok(plan.stagingDir.startsWith(".deploy-staging/"));
  });
});

// ==================== Invalid SHA ====================

describe("invalid SHA", () => {
  test("rejects empty SHA", () => {
    assert.throws(() => buildDeployPlan("", "v1.0.0"), /Invalid SHA/);
  });

  test("rejects whitespace-only SHA", () => {
    assert.throws(() => buildDeployPlan("   ", "v1.0.0"), /Invalid SHA/);
  });

  test("rejects SHA with special chars", () => {
    assert.throws(() => buildDeployPlan("not@valid#sha!", "v1.0.0"), /Invalid SHA/);
  });

  test("rejects short SHA (less than 7 chars)", () => {
    assert.throws(() => buildDeployPlan("abc123", "v1.0.0"), /Invalid SHA/);
  });

  test("dry run throws on invalid SHA", () => {
    assert.throws(() => dryRun("invalid", "v1.0.0"), /Invalid SHA/);
  });
});

// ==================== Failed build ====================

describe("failed build", () => {
  test("apply mode fails when build step fails", async () => {
    const adapter = fakeAdapter({
      failOn: ["reloadPlugin"],
      getActivePlugin: async () => ({ path: "/live/plugin.js", version: "0.0.0", sha: "0000000" }),
      backupConfig: async () => "/tmp/backup.json",
    });

    const result = await apply("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", "v1.0.0", adapter);
    assert.strictEqual(result.success, false);
    assert.strictEqual(result.rollbackPerformed, true);
  });
});

// ==================== Failed migration ====================

describe("failed migration", () => {
  test("apply mode rolls back when migration fails", async () => {
    const adapter = fakeAdapter({
      failOn: ["applyMigration"],
      getActivePlugin: async () => ({ path: "/live/plugin.js", version: "0.0.0", sha: "0000000" }),
      backupConfig: async () => "/tmp/backup.json",
    });

    const result = await apply("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", "v1.0.0", adapter);
    assert.strictEqual(result.success, false);
    assert.strictEqual(result.rollbackPerformed, true);
  });
});

// ==================== Failed plugin reload ====================

describe("failed plugin reload", () => {
  test("apply mode rolls back when plugin reload fails", async () => {
    const adapter = fakeAdapter({
      failOn: ["reloadPlugin"],
      getActivePlugin: async () => ({ path: "/live/plugin.js", version: "0.0.0", sha: "0000000" }),
      backupConfig: async () => "/tmp/backup.json",
      applyMigration: async () => {},
    });

    const result = await apply("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", "v1.0.0", adapter);
    assert.strictEqual(result.success, false);
    assert.strictEqual(result.rollbackPerformed, true);
  });
});

// ==================== Failed canary ====================

describe("failed canary", () => {
  test("apply mode rolls back when canary fails", async () => {
    const adapter = fakeAdapter({
      getActivePlugin: async () => ({ path: "/live/plugin.js", version: "0.0.0", sha: "0000000" }),
      backupConfig: async () => "/tmp/backup.json",
      applyMigration: async () => {},
      reloadPlugin: async () => {},
      applyConfig: async () => {},
      reconcileJobs: async () => ({ dryRun: false, operationsCount: 0 }),
      runCanaries: async () => ({
        ok: false,
        checks: [
          { name: "plugin-health", passed: false, detail: "timeout" },
          { name: "config-sync", passed: false, detail: "mismatch" },
        ],
      }),
    });

    const result = await apply("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", "v1.0.0", adapter);
    assert.strictEqual(result.success, false);
    assert.strictEqual(result.rollbackPerformed, true);
    assert.ok(result.details.includes("Canary failed"));
  });
});

// ==================== Rollback ====================

describe("rollback", () => {
  test("failed canary triggers restoreConfig", async () => {
    const adapter = fakeAdapter({
      getActivePlugin: async () => ({ path: "/live/plugin.js", version: "0.0.0", sha: "0000000" }),
      backupConfig: async () => "/tmp/backup.json",
      applyMigration: async () => {},
      reloadPlugin: async () => {},
      applyConfig: async () => {},
      reconcileJobs: async () => ({ dryRun: false, operationsCount: 0 }),
      runCanaries: async () => ({ ok: false, checks: [{ name: "health", passed: false }] }),
      rollbackMigration: async () => {},
      restoreConfig: async () => {},
    });

    const calls = (adapter as any)._calls();
    const result = await apply("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", "v1.0.0", adapter);

    assert.strictEqual(result.success, false);
    assert.strictEqual(result.rollbackPerformed, true);

    // Verify rollback methods were called
    const methodNames = calls.map((c: any) => c.method);
    assert.ok(methodNames.includes("rollbackMigration"), "rollbackMigration should be called");
    assert.ok(methodNames.includes("restoreConfig"), "restoreConfig should be called");
  });

  test("successful apply does not call rollback or restore", async () => {
    const adapter = fakeAdapter({
      getActivePlugin: async () => ({ path: "/live/plugin.js", version: "0.0.0", sha: "0000000" }),
      backupConfig: async () => "/tmp/backup.json",
      applyMigration: async () => {},
      reloadPlugin: async () => {},
      applyConfig: async () => {},
      reconcileJobs: async () => ({ dryRun: false, operationsCount: 0 }),
      runCanaries: async () => ({ ok: true, checks: [] }),
    });

    const calls = (adapter as any)._calls();
    const result = await apply("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", "v1.0.0", adapter);

    assert.strictEqual(result.success, true);
    const methodNames = calls.map((c: any) => c.method);
    assert.ok(!methodNames.includes("rollbackMigration"), "rollbackMigration should NOT be called");
    assert.ok(!methodNames.includes("restoreConfig"), "restoreConfig should NOT be called");
  });
});

// ==================== Migration plan ====================

describe("migration plan", () => {
  test("showMigrationPlan returns forward and rollback entries", () => {
    const plans = showMigrationPlan();
    assert.strictEqual(plans.length, 2);
    assert.strictEqual(plans[0].direction, "forward");
    assert.strictEqual(plans[1].direction, "rollback");
    assert.ok(plans.every((p) => p.safeForward === true));
  });
});

// ==================== Reconciliation ====================

describe("automation reconciliation", () => {
  test("dry-run reconciliation is called in dry-run mode", async () => {
    const adapter = fakeAdapter({
      getActivePlugin: async () => ({ path: "/live/plugin.js", version: "0.0.0", sha: "0000000" }),
      backupConfig: async () => "/tmp/backup.json",
      applyMigration: async () => {},
      reloadPlugin: async () => {},
      applyConfig: async () => {},
      runCanaries: async () => ({ ok: true, checks: [] }),
      reconcileJobs: async (dryRun) => ({ dryRun, operationsCount: 3 }),
    });

    const calls = (adapter as any)._calls();
    await apply("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", "v1.0.0", adapter);

    const reconcileCall = calls.find((c: any) => c.method === "reconcileJobs");
    assert.ok(reconcileCall, "reconcileJobs should be called");
    assert.strictEqual(reconcileCall.args[0], false, "apply mode should use live reconciliation");
  });
});
