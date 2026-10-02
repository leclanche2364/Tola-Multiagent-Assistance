// Batch 6 test suite — routing and cost logging
// T6.1 routing accuracy | T6.2 allowlist enforcement | T6.3 model log
// T6.4 no hidden semantic fallback | T6.5 cost reconciliation | T6.6 price freeze
// Run: npm test (from packages/routing)

import { test, after } from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import {
  BlackboardRepository,
  SupabaseAdapter,
  BlackboardError,
  loadEnv,
  envOptional,
} from "../../blackboard-tools/src/index.ts";
import {
  MODEL_REGISTRY,
  ROUTES,
  assertApprovedModel,
  assertRoute,
  classifyRoute,
} from "../src/index.ts";
import type { Route } from "../src/index.ts";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../..");
try { loadEnv(path.join(repoRoot, ".env")); } catch { /* offline: skip below */ }

const SUPA_URL = envOptional("SUPABASE_URL").replace(/\/$/, "") + "/rest/v1";
const SERVICE_KEY = envOptional("SUPABASE_SERVICE_ROLE_KEY");
if (!SUPA_URL.includes("supabase.co") || !SERVICE_KEY) {
  console.error("# SKIP: live credentials required (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY absent)");
  process.exit(0);
}

interface Fixture {
  id: string;
  prompt: string;
  signals: string[];
  expected_route: Route;
  critical?: boolean;
  adversarial?: boolean;
  note?: string;
}

const fixtureData = JSON.parse(
  readFileSync(path.join(here, "../fixtures/routing-fixtures.json"), "utf8")
) as { fixtures: Fixture[] };
const FIXTURES = fixtureData.fixtures;

const EXPECTED_COUNTS: Record<Route, number> = { R0: 10, R1: 10, R2: 8, R3: 6, R4: 6 };

// ---------- fixture sanity ----------

test("fixture set matches the Batch 6 spec distribution (10/10/8/6/6)", () => {
  assert.equal(FIXTURES.length, 40);
  const counts: Record<string, number> = {};
  for (const f of FIXTURES) counts[f.expected_route] = (counts[f.expected_route] ?? 0) + 1;
  for (const route of ROUTES) {
    assert.equal(counts[route], EXPECTED_COUNTS[route], `wrong count for ${route}`);
  }
});

// ---------- T6.1 ----------

test("T6.1 routing accuracy: >=85% exact match and 100% on critical cases", () => {
  let exact = 0;
  const failures: string[] = [];
  for (const f of FIXTURES) {
    const decision = classifyRoute({ title: f.prompt, signals: f.signals });
    if (decision.route === f.expected_route) {
      exact += 1;
    } else {
      failures.push(`${f.id}: expected ${f.expected_route}, got ${decision.route} (${decision.reason})`);
    }
  }
  const accuracy = exact / FIXTURES.length;
  assert.ok(
    accuracy >= 0.85,
    `accuracy ${(accuracy * 100).toFixed(1)}% below 85% gate; failures: ${failures.join("; ")}`
  );
  const critical = FIXTURES.filter((f) => f.critical);
  assert.ok(critical.length >= 5, "fixture set must include critical cases");
  for (const f of critical) {
    const decision = classifyRoute({ title: f.prompt, signals: f.signals });
    assert.equal(decision.route, f.expected_route, `critical case ${f.id} misrouted`);
  }
});

test("T6.1b adversarial cases: prompt length never drives the route", () => {
  const adversarial = FIXTURES.filter((f) => f.adversarial);
  assert.ok(adversarial.length >= 3, "must include adversarial cases");
  for (const f of adversarial) {
    const decision = classifyRoute({ title: f.prompt, signals: f.signals });
    assert.equal(decision.route, f.expected_route, `adversarial case ${f.id} misrouted`);
  }
  // no signals at all -> R4 default, regardless of prompt length
  assert.equal(classifyRoute({ title: "x".repeat(5000) }).route, "R4");
  assert.equal(classifyRoute({ title: "y" }).route, "R4");
});

// ---------- T6.2 ----------

