/**
 * IntenSIQ typed client — Batch 12.
 *
 * Provides typed operations for learning profile, weak topics,
 * study plans, sessions, learning materials, and quizzes.
 *
 * All detailed study content stays in IntenSIQ; returned
 * coordination objects carry metadata only (ids, statuses, counts).
 *
 * Pluggable transport: interface + InMemory mock. No real network calls.
 */

// ======================== types ========================

export interface LearningProfile {
  learnerId: string;
  domain: string;
  proficiencyLevel: number; // 0-100
  weakTopics: string[];
  lastActiveAt: string;
  totalStudyHours: number;
}

export interface LearningProgress {
  learnerId: string;
  modulesCompleted: number;
  modulesTotal: number;
  currentModuleId: string;
  progressPercent: number;
  lastSessionAt: string | null;
}

export interface WeakTopic {
  learnerId: string;
  topicId: string;
  topicName: string;
  domain: string;
  weaknessScore: number; // 0-100, higher = weaker
  lastAssessedAt: string;
  practiceSessions: number;
}

export interface StudyPlan {
  planId: string;
  learnerId: string;
  title: string;
  status: "draft" | "active" | "completed" | "archived";
  createdAt: string;
  sessionIds: string[];
  metadata: StudyPlanMetadata;
}

export interface StudyPlanMetadata {
  targetDomains: string[];
  totalSessions: number;
  estimatedHours: number;
}

export interface StudySession {
  sessionId: string;
  planId: string;
  learnerId: string;
  topicId: string;
  status: "scheduled" | "in-progress" | "completed" | "cancelled";
  startedAt: string | null;
  endedAt: string | null;
  durationMinutes: number;
}

export interface LearningMaterial {
  materialId: string;
  sessionId: string;
  learnerId: string;
  type: "article" | "video" | "interactive" | "reading";
  title: string;
  status: "pending" | "in-progress" | "completed";
  createdAt: string;
}

export interface Quiz {
  quizId: string;
  sessionId: string;
  learnerId: string;
  topicId: string;
  questionCount: number;
  status: "draft" | "active" | "completed";
  createdAt: string;
}

export interface QuizResult {
  quizId: string;
  correctAnswers: number;
  totalQuestions: number;
  scorePercent: number;
  weakAreas: string[];
}

export interface CoordinationResult {
  id: string;
  status: string;
  metadata: Record<string, unknown>;
}

// ======================== transport interface ========================

export interface IntenSIQTransport {
  getLearningProfile(learnerId: string): Promise<LearningProfile>;
  getLearningProgress(learnerId: string): Promise<LearningProgress>;
  getWeakTopics(learnerId: string): Promise<WeakTopic[]>;
  createStudyPlan(plan: Omit<StudyPlan, "planId" | "createdAt" | "sessionIds">): Promise<{ plan: StudyPlan; coordination: CoordinationResult }>;
  createStudySession(session: Omit<StudySession, "sessionId" | "startedAt" | "endedAt">): Promise<{ session: StudySession; coordination: CoordinationResult }>;
  createLearningMaterial(material: Omit<LearningMaterial, "materialId" | "createdAt">): Promise<{ material: LearningMaterial; coordination: CoordinationResult }>;
  createQuiz(quiz: Omit<Quiz, "quizId" | "createdAt">): Promise<{ quiz: Quiz; coordination: CoordinationResult }>;
}

// ======================== in-memory mock transport ========================

export class InMemoryIntenSIQTransport implements IntenSIQTransport {
  private profiles: Map<string, LearningProfile> = new Map();
  private progressMap: Map<string, LearningProgress> = new Map();
  private weakTopicsMap: Map<string, WeakTopic[]> = new Map();
  private _plans: StudyPlan[] = [];
  private _sessions: StudySession[] = [];
  private _materials: LearningMaterial[] = [];
  private _quizzes: Quiz[] = [];

  constructor(opts?: {
    profiles?: LearningProfile[];
    progress?: LearningProgress[];
    weakTopics?: WeakTopic[];
  }) {
    if (opts?.profiles) {
      for (const p of opts.profiles) this.profiles.set(p.learnerId, { ...p });
    }
    if (opts?.progress) {
      for (const p of opts.progress) this.progressMap.set(p.learnerId, { ...p });
    }
    if (opts?.weakTopics) {
      const grouped = new Map<string, WeakTopic[]>();
      for (const t of opts.weakTopics) {
        const existing = grouped.get(t.learnerId) ?? [];
        existing.push(t);
        grouped.set(t.learnerId, existing);
      }
      this.weakTopicsMap = grouped;
    }
  }

