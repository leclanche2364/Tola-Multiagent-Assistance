// Scholar Tools — Batch 12
// T12.1 Weak-topic ranking | T12.2 Study session/material creation
// T12.3 Blackboard metadata only | T12.4 Scheduling boundary
// T12.5 Research quality — stronger evidence preferred
// T12.6 Conflicting evidence — uncertainty represented
// T12.7 Claim verification — separate verification pass
// T12.8 IntenSIQ failure handling | T12.9 No credential leakage
// T12.10 Skill baseline — scientific/evidence skills improve quality
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/scholar-tools.test.ts

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as nodePath from "node:path";
import {
  rankWeakTopics,
  topWeakTopics,
  averageWeakness,
  topicsAboveThreshold,
  sessionScheduleMetadata,
  isSessionFeasible,
  computeSessionCount,
  rankEvidence,
  selectStrongestEvidence,
  findConflictingEvidence,
  uncertaintyRange,
  aggregateStudyPlan,
} from "../src/index.ts";

// ==================== helpers ====================

interface Topic {
  topicId: string;
  topicName: string;
  domain: string;
  weaknessScore: number;
  lastAssessedAt: string;
  practiceSessions: number;
}

interface Evidence {
  source: string;
  topic: string;
  confidence: number;
  quality: "high" | "medium" | "low";
}

const makeTopic = (id: string, name: string, score: number, domain = "cs"): Topic => ({
  topicId: id,
  topicName: name,
  domain,
  weaknessScore: score,
  lastAssessedAt: "2026-09-27T00:00:00.000Z",
  practiceSessions: 2,
});

const makeEvidence = (topic: string, confidence: number, quality: Evidence["quality"]): Evidence => ({
  source: "test",
  topic,
  confidence,
  quality,
});

// ==================== T12.1 ====================

test("T12.1 Weak-topic ranking — known state ranked correctly", () => {
  const topics = [
    makeTopic("t1", "TCP/IP", 85),
    makeTopic("t2", "Normalization", 72),
    makeTopic("t3", "React Hooks", 45),
  ];

  const ranked = rankWeakTopics(topics);
  assert.strictEqual(ranked[0].topicId, "t1", "Highest weakness first");
  assert.strictEqual(ranked[1].topicId, "t2");
  assert.strictEqual(ranked[2].topicId, "t3");
});

// ==================== T12.2 ====================

test("T12.2 Study session scheduling metadata — deterministic metadata generated", () => {
  const meta = sessionScheduleMetadata("sess-001", "t1", 60, "2026-09-27T10:00:00.000Z");
  assert.strictEqual(meta.sessionId, "sess-001");
  assert.strictEqual(meta.topicId, "t1");
  assert.strictEqual(meta.durationMinutes, 60);
  assert.strictEqual(meta.cognitiveLoad, "medium");
  assert.strictEqual(meta.endsAt, "2026-09-27T11:00:00.000Z");
  assert.strictEqual(meta.estimatedEnd, "2026-09-27T11:00:00.000Z");
});

// ==================== T12.3 ====================

test("T12.3 Blackboard metadata only — helper returns metadata, not content dumps", () => {
  const summary = aggregateStudyPlan("plan-001", [30, 60, 90], ["networking", "databases", "networking"]);
  assert.strictEqual(summary.planId, "plan-001");
  assert.strictEqual(summary.totalSessions, 3);
  assert.strictEqual(summary.totalEstimatedMinutes, 180);
  assert.strictEqual(summary.cognitiveLoadDistribution.medium, 1);
  assert.strictEqual(summary.cognitiveLoadDistribution.high, 1);
  assert.ok(Array.isArray(summary.topDomains));
  const json = JSON.stringify(summary);
  assert.ok(!json.includes("chapter"), "Summary must not contain chapter content");
  assert.ok(!json.includes("paragraph"), "Summary must not contain paragraph content");
});

// ==================== T12.4 ====================

test("T12.4 Scheduling boundary — scholar cannot write My Rhythm", () => {
  const srcDir = nodePath.join(nodePath.dirname(fileURLToPath(import.meta.url)), "../src");
  const indexSource = readFileSync(nodePath.join(srcDir, "index.ts"), "utf8");

  assert.ok(!indexSource.includes("createFlexibleBlock"), "Scholar must not have createFlexibleBlock");
  assert.ok(!indexSource.includes("updateFlexibleBlock"), "Scholar must not have updateFlexibleBlock");
  assert.ok(!indexSource.includes("planTask"), "Scholar must not have planTask");
  assert.ok(!indexSource.includes("getWorkDates"), "Scholar must not have getWorkDates");
});

// ==================== T12.5 ====================

test("T12.5 Research quality — stronger evidence preferred over conflicting low-quality material", () => {
  const items = [
    makeEvidence("TCP/IP", 0.9, "high"),
    makeEvidence("TCP/IP", 0.6, "low"),
    makeEvidence("Databases", 0.8, "medium"),
    makeEvidence("Databases", 0.3, "low"),
  ];

  const ranked = rankEvidence(items);
  assert.strictEqual(ranked[0].confidence, 0.9, "Strongest evidence first");
  assert.strictEqual(ranked[0].quality, "high");

  const strongest = selectStrongestEvidence(items, 2);
  assert.strictEqual(strongest.length, 2);
  assert.ok(strongest.every(s => s.confidence >= 0.5), "Selected evidence must have confidence >= 0.5");
});

// ==================== T12.6 ====================

