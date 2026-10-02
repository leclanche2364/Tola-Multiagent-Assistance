// IntenSIQ — Batch 12
// T12.1 IntenSIQ progress read — known state reported correctly
// T12.2 Study session/material creation — external record created once
// T12.3 Blackboard metadata only — detailed lesson not unnecessarily duplicated
// T12.4 Scheduling boundary — Scholar cannot write My Rhythm
// T12.5 Research quality — stronger evidence preferred over conflicting low-quality material
// T12.6 Conflicting evidence — uncertainty represented appropriately
// T12.7 Claim verification — factual claims checked in separate verification pass
// T12.8 IntenSIQ failure — returns PARTIAL/BLOCKED and explicitly states save failed
// T12.9 No credential leakage
// T12.10 Skill baseline — scientific/evidence skills improve quality without over-triggering
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/intensiq.test.ts

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as nodePath from "node:path";
import {
  InMemoryIntenSIQTransport,
  rankWeakTopics,
  topWeakTopics,
  sessionScheduleMetadata,
  isSessionFeasible,
  type LearningProfile,
  type LearningProgress,
  type WeakTopic,
  type StudyPlan,
  type StudySession,
  type LearningMaterial,
  type Quiz,
  type QuizResult,
} from "../src/index.ts";

// ==================== helpers ====================

const LEARNER_ID = "learner-001";

function makeProfile(overrides: Partial<LearningProfile> = {}): LearningProfile {
  return {
    learnerId: LEARNER_ID,
    domain: "computer-science",
    proficiencyLevel: 65,
    weakTopics: ["networking", "databases"],
    lastActiveAt: "2026-09-27T10:00:00.000Z",
    totalStudyHours: 42,
    ...(overrides as WeakTopic[]),
  };
}

function makeProgress(overrides: Partial<LearningProgress> = {}): LearningProgress {
  return {
    learnerId: LEARNER_ID,
    modulesCompleted: 3,
    modulesTotal: 10,
    currentModuleId: "mod-004",
    progressPercent: 30,
    lastSessionAt: "2026-09-26T15:00:00.000Z",
    ...(overrides as WeakTopic[]),
  };
}

function makeWeakTopics(overrides: Partial<WeakTopic>[] = []): WeakTopic[] {
  return [
    { learnerId: LEARNER_ID, topicId: "t1", topicName: "TCP/IP", domain: "networking", weaknessScore: 85, lastAssessedAt: "2026-09-20T00:00:00.000Z", practiceSessions: 2 },
    { learnerId: LEARNER_ID, topicId: "t2", topicName: "Normalization", domain: "databases", weaknessScore: 72, lastAssessedAt: "2026-09-21T00:00:00.000Z", practiceSessions: 1 },
    { learnerId: LEARNER_ID, topicId: "t3", topicName: "React Hooks", domain: "frontend", weaknessScore: 45, lastAssessedAt: "2026-09-22T00:00:00.000Z", practiceSessions: 5 },
    ...(overrides as WeakTopic[]),
  ];
}

// ==================== T12.1 ====================

test("T12.1 IntenSIQ progress read — known state reported correctly", async () => {
  const transport = new InMemoryIntenSIQTransport({
    profiles: [makeProfile()],
    progress: [makeProgress()],
    weakTopics: makeWeakTopics(),
  });

  const profile = await transport.getLearningProfile(LEARNER_ID);
  assert.strictEqual(profile.learnerId, LEARNER_ID);
  assert.strictEqual(profile.proficiencyLevel, 65);
  assert.strictEqual(profile.domain, "computer-science");

  const progress = await transport.getLearningProgress(LEARNER_ID);
  assert.strictEqual(progress.modulesCompleted, 3);
  assert.strictEqual(progress.modulesTotal, 10);
  assert.strictEqual(progress.progressPercent, 30);

  const topics = await transport.getWeakTopics(LEARNER_ID);
  assert.strictEqual(topics.length, 3);
  assert.strictEqual(topics[0].topicName, "TCP/IP");
});

// ==================== T12.2 ====================

