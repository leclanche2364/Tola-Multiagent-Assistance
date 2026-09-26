// Batch 4 test suite — BlackboardRepository (Supabase direct)
// T4.1 read-through cache | T4.2 write + audit | T4.3 duplicate idempotency
// T4.4 stale-version CONFLICT | T4.5 skill metadata gate | T4.6 malformed response
// Run: npm test (from packages/blackboard-tools)

import { test, beforeEach, after } from "node:test";
import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { BlackboardRepository, SupabaseAdapter, BlackboardError, loadEnv, envOptional } from "../src/index.ts";

const here = path.dirname(fileURLToPath(import.meta.url));
// tests/ -> blackboard-tools/ -> packages/ -> four-agent-repo/
const repoRoot = path.resolve(here, "../../..");
loadEnv(path.join(repoRoot, ".env"));

const SUPA_URL = envOptional("SUPABASE_URL").replace(/\/$/, "") + "/rest/v1";
const SERVICE_KEY = envOptional("SUPABASE_SERVICE_ROLE_KEY");
if (!SUPA_URL.includes("supabase.co") || !SERVICE_KEY) {
  throw new Error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from four-agent-repo/.env");
}

const AGENTS = ["tola", "rhythm", "growth", "scholar"] as const;
type AgentName = (typeof AGENTS)[number];

// ---------- helpers ----------

function makeLiveRepo(timeoutMs = 15_000): { repo: BlackboardRepository; adapter: SupabaseAdapter } {
  const adapter = new SupabaseAdapter({ url: SUPA_URL, serviceKey: SERVICE_KEY, timeoutMs });
  return { repo: new BlackboardRepository(adapter), adapter };
}

function assertCode(err: unknown, code: BlackboardError["code"]): void {
  assert.ok(err instanceof BlackboardError, `expected BlackboardError, got ${String(err)}`);
  assert.equal((err as BlackboardError).code, code, (err as BlackboardError).message);
}

let fixtureProjectId: string | null = null;
const createdTaskIds: string[] = [];
const createdSkillNames: string[] = [];

async function createFixtureProject(repo: BlackboardRepository): Promise<ProjectLike> {
  const res = await repo.listProjects();
  const name = `__t4_${randomUUID().slice(0, 8)}`;
  void res;
  // direct insert of the fixture project (setup, not under test)
  const created = await rawInsert("projects", {
    project_name: name,
    description: "Batch 4 test fixture",
    status: "active",
    strategic_priority: 5,
  });
  return created;
}

interface ProjectLike {
  project_id: string;
  project_name: string;
  version: number;
}

async function rawInsert(table: string, body: Record<string, unknown>): Promise<ProjectLike> {
  const adapter = new SupabaseAdapter({ url: SUPA_URL, serviceKey: SERVICE_KEY });
  const res = await adapter.request<ProjectLike>("POST", table, { body, prefer: "return=representation" });
  assert.equal(res.rows.length, 1);
  return res.rows[0];
}

async function rawDelete(table: string, column: string, values: string[]): Promise<void> {
  if (values.length === 0) return;
  const adapter = new SupabaseAdapter({ url: SUPA_URL, serviceKey: SERVICE_KEY });
  await adapter.request("DELETE", table, { searchParams: new URLSearchParams({ [column]: `in.(${values.join(",")})` }) });
}

// ---------- mock server (failure injection) ----------

type MockBehaviour = (req: { method: string; url: string; body: string }, res: import("node:http").ServerResponse) => void;

function startMock(behaviour: MockBehaviour): Promise<{ server: Server; port: number; url: string; requests: { method: string; url: string; body: string }[] }> {
  const requests: { method: string; url: string; body: string }[] = [];
  return new Promise((resolve) => {
    const server = createServer((req, res) => {
      let body = "";
      req.on("data", (c: Buffer) => (body += c.toString()));
      req.on("end", () => {
        const full = `${req.url}${body ? ` body=${body}` : ""}`;
        requests.push({ method: req.method ?? "", url: req.url ?? "", body });
        behaviour({ method: req.method ?? "", url: req.url ?? "", body }, res);
      });
    });
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address() as { port: number };
      resolve({ server, port: addr.port, url: `http://127.0.0.1:${addr.port}/rest/v1`, requests });
    });
  });
}

// ---------- tests ----------

beforeEach(() => {
  // no shared state; each test builds its own repo
});

test("T4.1 read-through cache: project metadata served from memory on repeat get", async () => {
  const { repo, adapter } = makeLiveRepo();
  const project = await createFixtureProject(repo);
  fixtureProjectId = project.project_id;

  // first get → network; second get within TTL → memory
  const p1 = await repo.getProject(project.project_id);
  const statsAfterFirst = repo.cacheStatsSnapshot();
  const p2 = await repo.getProject(project.project_id);
  const statsAfterSecond = repo.cacheStatsSnapshot();

  assert.equal(p1.project_id, project.project_id);
  assert.equal(p2.project_id, project.project_id);
  assert.equal(statsAfterFirst.projectMisses, 1);
  assert.equal(statsAfterFirst.projectHits, 0);
  assert.equal(statsAfterSecond.projectHits, 1, "second get must hit cache");
  assert.equal(statsAfterSecond.projectMisses, 1, "no extra network miss");

  void adapter;
});

