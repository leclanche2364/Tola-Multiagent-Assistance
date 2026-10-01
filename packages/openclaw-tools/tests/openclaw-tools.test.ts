// Batch 5 test suite — OpenClaw tool plugin
// T5.1 tool discovery | T5.2 input validation | T5.3 mutation audit
// T5.4 no raw query surface | T5.5 error redaction | T5.6 specialist visibility
// T5.7 approval API separation
// Run: npm test (from packages/openclaw-tools)

import { test, after } from "node:test";
import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import path from "node:path";
import {
  BlackboardRepository,
  SupabaseAdapter,
  BlackboardError,
  loadEnv,
  envOptional,
} from "../../blackboard-tools/src/index.ts";
import { __testInternals } from "../src/plugin.ts";

// Local adapter: the old Batch-5 surface keyed tool implementations directly.
// Batch 04 wraps them in the native plugin; tests drive the same functions.
function createPlugin(repo: BlackboardRepository) {
  const t = __testInternals;
  return {
    listProjects: () => t.listProjectsTool(repo),
    getProject: (p: { project_id: string }) => t.getProjectTool(repo, p as { project_id: string }),
    listGoals: (p: { project_id?: string | null }) => t.listGoalsTool(repo, p),
    getGoal: (p: { goal_id: string }) => t.getGoalTool(repo, p as { goal_id: string }),
    createTask: (p: unknown) => t.createTaskTool(repo, p),
    listTasks: () => t.listTasksTool(repo),
    getTask: (p: { task_id: string } | string) => t.getTaskTool(repo, typeof p === "string" ? { task_id: p } : p as { task_id: string }),
    assignTask: (p: unknown) => t.assignTaskTool(repo, p),
    updateTaskStatus: (p: unknown) => t.updateTaskStatusTool(repo, p),
    recordDecision: (p: unknown) => t.recordDecisionTool(repo, p),
    recordEvent: (p: unknown) => t.recordEventTool(repo, p),
    requestApproval: (p: unknown) => t.requestApprovalTool(repo, p),
    getApproval: (p: { approval_id: string } | string) => t.getApprovalTool(repo, typeof p === "string" ? { approval_id: p } : p as { approval_id: string }),
    getTaskRun: (p: { task_id: string } | string) => t.getTaskRunTool(repo, typeof p === "string" ? { task_id: p } : p as { task_id: string }),
  };
}
import { redactError } from "../src/redact.ts";
import * as pkg from "../src/index.ts";

const here = path.dirname(fileURLToPath(import.meta.url));
// tests/ -> openclaw-tools/ -> packages/ -> four-agent-repo/
const repoRoot = path.resolve(here, "../../..");
loadEnv(path.join(repoRoot, ".env"));

const SUPA_URL = envOptional("SUPABASE_URL").replace(/\/$/, "") + "/rest/v1";
const SERVICE_KEY = envOptional("SUPABASE_SERVICE_ROLE_KEY");
if (!SUPA_URL.includes("supabase.co") || !SERVICE_KEY) {
  throw new Error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from four-agent-repo/.env");
}

// ---------- constants ----------

// The single Tola-approved tool surface (T5.1 / T5.6).
const APPROVED_TOOLS = [
  "listProjects",
  "getProject",
  "listGoals",
  "getGoal",
  "createTask",
  "listTasks",
  "getTask",
  "assignTask",
  "updateTaskStatus",
  "recordDecision",
  "recordEvent",
  "requestApproval",
  "getApproval",
  "getTaskRun",
] as const;

// Names that must NEVER appear on the plugin surface (T5.4 / T5.6 / T5.7).
const FORBIDDEN_TOOLS = [
  "runSql",
  "rawQuery",
  "queryTable",
  "deleteRow",
  "promoteSkill",
  "elevate",
  "approveApproval",
  "grantApproval",
  "resolveApproval",
  "setApprovalStatus",
];

// ---------- helpers ----------

function makeLiveRepo(timeoutMs = 15_000): BlackboardRepository {
  const adapter = new SupabaseAdapter({ url: SUPA_URL, serviceKey: SERVICE_KEY, timeoutMs });
  return new BlackboardRepository(adapter);
}