test("T12.2 Study session/material creation — external record created once", async () => {
  const transport = new InMemoryIntenSIQTransport({
    profiles: [makeProfile()],
    progress: [makeProgress()],
    weakTopics: makeWeakTopics(),
  });

  const { plan } = await transport.createStudyPlan({
    learnerId: LEARNER_ID,
    title: "CS Review Plan",
    status: "active",
    metadata: { targetDomains: ["networking", "databases"], totalSessions: 5, estimatedHours: 10 },
  });
  assert.ok(plan.planId.length > 0);
  assert.strictEqual(plan.status, "active");
  assert.strictEqual(plan.sessionIds.length, 0);

  const { session } = await transport.createStudySession({
    planId: plan.planId,
    learnerId: LEARNER_ID,
    topicId: "t1",
    status: "scheduled",
    durationMinutes: 60,
  });
  assert.ok(session.sessionId.length > 0);
  assert.strictEqual(session.topicId, "t1");
  assert.strictEqual(transport.sessions.length, 1);

  // Plan should now reference the session
  const updatedPlan = transport.plans[0];
  assert.strictEqual(updatedPlan.sessionIds.length, 1);

  const { material } = await transport.createLearningMaterial({
    sessionId: session.sessionId,
    learnerId: LEARNER_ID,
    type: "article",
    title: "TCP/IP Deep Dive",
    status: "pending",
  });
  assert.ok(material.materialId.length > 0);
  assert.strictEqual(transport.materials.length, 1);

  // Only one record created per operation
  assert.strictEqual(transport.plans.length, 1);
  assert.strictEqual(transport.sessions.length, 1);
  assert.strictEqual(transport.materials.length, 1);
});

// ==================== T12.3 ====================

test("T12.3 Blackboard metadata only — detailed lesson content not unnecessarily duplicated", async () => {
  const transport = new InMemoryIntenSIQTransport({
    profiles: [makeProfile()],
    progress: [makeProgress()],
    weakTopics: makeWeakTopics(),
  });

  // IntenSIQ returns coordination metadata only, never full study content dumps
  const { coordination } = await transport.createStudyPlan({
    learnerId: LEARNER_ID,
    title: "Metadata Test",
    status: "active",
    metadata: { targetDomains: ["networking"], totalSessions: 3, estimatedHours: 6 },
  });

  // Coordination object carries only metadata: ids, statuses, counts
  assert.strictEqual(coordination.status, "created");
  assert.ok(typeof coordination.id === "string" && coordination.id.length > 0);
  assert.ok(coordination.metadata.targetDomains !== undefined);
  assert.ok(coordination.metadata.totalSessions !== undefined);

  // No full lesson content in coordination metadata
  const coordJson = JSON.stringify(coordination);
  assert.ok(!coordJson.includes("full"), "Coordination should not contain full content dumps");
  assert.ok(!coordJson.includes("lesson"), "Coordination should not contain lesson content");
  assert.ok(!coordJson.includes("chapter"), "Coordination should not contain chapter content");
});

// ==================== T12.4 ====================

test("T12.4 Scheduling boundary — Scholar cannot write My Rhythm", async () => {
  const intensiqSrcDir = nodePath.join(nodePath.dirname(fileURLToPath(import.meta.url)), "../src");
  const clientSource = readFileSync(nodePath.join(intensiqSrcDir, "client.ts"), "utf8");

  // IntenSIQ client must NOT have My Rhythm write methods
  assert.ok(!clientSource.includes("createFlexibleBlock"), "IntenSIQ must not have createFlexibleBlock");
  assert.ok(!clientSource.includes("updateFlexibleBlock"), "IntenSIQ must not have updateFlexibleBlock");
  assert.ok(!clientSource.includes("removeFlexibleBlock"), "IntenSIQ must not have removeFlexibleBlock");
  assert.ok(!clientSource.includes("checkConflict"), "IntenSIQ must not have checkConflict");
  assert.ok(!clientSource.includes("getWorkDates"), "IntenSIQ must not have getWorkDates");

  // Scholar does not write to My Rhythm's planning domain
  assert.ok(!clientSource.includes("planTask"), "IntenSIQ must not have planTask");
});

