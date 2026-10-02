// DeployAdapter — typed interface for the OpenClaw plugin/config lifecycle.
// Production adapter documents/subcommands the real lifecycle.
// Tests use a fake adapter that records calls without touching the live machine.

export interface DeployAdapter {
  /** Return the currently active plugin entry (path, version, sha). */
  getActivePlugin(): Promise<ActivePluginInfo>;
  /** Back up current config and workspace metadata. Returns backup path. */
  backupConfig(): Promise<string>;
  /** Restore config/workspace metadata from a backup path. */
  restoreConfig(backupPath: string): Promise<void>;
  /** Apply a Supabase migration file (conceptual — delegates to supabase CLI). */
  applyMigration(migrationFile: string): Promise<void>;
  /** Roll back a migration (conceptual — delegates to supabase CLI). */
  rollbackMigration(migrationFile: string): Promise<void>;
  /** Activate/reload the plugin after build. */
  reloadPlugin(pluginEntry: string): Promise<void>;
  /** Apply the candidate config to the live workspace. */
  applyConfig(configPath: string): Promise<void>;
  /** Run canary checks against the live gateway. */
  runCanaries(): Promise<CanaryResult>;
  /** Reconcile automation jobs (dry-run or live). */
  reconcileJobs(dryRun: boolean): Promise<ReconcileResult>;
}

export interface ActivePluginInfo {
  path: string;
  version: string;
  sha: string;
}

export interface CanaryResult {
  ok: boolean;
  checks: CanaryCheck[];
}

export interface CanaryCheck {
  name: string;
  passed: boolean;
  detail?: string;
}

export interface ReconcileResult {
  dryRun: boolean;
  operationsCount: number;
}

// ---------------------------------------------------------------------------
// Fake adapter for tests — records calls, never touches the live machine.
// ---------------------------------------------------------------------------

export interface FakeAdapterCall {
  method: string;
  args: unknown[];
  timestamp: number;
}

export function fakeAdapter(overrides: {
  getActivePlugin?: () => Promise<ActivePluginInfo>;
  backupConfig?: () => Promise<string>;
  restoreConfig?: () => Promise<void>;
  applyMigration?: () => Promise<void>;
  rollbackMigration?: () => Promise<void>;
  reloadPlugin?: () => Promise<void>;
  applyConfig?: () => Promise<void>;
  runCanaries?: () => Promise<CanaryResult>;
  reconcileJobs?: (dryRun: boolean) => Promise<ReconcileResult>;
  failOn?: string[];
}): DeployAdapter {
  const calls: FakeAdapterCall[] = [];
  const failOn = overrides.failOn ?? [];

  const record = (method: string, args: unknown[]) => {
    calls.push({ method, args, timestamp: Date.now() });
    if (failOn.includes(method)) {
      throw new Error(`FAKE_ADAPTER_FAILURE:${method}`);
    }
  };

  return {
    getActivePlugin: async () => {
      record("getActivePlugin", []);
      return overrides.getActivePlugin?.() ?? { path: "/live/plugin.js", version: "0.0.0", sha: "0000000" };
    },
    backupConfig: async () => {
      record("backupConfig", []);
      return overrides.backupConfig?.() ?? "/tmp/backup.json";
    },
    restoreConfig: async (path) => {
      record("restoreConfig", [path]);
      return overrides.restoreConfig?.() ?? Promise.resolve();
    },
    applyMigration: async (f) => {
      record("applyMigration", [f]);
      return overrides.applyMigration?.() ?? Promise.resolve();
    },
    rollbackMigration: async (f) => {
      record("rollbackMigration", [f]);
      return overrides.rollbackMigration?.() ?? Promise.resolve();
    },
    reloadPlugin: async (e) => {
      record("reloadPlugin", [e]);
      return overrides.reloadPlugin?.() ?? Promise.resolve();
    },
    applyConfig: async (p) => {
      record("applyConfig", [p]);
      return overrides.applyConfig?.() ?? Promise.resolve();
    },
    runCanaries: async () => {
      record("runCanaries", []);
      return overrides.runCanaries?.() ?? { ok: true, checks: [] };
    },
    reconcileJobs: async (dryRun) => {
      record("reconcileJobs", [dryRun]);
      return overrides.reconcileJobs?.(dryRun) ?? { dryRun, operationsCount: 0 };
    },
    _calls: () => calls,
  };
}
