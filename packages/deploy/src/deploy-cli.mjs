// Deploy CLI — entry point for `node deploy-cli.mjs <sha> [--apply]`
// Dry-run is the default. Apply mode requires explicit --apply flag.

import { dryRun, apply, buildDeployPlan, showMigrationPlan } from "./deploy.ts";
import { fakeAdapter } from "./adapter.ts";

const args = process.argv.slice(2);
const sha = args[0];
const applyMode = args.includes("--apply");

if (!sha) {
  console.error("Usage: node deploy-cli.mjs <sha|tag> [--apply]");
  console.error("  Dry-run is the default. --apply required for live deployment.");
  process.exit(1);
}

if (applyMode) {
  console.error("APPLY MODE REQUIRES OPERATOR AUTHORITY.");
  console.error("This tool must never be run against the live machine by the automation agent.");
  process.exit(1);
}

// Dry-run path
try {
  const result = dryRun(sha, sha);
  console.log(result.details);

  console.log("\n--- Migration Plan ---");
  for (const m of showMigrationPlan()) {
    console.log(`  ${m.direction}: ${m.file} — ${m.description}`);
  }

  console.log("\n--- Automation Reconciliation (dry-run) ---");
  console.log("  Reconciler dry-run mode: add/edit/remove operations listed, no mutations.");

  process.exit(result.success ? 0 : 1);
} catch (err) {
  console.error(`DEPLOY ERROR: ${(err as Error).message}`);
  process.exit(1);
}
