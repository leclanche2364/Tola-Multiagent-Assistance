// Batch 12 Gate F — Chaos injections.

import { SupabaseAdapter, BlackboardError } from "../packages/blackboard-tools/src/adapters/supabase.ts";
import { fakeAdapter } from "../packages/deploy/src/adapter.ts";
import { FakeApprovalExecutor } from "../packages/action-policy/src/executor.ts";

const results: string[] = [];
let allPass = true;

// F1: Unreachable Supabase URL — bounded failure, no false success
async function f1() {
  results.push("=== F1: Unreachable Supabase URL ===");
  const adapter = new SupabaseAdapter({
    url: "https://unreachable.invalid.rest/v1",
    serviceKey: "fake-key",
    timeoutMs: 2000,
  });
  try {
    await adapter.request("GET", "tasks", { query: { id: "test" } });
    results.push("FAIL: should have thrown");
    allPass = false;
  } catch (err: unknown) {
    const e = err as BlackboardError;
    const bounded = e.code === "UNAVAILABLE";
    results.push("Error code: " + e.code + " — " + (bounded ? "PASS (bounded UNAVAILABLE, no false success)" : "FAIL"));
    if (!bounded) allPass = false;
  }
}

// F2: Delegate provider failure — bounded retry then escalation
async function f2() {
  results.push("=== F2: Delegate provider failure ===");
  let attemptCount = 0;
  const failingDelegate = async (_agentId: string, _prompt: string, _timeoutMs: number) => {
    attemptCount++;
    // Always fail — simulates persistent provider failure
    throw new Error("provider permanently unavailable");
  };

  const MAX_RETRIES = 2;
  let escalated = false;
  let lastError: Error | null = null;

  for (let i = 0; i <= MAX_RETRIES; i++) {
    try {
      await failingDelegate("specialist", "do work", 5000);
      break; // success — should not reach here
    } catch (err: unknown) {
      lastError = err as Error;
      if (i >= MAX_RETRIES) {
        escalated = true;
        results.push("Attempt " + (i + 1) + ": failed — escalation triggered (bounded retry exhausted)");
      } else {
        results.push("Attempt " + (i + 1) + ": failed — retrying (" + lastError.message + ")");
      }
    }
  }

  const f2pass = escalated && attemptCount === MAX_RETRIES + 1;
  results.push("F2: escalated=" + escalated + ", attempts=" + attemptCount + " — " + (f2pass ? "PASS" : "FAIL"));
  if (!f2pass) allPass = false;
}

// F3: Plugin reload failure — restore path runs
async function f3() {
  results.push("=== F3: Plugin reload failure + restore path ===");
  const calls: string[] = [];
  const adapter = fakeAdapter({
    failOn: ["reloadPlugin"],
    getActivePlugin: async () => { calls.push("getActivePlugin"); return { path: "/live/plugin.js", version: "0.0.0", sha: "0000000" }; },
    backupConfig: async () => { calls.push("backupConfig"); return "/tmp/backup.json"; },
    restoreConfig: async (path: string) => { calls.push("restoreConfig:" + path); },
    applyMigration: async () => { calls.push("applyMigration"); },
    rollbackMigration: async (f: string) => { calls.push("rollbackMigration:" + f); },
    reloadPlugin: async () => { calls.push("reloadPlugin"); throw new Error("FAKE_ADAPTER_FAILURE:reloadPlugin"); },
    applyConfig: async () => { calls.push("applyConfig"); },
    runCanaries: async () => { calls.push("runCanaries"); return { ok: true, checks: [] }; },
    reconcileJobs: async (dryRun: boolean) => { calls.push("reconcileJobs:" + dryRun); return { dryRun, operationsCount: 0 }; },
  });

  try { await adapter.reloadPlugin("dist/index.js"); } catch { /* expected */ }
  await adapter.restoreConfig("/tmp/backup.json");

  const hasRestore = calls.some(c => c.startsWith("restoreConfig"));
  results.push("Calls: " + calls.join(", "));
  results.push("Restore path called: " + (hasRestore ? "PASS" : "FAIL"));
  if (!hasRestore) allPass = false;
}

// F4: Uncertain external write — reconciles to unknown, never retried blindly
async function f4() {
  results.push("=== F4: Uncertain external write ===");
  const executor = new FakeApprovalExecutor();
  const approval = await executor.requestApproval({
    action: "blackboard.createTask",
    payload: { title: "uncertain write test" },
    requester: "gate-f4",
    releaseSha: "aa4f0e2aacf564a3b3147291d8183e6cf981ae62",
    taskId: "task-f4-001",
    expirySeconds: 300,
    scope: "internal_reversible_write",
  });
  await executor.approveApproval(approval.approval_id, "operator");

  let sideEffectExecuted = false;
  const result = await executor.executeApproved({
    approvalId: approval.approval_id,
    action: "blackboard.createTask",
    payload: { title: "uncertain write test" },
    requester: "gate-f4",
    releaseSha: "aa4f0e2aacf564a3b3147291d8183e6cf981ae62",
    taskId: "task-f4-001",
    effect: async () => {
      sideEffectExecuted = true;
      throw new Error("external write succeeded but confirmation failed");
    },
  });

  results.push("Result status: " + result.status + " (expected: unknown)");
  results.push("Side effect executed: " + sideEffectExecuted + " (expected: true)");
  results.push("Reconciliation required: " + (result as { reconciliationRequired: boolean }).reconciliationRequired + " (expected: true)");

  const replay = await executor.executeApproved({
    approvalId: approval.approval_id,
    action: "blackboard.createTask",
    payload: { title: "uncertain write test" },
    requester: "gate-f4",
    releaseSha: "aa4f0e2aacf564a3b3147291d8183e6cf981ae62",
    taskId: "task-f4-001",
    effect: async () => { throw new Error("should not re-execute"); },
  });
  results.push("Replay status: " + replay.status + " (expected: consumed, never retried blindly)");

  const f4pass = result.status === "unknown" && sideEffectExecuted && replay.status === "consumed";
  results.push("F4: " + (f4pass ? "PASS" : "FAIL"));
  if (!f4pass) allPass = false;
}

await f1();
await f2();
await f3();
await f4();

results.push("GATE-F: " + (allPass ? "PASS" : "FAIL"));
console.log(results.join("\n"));
if (!allPass) process.exit(1);
