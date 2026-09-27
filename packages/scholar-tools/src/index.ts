/**
 * Scholar Tools — deterministic helper functions (Batch 12).
 *
 * Pure functions for weak-topic ranking, session scheduling metadata,
 * and evidence aggregation. Aggregation happens BEFORE any model call.
 */

// ======================== types ========================

export interface WeakTopic {
  topicId: string;
  topicName: string;
  domain: string;
  weaknessScore: number; // 0-100, higher = weaker
  lastAssessedAt: string;
  practiceSessions: number;
}

export interface SessionScheduleMetadata {
  sessionId: string;
  topicId: string;
  durationMinutes: number;
  startsAt: string;
  endsAt: string;
  estimatedEnd: string;
  cognitiveLoad: "low" | "medium" | "high";
}

export interface EvidenceItem {
  source: string;
  topic: string;
  confidence: number; // 0-1
  quality: "high" | "medium" | "low";
}

// ======================== weak-topic ranking ========================

/** Rank weak topics by weaknessScore descending. Pure/deterministic. */
export function rankWeakTopics(topics: WeakTopic[]): WeakTopic[] {
  return [...topics].sort((a, b) => b.weaknessScore - a.weaknessScore);
}

/** Select the top N weakest topics. Pure/deterministic. */
export function topWeakTopics(topics: WeakTopic[], n: number): WeakTopic[] {
  return rankWeakTopics(topics).slice(0, Math.max(0, n));
}

/** Compute the average weakness score across topics. Pure/deterministic. */
export function averageWeakness(topics: WeakTopic[]): number {
  if (topics.length === 0) return 0;
  return topics.reduce((s, t) => s + t.weaknessScore, 0) / topics.length;
}

/** Identify topics above a weakness threshold. Pure/deterministic. */
export function topicsAboveThreshold(topics: WeakTopic[], threshold: number): WeakTopic[] {
  return topics.filter(t => t.weaknessScore >= threshold);
}

// ======================== session scheduling metadata ========================

/** Generate scheduling metadata for a session block. Pure/deterministic. */
export function sessionScheduleMetadata(
  sessionId: string,
  topicId: string,
  durationMinutes: number,
  startsAt: string,
): SessionScheduleMetadata {
  const endsAt = new Date(new Date(startsAt).getTime() + durationMinutes * 60_000).toISOString();
  return {
    sessionId,
    topicId,
    durationMinutes,
    startsAt,
    endsAt,
    estimatedEnd: endsAt,
    cognitiveLoad: durationMinutes <= 30 ? "low" : durationMinutes <= 60 ? "medium" : "high",
  };
}

/** Check if a session fits within available windows. Pure/deterministic. */
export function isSessionFeasible(
  startsAt: string,
  durationMinutes: number,
  availableWindows: Array<{ startsAt: string; endsAt: string }>,
): boolean {
  const sessionEnd = new Date(new Date(startsAt).getTime() + durationMinutes * 60_000).getTime();
  return availableWindows.some(w => {
    const winStart = new Date(w.startsAt).getTime();
    const winEnd = new Date(w.endsAt).getTime();
    return new Date(startsAt).getTime() >= winStart && sessionEnd <= winEnd;
  });
}

/** Compute the number of sessions needed for a given total duration. Pure/deterministic. */
export function computeSessionCount(totalMinutes: number, maxSessionMinutes: number): number {
  if (maxSessionMinutes <= 0) return 0;
  return Math.ceil(totalMinutes / maxSessionMinutes);
}

// ======================== evidence aggregation ========================

const qualityWeight = { high: 3, medium: 2, low: 1 };

/** Rank evidence by confidence and quality. Stronger evidence first. Pure/deterministic. */
export function rankEvidence(items: EvidenceItem[]): EvidenceItem[] {
  return [...items].sort((a, b) => {
    const aScore = a.confidence * qualityWeight[a.quality];
    const bScore = b.confidence * qualityWeight[b.quality];
    return bScore - aScore;
  });
}

/** Select strongest evidence items, excluding conflicting low-quality material. Pure/deterministic. */
export function selectStrongestEvidence(
  items: EvidenceItem[],
  maxItems: number,
): EvidenceItem[] {
  const ranked = rankEvidence(items);
  return ranked.slice(0, Math.max(0, maxItems)).filter(item => item.confidence >= 0.5);
}

/** Identify conflicting evidence where confidence overlaps but quality differs. Pure/deterministic. */
export function findConflictingEvidence(items: EvidenceItem[]): Array<{ high: EvidenceItem; low: EvidenceItem }> {
  const conflicts: Array<{ high: EvidenceItem; low: EvidenceItem }> = [];
  const highQuality = items.filter(i => i.quality === "high");
  const lowQuality = items.filter(i => i.quality === "low");

  for (const h of highQuality) {
    for (const l of lowQuality) {
      if (h.topic === l.topic && Math.abs(h.confidence - l.confidence) < 0.3) {
        conflicts.push({ high: h, low: l });
      }
    }
  }
  return conflicts;
}

/** Represent uncertainty: return confidence range instead of a single value. Pure/deterministic. */
export function uncertaintyRange(items: EvidenceItem[]): { minConfidence: number; maxConfidence: number; spread: number } {
  if (items.length === 0) return { minConfidence: 0, maxConfidence: 0, spread: 0 };
  const confidences = items.map(i => i.confidence);
  const min = Math.min(...confidences);
  const max = Math.max(...confidences);
  return { minConfidence: min, maxConfidence: max, spread: max - min };
}

// ======================== study plan aggregation ========================

export interface StudyPlanSummary {
  planId: string;
  totalSessions: number;
  totalEstimatedMinutes: number;
  cognitiveLoadDistribution: { low: number; medium: number; high: number };
  topDomains: string[];
}

/** Aggregate study plan metadata into a compact summary. Pure/deterministic. */
export function aggregateStudyPlan(
  planId: string,
  sessionDurations: number[],
  domains: string[],
): StudyPlanSummary {
  const cognitiveLoadDistribution = { low: 0, medium: 0, high: 0 };
  for (const dur of sessionDurations) {
    if (dur <= 30) cognitiveLoadDistribution.low++;
    else if (dur <= 60) cognitiveLoadDistribution.medium++;
    else cognitiveLoadDistribution.high++;
  }

  const domainCounts = new Map<string, number>();
  for (const d of domains) {
    domainCounts.set(d, (domainCounts.get(d) ?? 0) + 1);
  }
  const topDomains = Array.from(domainCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([d]) => d);

  return {
    planId,
    totalSessions: sessionDurations.length,
    totalEstimatedMinutes: sessionDurations.reduce((s, d) => s + d, 0),
    cognitiveLoadDistribution,
    topDomains,
  };
}

// ======================== quarantined skill manifests ========================

export * from "./skills.ts";
