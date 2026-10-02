// Automation reconciler CLI — dry-run mode for deploy tool.
// Reads the manifest and lists add/edit/remove operations without mutating.

import { AutomationReconciler } from "../../automations/src/reconciler.ts";
import { loadManifest } from "../../automations/src/manifest.ts";
import { fakeJobSource } from "../../automations/src/adapter.ts";

const dryRun = true; // always dry-run for the deploy tool

async function main() {
  const manifest = await loadManifest();
  const source = fakeJobSource([]);
  const reconciler = new AutomationReconciler(source, dryRun);
  const result = await reconciler.reconcile(manifest);

  console.log("Automation Reconciliation (dry-run)");
  console.log(`Manifest version: ${result.manifestVersion}`);
  console.log(`Operations: ${result.operations.length}`);
  console.log(`Unchanged: ${result.unchangedCount}`);
  console.log("");

  for (const op of result.operations) {
    console.log(`  [${op.kind}] ${op.stableName} — ${op.summary}`);
  }
}

main().catch((err) => {
  console.error("Reconciliation failed:", err.message);
  process.exit(1);
});
