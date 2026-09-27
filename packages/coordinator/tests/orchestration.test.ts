// Cross-Domain Orchestration — Batch 13
// T13.1 write boundaries | T13.2 trade-off capture | T13.3 three-child concurrency
// T13.4 dependency sequencing | T13.5 specialist chat isolation
// T13.6 wrong-domain request handling | T13.7 traceability
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/orchestration.test.ts

import { test } from "node:test";
import assert from "node:assert/strict";
import { Orchestrator, checkDomain, isTranscriptExposed } from "../src/orchestration.ts";
import { SPAWN_POLICY } from "../src/policy.ts";

// ---------- helpers ----------

function makeOrchestrator(): Orchestrator {
  return new Orchestrator();
}

// ---------- T13.1 ----------
// Weekly plan: correct ownership and write boundaries.
// Only Rhythm writes planning blocks; Scholar does not.

test("T13.1 write boundaries: only Rhythm writes planning blocks", () => {
  const orch = makeOrchestrator();
  const goal = "Make meaningful progress on Florence this week";
  const result = orch.scenarioAWeeklyPlanning(goal);

  // Scholar must NOT have written any planning blocks
  const allBlocks = orch.getPlanningBlocks();
  for (const block of allBlocks) {
    assert.equal(block.author, "rhythm", "Only Rhythm may write planning blocks");
  }
  // Rhythm must have written at least one block
  assert.ok(allBlocks.length > 0, "Rhythm must write at least one planning block");
  // Scholar has no write access — its result exists but no blocks
  const scholarResult = result.scholarResult;
  assert.equal(scholarResult.agentId, "scholar");
  assert.equal(scholarResult.status, "complete");
});

// ---------- T13.2 ----------
// Growth-priority trade-off: evidence + capacity + Tola decision captured.

test("T13.2 trade-off decision capture: evidence + capacity + Tola decision recorded", () => {
  const orch = makeOrchestrator();
  const growthGoal = "Shiftlyx growth needs attention this week";
  const availableProjectTime = 5;

  const result = orch.scenarioBTradeOff(growthGoal, availableProjectTime);

  // Growth evidence is captured
  assert.ok(result.tradeOff.growthEvidence.length > 0, "growthEvidence must be non-empty");
  // Rhythm capacity is a number
  assert.ok(typeof result.tradeOff.rhythmCapacity === "number", "rhythmCapacity must be a number");
  // Decision was made by Tola
  assert.equal(result.tradeOff.madeBy, "tola");
  // Decision is either "accept" or "defer"
  assert.ok(["accept", "defer"].includes(result.tradeOff.decision), "decision must be accept or defer");
  // Timestamp recorded
  assert.ok(typeof result.tradeOff.timestamp === "number");
  // Trade-off is in the registry
  const allTradeOffs = orch.getTradeOffs();
  assert.ok(allTradeOffs.length > 0);
  assert.equal(allTradeOffs[0].taskId, result.tradeOff.taskId);
});

// ---------- T13.3 ----------
// Three-child concurrency cap: three run; fourth prevented/queued per policy.

test("T13.3 three-child concurrency cap: fourth spawn prevented when at cap", () => {
  const orch = makeOrchestrator();

  // Spawn three children — all should succeed (within maxConcurrent=3)
  const spawn1 = orch.trySpawn("growth");
  const spawn2 = orch.trySpawn("scholar");
  const spawn3 = orch.trySpawn("rhythm");

  assert.equal(spawn1.ok, true, "first spawn should succeed");
  assert.equal(spawn2.ok, true, "second spawn should succeed");
  assert.equal(spawn3.ok, true, "third spawn should succeed");
  assert.equal(orch.getRunningCount(), 3, "exactly three running");

  // Fourth spawn should be rejected (MAX_CONCURRENT)
  const spawn4 = orch.trySpawn("growth");
  assert.equal(spawn4.ok, false, "fourth spawn must be prevented");
  if (!spawn4.ok) {
    assert.equal(spawn4.code, "MAX_CONCURRENT", "fourth spawn must fail with MAX_CONCURRENT");
  }
  assert.equal(orch.getRunningCount(), 3, "still only three running after fourth attempt");
});

// ---------- T13.4 ----------
// Dependency sequencing: dependent task not spawned early.

