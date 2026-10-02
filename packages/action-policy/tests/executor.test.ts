/**
 * Batch 06 — Approval executor tests.
 *
 * Covers: denial, expiry, payload mutation, replay, concurrent execution,
 * wrong release, wrong agent, and successful single execution.
 * Uses FakeApprovalExecutor (no real external effects).
 */
import test from "node:test";
import assert from "node:assert/strict";
import {
  FakeApprovalExecutor,
  hashAction,
  redactApprovalScope,
  type ApprovalRequestParams,
  evaluateAction,
} from "../src/index.ts";

const RELEASE_SHA = "abc123def456";
const REQUESTER = "tola";
const TASK_ID = "00000000-0000-0000-0000-000000000001";
const APPROVAL_TYPE = "bound_action";
const FROZEN_NOW = "2026-10-02T12:00:00.000Z";

function cfg(over: Partial<{ envelopes: unknown[]; maxPayloadBytes: number }> = {}): { envelopes: unknown[]; maxPayloadBytes: number; now: () => string } {
  return {
    envelopes: over.envelopes ?? [],
    maxPayloadBytes: over.maxPayloadBytes ?? 16 * 1024,
    now: () => FROZEN_NOW,
  };
}

function makeParams(over: Partial<ApprovalRequestParams> = {}): ApprovalRequestParams {
  return {
    action: over.action ?? "messaging.sendPrivateMessage",
    payload: over.payload ?? { destination: "+447700900123", text: "hello" },
    requester: over.requester ?? REQUESTER,
    releaseSha: over.releaseSha ?? RELEASE_SHA,
    taskId: over.taskId ?? TASK_ID,
    expirySeconds: over.expirySeconds ?? 300,
    scope: over.scope ?? "private_external_write",
  };
}

test("T6.1 denial — unapproved action cannot execute", async () => {
  const exec = new FakeApprovalExecutor();
  const result = await exec.executeApproved({
    approvalId: "nonexistent",
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    effect: async () => { throw new Error("should not reach here"); },
  });
  assert.equal(result.status, "denied");
  assert.equal(result.reason, "approval_not_found");
});

test("T6.2 expiry — expired approval cannot execute", async () => {
  const exec = new FakeApprovalExecutor();
  const approval = await exec.requestApproval({
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    expirySeconds: -1, // already expired
    scope: "private_external_write",
  });
  assert.equal(approval.status, "pending");

  const result = await exec.executeApproved({
    approvalId: approval.approval_id,
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    effect: async () => { throw new Error("should not reach here"); },
  });
  assert.equal(result.status, "expired");
});

test("T6.3 payload mutation — altered payload after approval is rejected", async () => {
  const exec = new FakeApprovalExecutor();
  const approval = await exec.requestApproval({
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "original" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    expirySeconds: 300,
    scope: "private_external_write",
  });
  await exec.approveApproval(approval.approval_id, "operator");

  const result = await exec.executeApproved({
    approvalId: approval.approval_id,
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "MUTATED" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    effect: async () => { throw new Error("should not reach here"); },
  });
  assert.equal(result.status, "mismatch");
  assert.equal(result.reason, "hash_mismatch");
});

test("T6.4 replay — already consumed approval cannot execute again", async () => {
  const exec = new FakeApprovalExecutor();
  const approval = await exec.requestApproval({
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    expirySeconds: 300,
    scope: "private_external_write",
  });
  await exec.approveApproval(approval.approval_id, "operator");

  let effectCount = 0;
  const result1 = await exec.executeApproved({
    approvalId: approval.approval_id,
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    effect: async () => { effectCount++; return "done"; },
  });
  assert.equal(result1.status, "success");
  assert.equal(effectCount, 1);

  // After consumption, replay returns consumed (not denied) — the used flag is checked.
  const result2 = await exec.executeApproved({
    approvalId: approval.approval_id,
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    effect: async () => { effectCount++; return "done2"; },
  });
  assert.equal(result2.status, "consumed");
  assert.equal(result2.reason, "already_consumed");
  assert.equal(effectCount, 1); // effect not called again
});

