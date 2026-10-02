// Native OpenClaw automation reconciler — Batch 09.
// Reads current jobs via an OpenClawJobSource, compares against the
// manifest (matched by stableName), and produces add/edit/remove operations.
// Default mode is dry-run. Must not duplicate jobs.

import type {
  AutomationEntry,
  AutomationManifest,
  Schedule,
} from "./manifest.ts";
import type { OpenClawJob, OpenClawJobSource } from "./adapter.ts";

// ---------------------------------------------------------------------------
// Operation types
// ---------------------------------------------------------------------------

export type OpKind = "add" | "edit" | "remove" | "no-op";

export interface ReconcilerOperation {
  kind: OpKind;
  stableName: string;
  /** Present in add/edit; absent for remove. */
  jobId?: string;
  /** Human-readable summary of the proposed change. */
  summary: string;
  /** The manifest entry driving this operation (undefined for remove). */
  entry?: AutomationEntry;
}

export interface ReconciliationResult {
  dryRun: boolean;
  manifestVersion: string;
  manifestUpdatedAt: string;
  operations: ReconcilerOperation[];
  unchangedCount: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Normalise a manifest schedule into a comparable string.
 * e.g. {kind:"cron",expr:"0 6 * * *",tz:"Europe/London"} → "cron:0 6 * * * @ Europe/London"
 */
function scheduleKey(s: Schedule): string {
  if (s.kind === "cron") {
    const tz = s.tz ? ` @ ${s.tz}` : "";
    return `cron:${s.expr}${tz}`;
  }
  if (s.kind === "every") {
    const anchor = s.anchorMs !== undefined ? ` anchor=${s.anchorMs}` : "";
    return `every:${s.everyMs}${anchor}`;
  }
  if (s.kind === "at") {
    return `at:${s.at}`;
  }
  return JSON.stringify(s);
}

/**
 * Normalise an OpenClaw job schedule into the same string format.
 */
function jobScheduleKey(job: OpenClawJob): string {
  const s = job.schedule;
  if (s.kind === "cron") {
    const tz = s.tz ? ` @ ${s.tz}` : "";
    return `cron:${s.expr}${tz}`;
  }
  if (s.kind === "every") {
    const anchor = s.anchorMs !== undefined ? ` anchor=${s.anchorMs}` : "";
    return `every:${s.everyMs}${anchor}`;
  }
  if (s.kind === "at") {
    return `at:${s.at}`;
  }
  return JSON.stringify(s);
}

/**
 * Map a manifest riskCeiling to the OpenClaw job mode.
 * "isolated" stays "isolated"; "command" stays "command".
 */
function resolveMode(entry: AutomationEntry): string {
  return entry.mode === "command" ? "command" : "isolated";
}

// ---------------------------------------------------------------------------
// Reconciler
// ---------------------------------------------------------------------------

export class AutomationReconciler {
  private source: OpenClawJobSource;
  private dryRun: boolean;

  constructor(source: OpenClawJobSource, dryRun = true) {
    this.source = source;
    this.dryRun = dryRun;
  }

  /**
   * Reconcile manifest against current OpenClaw jobs.
   * Returns operations without mutating anything when dryRun=true (default).
   */
  async reconcile(manifest: AutomationManifest): Promise<ReconciliationResult> {
    const currentJobs = await this.source.listJobs();

    // Build index of current jobs by stableName (best-effort match).
    // Manifest stableName is the authoritative key.
    const manifestByName = new Map<string, AutomationEntry>();
    for (const entry of manifest.automations) {
      manifestByName.set(entry.stableName, entry);
    }

    // Try to match current jobs to manifest entries by stableName.
    // Since OpenClaw job names may differ from stableName, we use a
    // best-effort substring match: a job "matches" an entry if the
    // entry's stableName is contained in the job name (case-insensitive).
    const matchedJobIds = new Set<string>();
    const operations: ReconcilerOperation[] = [];

    // Pass 1: check existing jobs — edit or no-op.
    for (const job of currentJobs) {
      let matchedEntry: AutomationEntry | undefined;
      let matchedStableName: string | undefined;

      for (const [name, entry] of manifestByName) {
        if (job.name.toLowerCase().includes(name.toLowerCase())) {
          matchedEntry = entry;
          matchedStableName = name;
          break;
        }
      }

      if (!matchedEntry) {
        // Job not in manifest → mark for removal.
        operations.push({
          kind: "remove",
          stableName: job.name,
          jobId: job.id ?? job.name,
          summary: `Job "${job.name}" not in manifest — propose removal`,
        });
        continue;
      }

      if (!matchedStableName) continue;
      matchedJobIds.add(matchedStableName);

      // Check if the job needs editing.
      const edits: string[] = [];
      if (job.schedule.kind !== matchedEntry.schedule.kind) {
        edits.push(`schedule kind ${job.schedule.kind} → ${matchedEntry.schedule.kind}`);
      } else {
        const currentKey = jobScheduleKey(job);
        const manifestKey = scheduleKey(matchedEntry.schedule);
        if (currentKey !== manifestKey) {
          edits.push(`schedule ${currentKey} → ${manifestKey}`);
        }
      }
      if (job.mode !== resolveMode(matchedEntry)) {
        edits.push(`mode ${job.mode} → ${resolveMode(matchedEntry)}`);
      }
      if (job.agentId !== matchedEntry.owner) {
        edits.push(`owner ${job.agentId} → ${matchedEntry.owner}`);
      }

      if (edits.length > 0) {
        operations.push({
          kind: "edit",
          stableName: matchedStableName!,
          jobId: job.id ?? undefined,
          summary: `Job "${job.name}" needs update: ${edits.join("; ")}`,
          entry: matchedEntry,
        });
      } else {
        operations.push({
          kind: "no-op",
          stableName: matchedStableName!,
          jobId: job.id ?? undefined,
          summary: `Job "${job.name}" unchanged`,
          entry: matchedEntry,
        });
      }
    }

    // Pass 2: check manifest entries not yet matched → add.
    for (const entry of manifest.automations) {
      if (!matchedJobIds.has(entry.stableName)) {
        operations.push({
          kind: "add",
          stableName: entry.stableName,
          summary: `Manifest entry "${entry.stableName}" has no matching job — propose add`,
          entry,
        });
      }
    }

    return {
      dryRun: this.dryRun,
      manifestVersion: manifest.version,
      manifestUpdatedAt: manifest.updatedAt,
      operations,
      unchangedCount: operations.filter((o) => o.kind === "no-op").length,
    };
  }
}
