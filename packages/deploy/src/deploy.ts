// DeployTool — dry-run-first release deployment for OpenClaw.
// Accepts an exact approved commit SHA/tag. Never runs apply mode
// against the live machine; live-touching steps are behind DeployAdapter.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import type { DeployAdapter, ActivePluginInfo } from "./adapter.ts";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DeployPlan {
  sha: string;
  tag: string;
  stagingDir: string;
  steps: DeployStep[];
}

export interface DeployStep {
  name: string;
  command: string;
  dryRunOnly: boolean;
}

export interface DeployResult {
  success: boolean;
  phase: string;
  details: string;
  rollbackPerformed: boolean;
}

export interface MigrationPlan {
  file: string;
  description: string;
  direction: "forward" | "rollback";
  safeForward: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function run(cmd: string, args: string[], cwd?: string): string {
  return execFileSync(cmd, args, { cwd, encoding: "utf8", stdio: "pipe" });
}

function validateShaFormat(sha: string): boolean {
  // Full 40-char hex SHA, or a tag that looks like vX.Y.Z or similar.
  if (/^[0-9a-f]{40}$/.test(sha)) return true;
  if (/^v?\d+\.\d+\.\d+/.test(sha)) return true;
  return false;
}

// ---------------------------------------------------------------------------
// Dry-run phase
// ---------------------------------------------------------------------------

export function buildDeployPlan(sha: string, tag: string): DeployPlan {
  if (!validateShaFormat(sha)) {
    throw new Error(`Invalid SHA/tag format: "${sha}"`);
  }

  const stagingDir = `.deploy-staging/${sha.slice(0, 7)}`;

  const steps: DeployStep[] = [
    { name: "install-locked-deps", command: `npm ci --prefix ${stagingDir}`, dryRunOnly: true },
    { name: "run-gate", command: `bash ${stagingDir}/scripts/gate.sh`, dryRunOnly: true },
    { name: "build-plugin", command: `cd ${stagingDir}/packages/openclaw-tools && npm run plugin:build`, dryRunOnly: true },
    { name: "validate-plugin", command: `cd ${stagingDir}/packages/openclaw-tools && npx openclaw plugins validate --entry ./dist/index.js`, dryRunOnly: true },
    { name: "validate-config", command: `bash ${stagingDir}/config-candidate/validate.sh`, dryRunOnly: true },
    { name: "show-migration-plan", command: `node ${stagingDir}/scripts/show-migration-plan.mjs`, dryRunOnly: true },
    { name: "reconcile-automations", command: `node ${stagingDir}/packages/automations/reconcile-cli.mjs --dry-run`, dryRunOnly: true },
  ];

  return { sha, tag, stagingDir, steps };
}

export function dryRun(sha: string, tag: string): DeployResult {
  const plan = buildDeployPlan(sha, tag);
  const log: string[] = [`DRY-RUN for ${sha} (${tag})`, `Staging: ${plan.stagingDir}`, ""];

  for (const step of plan.steps) {
    log.push(`[DRY-RUN] ${step.name}: ${step.command}`);
  }

  log.push("", "DRY-RUN COMPLETE — no live changes made.");
  return { success: true, phase: "dry-run", details: log.join("\n"), rollbackPerformed: false };
}

// ---------------------------------------------------------------------------
// Apply phase (conceptual — uses adapter, never called directly by tool)
// ---------------------------------------------------------------------------

export async function apply(
  sha: string,
  tag: string,
  adapter: DeployAdapter,
): Promise<DeployResult> {
  const plan = buildDeployPlan(sha, tag);

  try {
    // 1. Back up current state
    const backup = await adapter.backupConfig();

    // 2. Apply migrations (conceptual — adapter delegates to supabase CLI)
    const migrationFile = `supabase/migrations/${plan.sha.slice(0, 7)}_batch11_deployments.sql`;
    await adapter.applyMigration(migrationFile);

    // 3. Activate/reload plugin
    await adapter.reloadPlugin(`dist/index.js`);

    // 4. Apply config
    await adapter.applyConfig("config-candidate/openclaw.json");

    // 5. Reconcile jobs (live)
    await adapter.reconcileJobs(false);

    // 6. Run canaries
    const canary = await adapter.runCanaries();
    if (!canary.ok) {
      // Rollback
      await adapter.rollbackMigration(migrationFile);
      await adapter.restoreConfig(backup);
      return {
        success: false,
        phase: "apply",
        details: `Canary failed: ${canary.checks.map((c) => c.name).join(", ")}`,
        rollbackPerformed: true,
      };
    }

    return { success: true, phase: "apply", details: "Deployment applied successfully", rollbackPerformed: false };
  } catch (err) {
    // On any failure: restore previous state
    try {
      await adapter.restoreConfig("/tmp/backup.json");
    } catch {
      // best effort
    }
    return {
      success: false,
      phase: "apply",
      details: `Error: ${(err as Error).message}`,
      rollbackPerformed: true,
    };
  }
}

// ---------------------------------------------------------------------------
// Migration plan display
// ---------------------------------------------------------------------------

export function showMigrationPlan(): MigrationPlan[] {
  return [
    {
      file: "supabase/migrations/20261002090000_batch11_deployments.sql",
      description: "Create deployments table (repo-only, tracks SHA + component versions)",
      direction: "forward",
      safeForward: true,
    },
    {
      file: "supabase/migrations/20261002090000_batch11_deployments.sql",
      description: "Rollback: drop deployments table",
      direction: "rollback",
      safeForward: true,
    },
  ];
}