test("T4.2 online write: create task succeeds, row exists, audit event recorded", async () => {
  const { repo } = makeLiveRepo();
  const project = await createFixtureProject(repo);
  fixtureProjectId = project.project_id;

  const key = randomUUID();
  const task = await repo.createTask({
    idempotency_key: key,
    project_id: project.project_id,
    title: "T4.2 smoke task",
    required_output: "task row + audit event",
    requested_by: "tola",
    assigned_to: "growth",
    risk_class: "A1",
  });
  createdTaskIds.push(task.task_id);

  assert.ok(task.task_id);
  assert.equal(task.status, "pending");
  assert.equal(task.version, 1);

  // authoritative check: row exists via independent read
  const read = await repo.getTask(task.task_id);
  assert.equal(read.idempotency_key, key);

  // audit event exists
  const events = await repo.listAgentEventsForTask(task.task_id);
  assert.ok(events.some((e) => e.event_type === "task.created"), "task.created audit row must exist");
});

test("T4.3 duplicate operation id: replay yields one authoritative effect", async () => {
  const { repo } = makeLiveRepo();
  const project = await createFixtureProject(repo);
  fixtureProjectId = project.project_id;

  const key = randomUUID();
  const t1 = await repo.createTask({
    idempotency_key: key,
    project_id: project.project_id,
    title: "idempotency probe",
    requested_by: "tola",
    assigned_to: "scholar",
  });
  createdTaskIds.push(t1.task_id);

  // replay with the SAME key and a (would-be) different title: must not create a second row
  const t2 = await repo.createTask({
    idempotency_key: key,
    project_id: project.project_id,
    title: "idempotency probe MUTATED",
    requested_by: "tola",
    assigned_to: "scholar",
  });
  createdTaskIds.push(t2.task_id);

  assert.equal(t1.task_id, t2.task_id, "same operation id → same task");
  assert.equal(t2.title, "idempotency probe", "original title preserved (no second effect)");

  const live = await repo.getTask(t1.task_id);
  assert.equal(live.title, "idempotency probe");
  const countCheck = await repo.listAgentEventsForTask(t1.task_id);
  const createdCount = countCheck.filter((e) => e.event_type === "task.created").length;
  assert.equal(createdCount, 1, "exactly one task.created audit event");
});

test("T4.4 stale-version update: explicit CONFLICT, no overwrite", async () => {
  const { repo } = makeLiveRepo();
  const project = await createFixtureProject(repo);
  fixtureProjectId = project.project_id;

  const key = randomUUID();
  const task = await repo.createTask({
    idempotency_key: key,
    project_id: project.project_id,
    title: "conflict probe v1",
    requested_by: "tola",
    assigned_to: "rhythm",
  });
  createdTaskIds.push(task.task_id);

  // first update: version 1 → 2 succeeds
  const updated = await repo.updateTask(task.task_id, 1, { title: "conflict probe v2" }, "tola");
  assert.equal(updated.version, 2);

  // second actor still believes version is 1 → stale write must CONFLICT
  await assert.rejects(
    () => repo.updateTask(task.task_id, 1, { title: "STALE WRITE" }, "tola"),
    (err: unknown) => {
      assertCode(err, "CONFLICT");
      const e = err as BlackboardError;
      assert.equal((e.detail as { authoritativeVersion: number }).authoritativeVersion, 2);
      return true;
    },
  );

  // authoritative content untouched by the stale write
  const live = await repo.getTask(task.task_id);
  assert.equal(live.title, "conflict probe v2");
  assert.equal(live.version, 2);
});

test("T4.5 skill promotion without required metadata is rejected by repository validation", async () => {
  const { repo } = makeLiveRepo();

  // incomplete provenance: no content_hash / source_repository / source_version
  await assert.rejects(
    () =>
      repo.registerSkill({
        skill_name: "bad-provenance-skill",
        origin_type: "generated",
        content_hash: "not-a-hash",
        source_repository: "",
        source_version: "",
        local_revision: 1,
      }),
    (err: unknown) => {
      assertCode(err, "VALIDATION");
      const detail = (err as BlackboardError).detail as { missing: string[] };
      assert.ok(detail.missing.length >= 3, "must list all missing metadata fields");
      return true;
    },
  );

  // valid metadata registers as quarantined
  const hash = "a".repeat(64);
  const skill = await repo.registerSkill({
    skill_name: "t4-provenance-ok",
    origin_type: "generated",
    content_hash: hash,
    source_repository: "github.com/leclanche2364/Tola-Multiagent-Assistance",
    source_version: "abc1234",
    local_revision: 1,
  });
  createdSkillNames.push("t4-provenance-ok");
  assert.equal(skill.status, "quarantined");

  // promotion of a registered skill with complete metadata succeeds
  const promoted = await repo.promoteSkill("t4-provenance-ok", "tola");
  assert.equal(promoted.status, "approved");
  assert.equal(promoted.approved_by, "tola");
  assert.ok(promoted.approved_at);
});