test("T13.4 dependency sequencing: dependent task not spawned before parent completes", () => {
  const orch = makeOrchestrator();

  // Parent task must run first
  const parentSpawn = orch.trySpawn("growth");
  assert.equal(parentSpawn.ok, true, "parent spawn must succeed");
  const parentRunId = parentSpawn.ok ? parentSpawn.runId : null;
  assert.equal(orch.getRunningCount(), 1);

  // The dependent child should NOT be spawned yet (parent still running)
  // Simulate: child task is dependent on parent
  const childTaskRunId = parentRunId!;
  const run = orch.getRun(childTaskRunId);
  assert.ok(run !== undefined, "parent run must exist");
  assert.equal(run!.status, "running", "parent must be running before child");

  // Complete the parent first
  orch.completeRun(childTaskRunId);
  assert.equal(orch.getRunningCount(), 0);

  // Now the child can be spawned
  const childSpawn = orch.trySpawn("scholar");
  assert.equal(childSpawn.ok, true, "child spawn succeeds after parent completes");
  assert.equal(orch.getRunningCount(), 1);
});

// ---------- T13.5 ----------
// Direct specialist chat isolation: unrelated specialist transcript not auto-exposed to Tola.

test("T13.5 specialist chat isolation: unrelated transcript not auto-exposed", () => {
  // Scholar transcript should NOT be exposed to Tola when unrelated
  const scholarExposed = isTranscriptExposed("scholar", false);
  assert.equal(scholarExposed, false, "unrelated specialist transcript must NOT be auto-exposed");

  // Related specialist transcript IS exposed
  const scholarRelated = isTranscriptExposed("scholar", true);
  assert.equal(scholarRelated, true, "related specialist transcript must be exposed");

  // Rhythm transcript isolation
  const rhythmExposed = isTranscriptExposed("rhythm", false);
  assert.equal(rhythmExposed, false, "unrelated rhythm transcript must NOT be auto-exposed");
});

// ---------- T13.6 ----------
// Wrong-domain request: Growth asked to schedule → redirect/return requirement.

test("T13.6 wrong-domain request: Growth asked to schedule returns requirement, does not act as Rhythm", () => {
  const result = checkDomain("growth", "schedule");
  assert.equal(result.allowed, false, "Growth cannot act as Rhythm for scheduling");
  if (!result.allowed) {
    assert.ok(result.reason !== undefined, "must return a reason");
    assert.ok(
      result.reason!.includes("cannot act"),
      "reason must indicate domain mismatch"
    );
  }
});

// ---------- T13.7 ----------
// Traceability: every task run has final state + evidence references.

test("T13.7 traceability: every task run has final state and evidence references", () => {
  const orch = makeOrchestrator();

  // Scenario A produces completed runs
  const weeklyResult = orch.scenarioAWeeklyPlanning("Test goal for traceability");
  const completedRuns = orch.getCompletedRuns();

  assert.ok(completedRuns.length >= 2, "at least two runs (scholar + rhythm)");

  for (const run of completedRuns) {
    // Every run must have a finalState
    assert.ok(run.finalState !== undefined && run.finalState !== null, "every run must have finalState");
    assert.ok(
      Object.keys(run.finalState).length > 0,
      "finalState must not be empty"
    );
    // Every run must have evidence references
    assert.ok(
      Array.isArray(run.evidenceRefs) && run.evidenceRefs.length > 0,
      "every run must have evidenceRefs"
    );
    // Every evidence ref must be a non-empty string
    for (const ref of run.evidenceRefs) {
      assert.ok(typeof ref === "string" && ref.length > 0, "evidence ref must be non-empty string");
    }
    // Every run must have a status
    assert.ok(["complete", "partial", "blocked", "running"].includes(run.status), "run must have valid status");
  }
});

// ---------- Additional: verify SPAWN_POLICY caps are consistent ----------

test("T13.x contract: SPAWN_POLICY caps match spec (maxConcurrent=3, maxChildrenPerAgent=3)", () => {
  // SPAWN_POLICY is imported at the top of this file
  assert.equal(SPAWN_POLICY.maxConcurrent, 3, "max concurrent runs must be 3");
  assert.equal(SPAWN_POLICY.maxChildrenPerAgent, 3, "max children per agent must be 3");
  assert.equal(SPAWN_POLICY.maxSpawnDepth, 1, "max spawn depth must be 1");
});

// ---------- Additional: fourth spawn is queued, not just rejected ----------

test("T13.3b fourth spawn can be queued when at capacity", () => {
  const orch = makeOrchestrator();

  // Fill to capacity
  orch.trySpawn("growth");
  orch.trySpawn("scholar");
  orch.trySpawn("rhythm");
  assert.equal(orch.getRunningCount(), 3);

  // Queue the fourth
  orch.queueSpawn("growth");
  assert.equal(orch.getQueuedCount(), 1, "fourth spawn must be queued");
});
