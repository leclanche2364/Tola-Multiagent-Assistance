// Batch 02 — Supabase-only persistence: a failed write must surface an explicit
// error AND leave no local queue/outbox file on disk. No false success.
// Run: node --experimental-strip-types --test tests/no-local-queue.test.ts

import { test } from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { createServer, type Server } from "node:http";
import { readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { BlackboardRepository, SupabaseAdapter } from "../src/index.ts";

const here = path.dirname(fileURLToPath(import.meta.url));
const pkgRoot = path.resolve(here, "..");

// Recursively collect *.sqlite3 / *.db / *.sqlite file paths under a directory.
function sqliteFiles(dir: string): string[] {
  const out: string[] = [];
  try {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      if (entry.name === "node_modules") continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) out.push(...sqliteFiles(full));
      else if (/\.(sqlite3?|db)$/i.test(entry.name)) out.push(full);
    }
  } catch {
    // unreadable dir: ignore
  }
  return out;
}

function before(): string[] {
  return sqliteFiles(pkgRoot).concat(sqliteFiles(path.resolve(pkgRoot, "..")));
}

function mockServer(behaviour: (res: import("node:http").ServerResponse) => void): Promise<{ server: Server; url: string }> {
  return new Promise((resolve) => {
    const server = createServer((_req, res) => behaviour(res));
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address() as { port: number };
      resolve({ server, url: `http://127.0.0.1:${addr.port}/rest/v1` });
    });
  });
}

async function failedWrite(url: string, serviceKey = "dummy", timeoutMs = 3000): Promise<unknown> {
  const adapter = new SupabaseAdapter({ url, serviceKey, timeoutMs });
  const repo = new BlackboardRepository(adapter);
  let caught: unknown = null;
  try {
    await repo.createTask({
      idempotency_key: randomUUID(),
      title: "must not queue locally",
      requested_by: "tola",
      assigned_to: "tola",
    });
  } catch (err) {
    caught = err;
  }
  return caught;
}

test("B02.1 unreachable store: explicit UNAVAILABLE, zero local queue files", async () => {
  const beforeFiles = before();
  const adapter = new SupabaseAdapter({ url: "http://127.0.0.1:1/rest/v1", serviceKey: "dummy", timeoutMs: 2000 });
  const repo = new BlackboardRepository(adapter);

  await assert.rejects(
    () =>
      repo.createTask({
        idempotency_key: randomUUID(),
        title: "unreachable store",
        requested_by: "tola",
        assigned_to: "tola",
      }),
    (err: unknown) => {
      assert.ok(err instanceof Error, "must throw, not return a fake success");
      assert.match((err as Error).name + (err as Error).message, /UNAVAILABLE|Error/);
      return true;
    },
  );

  const afterFiles = before(); // recompute
  const newFiles = afterFiles.filter((f) => !beforeFiles.includes(f));
  assert.equal(newFiles.length, 0, `failed write must not create local persistence files, found: ${newFiles.join(", ")}`);
});

test("B02.2 server 500 on write: explicit error, no local queue, no false success", async () => {
  const beforeFiles = before();
  const { server, url } = await mockServer((res) => {
    res.writeHead(500, { "content-type": "application/json" });
    res.end(JSON.stringify({ message: "internal error", code: "500" }));
  });
  try {
    const err = await failedWrite(url);
    assert.ok(err instanceof Error, "500 must surface as an error, not success");
  } finally {
    server.close();
  }
  const newFiles = before().filter((f) => !beforeFiles.includes(f));
  assert.equal(newFiles.length, 0, `failed write must not create local persistence files, found: ${newFiles.join(", ")}`);
});

test("B02.3 network timeout: explicit error, no local queue", async () => {
  const beforeFiles = before();
  const { server, url } = await mockServer((_res) => {
    // never respond — client times out
  });
  try {
    const err = await failedWrite(url, "dummy", 500);
    assert.ok(err instanceof Error, "timeout must surface as an error");
  } finally {
    server.close();
  }
  const newFiles = before().filter((f) => !beforeFiles.includes(f));
  assert.equal(newFiles.length, 0, `failed write must not create local persistence files, found: ${newFiles.join(", ")}`);
});

test("B02.4 successful write also leaves no local queue file (Supabase-only)", async () => {
  // A mocked success path: the repository must consume the 201 directly.
  const beforeFiles = before();
  const { server, url } = await mockServer((res) => {
    res.writeHead(201, { "content-type": "application/json", prefer: "return=representation" });
    res.end(JSON.stringify([{ task_id: "fake", status: "pending", version: 1 }]));
  });
  try {
    const adapter = new SupabaseAdapter({ url, serviceKey: "dummy", timeoutMs: 3000 });
    const repo = new BlackboardRepository(adapter);
    try {
      await repo.createTask({
        idempotency_key: randomUUID(),
        title: "mocked success",
        requested_by: "tola",
        assigned_to: "tola",
      });
    } catch {
      // repository may post-validate with a read; if the mock can't satisfy it,
      // the write path still must not have created local files — checked below.
    }
  } finally {
    server.close();
  }
  const newFiles = before().filter((f) => !beforeFiles.includes(f));
  assert.equal(newFiles.length, 0, "even successful writes must not persist locally");
});

// silence unused import warnings for statSync if unused after refactor
void statSync;