test("T6.5 concurrent execution — second in-flight execution is rejected", async () => {
  const exec = new FakeApprovalExecutor();
  const approval = await exec.requestApproval({
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    expirySeconds: 300,
    scope: "private_external_write",
  });
  await exec.approveApproval(approval.approval_id, "operator");

  // The executor consumes atomically before the effect runs.
  // To test concurrent rejection, we need two calls to executeApproved
  // racing before either has consumed. We simulate this by using a
  // custom hashFn that always matches, and checking that the second
  // call sees the record already consumed (used=true).

  let effectCount = 0;
  const slowEffect = async () => {
    effectCount++;
    // Simulate a slow external effect — during this time the
    // approval is already consumed (used=true, status=consumed).
    await new Promise((r) => setTimeout(r, 50));
    return "done";
  };

  // First call: consumes atomically, then runs effect.
  const firstPromise = exec.executeApproved({
    approvalId: approval.approval_id,
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    effect: slowEffect,
  });

  // Immediately attempt a second execution while the first is in-flight.
  // Because the first already consumed the approval atomically,
  // the second sees used=true and returns consumed.
  const secondPromise = exec.executeApproved({
    approvalId: approval.approval_id,
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    effect: async () => { throw new Error("should not reach here"); },
  });

  const secondResult = await secondPromise;
  // The second call finds the approval already consumed by the first.
  assert.equal(secondResult.status, "consumed");
  assert.equal(secondResult.reason, "already_consumed");
  assert.equal(effectCount, 1); // effect not called twice

  const firstResult = await firstPromise;
  assert.equal(firstResult.status, "success");
});

test("T6.6 wrong release — approval for a different release cannot execute", async () => {
  const exec = new FakeApprovalExecutor();
  const approval = await exec.requestApproval({
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    expirySeconds: 300,
    scope: "private_external_write",
  });
  await exec.approveApproval(approval.approval_id, "operator");

  const result = await exec.executeApproved({
    approvalId: approval.approval_id,
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: "wrong-sha-999",
    taskId: TASK_ID,
    effect: async () => { throw new Error("should not reach here"); },
  });
  assert.equal(result.status, "denied");
  assert.equal(result.reason, "wrong_release");
});

test("T6.7 wrong agent — approval for a different requester cannot execute", async () => {
  const exec = new FakeApprovalExecutor();
  const approval = await exec.requestApproval({
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    expirySeconds: 300,
    scope: "private_external_write",
  });
  await exec.approveApproval(approval.approval_id, "operator");

  const result = await exec.executeApproved({
    approvalId: approval.approval_id,
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: "rhythm", // wrong requester
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    effect: async () => { throw new Error("should not reach here"); },
  });
  assert.equal(result.status, "denied");
  assert.equal(result.reason, "wrong_requester");
});

test("T6.8 successful single execution — allowed action runs once and is consumed", async () => {
  const exec = new FakeApprovalExecutor();
  const approval = await exec.requestApproval({
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    expirySeconds: 300,
    scope: "private_external_write",
  });
  await exec.approveApproval(approval.approval_id, "operator");

  let effectCalled = false;
  const result = await exec.executeApproved({
    approvalId: approval.approval_id,
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    effect: async () => {
      effectCalled = true;
      return { sent: true };
    },
  });
  assert.equal(result.status, "success");
  assert.equal(effectCalled, true);
  assert.ok((result as { result: unknown }).result !== undefined);
  assert.ok(result.evidence.startsWith("executed:"));

  // Verify the approval is now consumed
  const status = await exec.getApprovalStatus(approval.approval_id);
  assert.equal(status?.status, "consumed");
  assert.equal(status?.used, true);
});

test("T6.9 unknown external outcome — recorded as unknown, reconciliation required", async () => {
  const exec = new FakeApprovalExecutor();
  const approval = await exec.requestApproval({
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    expirySeconds: 300,
    scope: "private_external_write",
  });
  await exec.approveApproval(approval.approval_id, "operator");

  const result = await exec.executeApproved({
    approvalId: approval.approval_id,
    action: "messaging.sendPrivateMessage",
    payload: { destination: "+447700900123", text: "hello" },
    requester: REQUESTER,
    releaseSha: RELEASE_SHA,
    taskId: TASK_ID,
    effect: async () => { throw new Error("external timeout"); },
  });
  assert.equal(result.status, "unknown");
  assert.ok(result.reason.includes("external timeout"));
  assert.equal(result.reconciliationRequired, true);

  // The approval is already consumed — cannot blindly retry
  const status = await exec.getApprovalStatus(approval.approval_id);
  assert.equal(status?.status, "consumed");
});

