> **SUPERSEDED**: this document is a historical plan, kept as history only. The current architecture contract is [docs/CURRENT_SYSTEM.md](../../docs/CURRENT_SYSTEM.md). Do not follow its architecture or model-routing claims.

# OpenClaw Scholar Agent
## Goal-Driven Learning Intelligence, IntenSIQ Orchestration and Project Research
### Batch-by-Batch Implementation Plan

**Version:** 1.0  
**Date:** 29 September 2026  
**Status:** Frozen architecture baseline for implementation  
**Primary agent:** Scholar  
**Primary model:** `inclusionai/ling-3.0-flash` only  
**Deterministic layer:** code for validation, calculations, event handling and state integrity  
**Learning execution platform:** IntenSIQ  
**Scheduling authority:** Rhythm  
**Portfolio priority authority:** Tola  
**Shared coordination state:** Supabase Blackboard + SQLite cache/outbox where required  
**Companion QA document:** `openclaw_scholar_testing_plan_v1_0.md`

---

# 1. Purpose

Scholar is the intelligence layer behind the user's critical-care learning and the evidence/research specialist for the wider project portfolio.

Scholar has two first-class jobs:

1. **Clinical Learning Intelligence**
   - manage the user's long-term Step 2 / Step 3 critical-care development;
   - understand course structure, learning outcomes and future proficiency context;
   - convert learning goals into adaptive learning strategies;
   - analyse IntenSIQ progress and assessment evidence;
   - identify knowledge/proficiency gaps;
   - determine what should be learned next and how much effort is required;
   - send study requirements to Rhythm;
   - update IntenSIQ's versioned learning plan;
   - monitor important recent evidence related to active learning goals.

2. **Project Research**
   - perform rigorous evidence-based research for Tola across Florence, VocalGaze, Shiftlyx, Revalidation Copilot, IntenSIQ and future projects;
   - separate fact, inference, hypothesis and unknown;
   - evaluate source quality and conflicting evidence;
   - return concise, decision-ready synthesis to Tola.

Scholar must not become a second learning interface.

---

# 2. Frozen Separation of Responsibilities

```text
TOLA
Portfolio priority / why the learning or research matters
        -
        -
SCHOLAR
What to learn
What sequence
How deeply
How much
What gaps exist
What evidence matters
How progress should be interpreted
        -
        ----------------- RHYTHM
        -                 When it fits
        -                 Capacity
        -                 Schedule execution
        -
        -
INTENSIQ
All actual studying:
teaching
cases
quizzes
flashcards
practice
reasoning
revision
weekly tests
study materials
        -
        -
LEARNING EVIDENCE
        -
        -
SCHOLAR
Analyse -> adapt -> continue
```

Core principle:

> **Scholar thinks. IntenSIQ teaches. Rhythm schedules. Tola prioritises.**

---

# 3. Explicit Non-Responsibilities

Scholar does **not** own:

- learner-facing tutoring;
- quiz generation for direct use outside IntenSIQ;
- flashcard generation for direct use outside IntenSIQ;
- case teaching outside IntenSIQ;
- study-material generation as an alternative to IntenSIQ;
- weekly-test generation outside IntenSIQ;
- marking study complete;
- submitting assessments;
- formal clinical sign-off;
- My Rhythm writes;
- portfolio priority;
- cross-agent delegation;
- raw Supabase access;
- arbitrary shell access;
- production security changes;
- model routing changes;
- self-authorised IntenSIQ feature development.

---

# 4. Model Routing

Scholar V1 uses one LLM only.

```text
R0 -- DETERMINISTIC CODE

schema validation
event deduplication
cursor processing
progress calculations
coverage calculations
version checks
plan validation
idempotency
freshness checks

R1 -- LING 3.0 FLASH

all Scholar reasoning:
learning goal decomposition
curriculum mapping
proficiency mapping
learning-gap analysis
mastery interpretation
adaptive learning strategy
IntenSIQ feedback analysis
literature triage/appraisal
project research
evidence synthesis
feature-gap detection
communication with Tola/Rhythm
```

No semantic model escalation.

Technical failure policy:

```text
Ling call
  -
technical failure
  -
one retry
  -
still fails
  -
PARTIAL / BLOCKED / FAILED
```

Scholar must not silently switch models.

---

# 5. Course and Proficiency Context Model

Scholar must be designed to ingest additional Step 2 and Step 3 proficiency context later.