test("T4.6 malformed Supabase response: no false success, error surfaced", async () => {
  const mock = await startMock((_req, res) => {
    res.writeHead(200, { "content-type": "application/json" });
    res.end("<html>Definitely not JSON</html>");
  });
  try {
    const adapter = new SupabaseAdapter({ url: mock.url, serviceKey: "dummy", timeoutMs: 3000 });
    const repo = new BlackboardRepository(adapter);
    await assert.rejects(
      () =>
        repo.createTask({
          idempotency_key: randomUUID(),
          title: "should never land",
          requested_by: "tola",
          assigned_to: "tola",
        }),
      (err: unknown) => {
        assertCode(err, "MALFORMED");
        return true;
      },
    );
  } finally {
    mock.server.close();
  }
});

test("T4.6b unreachable store: UNAVAILABLE surfaced, not a silent failure", async () => {
  // port 1 on localhost is effectively closed → connection refused
  const adapter = new SupabaseAdapter({ url: "http://127.0.0.1:1/rest/v1", serviceKey: "dummy", timeoutMs: 2000 });
  const repo = new BlackboardRepository(adapter);
  await assert.rejects(
    () =>
      repo.createTask({
        idempotency_key: randomUUID(),
        title: "unreachable",
        requested_by: "tola",
        assigned_to: "tola",
      }),
    (err: unknown) => {
      assertCode(err, "UNAVAILABLE");
      return true;
    },
  );
});

test("T4.6c timeout midway through write: UNAVAILABLE (failure injection)", async () => {
  const mock = await startMock((_req, res) => {
    // never respond until the client times out
    res.socket?.on("close", () => undefined);
  });
  try {
    const adapter = new SupabaseAdapter({ url: mock.url, serviceKey: "dummy", timeoutMs: 500 });
    const repo = new BlackboardRepository(adapter);
    await assert.rejects(
      () =>
        repo.createTask({
          idempotency_key: randomUUID(),
          title: "timeout case",
          requested_by: "tola",
          assigned_to: "tola",
        }),
      (err: unknown) => {
        assertCode(err, "UNAVAILABLE");
        return true;
      },
    );
  } finally {
    mock.server.close();
  }
});

test("T4.x decision + approval + metric + schedule reads work end to end", async () => {
  const { repo } = makeLiveRepo();
  const project = await createFixtureProject(repo);
  fixtureProjectId = project.project_id;

  const key = randomUUID();
  const task = await repo.createTask({
    idempotency_key: key,
    project_id: project.project_id,
    title: "end-to-end probe",
    requested_by: "tola",
    assigned_to: "rhythm",
  });
  createdTaskIds.push(task.task_id);

  const decision = await repo.recordDecision({
    task_id: task.task_id,
    made_by: "tola",
    decision_type: "route",
    rationale: "choose R2 for structured execution",
    payload: { route: "R2" },
  });
  assert.ok(decision.decision_id);

  const approval = await repo.requestApproval({
    task_id: task.task_id,
    requested_by: "tola",
    approval_type: "risk_override",
    payload: { risk: "A2", reason: "test" },
  });
  assert.equal(approval.status, "pending");
  const pending = await repo.listApprovals("pending");
  assert.ok(pending.some((a) => a.approval_id === approval.approval_id));

  const metric = await repo.recordMetric({
    project_id: project.project_id,
    metric_name: "__t4_metric",
    metric_value: 1.5,
    unit: "test",
  });
  assert.ok(metric.metric_id);

  const events = await repo.listAgentEventsForTask(task.task_id);
  const types = events.map((e) => e.event_type);
  assert.ok(types.includes("task.created"));
  assert.ok(types.includes("decision.recorded"));
  assert.ok(types.includes("approval.requested"));
});

after(async () => {
  // cleanup fixture rows (best effort; keep DB clean for the operator)
  try {
    await rawDelete("agent_events", "task_id", createdTaskIds);
    await rawDelete("approvals", "task_id", createdTaskIds);
    await rawDelete("decisions", "task_id", createdTaskIds);
    await rawDelete("metrics", "project_id", fixtureProjectId ? [fixtureProjectId] : []);
    await rawDelete("tasks", "task_id", createdTaskIds);
    await rawDelete("skill_registry", "skill_name", createdSkillNames);
    if (fixtureProjectId) await rawDelete("projects", "project_id", [fixtureProjectId]);
  } catch {
    // best-effort cleanup
  }
});