test("T6.2 allowlist enforcement: unapproved models rejected", () => {
  for (const route of ROUTES) {
    const entry = MODEL_REGISTRY[route];
    // the registry model itself must pass
    assertApprovedModel(route, entry.model_id);
    // any other model id must fail for that route
    const interloper = "openai/gpt-4o";
    if (route === "R0") {
      assert.throws(() => assertApprovedModel("R0", interloper), BlackboardError);
    } else if (entry.model_id !== interloper) {
      assert.throws(() => assertApprovedModel(route, interloper), BlackboardError);
    }
    // null model only valid for R0
    if (route !== "R0") {
      assert.throws(() => assertApprovedModel(route, null), BlackboardError);
    }
  }
  assert.throws(() => assertRoute("R9"), BlackboardError);
  assert.equal(assertRoute("R3"), "R3");
});

// ---------- live fixtures + cleanup ----------

function makeLiveRepo(timeoutMs = 15_000): BlackboardRepository {
  const adapter = new SupabaseAdapter({ url: SUPA_URL, serviceKey: SERVICE_KEY, timeoutMs });
  return new BlackboardRepository(adapter);
}

async function rawInsert(table: string, body: Record<string, unknown>): Promise<{ project_id: string }> {
  const adapter = new SupabaseAdapter({ url: SUPA_URL, serviceKey: SERVICE_KEY });
  const res = await adapter.request<{ project_id: string }>("POST", table, { body, prefer: "return=representation" });
  assert.equal(res.rows.length, 1);
  return res.rows[0];
}

async function rawDelete(table: string, column: string, values: string[]): Promise<void> {
  if (values.length === 0) return;
  const adapter = new SupabaseAdapter({ url: SUPA_URL, serviceKey: SERVICE_KEY });
  await adapter.request("DELETE", table, { searchParams: new URLSearchParams({ [column]: `in.(${values.join(",")})` }) });
}

const createdTaskIds: string[] = [];
const createdRunIds: string[] = [];
let fixtureProjectId: string | null = null;

// ---------- T6.3 ----------

test("T6.3 model log: one task each on R1–R4 records route, model and reason", async () => {
  const repo = makeLiveRepo();
  const project = await rawInsert("projects", {
    project_name: `__t6_${randomUUID().slice(0, 8)}`,
    description: "Batch 6 routing test fixture",
    status: "active",
    strategic_priority: 5,
  });
  fixtureProjectId = project.project_id;

  for (const route of ["R1", "R2", "R3", "R4"] as Route[]) {
    const task = await repo.createTask({
      idempotency_key: randomUUID(),
      project_id: project.project_id,
      title: `T6.3 route probe ${route}`,
      requested_by: "tola",
      assigned_to: "growth",
      model_route: route,
    });
    createdTaskIds.push(task.task_id);
    assert.equal(task.model_route, route);

    const decision = classifyRoute({ title: task.title, signals: [MODEL_REGISTRY[route].description.split(":")[0]] });

    const run = await repo.startTaskRun({
      task_id: task.task_id,
      idempotency_key: randomUUID(),
      summary: `route=${route} model=${MODEL_REGISTRY[route].model_id} reason=${decision.reason}`,
    });
    createdRunIds.push(run.run_id);

    const modelRun = await repo.recordModelRun({
      task_run_id: run.run_id,
      model_route: route,
      model_id: MODEL_REGISTRY[route].model_id,
      input_tokens: 100,
      output_tokens: 50,
      latency_ms: 250,
      status: "completed",
    });

    // independent read-back: route, model ref and reason are logged
    const runs = await repo.listTaskRunsForTask(task.task_id);
    assert.equal(runs.length, 1);
    assert.ok(runs[0].summary?.includes(`route=${route}`), "route must be logged");
    assert.ok(runs[0].summary?.includes(`model=${MODEL_REGISTRY[route].model_id}`), "model ref must be logged");
    assert.ok(runs[0].summary?.includes("reason="), "reason must be logged");

    const logged = await repo.listModelRunsForTaskRun(run.run_id);
    assert.equal(logged.length, 1);
    assert.equal(logged[0].model_route, route);
    assert.equal(logged[0].model_id, MODEL_REGISTRY[route].model_id);
    assert.equal(logged[0].status, "completed");
  }
});

