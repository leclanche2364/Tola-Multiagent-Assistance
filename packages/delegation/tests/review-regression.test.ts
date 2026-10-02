// Batch 07 regression tests — review.ts
// Verifies that the fixed logic stays fixed:
//   (a) partial result never emits mark_complete (was: did emit mark_complete with undefined evidence)
//   (b) malformed/give_up path is taken for partial, not mark_complete
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/review-regression.test.ts

import { test } from "node:test";
import assert from "node:assert/strict";
import { makeEnvelope, makeResult } from "../src/index.ts";
import { review } from "../src/review.ts";

function makeRepo(): any {
  class StubRepo {
    async request() { throw new Error("stub"); }
  }
  return new StubRepo();
}

// T1b(a): partial specialist result must NOT emit mark_complete
test("T1b(a) partial result never emits mark_complete", async () => {
  const repo = makeRepo();
  const result = makeResult({ status: "partial" });
  const envelope = makeEnvelope();
  const verdict = review(result, envelope, repo);
  assert.strictEqual(verdict.status, "partial");
  assert.notStrictEqual(verdict.action.type, "mark_complete", "partial must not mark_complete");
  assert.strictEqual(verdict.action.type, "record_blocker");
});

// T1b(a) old-logic check: the old code returned action.type === "mark_complete" for partial.
// This test ensures that behaviour is gone.
test("T1b(a) partial result action is record_blocker, not mark_complete", async () => {
  const repo = makeRepo();
  const result = makeResult({ status: "partial" });
  const envelope = makeEnvelope();
  const verdict = review(result, envelope, repo);
  assert.strictEqual(verdict.action.type, "record_blocker");
  assert.ok(
    !("evidence" in verdict.action) || verdict.action.evidence === undefined,
    "record_blocker must not carry evidence (old mark_complete path)"
  );
});