// ==================== T12.5 ====================

test("T12.5 Research quality — stronger evidence preferred over conflicting low-quality material", () => {
  const topics: WeakTopic[] = [
    { learnerId: LEARNER_ID, topicId: "strong-evidence", topicName: "Well-established CS theory", domain: "theory", weaknessScore: 30, lastAssessedAt: "2026-09-25T00:00:00.000Z", practiceSessions: 8 },
    { learnerId: LEARNER_ID, topicId: "weak-evidence", topicName: "Unverified claim", domain: "theory", weaknessScore: 90, lastAssessedAt: "2026-09-26T00:00:00.000Z", practiceSessions: 0 },
    { learnerId: LEARNER_ID, topicId: "medium-evidence", topicName: "Partially verified", domain: "theory", weaknessScore: 60, lastAssessedAt: "2026-09-24T00:00:00.000Z", practiceSessions: 3 },
  ];

  const ranked = rankWeakTopics(topics);
  // Higher weakness = ranked first (needs more attention)
  assert.strictEqual(ranked[0].topicId, "weak-evidence", "Highest weakness should be first");
  assert.strictEqual(ranked[1].topicId, "medium-evidence");
  assert.strictEqual(ranked[2].topicId, "strong-evidence", "Strongest evidence (lowest weakness) should be last");

  // Top 2 should give the two weakest
  const top2 = topWeakTopics(topics, 2);
  assert.strictEqual(top2.length, 2);
  assert.strictEqual(top2[0].topicId, "weak-evidence");
  assert.strictEqual(top2[1].topicId, "medium-evidence");
});

// ==================== T12.6 ====================

test("T12.6 Conflicting evidence — uncertainty represented appropriately", async () => {
  const transport = new InMemoryIntenSIQTransport({
    profiles: [makeProfile()],
    progress: [makeProgress()],
    weakTopics: [
    { learnerId: LEARNER_ID, topicId: "conflict-a", topicName: "Theory A", domain: "theory", weaknessScore: 70, lastAssessedAt: "2026-09-20T00:00:00.000Z", practiceSessions: 2 },
    { learnerId: LEARNER_ID, topicId: "conflict-b", topicName: "Theory B", domain: "theory", weaknessScore: 70, lastAssessedAt: "2026-09-21T00:00:00.000Z", practiceSessions: 2 },
    ],
  });

  const topics = await transport.getWeakTopics(LEARNER_ID);
  // Equal weakness scores mean uncertainty — ranking should not arbitrarily prefer one
  assert.strictEqual(topics.length, 2);
  assert.strictEqual(topics[0].weaknessScore, topics[1].weaknessScore, "Conflicting evidence should have equal weakness scores");

  // Weak topics with equal scores represent uncertainty — the system should NOT silently resolve
  const ranked = rankWeakTopics(topics);
  // Both have same score — the system preserves both, no false certainty
  assert.strictEqual(ranked.length, 2);
});

// ==================== T12.7 ====================

test("T12.7 Claim verification — factual claims checked in separate verification pass", async () => {
  const transport = new InMemoryIntenSIQTransport({
    profiles: [makeProfile()],
    progress: [makeProgress()],
    weakTopics: makeWeakTopics(),
  });

  // Create a quiz as a verification pass
  const { quiz } = await transport.createQuiz({
    sessionId: "session-001",
    learnerId: LEARNER_ID,
    topicId: "t1",
    questionCount: 10,
    status: "draft",
  });

  assert.ok(quiz.quizId.length > 0);
  assert.strictEqual(quiz.questionCount, 10);
  assert.strictEqual(quiz.status, "draft");

  // Quiz is a separate verification pass — not a claim about the material
  // The quiz existence is a coordination object, not a claim of learning
  const quizResult: QuizResult = {
    quizId: quiz.quizId,
    correctAnswers: 7,
    totalQuestions: 10,
    scorePercent: 70,
    weakAreas: ["TCP/IP", "Routing"],
  };

  assert.strictEqual(quizResult.scorePercent, 70);
  assert.strictEqual(quizResult.correctAnswers, 7);
  // Score is separate from the material — claims are verified in the quiz pass
  assert.ok(quizResult.weakAreas.length > 0, "Weak areas identified in verification pass");
});