function assertCode(err: unknown, code: BlackboardError["code"]): void {
  assert.ok(err instanceof BlackboardError, `expected BlackboardError, got ${String(err)}`);
  assert.equal((err as BlackboardError).code, code, (err as BlackboardError).message);
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

async function createFixtureProject(): Promise<ProjectLike> {
  return rawInsert("projects", {
    project_name: `__t5_${randomUUID().slice(0, 8)}`,
    description: "Batch 5 test fixture",
    status: "active",
    strategic_priority: 5,
  });
}

// ---------- mock server (failure injection / request counting) ----------

type MockBehaviour = (req: { method: string; url: string; body: string }, res: import("node:http").ServerResponse) => void;

function startMock(behaviour: MockBehaviour): Promise<{ server: Server; url: string; requests: { method: string; url: string; body: string }[] }> {
  const requests: { method: string; url: string; body: string }[] = [];
  return new Promise((resolve) => {
    const server = createServer((req, res) => {
      let body = "";
      req.on("data", (c: Buffer) => (body += c.toString()));
      req.on("end", () => {
        requests.push({ method: req.method ?? "", url: req.url ?? "", body });
        behaviour({ method: req.method ?? "", url: req.url ?? "", body }, res);
      });
    });
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address() as { port: number };
      resolve({ server, url: `http://127.0.0.1:${addr.port}/rest/v1`, requests });
    });
  });
}

// ---------- cleanup registry ----------

const createdTaskIds: string[] = [];
let fixtureProjectId: string | null = null;

// ---------- tests ----------

test("T5.1 tool discovery: plugin surface is exactly the approved tool set", () => {
  const plugin = createPlugin(makeLiveRepo());
  const keys = Object.keys(plugin).sort();
  assert.deepEqual(keys, [...APPROVED_TOOLS].sort());
});

test("T5.2 input validation: malformed create/update rejected BEFORE any mutation", async () => {
  const mock = await startMock((_req, res) => {
    res.writeHead(500, { "content-type": "application/json" });
    res.end('{"message":"must never be reached"}');
  });
  try {
    const adapter = new SupabaseAdapter({ url: mock.url, serviceKey: "dummy", timeoutMs: 3000 });
    const plugin = createPlugin(new BlackboardRepository(adapter));

    // malformed create: bad idempotency key
    await assert.rejects(() =>
      plugin.createTask({
        idempotency_key: "not-a-uuid",
        title: "should never land",
        requested_by: "tola",
        assigned_to: "growth",
      } as never)
    );
    // malformed create: bad UUID project_id
    await assert.rejects(() =>
      plugin.createTask({
        idempotency_key: randomUUID(),
        project_id: "not-a-uuid",
        title: "should never land either",
        requested_by: "tola",
        assigned_to: "growth",
      } as never)
    );
    // malformed status update
    await assert.rejects(() =>
      plugin.updateTaskStatus({
        task_id: randomUUID(),
        new_status: "exploded" as never,
        acting_agent: "tola",
      } as never)
    );
    // malformed assignment: unknown agent
    await assert.rejects(() =>
      plugin.assignTask({ task_id: randomUUID(), agent_name: "jarvis" as never } as never)
    );

    assert.equal(mock.requests.length, 0, "no network request may fire for malformed input");
  } finally {
    mock.server.close();
  }
});

test("T5.2b validation errors carry the VALIDATION code", async () => {
  const plugin = createPlugin(makeLiveRepo());
  await assert.rejects(
    () =>
      plugin.createTask({
        idempotency_key: "not-a-uuid",
        title: "x",
        requested_by: "tola",
        assigned_to: "growth",
      } as never),
    (err: unknown) => {
      assertCode(err, "VALIDATION");
      return true;
    }
  );
});

test("T5.3 mutation audit: valid mutation produces entity + agent_events record", async () => {
  const repo = makeLiveRepo();
  const plugin = createPlugin(repo);
  const project = await createFixtureProject();
  fixtureProjectId = project.project_id;

  const key = randomUUID();
  const { task } = await plugin.createTask({
    idempotency_key: key,
    project_id: project.project_id,
    title: "T5.3 audited mutation",
    required_output: "task row + audit event",
    requested_by: "tola",
    assigned_to: "growth",
    risk_class: "A1",
  });
  createdTaskIds.push(task.task_id);

  assert.ok(task.task_id);
  assert.equal(task.status, "pending");

  // independent read: row really exists
  const run = await plugin.getTaskRun(task.task_id);
  assert.equal(run.task.task_id, task.task_id);
  assert.equal(run.task.idempotency_key, key);

  // audit event recorded by the repository path
  const events = await repo.listAgentEventsForTask(task.task_id);
  assert.ok(events.some((e) => e.event_type === "task.created"), "task.created audit row must exist");
});

