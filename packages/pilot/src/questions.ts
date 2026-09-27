/**
 * Pilot questions — Batch 16 spec §9.4.
 *
 * These are typed review prompts with answer enums and evidence refs.
 * This module is data, not logic — no computation, no side effects.
 */

/** Answer options for each pilot question */
export type PilotAnswer = "yes" | "partially" | "no";

/** Evidence reference — points to a data source or log */
export type EvidenceRef = string;

/** A single pilot question with its answer enum and evidence refs */
export type PilotQuestion = {
  /** Question number (1–11) */
  id: number;
  /** The question text */
  text: string;
  /** Which agent(s) the question targets */
  targetAgent: "tola" | "rhythm" | "growth" | "scholar" | "system";
  /** Possible answers */
  answerEnum: [PilotAnswer, PilotAnswer, PilotAnswer];
  /** Evidence references the responder must cite */
  evidenceRefs: EvidenceRef[];
};

/** The 11 pilot questions from the Batch 16 spec. */
export const PILOT_QUESTIONS: PilotQuestion[] = [
  {
    id: 1,
    text: "Does Tola reduce manual coordination?",
    targetAgent: "tola",
    answerEnum: ["yes", "partially", "no"],
    evidenceRefs: ["task-runs/weekly", "manual-reroutes/daily", "agent-events/tola"],
  },
  {
    id: 2,
    text: "Does Rhythm reduce planning effort without over-scheduling?",
    targetAgent: "rhythm",
    answerEnum: ["yes", "partially", "no"],
    evidenceRefs: ["schedule-constraints/weekly", "planning-effort/metrics", "over-schedule-count"],
  },
  {
    id: 3,
    text: "Does Rhythm respect recovery?",
    targetAgent: "rhythm",
    answerEnum: ["yes", "partially", "no"],
    evidenceRefs: ["recovery-blocks/daily", "shift-overlap-logs", "agent-events/rhythm"],
  },
  {
    id: 4,
    text: "Does Growth surface material information rather than generic marketing advice?",
    targetAgent: "growth",
    answerEnum: ["yes", "partially", "no"],
    evidenceRefs: ["growth-insights/weekly", "advice-classification/log", "user-feedback/growth"],
  },
  {
    id: 5,
    text: "Does Scholar materially improve IntenSIQ learning?",
    targetAgent: "scholar",
    answerEnum: ["yes", "partially", "no"],
    evidenceRefs: ["scholar-content/weekly", "intensiq-learning-metrics", "content-acceptance/log"],
  },
  {
    id: 6,
    text: "Are external Skills improving outcomes?",
    targetAgent: "system",
    answerEnum: ["yes", "partially", "no"],
    evidenceRefs: ["skill-outcomes/weekly", "external-skill-execution/log", "outcome-comparison/baseline"],
  },
  {
    id: 7,
    text: "Which Skills should be removed?",
    targetAgent: "system",
    answerEnum: ["yes", "partially", "no"],
    evidenceRefs: ["skill-usage/stats", "skill-performance/metrics", "governance-review/log"],
  },
  {
    id: 8,
    text: "Is self-learning producing useful proposals or noise?",
    targetAgent: "system",
    answerEnum: ["yes", "partially", "no"],
    evidenceRefs: ["skill-proposals/weekly", "proposal-quality/score", "noise-ratio/metrics"],
  },
  {
    id: 9,
    text: "Are model routes economical and reliable?",
    targetAgent: "system",
    answerEnum: ["yes", "partially", "no"],
    evidenceRefs: ["model-runs/weekly", "cost-per-task/metrics", "route-reliability/stats"],
  },
  {
    id: 10,
    text: "Are approvals concentrated at the right boundaries?",
    targetAgent: "system",
    answerEnum: ["yes", "partially", "no"],
    evidenceRefs: ["approval-log/weekly", "approval-boundary/analysis", "concentration-metrics"],
  },
  {
    id: 11,
    text: "What measured bottleneck would a fifth agent solve?",
    targetAgent: "system",
    answerEnum: ["yes", "partially", "no"],
    evidenceRefs: ["bottleneck-analysis/weekly", "agent-capacity/metrics", "queue-depth/stats"],
  },
];
