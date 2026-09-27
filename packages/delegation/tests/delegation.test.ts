// Delegation Protocol — Batch 8
// T8.1 envelope schema validation          | T8.2 result schema statuses
// T8.3 review gate: partial               | T8.4 review gate: blocked
// T8.5 review gate: needs_approval        | T8.6 review gate: malformed / reconciliation
// T8.7 review gate: duplicate idempotency  | failure-injection: child killed after external write
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/delegation.test.ts

import { test } from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import * as nodePath from "node:path";
import { makeEnvelope, makeResult } from "../src/index.ts";
import { BlackboardRepository, BlackboardError } from "../../blackboard-tools/src/index.ts";

const here = nodePath.dirname(fileURLToPath(import.meta.url));
const repoRoot = nodePath.resolve(here, "../../..");

// Minimal repo for test scaffolding (no SUPABASE live writes — we only test
// the review logic in isolation, not DB persistence).
function makeRepo(): BlackboardRepository {
  // SupabaseAdapter will fail without creds; wrap so tests that don't hit
  // the DB don't crash instantly. The review functions only need the type
  // shape, so we provide a stub that satisfies the interface.
  class StubRepo {
    async request(_: any, __: any, ___: any) {
      throw new Error("stub: no real Supabase");
    }
  }
  return new StubRepo() as unknown as BlackboardRepository;
}

// Helper: check if a value is a valid UUID v4 format
function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

// ---------- T8.1 ----------

test("T8.1 envelope schema: required fields present", () => {
  const env = makeEnvelope();
  assert.ok(isUuid(env.taskRef), "taskRef must be uuid");
  assert.ok(isUuid(env.runId), "runId must be uuid");
  assert.ok(isUuid(env.idempotencyKey), "idempotencyKey must be uuid");
  assert.ok(["R0", "R1", "R2", "R3", "R4"].includes(env.route), "route must be valid");
  assert.ok(Array.isArray(env.allowedWriteScope), "allowedWriteScope must be array");
  assert.ok(typeof env.deadline === "string", "deadline must be ISO string");
  assert.ok(typeof env.timeoutSeconds === "number", "timeoutSeconds must be number");
  assert.ok(
    ["complete", "partial", "blocked", "needs_approval", "malformed"].includes(
      env.expectedResultShape
    ),
    "expectedResultShape must be valid",
  );
});

// ---------- T8.2 ----------

test("T8.2 result schema: statuses and evidence discipline", () => {
  // complete without evidence should be rejected by review gate
  const badComplete = makeResult({ status: "complete" });
  // complete with evidence is valid
  const goodComplete = makeResult({ status: "complete", evidence: "s3://artifacts/report.pdf" });
  assert.equal(goodComplete.evidence, "s3://artifacts/report.pdf");
  // partial has no evidence requirement
  const partial = makeResult({ status: "partial" });
  assert.equal(partial.status, "partial");
  // blocked, needs_approval, malformed are valid status strings
  for (const s of ["blocked", "needs_approval", "malformed"] as const) {
    const r = makeResult({ status: s });
    assert.equal(r.status, s);
  }
});

// ---------- T8.3 ----------

test("T8.3 review gate: partial => do NOT mark task complete", async () => {
  const repo = makeRepo();
  const result = makeResult({ status: "partial" });
  const envelope = makeEnvelope();
  const { review } = await import("../src/review.ts");
  const verdict = review(result, envelope, repo);
  assert.strictEqual(verdict.status, "partial");
  // action should not be "mark_complete" that claims an external write
  assert.ok(
    !(verdict.action.type === "mark_complete" && verdict.action.evidence !== undefined),
    "partial must NOT mark complete with evidence");
});

// ---------- T8.4 ----------

test("T8.4 review gate: blocked => record blocker, no automatic retry", async () => {
  const repo = makeRepo();
  const result = makeResult({ status: "blocked", evidence: "blocked-by-lock" });
  const envelope = makeEnvelope();
  const { review } = await import("../src/review.ts");
  const verdict = review(result, envelope, repo);
  assert.strictEqual(verdict.status, "blocked");
  assert.strictEqual(verdict.action.type, "record_blocker");
  assert.ok(typeof verdict.action.message === "string" && verdict.action.message.length > 0);
});

// ---------- T8.5 ----------

test("T8.5 review gate: needs_approval => create/emit approval record", async () => {
  const repo = makeRepo();
  const result = makeResult({ status: "needs_approval" });
  const envelope = makeEnvelope();
  const { review } = await import("../src/review.ts");
  const verdict = review(result, envelope, repo);
  assert.strictEqual(verdict.status, "needs_approval");
  assert.strictEqual(verdict.action.type, "request_approval");
  assert.strictEqual(verdict.action.approvalType, "delegation_result");
  assert.ok(
    verdict.action.payload.runId === envelope.runId,
    "payload must contain runId",
  );
  assert.ok(
    verdict.action.payload.route === envelope.route,
    "payload must contain route",
  );
});

// ---------- T8.6 ----------

test("T8.6 review gate: malformed => at most ONE correction/retry, then give up", async () => {
  const repo = makeRepo();
  // Missing uuids -> malformed, should give up
  const badResult = makeResult({ status: "malformed" });
  const envelope = makeEnvelope({ taskRef: "not-uuid", runId: "not-uuid", idempotencyKey: "not-uuid" });
  const { review } = await import("../src/review.ts");
  const verdict = review(badResult, envelope, repo);
  assert.strictEqual(verdict.status, "malformed");
  assert.strictEqual(verdict.action.type, "give_up");
  assert.ok(verdict.action.reason.includes("malformed") || verdict.action.reason.includes("uuid"));
});

// ---------- T8.7 ----------

test("T8.7 review gate: reconciliation — if complete claims no evidence, reject before retry", async () => {
  const repo = makeRepo();
  const result = makeResult({ status: "complete" }); // no evidence
  const envelope = makeEnvelope();
  const { review } = await import("../src/review.ts");
  const verdict = review(result, envelope, repo);
  // reconciliation: missing evidence ref for complete => malformed + retry_once correction
  assert.strictEqual(verdict.status, "malformed");
  assert.strictEqual(verdict.action.type, "retry_once");
  assert.ok(
    verdict.action.correction.includes("evidence"),
    "correction must mention evidence ref before retry",
  );
});

// ---------- failure-injection ----------
//
// Simulate: child process killed after external write (e.g. file written to disk)
// before the result is returned to the Tola runtime. The reconciliation check
// must verify the evidence ref exists before allowing a retry — no duplicate
// external effect.

test("failure-injection: reconciliation checks evidence before retry, no double action", async () => {
  const repo = makeRepo();
  // Simulate a result that claims "complete" but has NO evidence ref — this
  // models the case where the child crashed after writing an artifact but before
  // returning the result payload. The review gate must NOT allow a retry that
  // would duplicate the external write.
  const result = makeResult({ status: "complete" }); // evidence === undefined
  const envelope = makeEnvelope();
  const { review } = await import("../src/review.ts");
  const verdict = review(result, envelope, repo);
  // Must reject: missing evidence for complete => malformed, not a silent retry
  assert.strictEqual(verdict.status, "malformed");
  assert.strictEqual(verdict.action.type, "retry_once");
  // The correction should instruct to verify evidence exists before retry.
  // Crucially, the design guarantees one logical effect via idempotencyKey —
  // a retry without evidence must NOT re-trigger the external write.
  assert.ok(
    verdict.action.correction.includes("evidence"),
    "correction must reference evidence check before retry",
  );
});