Do not hard-code proficiency wording in Scholar's prompt.

Use a versioned curriculum/proficiency model:

```text
Course handbook
Assignment guidance
Module outcomes
Step 2 proficiencies
Step 3 proficiencies
Future course updates
IntenSIQ course/topic structure
        -
CURRICULUM & PROFICIENCY REGISTRY
        -
SCHOLAR
```

Each proficiency should preserve:

```text
proficiency_id
step
domain
source
source_version
verbatim_requirement
knowledge_requirements
application_requirements
rationale_requirements
linked_topics
linked_learning_outcomes
linked_evidence
status
```

The original proficiency wording remains authoritative.

Scholar's interpretation is derived metadata.

---

# 6. Mastery Model

Scholar tracks learning quality rather than simple completion.

Suggested dimensions:

```text
KNOWLEDGE
RATIONALE
APPLICATION
CRITICAL_ANALYSIS
RECALL
TRANSFER
PRACTICAL_READINESS
FORMAL_COMPETENCE
```

`FORMAL_COMPETENCE` may only become signed off from an authoritative assessment source.

Scholar may conclude:

```text
READY_FOR_MORE_APPLICATION
READY_FOR_CLINICAL_ASSESSMENT
```

but not:

```text
SIGNED_OFF
```

unless the authorised course/PAD system provides that state.

---

# 7. Goal-Driven Learning

A user or Tola learning goal becomes a persistent Scholar goal.

Example:

```text
Goal:
Become highly competent in mechanical ventilation within six weeks.
```

Scholar loop:

```text
GOAL
 -
map curriculum/proficiencies
 -
read IntenSIQ learner state
 -
determine baseline
 -
identify prerequisites/gaps
 -
build strategy
 -
calculate effort
 -
ask Rhythm for capacity
 -
adapt plan to feasible capacity
 -
write versioned plan to IntenSIQ
 -
user studies in IntenSIQ
 -
receive evidence/events
 -
recalculate mastery/gaps
 -
adapt plan
 -
repeat until goal achieved/stopped/superseded
```

---

# 8. IntenSIQ Integration Contract

The existing IntenSIQ codebase already provides course/topic/content, goals, progress, practice, tests, cases, study materials, recordings and reasoning features.

Scholar requires only three narrow integration additions.

## 8.1 Learner State Read Model

```text
GET /api/v1/integration/learner-state?course_id=...
```

Recommended response:

```text
schema_version
state_version
as_of
course
course_goals
proficiency_context[]
topics[]
  progress
  next_action
  practice_units
  recent_assessments
  recent_study_activity
reasoning_evidence[]
competency_evidence[]
revision_items[]
cursor
```

Principle:

```text
learner-state = what is true now
```

The read model must expose evidence, not formal clinical sign-off unless that sign-off is authoritative.

## 8.2 Versioned Learning Plan

```text
GET /api/v1/integration/courses/:courseId/learning-plan
PUT /api/v1/integration/courses/:courseId/learning-plan
```

Minimum fields:

```text
plan_id
goal_id
course_id
version
expected_previous_version
status
objective
target_date
proficiency_refs[]
ordered_learning_items[]
weekly_minutes
minimum_session_minutes
review_policy
mastery_targets
rationale
created_by = "scholar"
updated_at
```

The plan defines **what to study and how much**.

It must not contain calendar times.

## 8.3 Durable Learning Events

Start with a pollable outbox:

```text
GET /api/v1/integration/events?cursor=...
```

Minimum event types:

```text
study_session.recorded
practice_unit.completed
assessment.submitted
reasoning_session.completed
recording.transcription_completed
course_goals.updated
learning_plan.updated
topic.progress_changed
proficiency_context.updated
```

Minimum event fields:

```text
event_id
event_type
schema_version
occurred_at
course_id
topic_id
aggregate_id
payload
```

Principle:

```text
events = what changed
```

---

# 9. Evidence Integrity

Scholar must never manufacture its own evidence.

Correct:

```text
USER studies in IntenSIQ
        -
IntenSIQ records evidence
        -
Scholar interprets evidence
```

Prohibited:

```text
Scholar marks topic complete
Scholar submits quiz
Scholar records fake review
Scholar creates evidence
Scholar reads that same evidence
Scholar concludes mastery
```

This boundary is a hard production gate.

---

# 10. Scholar - Rhythm Contract

Scholar owns:

```text
WHAT to learn
HOW MUCH
SEQUENCE
COGNITIVE LOAD
MINIMUM USEFUL SESSION
DEADLINE/LEARNING WINDOW
```

Rhythm owns:

```text
WHEN
CALENDAR PLACEMENT
SHIFT/RECOVERY FEASIBILITY
REPLANNING
MY RHYTHM WRITES
```

Example `STUDY_REQUIREMENT` fields:

```text
goal_id
course_id
topic/proficiency focus
weekly_minutes
minimum_session_minutes
cognitive_load
priority
deadline
splittable
rationale
```

Scholar must never specify exact calendar times as part of the learning plan.

---

# 11. Scholar - Tola Contract

Tola may send:

```text
LEARNING_GOAL
RESEARCH_REQUEST
EVIDENCE_REQUEST
PLAN_REVIEW_REQUEST
PRIORITY_CHANGE
GOAL_STOPPED
GOAL_SUPERSEDED
```

Scholar may send:

```text
LEARNING_PLAN
LEARNING_PROGRESS
LEARNING_RISK
PROFICIENCY_GAP
GOAL_COMPLETED
RESEARCH_SYNTHESIS
RESEARCH_UNCERTAINTY
IMPORTANT_EVIDENCE
INTENSIQ_FEATURE_GAP
CAPACITY_REQUIREMENT
```

Tola remains portfolio authority.

Scholar does not reprioritise the user's portfolio.

---

# 12. Literature Intelligence

Scholar maintains topic watchlists related to active learning goals, course topics, proficiency gaps and major critical-care developments.

Pipeline:

```text
DISCOVER
 -
RELEVANT?
 -
SOURCE QUALITY?
 -
IMPORTANT?
 -
CHANGES OR ADDS USEFUL KNOWLEDGE?
 -
RELEVANT TO ACTIVE GOAL/PROFICIENCY?
 -
INCORPORATE INTO LEARNING STRATEGY
```

Prefer guidelines, systematic reviews, meta-analyses, important RCTs, major observational studies, consensus statements and high-quality reviews.

Scholar should not become a generic ICU-news feed.

---

# 13. Project Research Mode

```text
RESEARCH REQUEST
 -
define question
 -
decompose
 -
search
 -
source quality
 -
evidence extraction
 -
conflict analysis
 -
claim verification
 -
synthesis
 -
uncertainty
 -
TOLA
```

Every material conclusion should distinguish:

```text
FACT
INFERENCE
HYPOTHESIS
UNKNOWN
```

---

# 14. Assessment Integrity

Scholar must recognise assessed coursework.

For assessment-restricted work, Scholar may support understanding, literature discovery, evidence appraisal, learning planning, self-testing through IntenSIQ and permitted language support.

Scholar must not autonomously generate assessed submission content where the course prohibits it.

---

# 15. IntenSIQ Feature-Gap Path

```text
Scholar detects gap
 -
INTENSIQ_FEATURE_GAP
 -
Tola
 -
evaluate value / effort / priority / capacity
 -
BUILD / DEFER / REJECT
```

Feature-gap object:

```text
capability
affected_goal
learning_problem
current_capability
gap
expected_learning_value
frequency_of_need
workaround
evidence
```

Scholar does not build a shadow learning system.

---

# 16. Scholar Core Skills

Freeze these V1 Skills:

```text
curriculum-ingestion
proficiency-mapping
learning-goal-decomposition
learner-state-analysis
learning-gap-analysis
adaptive-learning-strategy
mastery-estimation
proficiency-readiness
intensiq-plan-orchestration
intensiq-feedback-analysis
intensiq-feature-gap-detection
study-requirement-to-rhythm
literature-discovery
evidence-appraisal
evidence-to-learning-strategy
research-question-decomposition
source-quality-assessment
claim-verification
evidence-synthesis
research-to-tola
assessment-integrity
learning-effectiveness-review
```

Explicitly excluded:

```text
quiz-generation
flashcard-generation
case-teaching
direct tutoring
study-material-generation
weekly-test-generation
```

---

# 17. Batch-by-Batch Implementation

## Batch S0 -- Baseline, Backup and Boundary Freeze
Create a restorable baseline; capture current OpenClaw config, four-agent architecture, Scholar stub/contract, IntenSIQ integration notes, agent boundaries and Ling-only routing. Create `/scholar/{contracts,curriculum,goals,learner_state,mastery,intensiq,research,evidence,literature,integrity,events,skills,tests,fixtures,docs}`.