test("T6.10 hash function is canonical and deterministic", () => {
  const payload = { destination: "+447700900123", text: "hello" };
  const h1 = hashAction("messaging.sendPrivateMessage", payload);
  const h2 = hashAction("messaging.sendPrivateMessage", payload);
  assert.equal(h1, h2);

  // Different key order should produce same hash (sorted keys)
  const payload2 = { text: "hello", destination: "+447700900123" };
  const h3 = hashAction("messaging.sendPrivateMessage", payload2);
  assert.equal(h1, h3);

  // Different payload produces different hash
  const h4 = hashAction("messaging.sendPrivateMessage", { ...payload, text: "changed" });
  assert.notEqual(h1, h4);
});

test("T6.11 scope redaction hides sensitive values", () => {
  const scope = "account=1234567890123456; key=sk_live_abc123; action=send";
  const redacted = redactApprovalScope(scope);
  assert.ok(!redacted.includes("1234567890123456"), "long number should be redacted");
  assert.ok(redacted.includes("[REDACTED]"), "secret keyword should be redacted");
  assert.ok(redacted.includes("action=send"), "safe scope should pass through");
});

test("T6.12 requestApproval creates pending record with correct hash", async () => {
  const exec = new FakeApprovalExecutor();
  const params = makeParams();
  const approval = await exec.requestApproval(params);
  assert.equal(approval.status, "pending");
  assert.equal(approval.action, params.action);
  assert.equal(approval.actionHash, hashAction(params.action, params.payload));
  assert.equal(approval.requester, params.requester);
  assert.equal(approval.releaseSha, params.releaseSha);
  assert.equal(approval.taskId, params.taskId);
  assert.ok(new Date(approval.expiry) > new Date());
});

test("T6.13 approve and reject change status correctly", async () => {
  const exec = new FakeApprovalExecutor();
  const approval = await exec.requestApproval(makeParams());
  assert.equal(approval.status, "pending");

  const approved = await exec.approveApproval(approval.approval_id, "operator");
  assert.equal(approved.status, "approved");
  assert.equal(approved.decidedBy, "operator");
  assert.ok(approved.decidedAt);

  const exec2 = new FakeApprovalExecutor();
  const approval2 = await exec2.requestApproval(makeParams());
  const rejected = await exec2.rejectApproval(approval2.approval_id, "operator");
  assert.equal(rejected.status, "rejected");
  assert.equal(rejected.decidedBy, "operator");
});
// --- Metricool Growth G01 two-tier tests ---

import {
  createTwoTierState,
  validateTwoTier,
  type TwoTierState,
} from "../src/index.ts";

test("G01.1 Metricool read tools are auto-allowed", () => {
  for (const action of [
    "metricool.getAnalyticsDataByMetrics",
    "metricool.getBestTimeToPostByNetwork",
    "metricool.getBrandSettings",
    "metricool.getScheduledPosts",
  ]) {
    const r = evaluateAction(action, {}, cfg());
    assert.equal(r.decision, "ALLOW", action);
    assert.match(r.reason, /^auto:/, action);
  }
});

test("G01.2 Metricool createScheduledPostForReview is auto-allowed (internal draft)", () => {
  const r = evaluateAction("metricool.createScheduledPostForReview", { text: "draft" }, cfg());
  assert.equal(r.decision, "ALLOW");
  assert.match(r.reason, /^auto:internal_reversible_write/);
});

test("G01.3 Metricool scheduling writes require approval (gated public_communication)", () => {
  for (const action of [
    "metricool.createScheduledPost",
    "metricool.sendScheduledPostForReview",
    "metricool.updateScheduledPost",
  ]) {
    const r = evaluateAction(action, { text: "hi" }, cfg());
    assert.equal(r.decision, "REQUIRE_APPROVAL", action);
    assert.match(r.reason, /^gated:public_communication/);
  }
});