test("T5.4 no raw query surface: no SQL/table/export escape hatch exists", async () => {
  // plugin surface has no raw/sql/query/admin tools
  const plugin = createPlugin(makeLiveRepo());
  const keys = Object.keys(plugin);
  for (const forbidden of FORBIDDEN_TOOLS) {
    assert.ok(!keys.includes(forbidden), `forbidden tool on surface: ${forbidden}`);
  }
  for (const k of keys) {
    assert.ok(!/sql|query|exec|fetch|table|admin|raw/i.test(k), `suspicious tool name on surface: ${k}`);
  }
  // module export surface: no generic execution/export escapes either
  const exportNames = Object.keys(pkg);
  for (const name of exportNames) {
    assert.ok(
      !/sql|querytable|rawquery|runsql|deleteall|exec/i.test(name),
      `suspicious module export: ${name}`
    );
  }
});

test("T5.5 error redaction: forced auth failure leaks no secret", async () => {
  const SECRET = "sk-test-SECRET123-do-not-leak";
  const mock = await startMock((_req, res) => {
    res.writeHead(401, { "content-type": "application/json" });
    res.end(JSON.stringify({ message: `apikey ${SECRET} invalid`, code: 401, hint: "Check your API key" }));
  });
  try {
    const adapter = new SupabaseAdapter({ url: mock.url, serviceKey: SERVICE_KEY, timeoutMs: 3000 });
    const plugin = createPlugin(new BlackboardRepository(adapter));
    await assert.rejects(() => plugin.listProjects());
    // the thrown error (message + detail) must not contain the injected secret
    try {
      await plugin.listProjects();
      assert.fail("expected rejection");
    } catch (err: unknown) {
      const visible = `${(err as Error).message} ${JSON.stringify((err as { detail?: unknown }).detail ?? "")}`;
      assert.ok(!visible.includes(SECRET), "secret leaked in model-visible error");
      assert.ok(!visible.includes("sk-test-"), "partial secret leaked in model-visible error");
    }
  } finally {
    mock.server.close();
  }
});

test("T5.5b redactError strips secrets from generic provider errors", () => {
  const out = redactError(new Error("connect failed: key sb_secret_abcdef123456 rejected"));
  assert.ok(!out.message.includes("sb_secret_abcdef123456"), "provider message must not pass through raw");
  assert.ok(out.code);
});

test("T5.6 specialist visibility: surface is the Tola-approved allowlist only", () => {
  const plugin = createPlugin(makeLiveRepo());
  const keys = Object.keys(plugin);
  // every exposed tool is on the approved allowlist (specialists can see nothing extra)
  for (const k of keys) {
    assert.ok((APPROVED_TOOLS as readonly string[]).includes(k), `tool not on approved allowlist: ${k}`);
  }
  // and no capability that would let a specialist escalate/act as approver
  for (const forbidden of FORBIDDEN_TOOLS) {
    assert.ok(!keys.includes(forbidden), `escalation surface present: ${forbidden}`);
  }
});

test("T5.7 approval API separation: request-only, cannot self-approve", async () => {
  const repo = makeLiveRepo();
  const plugin = createPlugin(repo);
  const project = await createFixtureProject();
  fixtureProjectId = project.project_id;

  const { task } = await plugin.createTask({
    idempotency_key: randomUUID(),
    project_id: project.project_id,
    title: "T5.7 approval probe",
    requested_by: "tola",
    assigned_to: "scholar",
  });
  createdTaskIds.push(task.task_id);

  const { approval } = await plugin.requestApproval({
    task_id: task.task_id,
    requested_by: "tola",
    approval_type: "risk_override",
    payload: { reason: "T5.7 probe" },
  });

  assert.equal(approval.status, "pending");
  assert.equal(approval.decided_by ?? null, null, "agent must not be able to fabricate decided_by");

  // independent read confirms pending state
  const fetched = await plugin.getApproval(approval.approval_id);
  assert.equal(fetched.status, "pending");
  assert.equal(fetched.decided_by ?? null, null);

  // no approve/grant/resolve tool exists on the plugin surface
  const keys = Object.keys(plugin);
  const approver = keys.filter((k) => /^approve|^grant|^resolve|^setApproval/i.test(k));
  assert.deepEqual(approver, [], "no approval-granting tool may exist on the agent surface");
});

after(async () => {
  try {
    await rawDelete("agent_events", "task_id", createdTaskIds);
    await rawDelete("approvals", "task_id", createdTaskIds);
    await rawDelete("decisions", "task_id", createdTaskIds);
    await rawDelete("tasks", "task_id", createdTaskIds);
    if (fixtureProjectId) await rawDelete("projects", "project_id", [fixtureProjectId]);
  } catch {
    // best-effort cleanup
  }
});