**Exit:** system restorable and Scholar role unambiguous.  
**Hard gate:** QA S0.

## Batch S1 -- IntenSIQ Capability Contract
Classify existing IntenSIQ routes as `READ_EXISTING`, `WRITE_EXISTING`, `NOT_FOR_SCHOLAR`, or `NEW_INTEGRATION_NEEDED`. Freeze the exact contracts for learner-state, learning-plan and events. Explicitly deny learner-evidence mutations.

**Exit:** no Scholar implementation depends on invented IntenSIQ behaviour.  
**Hard gate:** QA S1.

## Batch S2 -- Scholar Authentication and Scope
Create narrow integration credentials/scopes equivalent to `learner-state:read`, `learning-plan:read`, `learning-plan:write`, `events:read`. Deny progress/practice/assessment mutation, delete operations and user mutation.

**Exit:** Scholar can access only its integration contract.  
**Hard gate:** QA S2.

## Batch S3 -- Learner-State Endpoint
Implement the typed learner-state aggregate with schema/state version, timestamp, course, goals, proficiency context, topic progress, next actions, practice, assessments, recent study activity, reasoning/competency evidence and revision items.

**Exit:** one read reconstructs current learner state.  
**Hard gate:** QA S3.

## Batch S4 -- Versioned Learning Plan
Implement GET/PUT learning plan with optimistic concurrency through `expected_previous_version`. Reject calendar-time fields.

**Exit:** Scholar can safely version strategy without scheduling.  
**Hard gate:** QA S4.

## Batch S5 -- Durable Learning Event Outbox
Create stable immutable event IDs, schema versions, cursor pagination and replay-safe persistence.

**Exit:** learning changes are durable and replayable.  
**Hard gate:** QA S5.

## Batch S6 -- Scholar Event Consumer
Implement polling, deduplication, processing and cursor commit. Commit cursor only after safe processing.

**Exit:** duplicate/replayed events produce one logical effect.  
**Hard gate:** QA S6.

## Batch S7 -- Curriculum Registry
Create versioned curriculum sources, nodes, learning outcomes and topic links. Ingest course handbook, assignment guidance and IntenSIQ structure with provenance.

**Exit:** course structure is source-grounded, not prompt hard-coded.  
**Hard gate:** QA S7.

## Batch S8 -- Proficiency Registry and Future Ingestion
Create proficiency versions, topic links and evidence links. Implement ingest/map/supersede while preserving verbatim source wording.

**Exit:** future Step 2/3 context can be added without redesign.  
**Hard gate:** QA S8.

## Batch S9 -- Learning Goal Contract
Create persistent `scholar_goals` supporting direct-user and Tola sources, with ACTIVE/PAUSED/COMPLETED/STOPPED/SUPERSEDED states.

**Exit:** goals persist beyond chat sessions.  
**Hard gate:** QA S9.

## Batch S10 -- Learning-Goal Decomposition
Build `learning-goal-decomposition`: map goals to curriculum nodes, proficiencies, prerequisites, mastery dimensions, time horizon and evidence requirements.

**Exit:** representative goals produce valid target structures.  
**Hard gate:** QA S10.

## Batch S11 -- Learner-State Analysis
Build `learner-state-analysis` using deterministic summaries plus Ling. Separate observed evidence, interpretation and uncertainty.

**Exit:** Scholar describes strengths/gaps without inventing evidence.  
**Hard gate:** QA S11.

## Batch S12 -- Mastery Model
Track knowledge, rationale, application, critical analysis, recall, transfer, practical readiness and formal competence. Formal competence only changes from authoritative evidence.

**Exit:** Scholar distinguishes learning from sign-off.  
**Hard gate:** QA S12.

## Batch S13 -- Learning Gap Analysis
Build `learning-gap-analysis` for missing prerequisites, weak knowledge/application/recall, insufficient evidence/practice and uncovered proficiencies.

**Exit:** every gap is traceable to evidence.  
**Hard gate:** QA S13.

## Batch S14 -- Adaptive Learning Strategy
Build `adaptive-learning-strategy`. Ordered items contain topic/proficiency, sequence, priority, target depth/mastery, recommended effort, outcomes and rationale--not learner-facing quizzes or teaching scripts.

**Exit:** Scholar plans learning while IntenSIQ retains delivery control.  
**Hard gate:** QA S14.

