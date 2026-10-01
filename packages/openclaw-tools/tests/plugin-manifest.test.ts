// Batch 04 test suite — plugin/manifest agreement and strict schemas.
// Run: node --experimental-strip-types --test tests/plugin-manifest.test.ts
// No network, no Supabase, no credentials. Manifest is the generated one.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import plugin from "../src/plugin.ts";
import { getToolPluginMetadata } from "openclaw/plugin-sdk/tool-plugin";

const here = path.dirname(fileURLToPath(import.meta.url));
const manifest = JSON.parse(readFileSync(path.join(here, "../openclaw.plugin.json"), "utf8"));

const APPROVED_TOOLS = [
  "listProjects", "getProject", "listGoals", "getGoal",
  "createTask", "listTasks", "getTask", "assignTask", "updateTaskStatus",
  "recordDecision", "recordEvent", "requestApproval", "getApproval", "getTaskRun",
] as const;

test("T4.1 manifest/runtime agreement: metadata matches generated manifest", () => {
  const meta = getToolPluginMetadata(plugin);
  assert.ok(meta, "entry must expose defineToolPlugin metadata");
  assert.equal(meta.id, manifest.id);
  assert.equal(meta.name, manifest.name);
  assert.equal(meta.description, manifest.description);
  const runtimeNames = meta.tools.map((t: { name: string }) => t.name).sort();
  assert.deepEqual(runtimeNames, [...manifest.contracts.tools].sort());
  assert.deepEqual(runtimeNames, [...APPROVED_TOOLS].sort());
});

test("T4.2 manifest version matches package version", () => {
  const pkg = JSON.parse(readFileSync(path.join(here, "../package.json"), "utf8"));
  assert.equal(manifest.version, pkg.version);
});

test("T4.3 every tool schema is strict: additionalProperties false", () => {
  const meta = getToolPluginMetadata(plugin);
  assert.ok(meta);
  for (const tool of meta.tools) {
    const schema = tool.parameters as Record<string, unknown>;
    assert.equal(schema.additionalProperties, false, `tool ${tool.name} schema not strict`);
    assert.equal(schema.type, "object");
  }
});

test("T4.4 config schema is strict and declares only the Supabase binding", () => {
  const cfg = manifest.configSchema as Record<string, unknown>;
  assert.equal(cfg.additionalProperties, false);
  const props = cfg.properties as Record<string, unknown>;
  assert.deepEqual(Object.keys(props).sort(), ["supabaseKey", "supabaseUrl", "timeoutMs"]);
});

test("T4.5 no generic/forbidden tool names on the contract", () => {
  for (const name of manifest.contracts.tools) {
    assert.ok(!/sql|query|exec|fetch|table|admin|raw|http/i.test(name), `suspicious tool name: ${name}`);
  }
  const forbidden = ["runSql", "rawQuery", "queryTable", "deleteRow", "promoteSkill", "elevate", "approveApproval", "grantApproval", "resolveApproval", "setApprovalStatus"];
  for (const f of forbidden) {
    assert.ok(!manifest.contracts.tools.includes(f), `forbidden tool on contract: ${f}`);
  }
});

test("T4.6 no credentials anywhere in the manifest or package metadata", () => {
  const raw = readFileSync(path.join(here, "../openclaw.plugin.json"), "utf8");
  assert.ok(!/eyJ|service_role|sk-|sb_secret/i.test(raw), "possible credential in manifest");
  const pkg = readFileSync(path.join(here, "../package.json"), "utf8");
  assert.ok(!/eyJ|service_role|sk-|sb_secret/i.test(pkg), "possible credential in package.json");
});