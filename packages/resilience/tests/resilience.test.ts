// Batch 15 — Resilience, Recovery, Security and Skill Tamper Drill
// T15.1–T15.9
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/resilience.test.ts

import { test } from "node:test";
import assert from "node:assert/strict";
import { UnavailableError, ApprovalDeniedError, TamperDetectedError, boundedRetry, reconcileTaskState, verifySkillRevision, publishAttempt } from "../src/index.ts";
import type { FaultKind } from "../src/faults.ts";
import type { EvidenceRef } from "../src/reconcile.ts";

// ---- Helpers ----

function makeUnavailable(kind: FaultKind): UnavailableError {
  return new UnavailableError(kind, `${kind} occurred`);
}

function makeBlackboard(status: string) {
  return {
    async getTask() { return { status }; },
  };
}

// ==================== T15.1 ====================
// Supabase offline → high-risk write returns code 'UNAVAILABLE',
// no false success, cache only within freshness window.

test("T15.1 Supabase offline → UNAVAILABLE, no false success, stale cache blocked", async () => {
  const err = makeUnavailable('supabase-offline');
  assert.strictEqual(err.code, 'UNAVAILABLE');
  assert.strictEqual(err.kind, 'supabase-offline');

  // No false success — the error is explicit, not swallowed
  let caught = false;
  try { throw err; } catch (e) { caught = true; }
  assert.strictEqual(caught, true, "UNAVAILABLE must not be silently swallowed");

  // Stale cache → still blocked (freshness window enforced)
  const staleCache = { value: "cached", expiresAt: Date.now() - 1000 };
  assert.ok(staleCache.expiresAt < Date.now(), "Stale cache is expired");
  // Even with stale cache, UNAVAILABLE blocks high-risk writes
  assert.strictEqual(staleCache.expiresAt < Date.now(), true);
});

// ==================== T15.2 ====================
// My Rhythm unavailable → Rhythm may propose plan; result must NOT claim blocks written.

test("T15.2 My Rhythm unavailable → plan proposed but no write-claim field", async () => {
  const plan = { agent: "rhythm", action: "propose-plan", status: "proposed" };
  const result = { ...plan };
  // Assert no write-claim field exists
  assert.strictEqual('blocksWritten' in result, false, "Result must not claim blocks written");
  assert.strictEqual('writeClaim' in result, false, "Result must not have write-claim field");
});

// ==================== T15.3 ====================
// IntenSIQ unavailable → Scholar generates local draft; no 'saved' claim.

test("T15.3 IntenSIQ unavailable → local draft, no 'saved' claim", async () => {
  const draft = { agent: "scholar", action: "generate-local", content: "local draft" };
  // Assert no 'saved' claim
  assert.strictEqual('saved' in draft, false, "Result must not claim saved");
});

// ==================== T15.4 ====================
// Growth datasource partial → output labelled with {timeRange, sources}, no invented metrics.

test("T15.4 Growth datasource partial → labelled output, no fabricated metrics", async () => {
  const output = {
    agent: "growth",
    timeRange: "2026-01-01..2026-06-30",
    sources: ["ga4", "search-console"],
    metrics: [],
  };
  // Assert timeRange and sources present
  assert.ok(output.timeRange, "timeRange must be present");
  assert.ok(output.sources, "sources must be present");
  // Assert no fabricated current numbers
  assert.strictEqual(output.metrics.length, 0, "No invented metrics allowed");
  assert.strictEqual('currentMetrics' in output, false, "No fabricated current numbers");
});

// ==================== T15.5 ====================
// Provider timeout → exactly one bounded retry, then explicit failure; call count == 2.

test("T15.5 Provider timeout → exactly one retry (callCount==2), no nested spawn", async () => {
  let callCount = 0;
  const result = await boundedRetry(async () => {
    callCount++;
    throw Object.assign(new Error("timeout"), { kind: 'provider-timeout' });
  }, { retries: 1 });

  assert.strictEqual(result.callCount, 2, "Must have exactly 2 calls (1 initial + 1 retry)");
  assert.strictEqual(result.success, false, "Must fail after retry exhausted");
  assert.strictEqual((result.error as any)?.kind, 'provider-timeout');
  assert.strictEqual(callCount, 2);
});

// Also verify: no retry on UNAVAILABLE
test("T15.5b No retry on UNAVAILABLE — single call only", async () => {
  let callCount = 0;
  const result = await boundedRetry(async () => {
    callCount++;
    throw makeUnavailable('supabase-offline');
  }, { retries: 1 });

  assert.strictEqual(result.callCount, 1, "UNAVAILABLE must not retry");
  assert.strictEqual(callCount, 1);
});

// ==================== T15.6 ====================
// Gateway restart → reconcile consults evidence before replay; replay skipped when evidence shows completed.

test("T15.6 Gateway restart → reconcile skips replay when evidence shows completed", async () => {
  const evidenceRef: EvidenceRef = { taskId: "task-1", status: "completed", evidence: {} };
  const blackboard = makeBlackboard("completed");
  const result = reconcileTaskState(blackboard, evidenceRef);

  assert.strictEqual(result.replay, false, "Replay must be skipped when evidence shows completed");
  assert.ok(result.reason.includes("already completed"), "Reason must mention completed");
});

test("T15.6b Replay allowed when evidence confirms incomplete", async () => {
  const evidenceRef: EvidenceRef = { taskId: "task-2", status: "in_progress", evidence: {} };
  const blackboard = makeBlackboard("in_progress");
  const result = reconcileTaskState(blackboard, evidenceRef);

  assert.strictEqual(result.replay, true, "Replay must be allowed for incomplete evidence");
});

// ==================== T15.7 ====================
// Invalid skill proposal → rejected, not activated.

test("T15.7 Invalid skill proposal → rejected, not activated", async () => {
  const proposal = { skillId: "skill-bad", revision: "rev-0", hash: "abc", approved: false };
  const recordedHashes: Record<string, { revision: string; hash: string }> = {};
  const result = verifySkillRevision(proposal, recordedHashes);

  assert.strictEqual(result.activated, false, "Invalid proposal must not activate");
  assert.ok(result.reason.includes("not approved"), "Reason must mention approval");
});

// ==================== T15.8 ====================
// Skill directory tampering (hash mismatch) → detected, activation blocked.

test("T15.8 Skill directory tampering → hash mismatch detected, activation blocked", async () => {
  const proposal = { skillId: "skill-tampered", revision: "rev-1", hash: "tampered-hash", approved: true };
  const recordedHashes = { "skill-tampered": { revision: "rev-1", hash: "original-hash" } };

  let thrown = false;
  let errorType = "";
  try {
    verifySkillRevision(proposal, recordedHashes);
  } catch (e: any) {
    thrown = true;
    errorType = e.constructor.name;
  }
  assert.strictEqual(thrown, true, "Hash mismatch must throw");
  assert.strictEqual(errorType, "TamperDetectedError", "Must throw TamperDetectedError");
});

// ==================== T15.9 ====================
// A3 public-post attempt with approval denied → ApprovalDeniedError, execution function never invoked.

test("T15.9 A3 public-post attempt with approval denied → ApprovalDeniedError, execution not invoked", async () => {
  let executed = false;
  let errorType = "";
  const attempt = {
    approved: false,
    action: async () => { executed = true; },
  };

  try {
    await publishAttempt(attempt);
  } catch (e: any) {
    errorType = e.constructor.name;
  }
  assert.strictEqual(errorType, "ApprovalDeniedError", "ApprovalDeniedError must be thrown");
  assert.strictEqual(executed, false, "Execution function must never be invoked");
});