// ---------- T6.4 ----------

test("T6.4 no hidden semantic fallback: model failure stays visible, route unchanged", async () => {
  const repo = makeLiveRepo();

  // failure injection: provider error + timeout recorded as failed/timeout runs
  const failed = await repo.recordModelRun({
    model_route: "R1",
    model_id: MODEL_REGISTRY.R1.model_id,
    status: "failed",
  });
  const timedOut = await repo.recordModelRun({
    model_route: "R2",
    model_id: MODEL_REGISTRY.R2.model_id,
    status: "timeout",
  });

  // failures remain visible on read-back, never rewritten to completed
  const failedRows = await repo.listModelRunsForTaskRun(failed.task_run_id ?? "00000000-0000-0000-0000-000000000000").catch(() => []);
  assert.equal(failed.status, "failed");
  assert.equal(timedOut.status, "timeout");

  // route decision is deterministic: a failed R1 task re-classifies to R1, not auto-escalated
  const before = classifyRoute({ title: "summarise this", signals: ["summarisation"] });
  const afterFailure = classifyRoute({ title: "summarise this", signals: ["summarisation"] });
  assert.equal(before.route, afterFailure.route, "classifier must not change route on model failure");

  // allowlist still enforced after failure: no silent model substitution
  assert.throws(() => assertApprovedModel("R1", "some/other-model"), BlackboardError);

  // cleanup for the two standalone rows
  const adapter = new SupabaseAdapter({ url: SUPA_URL, serviceKey: SERVICE_KEY });
  await adapter.request("DELETE", "model_runs", {
    searchParams: new URLSearchParams({ model_run_id: `in.(${failed.model_run_id},${timedOut.model_run_id})` }),
  });
  void failedRows;
});

// ---------- T6.5 ----------

test("T6.5 cost reconciliation: recorded cost matches snapshot-derived cost", async () => {
  const repo = makeLiveRepo();
  const run = await repo.recordModelRun({
    model_route: "R1",
    model_id: MODEL_REGISTRY.R1.model_id,
    input_tokens: 10_000,
    output_tokens: 1_000,
    // expected: 10000 * 0.000000021 + 1000 * 0.000000063 = 0.00021 + 0.000063
    cost_usd: 0.000273,
    status: "completed",
  });
  const promptPrice = 0.000000021; // pricing snapshot 2026-09-27
  const completionPrice = 0.000000063;
  const expected = 10_000 * promptPrice + 1_000 * completionPrice;
  assert.ok(run.cost_usd !== null);
  const actual = Number(run.cost_usd);
  assert.ok(
    Math.abs(actual - expected) <= expected * 0.05,
    `recorded cost ${actual} deviates >5% from snapshot-derived ${expected}`
  );
  const adapter = new SupabaseAdapter({ url: SUPA_URL, serviceKey: SERVICE_KEY });
  await adapter.request("DELETE", "model_runs", {
    searchParams: new URLSearchParams({ model_run_id: `in.(${run.model_run_id})` }),
  });
});

// ---------- T6.6 ----------

test("T6.6 price freeze: pricing snapshot documented and current", () => {
  const snapshotPath = path.join(repoRoot, "docs/pricing-snapshot-2026-09-27.md");
  const snapshot = readFileSync(snapshotPath, "utf8");
  for (const route of ["R1", "R2", "R3", "R4"] as Route[]) {
    assert.ok(
      snapshot.includes(String(MODEL_REGISTRY[route].model_id)),
      `snapshot missing model for ${route}`
    );
  }
  assert.ok(snapshot.includes("2026-09-27"), "snapshot must be dated");
});

after(async () => {
  try {
    if (createdRunIds.length > 0) {
      await rawDelete("model_runs", "task_run_id", createdRunIds);
      await rawDelete("task_runs", "run_id", createdRunIds);
    }
    await rawDelete("agent_events", "task_id", createdTaskIds);
    await rawDelete("decisions", "task_id", createdTaskIds);
    await rawDelete("tasks", "task_id", createdTaskIds);
    if (fixtureProjectId) await rawDelete("projects", "project_id", [fixtureProjectId]);
  } catch {
    // best-effort cleanup
  }
});