  async getLearningProfile(learnerId: string): Promise<LearningProfile> {
    const profile = this.profiles.get(learnerId);
    if (!profile) throw new Error(`Profile not found for learner ${learnerId}`);
    return { ...profile };
  }

  async getLearningProgress(learnerId: string): Promise<LearningProgress> {
    const progress = this.progressMap.get(learnerId);
    if (!progress) throw new Error(`Progress not found for learner ${learnerId}`);
    return { ...progress };
  }

  async getWeakTopics(learnerId: string): Promise<WeakTopic[]> {
    const topics = this.weakTopicsMap.get(learnerId) ?? [];
    return topics.map(t => ({ ...t }));
  }

  async createStudyPlan(plan: Omit<StudyPlan, "planId" | "createdAt" | "sessionIds">): Promise<{ plan: StudyPlan; coordination: CoordinationResult }> {
    const planId = crypto.randomUUID();
    const createdAt = new Date().toISOString();
    const full: StudyPlan = { ...plan, planId, createdAt, sessionIds: [] };
    this._plans.push(full);
    const coordination: CoordinationResult = {
      id: planId,
      status: "created",
      metadata: { targetDomains: plan.metadata.targetDomains, totalSessions: plan.metadata.totalSessions },
    };
    return { plan: full, coordination };
  }

  async createStudySession(session: Omit<StudySession, "sessionId" | "startedAt" | "endedAt">): Promise<{ session: StudySession; coordination: CoordinationResult }> {
    const sessionId = crypto.randomUUID();
    const full: StudySession = { ...session, sessionId, startedAt: null, endedAt: null };
    this._sessions.push(full);
    // Link to plan
    const plan = this._plans.find(p => p.planId === session.planId);
    if (plan) plan.sessionIds.push(sessionId);
    const coordination: CoordinationResult = {
      id: sessionId,
      status: "scheduled",
      metadata: { topicId: session.topicId, durationMinutes: session.durationMinutes },
    };
    return { session: full, coordination };
  }

  async createLearningMaterial(material: Omit<LearningMaterial, "materialId" | "createdAt">): Promise<{ material: LearningMaterial; coordination: CoordinationResult }> {
    const materialId = crypto.randomUUID();
    const createdAt = new Date().toISOString();
    const full: LearningMaterial = { ...material, materialId, createdAt };
    this._materials.push(full);
    const coordination: CoordinationResult = {
      id: materialId,
      status: "pending",
      metadata: { sessionId: material.sessionId, type: material.type },
    };
    return { material: full, coordination };
  }

  async createQuiz(quiz: Omit<Quiz, "quizId" | "createdAt">): Promise<{ quiz: Quiz; coordination: CoordinationResult }> {
    const quizId = crypto.randomUUID();
    const createdAt = new Date().toISOString();
    const full: Quiz = { ...quiz, quizId, createdAt };
    this._quizzes.push(full);
    const coordination: CoordinationResult = {
      id: quizId,
      status: "draft",
      metadata: { topicId: quiz.topicId, questionCount: quiz.questionCount },
    };
    return { quiz: full, coordination };
  }

  // Accessors for tests
  get plans(): readonly StudyPlan[] { return this._plans; }
  get sessions(): readonly StudySession[] { return this._sessions; }
  get materials(): readonly LearningMaterial[] { return this._materials; }
  get quizzes(): readonly Quiz[] { return this._quizzes; }
}

// ======================== deterministic helpers ========================

/** Rank weak topics by weaknessScore descending. Pure/deterministic. */
export function rankWeakTopics(topics: WeakTopic[]): WeakTopic[] {
  return [...topics].sort((a, b) => b.weaknessScore - a.weaknessScore);
}

/** Compute the top N weakest topics. Pure/deterministic. */
export function topWeakTopics(topics: WeakTopic[], n: number): WeakTopic[] {
  return rankWeakTopics(topics).slice(0, n);
}

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

export interface SessionScheduleMetadata {
  sessionId: string;
  topicId: string;
  durationMinutes: number;
  startsAt: string;
  endsAt: string;
  estimatedEnd: string;
  cognitiveLoad: "low" | "medium" | "high";
}

/** Determine if a session placement is feasible within available windows. Pure/deterministic. */
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
