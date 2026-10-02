#!/usr/bin/env node
// Migration lint — Batch 07 CI gate. Lightweight static checks on supabase/migrations.
// No database required; no secrets involved.
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const dir = "supabase/migrations";
const files = readdirSync(dir).filter((f) => f.endsWith(".sql"));
let failures = 0;

const fail = (f, msg) => {
  console.error(`MIGRATION LINT FAIL: ${f}: ${msg}`);
  failures++;
};

for (const f of files) {
  if (!/^\d{14}_[a-z0-9_]+\.sql$/.test(f)) fail(f, "filename must be <timestamp14>_<snake_name>.sql");
  const text = readFileSync(join(dir, f), "utf8");
  if (text.trim().length === 0) fail(f, "empty migration");
  // Balanced transaction statements.
  const begins = (text.match(/\bBEGIN\b/g) ?? []).length;
  const commits = (text.match(/\bCOMMIT\b/g) ?? []).length;
  if (begins !== commits) fail(f, `unbalanced BEGIN/COMMIT (${begins}/${commits})`);
  // Destructive statements must be guarded.
  const drops = text.match(/\bDROP\s+(TABLE|COLUMN)\b[^;]*;/gi) ?? [];
  for (const d of drops) {
    if (!/\bIF\s+EXISTS\b/i.test(d) && !/\bCASCADE\b/i.test(d)) fail(f, `unguarded DROP: ${d.trim().slice(0, 60)}`);
  }
}

if (failures > 0) {
  console.error(`migration lint: ${failures} failure(s)`);
  process.exit(1);
}
console.log(`migration lint OK (${files.length} migrations)`);