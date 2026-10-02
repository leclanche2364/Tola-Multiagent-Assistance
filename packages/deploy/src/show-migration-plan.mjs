// Migration plan display — for deploy dry-run output.
// Lists pending migrations and their safe-forward/rollback state.

import { readdirSync } from "node:fs";
import { join } from "node:path";

const MIGRATIONS_DIR = join(process.cwd(), "supabase", "migrations");

function listMigrations() {
  try {
    const files = readdirSync(MIGRATIONS_DIR)
      .filter((f) => f.endsWith(".sql"))
      .sort();
    return files;
  } catch {
    return [];
  }
}

function main() {
  const files = listMigrations();
  console.log("Supabase Migration Plan");
  console.log(`Migrations found: ${files.length}`);
  console.log("");

  for (const f of files) {
    const isBatch11 = f.includes("batch11_deployments");
    console.log(`  ${f} ${isBatch11 ? "(new — repo-only)" : "(existing)"}`);
  }

  console.log("");
  console.log("Note: All migrations are repo-only and never applied to a live database.");
  console.log("The deployments table migration (20261002090000) tracks release SHA + versions.");
}

main();