## Batch S15 -- Rhythm Capacity Protocol
Send `STUDY_REQUIREMENT` containing required minutes, minimum block, cognitive load, priority, deadline and splitability. Adapt strategy when capacity is lower than requested.

**Exit:** Scholar cannot assume unlimited study time.  
**Hard gate:** QA S15.

## Batch S16 -- IntenSIQ Plan Orchestration
Implement current-plan read -> compare -> validate -> versioned PUT -> verify. Never call progress/evidence mutation endpoints.

**Exit:** plan updates are safe, idempotent and verified.  
**Hard gate:** QA S16.

## Batch S17 -- Feedback Analysis and Plan Adaptation
On relevant IntenSIQ events, update mastery/gaps and adapt only when evidence is material. Avoid plan churn.

**Exit:** Scholar responds proportionately to evidence.  
**Hard gate:** QA S17.

## Batch S18 -- Proficiency Readiness
Implement states `NOT_STARTED`, `KNOWLEDGE_BUILDING`, `APPLICATION_BUILDING`, `PRACTICE_REQUIRED`, `EVIDENCE_REQUIRED`, `READY_FOR_CLINICAL_ASSESSMENT`, `ASSESSED_SIGNED_OFF`. Final state requires authoritative sign-off.

**Exit:** Scholar never self-certifies competence.  
**Hard gate:** QA S18.

## Batch S19 -- Literature Discovery
Build goal/proficiency-driven evidence watchlists and literature searches. Avoid generic ICU-news behaviour.

**Exit:** relevant important evidence is found with low noise.  
**Hard gate:** QA S19.

## Batch S20 -- Evidence Appraisal
Build source-quality assessment, evidence appraisal and claim verification. Evaluate study type, quality, relevance, recency, clinical importance, consistency and uncertainty.

**Exit:** weak evidence cannot silently override stronger evidence.  
**Hard gate:** QA S20.

## Batch S21 -- Evidence to Learning Strategy
Link important relevant evidence to curriculum/proficiency and update learning strategy where justified. Archive non-material evidence metadata.

**Exit:** only justified evidence changes learning strategy.  
**Hard gate:** QA S21.

## Batch S22 -- Assessment Integrity Gate
Classify `GENERAL_LEARNING`, `ASSESSED_WORK`, `UNCLEAR`. Apply course-safe assistance rules.

**Exit:** Scholar supports learning without completing prohibited assessed work.  
**Hard gate:** QA S22.

## Batch S23 -- Project Research Intake
Create structurally separate `research_requests` with project, question, purpose, required output, success criteria, deadline, risk and state.

**Exit:** project research does not contaminate learner state.  
**Hard gate:** QA S23.

## Batch S24 -- Research Question Decomposition
Build `research-question-decomposition` with subquestions, evidence types, source hierarchy, unknowns and decision relevance.

**Exit:** complex research is structured before investigation.  
**Hard gate:** QA S24.

## Batch S25 -- Evidence Synthesis
Build `evidence-synthesis` and `research-to-tola`. Separate FACT / INFERENCE / HYPOTHESIS / UNKNOWN; include quality, conflicts, uncertainty and practical implications.

**Exit:** Tola receives traceable decision-ready research.  
**Hard gate:** QA S25.

## Batch S26 -- IntenSIQ Feature-Gap Detection
Build `intensiq-feature-gap-detection` and route `INTENSIQ_FEATURE_GAP` proposals to Tola with evidence, expected learning value and workaround state.

**Exit:** Scholar proposes missing capability but cannot build/bypass it.  
**Hard gate:** QA S26.

## Batch S27 -- Learning Effectiveness Review
Track goal progress, mastery change, retention, repeated weakness, time spent versus gain, plan revisions, proficiency coverage and study completion.

**Exit:** Scholar distinguishes effort from learning progress.  
**Hard gate:** QA S27.

## Batch S28 -- Daily/Weekly Proactivity
Event-driven response to learning evidence; lightweight daily checks for goal risk/unprocessed events/stale state/missed requirements; weekly review of mastery, proficiencies, capacity, literature and next requirements.

**Exit:** Scholar remains current without noisy constant polling.  
**Hard gate:** QA S28.

## Batch S29 -- Tola/Rhythm Cross-Agent Integration
Prove complete learning and research flows: Tola goal -> Scholar -> Rhythm capacity -> Scholar -> IntenSIQ -> evidence -> Scholar -> Tola, plus project research -> Tola.

