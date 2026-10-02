// Batch 7 tests — Tola Command Centre
// T7.4 Blackboard access | T7.5 explicit agent ID | T7.6 spawn allowlist | T7.7 max depth
// (T7.1–T7.3 are live-channel tests: Discord binding, Telegram continuity, session separation —
//  executed by Tola in the live runtime, not in this suite.)
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/coordinator.test.ts

import { test, after } from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import {
  BlackboardRepository,
  SupabaseAdapter,
  loadEnv,
  envOptional,
} from "../../blackboard-tools/src/index.ts";
import { SPAWN_POLICY, checkSpawn } from "../src/index.ts";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../..");
try { loadEnv(path.join(repoRoot, ".env")); } catch { /* offline: skip below */ }

const SUPA_URL = envOptional("SUPABASE_URL").replace(/\/$/, "") + "/rest/v1";
const SERVICE_KEY = envOptional("SUPABASE_SERVICE_ROLE_KEY");
if (!SUPA_URL.includes("supabase.co") || !SERVICE_KEY) {
  console.error("# SKIP: live credentials required (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY absent)");
  process.exit(0);
}

function makeLiveRepo(timeoutMs = 15_000): BlackboardRepository {
  return new BlackboardRepository(new SupabaseAdapter({ url: SUPA_URL, serviceKey: SERVICE_KEY, timeoutMs }));
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
let fixtureProjectId: string | null = null;

// ---------- contract sanity ----------

test("contract: spawn policy pins allowlist, explicit IDs, depth 1, caps of 3", () => {
  assert.deepEqual([...SPAWN_POLICY.allowlist], ["rhythm", "growth", "scholar"]);
  assert.equal(SPAWN_POLICY.requireExplicitAgentId, true);
  assert.equal(SPAWN_POLICY.maxSpawnDepth, 1);
  assert.equal(SPAWN_POLICY.maxChildrenPerAgent, 3);
  assert.equal(SPAWN_POLICY.maxConcurrent, 3);
});

test("contract: agents/tola.md declares Chief-of-Staff ownership and non-ownership", () => {
  const contract = readFileSync(path.join(repoRoot, "agents/tola.md"), "utf8");
  for (const mustHave of ["Chief of Staff", "delegation", "Blackboard", "approval", "does not own", "route"]) {
    assert.ok(contract.toLowerCase().includes(mustHave.toLowerCase()), `contract missing: ${mustHave}`);
  }
  const stubs = readFileSync(path.join(repoRoot, "agents/specialists.md"), "utf8");
  for (const id of SPAWN_POLICY.allowlist) {
    assert.ok(stubs.includes(id), `specialists doc missing stub: ${id}`);
  }
});

// ---------- T7.4 ----------

test("T7.4 Blackboard access: Tola creates a task via typed tool path", async () => {
  const repo = makeLiveRepo();
  const project = await rawInsert("projects", {
    project_name: `__t7_${randomUUID().slice(0, 8)}`,
    description: "Batch 7 command-centre test fixture",
    status: "active",
    strategic_priority: 5,
  });
  fixtureProjectId = project.project_id;

  const task = await repo.createTask({
    idempotency_key: randomUUID(),
    project_id: project.project_id,
    title: "T7.4 command-centre smoke task",
    requested_by: "tola",
    assigned_to: "growth",
    model_route: "R3",
  });
  createdTaskIds.push(task.task_id);
  assert.equal(task.requested_by, "tola");
  assert.equal(task.assigned_to, "growth");
  assert.equal(task.status, "pending");
  // same agent id continues to be the operator across surfaces (T7.2 evidence at data level)
  const again = await repo.createTask({
    idempotency_key: randomUUID(),
    project_id: project.project_id,
    title: "T7.4 second task same operator",
    requested_by: "tola",
    assigned_to: "scholar",
    model_route: "R1",
  });
  createdTaskIds.push(again.task_id);
  assert.equal(again.requested_by, "tola");
});

// ---------- T7.5 ----------

test("T7.5 explicit agent ID guard: missing ID rejected", () => {
  const r1 = checkSpawn({ depth: 0, activeChildren: 0, runningNow: 0 });
  assert.equal(r1.ok, false);
  if (!r1.ok) {
    assert.equal(r1.code, "MISSING_AGENT_ID");
  }
  const r2 = checkSpawn({ agentId: null, depth: 0 });
  assert.equal(r2.ok, false);
  if (!r2.ok) assert.equal(r2.code, "MISSING_AGENT_ID");
});

// ---------- T7.6 ----------

test("T7.6 spawn allowlist: unknown/unapproved agent rejected, approved accepted", () => {
  for (const bad of ["tola", "shiftlyx", "main", "admin", "unknown-agent", "growth-rhythm"]) {
    const r = checkSpawn({ agentId: bad, depth: 0, activeChildren: 0, runningNow: 0 });
    assert.equal(r.ok, false, `expected rejection for ${bad}`);
    if (!r.ok) assert.equal(r.code, "DISALLOWED_AGENT");
  }
  for (const good of SPAWN_POLICY.allowlist) {
    const r = checkSpawn({ agentId: good, depth: 0, activeChildren: 0, runningNow: 0 });
    assert.equal(r.ok, true, `expected acceptance for ${good}`);
  }
});

// ---------- T7.7 ----------

test("T7.7 max depth: child cannot spawn child", () => {
  // depth 0 (Tola) -> child at depth 1: allowed
  assert.equal(checkSpawn({ agentId: "growth", depth: 0 }).ok, true);
  // depth 1 (a child) -> depth 2: denied regardless of target
  const r = checkSpawn({ agentId: "growth", depth: 1 });
  assert.equal(r.ok, false);
  if (!r.ok) assert.equal(r.code, "MAX_DEPTH");
  // defensive: even deeper is denied
  assert.equal(checkSpawn({ agentId: "rhythm", depth: 4 }).ok, false);
});

test("caps: max three children per session, max three concurrent", () => {
  assert.equal(checkSpawn({ agentId: "growth", depth: 0, activeChildren: 3 }).ok, false);
  assert.equal(checkSpawn({ agentId: "growth", depth: 0, activeChildren: 2 }).ok, true);
  assert.equal(checkSpawn({ agentId: "growth", depth: 0, runningNow: 3 }).ok, false);
  assert.equal(checkSpawn({ agentId: "growth", depth: 0, runningNow: 2 }).ok, true);
});

after(async () => {
  try {
    await rawDelete("agent_events", "task_id", createdTaskIds);
    await rawDelete("decisions", "task_id", createdTaskIds);
    await rawDelete("tasks", "task_id", createdTaskIds);
    if (fixtureProjectId) await rawDelete("projects", "project_id", [fixtureProjectId]);
  } catch {
    // best-effort cleanup
  }
});