test("G01.4 Metricool denied actions (ads/spend, DMs/replies, live edit/delete)", () => {
  for (const action of [
    "metricool.createAd",
    "metricool.sendDM",
    "metricool.editLivePost",
    "metricool.deleteLivePost",
  ]) {
    const r = evaluateAction(action, {}, cfg());
    assert.equal(r.decision, "DENY", action);
    assert.match(r.reason, /^permanent_deny:/, action);
  }
});

test("G01.5 two-tier state machine — both tiers required, unexpired, unused", () => {
  const payload = { text: "hello", platform: "instagram" };
  const hash = hashAction("metricool.createScheduledPost", payload);
  const state = createTwoTierState(
    "metricool.createScheduledPost",
    payload,
    hash,
    "operator",
    "abc123",
    null,
    300,
  );
  assert.equal(state.isReady, false);
  assert.equal(state.payloadHash, hash);
  assert.equal(state.tier1, null);
  assert.equal(state.tier2, null);
});

test("G01.6 two-tier validation — missing tiers are invalid", () => {
  const payload = { text: "hello" };
  const hash = hashAction("metricool.createScheduledPost", payload);
  const state = createTwoTierState("metricool.createScheduledPost", payload, hash, "op", "sha", null, 300);
  assert.equal(validateTwoTier(state).valid, false);
  assert.equal(validateTwoTier(state).reason, "missing_tier1");
});

test("G01.7 two-tier validation — both tiers approved and matching hash is valid", () => {
  const payload = { text: "hello", platform: "instagram" };
  const hash = hashAction("metricool.createScheduledPost", payload);
  const state = createTwoTierState("metricool.createScheduledPost", payload, hash, "op", "sha", null, 300);
  state.tier1 = {
    tier: 1,
    approvalId: "app_1",
    action: "metricool.createScheduledPost",
    actionHash: hash,
    status: "approved",
    used: false,
    decidedBy: "editor",
    decidedAt: "2026-10-02T12:00:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z",
    requester: "op",
    releaseSha: "sha",
    taskId: null,
  };
  state.tier2 = {
    tier: 2,
    approvalId: "app_2",
    action: "metricool.createScheduledPost",
    actionHash: hash,
    status: "approved",
    used: false,
    decidedBy: "release_mgr",
    decidedAt: "2026-10-02T12:01:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z",
    requester: "op",
    releaseSha: "sha",
    taskId: null,
  };
  const v = validateTwoTier(state);
  assert.equal(v.valid, true, v.reason);
  assert.equal(state.isReady, true);
});