**Exit:** no authority boundary crossed.  
**Hard gate:** QA S29.

## Batch S30 -- Controlled Pilot
Pilot one real critical-care learning goal plus real project research. Measure plan usefulness, mastery/gap accuracy, false readiness, event duplicates, plan churn, boundary violations, research quality, Ling failures, cost and latency.

**Exit:** repeated operation with zero critical integrity/authority failures.  
**Hard gate:** QA S30.

## Batch S31 -- Production Hardening and Freeze
Audit Ling-only routing, auth scopes, learner-state, versioning, event replay, curriculum/proficiency registry, mastery, Rhythm/Tola boundaries, literature/research, academic integrity, feature-gap process, audit trail and resilience.

**Deliverables:** final Scholar contract, IntenSIQ integration contract, auth map, schemas, Skill inventory, runbook and pilot report.

**Exit:** all QA gates passed with no critical unresolved defect.

---

# 18. Dependency Chain

```text
S0  Baseline
 -
S1  IntenSIQ capability contract
 -
S2  Integration auth
 -
S3  Learner state
 -
S4  Versioned learning plan
 -
S5  Event outbox
 -
S6  Event consumer
 -
S7  Curriculum registry
 -
S8  Proficiency registry
 -
S9  Learning goals
 -
S10 Goal decomposition
 -
S11 Learner-state analysis
 -
S12 Mastery model
 -
S13 Gap analysis
 -
S14 Adaptive strategy
 -
S15 Rhythm capacity
 -
S16 IntenSIQ plan orchestration
 -
S17 Feedback adaptation
 -
S18 Proficiency readiness
 -
S19 Literature discovery
 -
S20 Evidence appraisal
 -
S21 Evidence -> learning strategy
 -
S22 Assessment integrity
 -
S23 Project research intake
 -
S24 Research decomposition
 -
S25 Evidence synthesis
 -
S26 Feature-gap detection
 -
S27 Learning effectiveness
 -
S28 Proactivity
 -
S29 Cross-agent integration
 -
S30 Controlled pilot
 -
S31 Production freeze
```

---

# 19. Global Stop Rules

Immediately fail the active batch if:

- Scholar writes directly to My Rhythm;
- Scholar specifies calendar placement instead of study requirements;
- Scholar marks a study session complete;
- Scholar submits quiz/practice/assessment evidence;
- Scholar fabricates learner evidence;
- Scholar claims formal clinical sign-off without authoritative evidence;
- Scholar creates a second learning interface outside IntenSIQ;
- Scholar generates learner-facing study content as a workaround for a missing IntenSIQ feature;
- Scholar silently changes portfolio priority;
- Scholar delegates work to other agents;
- Scholar uses a model other than Ling 3.0 Flash for reasoning;
- duplicate events create duplicate logical effects;
- stale plan write overwrites a newer version;
- project research contaminates learner state;
- assessed-work restrictions are bypassed;
- source quality is hidden in research synthesis;
- Blackboard becomes a copy of detailed IntenSIQ study content;
- a proficiency's original wording is lost or overwritten.

---

# 20. Programme Definition of Done

Scholar V1 is complete when it can repeatedly:

1. understand the course/curriculum from versioned sources;
2. ingest future Step 2/Step 3 proficiency context without redesign;
3. accept persistent learning goals;
4. read current IntenSIQ learner state;
5. identify evidence-backed gaps;
6. estimate multidimensional mastery;
7. build adaptive learning strategy;
8. request realistic study capacity from Rhythm;
9. write a versioned learning plan to IntenSIQ;
10. never schedule calendar time itself;
11. consume durable IntenSIQ events;
12. adapt strategy when evidence changes;
13. monitor proficiency readiness without self-sign-off;
14. discover/appraise important literature;
15. incorporate material evidence into learning strategy;
16. enforce assessment-integrity boundaries;
17. perform rigorous project research for Tola;
18. distinguish fact/inference/hypothesis/unknown;
19. propose IntenSIQ feature gaps to Tola;
20. use Ling 3.0 Flash as the sole reasoning model;
21. preserve evidence integrity;
22. pass every QA gate.

---

# 21. Final Principle

Scholar should not be judged by how much content it produces.

Scholar should be judged by whether it improves the quality, direction and efficiency of learning and research.

> **Scholar thinks. IntenSIQ teaches. Rhythm schedules. Tola prioritises.**