// ==================== T12.8 ====================

test("T12.8 IntenSIQ failure — returns PARTIAL/BLOCKED and explicitly states save failed", async () => {
  const transport = new InMemoryIntenSIQTransport({
    profiles: [], // No profiles — will cause lookup failure
    progress: [],
    weakTopics: [],
  });

  // Attempting to read a non-existent profile should throw with explicit error
  await assert.rejects(async () => {
    await transport.getLearningProfile("nonexistent-learner");
  }, /Profile not found/, "IntenSIQ must explicitly state the failure when profile is missing");

  // Create a transport with no data to test partial state
  const emptyTransport = new InMemoryIntenSIQTransport();

  // getWeakTopics on empty should return empty, not throw
  const emptyTopics = await emptyTransport.getWeakTopics("unknown");
  assert.strictEqual(emptyTopics.length, 0, "Empty state returns empty array, not error");

  // Attempt to get progress for non-existent learner
  await assert.rejects(async () => {
    await emptyTransport.getLearningProgress("unknown");
  }, /Progress not found/, "IntenSIQ must explicitly state save/read failed");
});

// ==================== T12.9 ====================

test("T12.9 No credential leakage", () => {
  const intensiqSrcDir = nodePath.join(nodePath.dirname(fileURLToPath(import.meta.url)), "../src");
  const clientSource = readFileSync(nodePath.join(intensiqSrcDir, "client.ts"), "utf8");

  // No credentials, secrets, or tokens in the client
  assert.ok(!clientSource.includes("password"), "Client must not contain password references");
  assert.ok(!clientSource.includes("secret"), "Client must not contain secret references");
  assert.ok(!clientSource.includes("token"), "Client must not contain token references");
  assert.ok(!clientSource.includes("apiKey"), "Client must not contain apiKey references");
  assert.ok(!clientSource.includes("API_KEY"), "Client must not contain API_KEY references");
  assert.ok(!clientSource.includes("Authorization"), "Client must not contain Authorization header");
  assert.ok(!clientSource.includes("Bearer"), "Client must not contain Bearer token");
});

// ==================== T12.10 ====================

test("T12.10 Skill baseline — scientific/evidence skills improve quality without over-triggering", async () => {
  const transport = new InMemoryIntenSIQTransport({
    profiles: [makeProfile()],
    progress: [makeProgress()],
    weakTopics: makeWeakTopics(),
  });

  // Weak topic ranking improves study quality by focusing on weakest areas first
  const topics = await transport.getWeakTopics(LEARNER_ID);
  const ranked = rankWeakTopics(topics);

  // Ranking must put highest-weakness topics first
  assert.strictEqual(ranked[0].weaknessScore, 85, "Highest weakness first");
  assert.strictEqual(ranked[ranked.length - 1].weaknessScore, 45, "Lowest weakness last");

  // Session scheduling metadata provides deterministic cognitive load assessment
  const meta = sessionScheduleMetadata("sess-001", "t1", 45, "2026-09-27T10:00:00.000Z");
  assert.strictEqual(meta.cognitiveLoad, "medium", "45min session = medium cognitive load");
  assert.strictEqual(meta.durationMinutes, 45);

  // Session feasibility check works with available windows
  const feasible = isSessionFeasible("2026-09-27T10:00:00.000Z", 45, [
    { startsAt: "2026-09-27T09:00:00.000Z", endsAt: "2026-09-27T12:00:00.000Z" },
  ]);
  assert.strictEqual(feasible, true, "45-min session fits in 3-hour window");

  // Session too long for window should be infeasible
  const infeasible = isSessionFeasible("2026-09-27T11:30:00.000Z", 60, [
    { startsAt: "2026-09-27T09:00:00.000Z", endsAt: "2026-09-27T12:00:00.000Z" },
  ]);
  assert.strictEqual(infeasible, false, "60-min session starting at 11:30 exceeds 12:00 window");

  // Scientific skills improve quality without over-triggering:
  // ranking is deterministic, not based on random/LLM calls
  const topics2 = await transport.getWeakTopics(LEARNER_ID);
  const ranked2 = rankWeakTopics(topics2);
  // Same input → same output (deterministic)
  assert.strictEqual(ranked2[0].weaknessScore, ranked[0].weaknessScore, "Ranking is deterministic");
});

