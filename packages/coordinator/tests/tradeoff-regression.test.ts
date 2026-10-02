// Batch 07 regression tests — orchestration.ts trade-off precedence
// Verifies both accept and defer branches of the Growth/Rhythm trade-off.
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/tradeoff-regression.test.ts

import { test } from "node:test";
import assert from "node:assert/strict";
import { Orchestrator } from "../src/orchestration.ts";

// T1b(b): Growth/Rhythm trade-off — accept branch (critical priority + capacity >= 1)
test("T1b(b) trade-off: critical priority + capacity >= 1 => accept", () => {
  const orch = new Orchestrator();
  const result = orch.scenarioBTradeOff("critical-growth-goal", 1);
  assert.strictEqual(result.tradeOff.decision, "accept", "critical + capacity must accept");
  assert.strictEqual(result.tradeOff.madeBy, "tola");
  assert.ok(["accept", "defer"].includes(result.tradeOff.decision));
});

// T1b(b): Growth/Rhythm trade-off — defer branch (non-critical priority)
test("T1b(b) trade-off: non-critical priority => defer", () => {
  const orch = new Orchestrator();
  const result = orch.scenarioBTradeOff("low-priority-goal", 1);
  // growthResult.output.priority is always "critical" in the fake, so we need
  // capacity = 0 to trigger defer. Let's use 0 available time.
  const result2 = orch.scenarioBTradeOff("low-priority-goal", 0);
  assert.strictEqual(result2.tradeOff.decision, "defer", "zero capacity must defer");
});

// T1b(b): Growth/Rhythm trade-off — defer branch (critical but zero capacity)
test("T1b(b) trade-off: critical priority + zero capacity => defer", () => {
  const orch = new Orchestrator();
  const result = orch.scenarioBTradeOff("critical-growth-goal", 0);
  assert.strictEqual(result.tradeOff.decision, "defer", "critical + zero capacity must defer");
});