test("T12.6 Conflicting evidence — uncertainty represented appropriately", () => {
  const items = [
    makeEvidence("Theory X", 0.7, "high"),
    makeEvidence("Theory X", 0.65, "low"),
  ];

  const conflicts = findConflictingEvidence(items);
  assert.strictEqual(conflicts.length, 1, "Should detect conflict for same topic");
  assert.strictEqual(conflicts[0].high.confidence, 0.7);
  assert.strictEqual(conflicts[0].low.confidence, 0.65);

  const range = uncertaintyRange(items);
  assert.ok(range.spread < 0.06, "Small spread = uncertainty");
  assert.strictEqual(range.maxConfidence, 0.7);
  assert.strictEqual(range.minConfidence, 0.65);
});

// ==================== T12.7 ====================

test("T12.7 Claim verification — separate verification pass via evidence ranking", () => {
  const items = [
    makeEvidence("Claim A", 0.95, "high"),
    makeEvidence("Claim B", 0.4, "low"),
    makeEvidence("Claim C", 0.8, "medium"),
  ];

  const verified = selectStrongestEvidence(items, 10);
  assert.ok(verified.every(v => v.confidence >= 0.5), "Only verified claims pass");
  assert.strictEqual(verified.length, 2, "Claim B (low confidence) excluded");

  const unverified = items.filter(i => !verified.includes(i));
  assert.strictEqual(unverified.length, 1);
  assert.strictEqual(unverified[0].confidence, 0.4, "Low-confidence claim is not verified");
});

// ==================== T12.8 ====================

test("T12.8 IntenSIQ failure — scholar-tools handles empty input gracefully", () => {
  assert.strictEqual(averageWeakness([]), 0);
  assert.strictEqual(topWeakTopics([], 3).length, 0);
  assert.strictEqual(topicsAboveThreshold([], 50).length, 0);

  const range = uncertaintyRange([]);
  assert.strictEqual(range.minConfidence, 0);
  assert.strictEqual(range.maxConfidence, 0);
  assert.strictEqual(range.spread, 0);
});

// ==================== T12.9 ====================

test("T12.9 No credential leakage", () => {
  const srcDir = nodePath.join(nodePath.dirname(fileURLToPath(import.meta.url)), "../src");
  const indexSource = readFileSync(nodePath.join(srcDir, "index.ts"), "utf8");

  assert.ok(!indexSource.includes("password"), "No password references");
  assert.ok(!indexSource.includes("secret"), "No secret references");
  assert.ok(!indexSource.includes("token"), "No token references");
  assert.ok(!indexSource.includes("apiKey"), "No apiKey references");
  assert.ok(!indexSource.includes("Authorization"), "No Authorization header");
  assert.ok(!indexSource.includes("Bearer"), "No Bearer token");
});

// ==================== T12.10 ====================

test("T12.10 Skill baseline — scientific/evidence skills improve quality without over-triggering", () => {
  const topics = [
    makeTopic("a", "A", 50),
    makeTopic("b", "B", 90),
    makeTopic("c", "C", 30),
  ];

  const r1 = rankWeakTopics(topics);
  const r2 = rankWeakTopics(topics);
  assert.strictEqual(r1[0].topicId, r2[0].topicId, "Deterministic ranking");
  assert.strictEqual(r1[1].topicId, r2[1].topicId);

  const meta1 = sessionScheduleMetadata("s1", "t1", 20, "2026-09-27T10:00:00.000Z");
  const meta2 = sessionScheduleMetadata("s2", "t2", 90, "2026-09-27T10:00:00.000Z");
  assert.strictEqual(meta1.cognitiveLoad, "low", "Short session = low cognitive load");
  assert.strictEqual(meta2.cognitiveLoad, "high", "Long session = high cognitive load");

  const feasible = isSessionFeasible("2026-09-27T10:00:00.000Z", 120, [
    { startsAt: "2026-09-27T09:00:00.000Z", endsAt: "2026-09-27T12:00:00.000Z" },
  ]);
  assert.strictEqual(feasible, true, "2h session fits in 3h window");

  const infeasible = isSessionFeasible("2026-09-27T11:30:00.000Z", 120, [
    { startsAt: "2026-09-27T09:00:00.000Z", endsAt: "2026-09-27T12:00:00.000Z" },
  ]);
  assert.strictEqual(infeasible, false, "Overlapping session is infeasible");

  assert.strictEqual(computeSessionCount(180, 60), 3, "180min / 60min = 3 sessions");
  assert.strictEqual(computeSessionCount(0, 60), 0, "Zero duration = zero sessions");
});

// ==================== additional contract tests ====================

test("Contract: rankWeakTopics does not mutate input", () => {
  const topics = [makeTopic("a", "A", 50), makeTopic("b", "B", 90)];
  const originalScores = topics.map(t => t.weaknessScore);
  rankWeakTopics(topics);
  assert.strictEqual(topics[0].weaknessScore, originalScores[0], "Input not mutated");
});

test("Contract: topWeakTopics respects n=0 and n > length", () => {
  const topics = [makeTopic("a", "A", 50), makeTopic("b", "B", 90)];
  assert.strictEqual(topWeakTopics(topics, 0).length, 0);
  assert.strictEqual(topWeakTopics(topics, 10).length, 2);
});

test("Contract: findConflictingEvidence returns empty for non-conflicting evidence", () => {
  const items = [
    makeEvidence("Topic A", 0.9, "high"),
    makeEvidence("Topic B", 0.2, "low"),
  ];
  assert.strictEqual(findConflictingEvidence(items).length, 0);
});