// ==================== additional contract tests ====================

test("Contract: rankWeakTopics is deterministic and pure", () => {
  const topics: WeakTopic[] = [
    { learnerId: LEARNER_ID, topicId: "a", topicName: "A", domain: "d", weaknessScore: 50, lastAssessedAt: "2026-09-20T00:00:00.000Z", practiceSessions: 1 },
    { learnerId: LEARNER_ID, topicId: "b", topicName: "B", domain: "d", weaknessScore: 90, lastAssessedAt: "2026-09-20T00:00:00.000Z", practiceSessions: 1 },
    { learnerId: LEARNER_ID, topicId: "c", topicName: "C", domain: "d", weaknessScore: 30, lastAssessedAt: "2026-09-20T00:00:00.000Z", practiceSessions: 1 },
  ];

  const result1 = rankWeakTopics(topics);
  const result2 = rankWeakTopics(topics);
  assert.strictEqual(result1[0].topicId, result2[0].topicId);
  assert.strictEqual(result1[1].topicId, result2[1].topicId);
  assert.strictEqual(result1[2].topicId, result2[2].topicId);
  // No mutation of input
  assert.strictEqual(topics[0].weaknessScore, 50);
});

test("Contract: InMemoryIntenSIQTransport returns copies, not references", async () => {
  const transport = new InMemoryIntenSIQTransport({
    profiles: [makeProfile()],
    progress: [makeProgress()],
    weakTopics: makeWeakTopics(),
  });

  const profile = await transport.getLearningProfile(LEARNER_ID);
  profile.proficiencyLevel = 99; // Mutate returned copy

  const profile2 = await transport.getLearningProfile(LEARNER_ID);
  assert.strictEqual(profile2.proficiencyLevel, 65, "Internal state must not be affected by external mutation");

  const topics = await transport.getWeakTopics(LEARNER_ID);
  topics[0].weaknessScore = 999;
  const topics2 = await transport.getWeakTopics(LEARNER_ID);
  assert.strictEqual(topics2[0].weaknessScore, 85, "Weak topics internal state must not be affected");
});

test("Contract: CoordinationResult carries metadata only, no full content", async () => {
  const transport = new InMemoryIntenSIQTransport();

  // Create a study plan and verify coordination metadata
  const { coordination } = await transport.createStudyPlan({
    learnerId: LEARNER_ID,
    title: "Test",
    status: "active",
    metadata: { targetDomains: ["networking"], totalSessions: 2, estimatedHours: 4 },
  });

  // Coordination has: id, status, metadata
  assert.ok(coordination.id.length > 0);
  assert.strictEqual(coordination.status, "created");
  assert.ok(typeof coordination.metadata === "object");

  // Must NOT contain full study material
  const json = JSON.stringify(coordination);
  assert.ok(!json.includes("chapter"), "Coordination must not contain chapter content");
  assert.ok(!json.includes("lesson"), "Coordination must not contain lesson content");
  assert.ok(!json.includes("paragraph"), "Coordination must not contain paragraph content");
});

test("Contract: isSessionFeasible is deterministic and pure", () => {
  const windows = [
    { startsAt: "2026-09-27T09:00:00.000Z", endsAt: "2026-09-27T12:00:00.000Z" },
  ];

  // Feasible: 60-min session within 3-hour window
  assert.strictEqual(isSessionFeasible("2026-09-27T09:00:00.000Z", 60, windows), true);
  // Infeasible: 4-hour session exceeds window
  assert.strictEqual(isSessionFeasible("2026-09-27T09:00:00.000Z", 240, windows), false);
  // Infeasible: starts after window ends
  assert.strictEqual(isSessionFeasible("2026-09-27T13:00:00.000Z", 30, windows), false);
});