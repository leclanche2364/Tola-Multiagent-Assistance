/**
 * Cross-Domain Orchestration Policy — Batch 13
 *
 * Implements the three scenarios from the spec:
 *   Scenario A – Weekly planning: Scholar + Rhythm run independently;
 *               only Rhythm writes planning blocks; Tola synthesises.
 *   Scenario B – Growth + scheduling trade-off: evidence + capacity →
 *               coordinator records the trade-off decision.
 *   Scenario C – Parallel delegation: max three concurrent children;
 *               fourth spawn is prevented/queued per policy.
 *
 * All specialists are modelled as deterministic in-memory fakes
 * (no network, no model calls, no OpenClaw API calls).
 */

import { SPAWN_POLICY, checkSpawn } from "./policy.ts";

// ---------- Types ----------

export type AgentId = "rhythm" | "growth" | "scholar";
export type SpecialistId = AgentId | "tola";

export interface TaskRun {
  runId: string;
  taskId: string;
  agentId: AgentId;
  status: "pending" | "running" | "complete" | "blocked" | "cancelled";
  finalState: Record<string, unknown>;
  evidenceRefs: string[];
  spawnedAt: number;
  completedAt: number | null;
}

export interface PlanningBlock {
  author: "rhythm"; // Only Rhythm may write planning blocks
  content: string;
  taskId: string;
}

export interface TradeOffRecord {
  taskId: string;
  growthEvidence: string;
  rhythmCapacity: number;
  decision: string;
  madeBy: "tola";
  timestamp: number;
}

export interface SpecialistResult {
  agentId: AgentId;
  runId: string;
  status: "complete" | "partial" | "blocked";
  output: unknown;
  evidenceRefs: string[];
}

// ---------- In-memory synthetic specialist fakes ----------

/** Deterministic fake specialist — no network, no model calls. */
class SyntheticSpecialist {
  readonly agentId: AgentId;
  private writes: PlanningBlock[] = [];
  private results: Map<string, SpecialistResult> = new Map();

  constructor(agentId: AgentId) {
    this.agentId = agentId;
  }

  /** Scholar: determines what learning matters. */
  scholarLearn(goal: string, runId: string): SpecialistResult {
    const result: SpecialistResult = {
      agentId: "scholar",
      runId,
      status: "complete",
      output: { learningPriority: goal, priorityLevel: "high", method: "structured-study" },
      evidenceRefs: [`evidence:scholar:${runId}`],
    };
    this.results.set(runId, result);
    return result;
  }

  /** Rhythm: determines feasible placement around work/recovery. */
  rhythmPlace(goal: string, runId: string, writeBlock: boolean = true): SpecialistResult {
    const result: SpecialistResult = {
      agentId: "rhythm",
      runId,
      status: "complete",
      output: { feasiblePlacement: true, constraints: ["post-shift-rest"], daySlots: ["morning", "evening"] },
      evidenceRefs: [`evidence:rhythm:${runId}`],
    };
    this.results.set(runId, result);
    // Only Rhythm writes planning blocks
    if (writeBlock) {
      this.writes.push({
        author: "rhythm",
        content: `Planning block for ${goal}`,
        taskId: runId,
      });
    }
    return result;
  }

  /** Growth: identifies highest-value evidence-backed work. */
  growthIdentify(goal: string, runId: string): SpecialistResult {
    const result: SpecialistResult = {
      agentId: "growth",
      runId,
      status: "complete",
      output: { highestValueWork: goal, evidenceBacked: true, priority: "critical" },
      evidenceRefs: [`evidence:growth:${runId}`],
    };
    this.results.set(runId, result);
    return result;
  }

  /** Get all planning block writes (for T13.1 boundary assertion). */
  getWrites(): readonly PlanningBlock[] {
    return this.writes;
  }

  /** Get a result by runId. */
  getResult(runId: string): SpecialistResult | undefined {
    return this.results.get(runId);
  }
}

// ---------- Orchestrator ----------

export class Orchestrator {
  private running: Map<string, TaskRun> = new Map();
  private completed: TaskRun[] = [];
  private queued: string[] = [];
  private planningBlocks: PlanningBlock[] = [];
  private tradeOffs: TradeOffRecord[] = [];
  private specialists: Map<AgentId, SyntheticSpecialist> = new Map();
  private runCounter = 0;

  // Synthetic specialist instances (deterministic fakes)
  private scholarFake: SyntheticSpecialist;
  private rhythmFake: SyntheticSpecialist;
  private growthFake: SyntheticSpecialist;