test("G01.8 two-tier validation — different approvers for tier1 and tier2 is valid", () => {
  const payload = { text: "hello" };
  const hash = hashAction("metricool.createScheduledPost", payload);
  const state = createTwoTierState("metricool.createScheduledPost", payload, hash, "op", "sha", null, 300);
  state.tier1 = {
    tier: 1, approvalId: "app_1", action: "metricool.createScheduledPost", actionHash: hash,
    status: "approved", used: false, decidedBy: "editor", decidedAt: "2026-10-02T12:00:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  state.tier2 = {
    tier: 2, approvalId: "app_2", action: "metricool.createScheduledPost", actionHash: hash,
    status: "approved", used: false, decidedBy: "release_mgr", decidedAt: "2026-10-02T12:01:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  assert.equal(validateTwoTier(state).valid, true);
});

test("G01.9 two-tier validation — expired tier invalidates both", () => {
  const payload = { text: "hello" };
  const hash = hashAction("metricool.createScheduledPost", payload);
  const state = createTwoTierState("metricool.createScheduledPost", payload, hash, "op", "sha", null, 300);
  state.tier1 = {
    tier: 1, approvalId: "app_1", action: "metricool.createScheduledPost", actionHash: hash,
    status: "approved", used: false, decidedBy: "editor", decidedAt: "2026-10-02T12:00:00.000Z",
    expiry: "2026-10-01T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  state.tier2 = {
    tier: 2, approvalId: "app_2", action: "metricool.createScheduledPost", actionHash: hash,
    status: "approved", used: false, decidedBy: "release_mgr", decidedAt: "2026-10-02T12:01:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  const v = validateTwoTier(state);
  assert.equal(v.valid, false);
  assert.ok(v.reason.includes("expired"));
});

test("G01.10 two-tier validation — used tier invalidates both", () => {
  const payload = { text: "hello" };
  const hash = hashAction("metricool.createScheduledPost", payload);
  const state = createTwoTierState("metricool.createScheduledPost", payload, hash, "op", "sha", null, 300);
  state.tier1 = {
    tier: 1, approvalId: "app_1", action: "metricool.createScheduledPost", actionHash: hash,
    status: "approved", used: true, decidedBy: "editor", decidedAt: "2026-10-02T12:00:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  state.tier2 = {
    tier: 2, approvalId: "app_2", action: "metricool.createScheduledPost", actionHash: hash,
    status: "approved", used: false, decidedBy: "release_mgr", decidedAt: "2026-10-02T12:01:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  assert.equal(validateTwoTier(state).valid, false);
  assert.equal(validateTwoTier(state).reason, "tier1_already_used");
});

test("G01.11 two-tier validation — payload hash mismatch invalidates both", () => {
  const payload = { text: "hello" };
  const hash = hashAction("metricool.createScheduledPost", payload);
  const state = createTwoTierState("metricool.createScheduledPost", payload, hash, "op", "sha", null, 300);
  state.tier1 = {
    tier: 1, approvalId: "app_1", action: "metricool.createScheduledPost", actionHash: hash,
    status: "approved", used: false, decidedBy: "editor", decidedAt: "2026-10-02T12:00:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  state.tier2 = {
    tier: 2, approvalId: "app_2", action: "metricool.createScheduledPost", actionHash: "different-hash",
    status: "approved", used: false, decidedBy: "release_mgr", decidedAt: "2026-10-02T12:01:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  const v = validateTwoTier(state);
  assert.equal(v.valid, false);
  assert.ok(v.reason.includes("hash_mismatch"));
});

test("G01.12 two-tier validation — missing tier2 is invalid", () => {
  const payload = { text: "hello" };
  const hash = hashAction("metricool.createScheduledPost", payload);
  const state = createTwoTierState("metricool.createScheduledPost", payload, hash, "op", "sha", null, 300);
  state.tier1 = {
    tier: 1, approvalId: "app_1", action: "metricool.createScheduledPost", actionHash: hash,
    status: "approved", used: false, decidedBy: "editor", decidedAt: "2026-10-02T12:00:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  assert.equal(validateTwoTier(state).valid, false);
  assert.equal(validateTwoTier(state).reason, "missing_tier2");
});

test("G01.13 two-tier validation — tier in pending status is invalid", () => {
  const payload = { text: "hello" };
  const hash = hashAction("metricool.createScheduledPost", payload);
  const state = createTwoTierState("metricool.createScheduledPost", payload, hash, "op", "sha", null, 300);
  state.tier1 = {
    tier: 1, approvalId: "app_1", action: "metricool.createScheduledPost", actionHash: hash,
    status: "pending", used: false, decidedBy: null, decidedAt: null,
    expiry: "2026-10-04T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  state.tier2 = {
    tier: 2, approvalId: "app_2", action: "metricool.createScheduledPost", actionHash: hash,
    status: "approved", used: false, decidedBy: "release_mgr", decidedAt: "2026-10-02T12:01:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  assert.equal(validateTwoTier(state).valid, false);
  assert.equal(validateTwoTier(state).reason, "tier1_not_approved:pending");
});

test("G01.14 out-of-order tiers — tier2 before tier1 is invalid (missing tier1)", () => {
  const payload = { text: "hello" };
  const hash = hashAction("metricool.createScheduledPost", payload);
  const state = createTwoTierState("metricool.createScheduledPost", payload, hash, "op", "sha", null, 300);
  state.tier1 = null;
  state.tier2 = {
    tier: 2, approvalId: "app_2", action: "metricool.createScheduledPost", actionHash: hash,
    status: "approved", used: false, decidedBy: "release_mgr", decidedAt: "2026-10-02T12:01:00.000Z",
    expiry: "2026-10-04T00:00:00.000Z", requester: "op", releaseSha: "sha", taskId: null,
  };
  assert.equal(validateTwoTier(state).valid, false);
  assert.equal(validateTwoTier(state).reason, "missing_tier1");
});
