// Staging-adapter tests — Batch 10.
// Tests the staging view and ensure_occurrence helper from the
// Batch 10 migration. Uses a real PostgreSQL connection only
// when SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are present;
// otherwise skips with an explicit reason (offline-safe).
//
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/workflows.staging.test.ts

import { test, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../..");

// ---------------------------------------------------------------------------
// Load env only if present — never fail offline
// ---------------------------------------------------------------------------
let SUPA_URL: string | null = null;
let SERVICE_KEY: string | null = null;
try {
  const { loadEnv } = await import("../../blackboard-tools/src/env.ts");
  loadEnv(path.join(repoRoot, ".env"));
  // eslint-disable-next-line no-empty
} catch { /* offline: no .env */ }

// Read env vars directly (they may be in process.env from shell)
SUPA_URL = process.env.SUPABASE_URL ?? null;
SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? null;

const hasLiveCreds = !!(SUPA_URL && SERVICE_KEY && SUPA_URL.includes("supabase.co"));

if (!hasLiveCreds) {
  console.error("# SKIP: live Supabase credentials required for staging-adapter tests (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY absent)");
  process.exit(0);
}

// ---------------------------------------------------------------------------
// Live staging-adapter tests (only reached with credentials)
// ---------------------------------------------------------------------------

import { SupabaseAdapter } from "../../blackboard-tools/src/adapters/supabase.ts";

const adapter = new SupabaseAdapter({ url: SUPA_URL!, serviceKey: SERVICE_KEY!, timeoutMs: 10_000 });

// The staging view and ensure_occurrence function are defined in
// the Batch 10 migration (20261002080000). These tests verify
// the adapter can read the staging view and call the helper.

test("staging view is queryable via Supabase adapter", async () => {
  const res = await adapter.request("GET", "automation_occurrences_staging", {
    select: "occurrence_id,automation_key,status",
    limit: "1",
  });
  // The view exists and is readable (may be empty — that's fine)
  assert.ok(Array.isArray(res.rows), "Staging view must return an array");
});

test("ensure_occurrence is idempotent (insert-if-absent)", async () => {
  const key = `test-ensure-${Date.now()}`;
  const scheduled = new Date().toISOString();

  // First call: should create
  const first = await adapter.request("POST", "rpc/ensure_occurrence", {
    body: { p_automation_key: key, p_scheduled_for: scheduled, p_release_sha: "sha-1" },
  });
  assert.ok(first.data?.[0]?.created === true, "First call should create the occurrence");

  // Second call: should not create (idempotent)
  const second = await adapter.request("POST", "rpc/ensure_occurrence", {
    body: { p_automation_key: key, p_scheduled_for: scheduled, p_release_sha: "sha-2" },
  });
  assert.ok(second.data?.[0]?.created === false, "Second call should not duplicate");
});

test("staging view columns include claim tracking fields", async () => {
  const res = await adapter.request("GET", "automation_occurrences_staging", {
    select: "occurrence_id,automation_key,scheduled_for,claimed_by,claimed_at,status",
    limit: "1",
  });
  assert.ok(Array.isArray(res.rows), "Staging view must return rows");
  // If rows exist, verify the claim-tracking columns are present
  if (res.rows.length > 0) {
    const row = res.rows[0] as Record<string, unknown>;
    assert.ok("claimed_by" in row, "Staging view must include claimed_by");
    assert.ok("claimed_at" in row, "Staging view must include claimed_at");
  }
});