  constructor() {
    this.scholarFake = new SyntheticSpecialist("scholar");
    this.rhythmFake = new SyntheticSpecialist("rhythm");
    this.growthFake = new SyntheticSpecialist("growth");
    for (const id of ["scholar", "rhythm", "growth"] as AgentId[]) {
      this.specialists.set(id, new SyntheticSpecialist(id));
    }
  }

  /** Get the rhythm specialist for planning-block boundary assertions. */
  getRhythm(): SyntheticSpecialist {
    return this.rhythmFake;
  }

  /** Get the scholar specialist. */
  getScholar(): SyntheticSpecialist {
    return this.scholarFake;
  }

  /** Get the growth specialist. */
  getGrowth(): SyntheticSpecialist {
    return this.growthFake;
  }

  /** Generate a unique run ID. */
  private nextRunId(): string {
    this.runCounter++;
    return `run-${this.runCounter}-${Date.now()}`;
  }

  private nextTaskId(): string {
    return `task-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  // ---------- Scenario A: Weekly Planning ----------
  /**
   * Scholar + Rhythm run independently for weekly planning.
   * Only Rhythm writes planning blocks. Tola synthesises.
   */
  scenarioAWeeklyPlanning(goal: string): { scholarResult: SpecialistResult; rhythmResult: SpecialistResult; planningBlocks: PlanningBlock[]; synthesis: Record<string, unknown> } {
    const taskId = this.nextTaskId();
    const scholarRunId = this.nextRunId();
    const rhythmRunId = this.nextRunId();

    // Check spawn policy for both
    const scholarSpawn = checkSpawn({ agentId: "scholar", depth: 0, activeChildren: this.running.size, runningNow: this.running.size });
    const rhythmSpawn = checkSpawn({ agentId: "rhythm", depth: 0, activeChildren: this.running.size, runningNow: this.running.size });
    if (!scholarSpawn.ok) throw new Error(`Scholar spawn rejected: ${scholarSpawn.message}`);
    if (!rhythmSpawn.ok) throw new Error(`Rhythm spawn rejected: ${rhythmSpawn.message}`);

    // Run independently
    const scholarResult = this.scholarFake.scholarLearn(goal, scholarRunId);
    const rhythmResult = this.rhythmFake.rhythmPlace(goal, rhythmRunId);

    // Record task runs (traceability T13.7)
    this.running.set(scholarRunId, {
      runId: scholarRunId, taskId, agentId: "scholar", status: "complete",
      finalState: scholarResult.output as Record<string, unknown>,
      evidenceRefs: scholarResult.evidenceRefs,
      spawnedAt: Date.now(), completedAt: Date.now(),
    });
    this.running.set(rhythmRunId, {
      runId: rhythmRunId, taskId, agentId: "rhythm", status: "complete",
      finalState: rhythmResult.output as Record<string, unknown>,
      evidenceRefs: rhythmResult.evidenceRefs,
      spawnedAt: Date.now(), completedAt: Date.now(),
    });

    // Only Rhythm's planning blocks are collected
    this.planningBlocks = this.rhythmFake.getWrites();
    this.completed.push(this.running.get(scholarRunId)!);
    this.completed.push(this.running.get(rhythmRunId)!);

    // Tola synthesises
    const synthesis: Record<string, unknown> = {
      goal,
      learningPriority: scholarResult.output.learningPriority,
      feasiblePlacement: rhythmResult.output.feasiblePlacement,
      constraints: rhythmResult.output.constraints,
      synthesisedBy: "tola",
      planningBlockCount: this.planningBlocks.length,
    };

    return { scholarResult, rhythmResult, planningBlocks: this.planningBlocks, synthesis };
  }

  // ---------- Scenario B: Growth + Scheduling Trade-off ----------
  /**
   * Growth identifies evidence-backed work; Rhythm estimates capacity.
   * Coordinator (Tola) records the trade-off decision.
   */
  scenarioBTradeOff(growthGoal: string, availableProjectTime: number): { growthResult: SpecialistResult; rhythmResult: SpecialistResult; tradeOff: TradeOffRecord } {
    const taskId = this.nextTaskId();
    const growthRunId = this.nextRunId();
    const rhythmRunId = this.nextRunId();

    const growthSpawn = checkSpawn({ agentId: "growth", depth: 0, activeChildren: this.running.size, runningNow: this.running.size });
    const rhythmSpawn = checkSpawn({ agentId: "rhythm", depth: 0, activeChildren: this.running.size, runningNow: this.running.size });
    if (!growthSpawn.ok) throw new Error(`Growth spawn rejected: ${growthSpawn.message}`);
    if (!rhythmSpawn.ok) throw new Error(`Rhythm spawn rejected: ${rhythmSpawn.message}`);

    const growthResult = this.growthFake.growthIdentify(growthGoal, growthRunId);
    const rhythmResult = this.rhythmFake.rhythmPlace(growthGoal, rhythmRunId, false); // no planning block here

    // Growth evidence priority vs Rhythm capacity
    const rhythmCapacity = rhythmResult.output.daySlots.length * availableProjectTime;
    const growthEvidence = growthResult.output.highestValueWork;

    // Tola records the trade-off decision
    const tradeOff: TradeOffRecord = {
      taskId,
      growthEvidence,
      rhythmCapacity,
      decision: rhythmCapacity >= growthResult.output.priority === "critical" ? "accept" : "defer",
      madeBy: "tola",
      timestamp: Date.now(),
    };
    this.tradeOffs.push(tradeOff);

    // Record runs for traceability
    this.running.set(growthRunId, {
      runId: growthRunId, taskId, agentId: "growth", status: "complete",
      finalState: growthResult.output as Record<string, unknown>,
      evidenceRefs: growthResult.evidenceRefs,
      spawnedAt: Date.now(), completedAt: Date.now(),
    });
    this.running.set(rhythmRunId, {
      runId: rhythmRunId, taskId, agentId: "rhythm", status: "complete",
      finalState: rhythmResult.output as Record<string, unknown>,
      evidenceRefs: rhythmResult.evidenceRefs,
      spawnedAt: Date.now(), completedAt: Date.now(),
    });
    this.completed.push(this.running.get(growthRunId)!);
    this.completed.push(this.running.get(rhythmRunId)!);

    return { growthResult, rhythmResult, tradeOff };
  }

  // ---------- Scenario C: Parallel Delegation with Concurrency Cap ----------
  /**
   * Try to spawn an agent. Returns ok=true if spawned, ok=false with MAX_CONCURRENT
   * if at the cap (per SPAWN_POLICY.maxConcurrent = 3).
   */
  trySpawn(agentId: AgentId, depth: number = 0, activeChildren: number = 0): { ok: true; runId: string } | { ok: false; code: string; message: string } {
    const result = checkSpawn({ agentId, depth, activeChildren, runningNow: this.running.size });
    if (!result.ok) return { ok: false, code: result.code, message: result.message };
    const runId = this.nextRunId();
    this.running.set(runId, {
      runId, taskId: this.nextTaskId(), agentId: agentId,
      status: "running",
      finalState: {},
      evidenceRefs: [],
      spawnedAt: Date.now(),
      completedAt: null,
    });
    return { ok: true, runId };
  }

  /** Mark a run as complete. */
  completeRun(runId: string): void {
    const run = this.running.get(runId);
    if (run) {
      run.status = "complete";
      run.completedAt = Date.now();
      this.completed.push(run);
      this.running.delete(runId);
    }
  }

  /** Queue a spawn request when at capacity. */
  queueSpawn(agentId: AgentId): void {
    this.queued.push(`${agentId}-${Date.now()}`);
  }

  /** Get current running count. */
  getRunningCount(): number {
    return this.running.size;
  }

  /** Get queued count. */
  getQueuedCount(): number {
    return this.queued.length;
  }

  /** Get all completed runs (traceability T13.7). */
  getCompletedRuns(): readonly TaskRun[] {
    return this.completed;
  }

  /** Get all planning blocks. */
  getPlanningBlocks(): readonly PlanningBlock[] {
    return this.planningBlocks;
  }

  /** Get all trade-off records. */
  getTradeOffs(): readonly TradeOffRecord[] {
    return this.tradeOffs;
  }

  /** Get a task run by runId for traceability. */
  getRun(runId: string): TaskRun | undefined {
    return this.running.get(runId) ?? this.completed.find(r => r.runId === runId);
  }
}

// ---------- Convenience: check if a request is within the correct domain ----------
export function checkDomain(agentId: string, requestedDomain: string): { allowed: boolean; reason?: string } {
  const domainMap: Record<string, string[]> = {
    rhythm: ["schedule", "planning", "placement"],
    growth: ["growth", "analytics", "seo", "metrics"],
    scholar: ["learning", "study", "education", "reading"],
  };
  const allowed = domainMap[agentId]?.includes(requestedDomain) ?? false;
  if (!allowed) {
    return { allowed: false, reason: `${agentId} cannot act as ${requestedDomain}; request redirected to appropriate domain or requirement returned` };
  }
  return { allowed: true };
}

// ---------- T13.5: Specialist chat isolation ----------
/**
 * Determines whether a specialist transcript should be auto-exposed to Tola.
 * Unrelated specialists' transcripts are NOT auto-exposed.
 */
export function isTranscriptExposed(agentId: AgentId, isRelated: boolean): boolean {
  return isRelated;
}
