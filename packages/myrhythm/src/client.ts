/**
 * My Rhythm typed client — Batch 10.
 *
 * Provides typed operations over a pluggable transport (interface + in-memory mock).
 * All time arithmetic and conflict checks are deterministic pure functions.
 */

// ---------- types ----------

export interface WorkDate {
  date: string; // ISO-8601 date
  label: string;
  available: boolean;
}

export interface PlanEntry {
  id: string;
  title: string;
  startsAt: string; // ISO-8601 datetime
  endsAt: string;   // ISO-8601 datetime
  type: "flexible-block" | "deep-work" | "recovery";
  projectId?: string;
}

export interface CurrentPlan {
  planDate: string;
  entries: PlanEntry[];
}

export interface AvailableWindow {
  startsAt: string;
  endsAt: string;
  constraints: string[];
}

export interface Constraints {
  maxBlocksPerDay: number;
  requiresRecoveryBuffer: boolean;
  postShiftRecoveryWindow: { startsAt: string; endsAt: string };
}

export interface FlexibleBlock {
  id: string;
  title: string;
  startsAt: string;
  endsAt: string;
  projectId: string;
  createdAt: string;
}

export interface ConflictResult {
  hasConflict: boolean;
  conflictingEntries: PlanEntry[];
}

export interface PlannerProposal {
  date: string;
  block: FlexibleBlock;
  reasoning: string;
}

export interface AuditRecord {
  action: string;
  targetId: string;
  timestamp: string;
  reversible: boolean;
}

// ---------- transport interface ----------

export interface MyRhythmTransport {
  getWorkDates(): Promise<WorkDate[]>;
  getCurrentPlan(): Promise<CurrentPlan>;
  getAvailableWindows(): Promise<{ windows: AvailableWindow[]; constraints: Constraints }>;
  checkConflict(block: Partial<FlexibleBlock>): Promise<ConflictResult>;
  createFlexibleBlock(block: Omit<FlexibleBlock, "id" | "createdAt">): Promise<{ block: FlexibleBlock; audit: AuditRecord }>;
  updateFlexibleBlock(id: string, patch: Partial<FlexibleBlock>): Promise<{ block: FlexibleBlock; audit: AuditRecord }>;
  removeFlexibleBlock(id: string): Promise<{ removed: boolean; audit: AuditRecord }>;
}

// ---------- deterministic time helpers ----------

/** Parse an ISO datetime to milliseconds since epoch. Pure/deterministic. */
function parseMs(iso: string): number {
  return new Date(iso).getTime();
}

/** Add minutes to an ISO datetime string. Pure/deterministic. */
export function addMinutes(iso: string, minutes: number): string {
  return new Date(parseMs(iso) + minutes * 60_000).toISOString();
}

/** Subtract minutes from an ISO datetime string. Pure/deterministic. */
export function subMinutes(iso: string, minutes: number): string {
  return new Date(parseMs(iso) - minutes * 60_000).toISOString();
}

/** Check if two time ranges overlap. Pure/deterministic. */
export function rangesOverlap(
  aStart: string, aEnd: string,
  bStart: string, bEnd: string,
): boolean {
  return parseMs(aStart) < parseMs(bEnd) && parseMs(bEnd) > parseMs(aStart) && parseMs(bStart) < parseMs(aEnd);
}

/** Check if a datetime falls within a window. Pure/deterministic. */
export function fallsWithin(dt: string, start: string, end: string): boolean {
  return parseMs(dt) >= parseMs(start) && parseMs(dt) <= parseMs(end);
}

/** Duration in minutes between two ISO datetimes. Pure/deterministic. */
export function durationMinutes(start: string, end: string): number {
  return (parseMs(end) - parseMs(start)) / 60_000;
}

// ---------- in-memory mock transport ----------

export class InMemoryMyRhythmTransport implements MyRhythmTransport {
  private blocks: FlexibleBlock[] = [];
  private workDates: WorkDate[] = [];
  private plan: CurrentPlan = { planDate: "", entries: [] };
  private auditLog: AuditRecord[] = [];

  constructor(opts?: { workDates?: WorkDate[]; plan?: CurrentPlan; blocks?: FlexibleBlock[] }) {
    this.workDates = opts?.workDates ?? [];
    this.plan = opts?.plan ?? { planDate: "", entries: [] };
    this.blocks = opts?.blocks ?? [];
  }

  get auditLog(): readonly AuditRecord[] {
    return this.auditLog;
  }

  get blocks(): readonly FlexibleBlock[] {
    return this.blocks;
  }

  async getWorkDates(): Promise<WorkDate[]> {
    return [...this.workDates];
  }

  async getCurrentPlan(): Promise<CurrentPlan> {
    return { ...this.plan, entries: [...this.plan.entries] };
  }

  async getAvailableWindows(): Promise<{ windows: AvailableWindow[]; constraints: Constraints }> {
    const constraints: Constraints = {
      maxBlocksPerDay: 6,
      requiresRecoveryBuffer: true,
      postShiftRecoveryWindow: { startsAt: "2025-01-01T07:00:00.000Z", endsAt: "2025-01-01T09:00:00.000Z" },
    };
    const windows: AvailableWindow[] = [
      { startsAt: "2025-01-01T09:00:00.000Z", endsAt: "2025-01-01T12:00:00.000Z", constraints: ["morning-block"] },
      { startsAt: "2025-01-01T13:00:00.000Z", endsAt: "2025-01-01T17:00:00.000Z", constraints: ["afternoon-block"] },
    ];
    return { windows, constraints };
  }

  async checkConflict(block: Partial<FlexibleBlock>): Promise<ConflictResult> {
    const conflicting: PlanEntry[] = [];
    for (const entry of this.plan.entries) {
      if (block.startsAt && block.endsAt && rangesOverlap(block.startsAt, block.endsAt, entry.startsAt, entry.endsAt)) {
        conflicting.push(entry);
      }
    }
    return { hasConflict: conflicting.length > 0, conflictingEntries: conflicting };
  }

  async createFlexibleBlock(block: Omit<FlexibleBlock, "id" | "createdAt">): Promise<{ block: FlexibleBlock; audit: AuditRecord }> {
    const id = crypto.randomUUID();
    const createdAt = new Date().toISOString();
    const full: FlexibleBlock = { ...block, id, createdAt };
    this.blocks.push(full);
    const audit: AuditRecord = { action: "create", targetId: id, timestamp: createdAt, reversible: true };
    this.auditLog.push(audit);
    return { block: full, audit };
  }

  async updateFlexibleBlock(id: string, patch: Partial<FlexibleBlock>): Promise<{ block: FlexibleBlock; audit: AuditRecord }> {
    const idx = this.blocks.findIndex(b => b.id === id);
    if (idx === -1) throw new Error(`block ${id} not found`);
    this.blocks[idx] = { ...this.blocks[idx], ...patch };
    const timestamp = new Date().toISOString();
    const audit: AuditRecord = { action: "update", targetId: id, timestamp, reversible: true };
    this.auditLog.push(audit);
    return { block: this.blocks[idx], audit };
  }

  async removeFlexibleBlock(id: string): Promise<{ removed: boolean; audit: AuditRecord }> {
    const idx = this.blocks.findIndex(b => b.id === id);
    if (idx === -1) throw new Error(`block ${id} not found`);
    const removed = this.blocks.splice(idx, 1).length === 1;
    const timestamp = new Date().toISOString();
    const audit: AuditRecord = { action: "remove", targetId: id, timestamp, reversible: true };
    this.auditLog.push(audit);
    return { removed, audit };
  }
}
