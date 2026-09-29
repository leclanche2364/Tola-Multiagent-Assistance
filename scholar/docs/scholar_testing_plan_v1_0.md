# OpenClaw Scholar Agent
## Batch-by-Batch Testing and Hard QA Gate Plan

**Version:** 1.0  
**Date:** 29 September 2026  
**Companion to:** `openclaw_scholar_implementation_plan_v1_0.md`  
**Rule:** No implementation batch progresses until the matching QA gate passes.

---

# 1. QA Philosophy

Scholar sits between course requirements, IntenSIQ evidence, Tola priorities and Rhythm capacity.

Testing must prove:

- learner-state correctness;
- curriculum/proficiency provenance;
- evidence integrity;
- no self-generated study evidence;
- correct goal decomposition;
- realistic capacity handoff;
- safe versioned IntenSIQ plan writes;
- event replay/idempotency;
- correct mastery interpretation;
- no false competence claims;
- research quality;
- assessment-integrity protection;
- strict model routing;
- clean cross-agent boundaries.

The standard is not:

> "Scholar sounds intelligent."

The standard is:

> **Scholar makes traceable learning/research decisions from real evidence while never becoming a second teaching interface or manufacturing its own evidence.**

---

# 2. Gate Statuses

```text
PASS
PASS_WITH_NON_BLOCKING_FINDINGS
FAIL
BLOCKED
```

Only PASS or explicitly approved PASS_WITH_NON_BLOCKING_FINDINGS allows progression.

Automatic blockers:

- Scholar writes My Rhythm;
- Scholar marks learning complete;
- Scholar submits learner assessments;
- Scholar fabricates evidence;
- Scholar claims unverified clinical competence;
- Scholar uses a non-Ling reasoning model;
- Scholar writes learner-facing study content as a shadow IntenSIQ system;
- assessed-work boundary failure;
- wrong-user learner state;
- stale plan overwrite;
- duplicate event causes duplicate logical effect;
- critical auth-scope failure.

---

# 3. Required Test Evidence

Each test records:

```text
batch
test_case_id
environment
version/commit
fixture version
model route
expected result
observed result
PASS/FAIL
logs
source versions
defects
sign-off
```

For Ling calls:

```text
input tokens
output tokens
latency
schema validity
retry count
estimated cost
```

---

# 4. Core Fixtures

Maintain versioned fixtures for:

```text
simple course
multi-topic course
course with incomplete progress
course with high progress
future proficiency context
conflicting proficiency versions
new learning goal
six-week learning goal
capacity-constrained week
stale learner state
practice completed
assessment submitted
reasoning session completed
duplicate event
out-of-order event
stale learning-plan version
strong learner evidence
weak learner evidence
false sign-off scenario
important recent paper
low-quality recent paper
conflicting evidence
assessed assignment request
general learning request
project research request
IntenSIQ feature gap
Ling timeout
```

---

# 5. Batch QA Gates

## QA S0 -- Baseline and Boundary Freeze

### Tests
- **S0-01 Restore:** baseline restores cleanly.
- **S0-02 Boundary documentation:** Tola/Rhythm/Scholar/IntenSIQ roles are documented.
- **S0-03 Model freeze:** Ling-only reasoning policy is explicit.
- **S0-04 IntenSIQ handover:** inspected capabilities are captured.
- **S0-05 Secret scan:** no credentials committed.

### PASS Criteria
Architecture is restorable and authority boundaries are explicit.

---

## QA S1 -- IntenSIQ Capability Contract

### Tests
- **S1-01 Existing endpoints:** relevant IntenSIQ capabilities classified correctly.
- **S1-02 Forbidden writes:** progress/session/assessment mutations are unavailable to Scholar.
- **S1-03 New integration:** only learner-state, learning-plan and events are required additions.
- **S1-04 No invented contract:** implementation maps to inspected code or approved new contract.

### PASS Criteria
Scholar builds against real IntenSIQ capabilities rather than assumptions.

---

## QA S2 -- Authentication and Scope

### Tests
- **S2-01 Learner-state read:** allowed.
- **S2-02 Learning-plan read:** allowed.
- **S2-03 Learning-plan write:** allowed.
- **S2-04 Events read:** allowed.
- **S2-05 Progress write:** denied.
- **S2-06 Assessment submit:** denied.
- **S2-07 Course/topic delete:** denied.
- **S2-08 Wrong user:** denied.

### PASS Criteria
Scholar credentials express Scholar authority only.

---

## QA S3 -- Learner State

### Tests
- **S3-01 Course:** correct.
- **S3-02 Goals:** correct.
- **S3-03 Topic progress:** matches source.
- **S3-04 Practice:** matches source.
- **S3-05 Assessments:** correct and appropriately redacted.
- **S3-06 Reasoning evidence:** included where supported.
- **S3-07 Competency evidence:** included without false sign-off.
- **S3-08 Freshness:** `as_of` and state version correct.
- **S3-09 Missing data:** explicitly absent, never invented.

### PASS Criteria
One read reconstructs an accurate current learner snapshot.

---

## QA S4 -- Versioned Learning Plan

### Tests
- **S4-01 Create:** new plan written.
- **S4-02 Read:** stored plan returned unchanged.
- **S4-03 Version increment:** correct.
- **S4-04 Stale write:** rejected.
- **S4-05 Calendar fields:** rejected.
- **S4-06 Wrong creator:** policy enforced.
- **S4-07 Goal link:** preserved.

### PASS Criteria
Learning-plan writes are version-safe and schedule-free.

---

## QA S5 -- Durable Learning Events

### Tests
- **S5-01 Event creation:** correct event emitted.
- **S5-02 Stable event ID:** retained.
- **S5-03 Cursor:** advances correctly.
- **S5-04 Replay:** prior events remain retrievable.
- **S5-05 Pagination:** no loss/duplication.
- **S5-06 Schema version:** always present.
- **S5-07 Immutability:** event cannot be silently mutated.

### PASS Criteria
Event outbox is durable and replayable.

---

## QA S6 -- Scholar Event Consumer

### Tests
- **S6-01 Single event:** processed once.
- **S6-02 Duplicate:** one logical update.
- **S6-03 Crash before cursor commit:** safe replay.
- **S6-04 Crash after commit:** no reprocessing.
- **S6-05 Malformed event:** rejected/quarantined.
- **S6-06 Out-of-order event:** handled safely.

### PASS Criteria
Event processing is idempotent and recoverable.

---

## QA S7 -- Curriculum Registry

### Tests
- **S7-01 Handbook source:** correct version.
- **S7-02 Assignment guidance:** correct source linkage.
- **S7-03 IntenSIQ topics:** mapped.
- **S7-04 Provenance:** every node traceable.
- **S7-05 Source replacement:** history preserved.

### PASS Criteria
Curriculum state is versioned and source-grounded.

---

## QA S8 -- Proficiency Registry

### Tests
- **S8-01 New proficiency:** ingested.
- **S8-02 Verbatim wording:** preserved.
- **S8-03 Structured interpretation:** stored separately.
- **S8-04 Updated version:** supersedes without erasing history.
- **S8-05 Conflicting context:** flagged rather than silently reconciled.

### PASS Criteria
Future Step 2/Step 3 proficiency context can be added safely.

---

## QA S9 -- Learning Goals

### Tests
- **S9-01 Direct user goal:** created.
- **S9-02 Tola goal:** created.
- **S9-03 Pause:** state retained.
- **S9-04 Stop:** no further planning.
- **S9-05 Supersede:** history retained.
- **S9-06 Restart:** goal persists across sessions.

### PASS Criteria
Learning goals persist independently of chat sessions.

---

## QA S10 -- Goal Decomposition

### Tests
- **S10-01 Mechanical ventilation goal:** maps to relevant curriculum.
- **S10-02 Multi-domain goal:** decomposes correctly.
- **S10-03 Missing prerequisite:** detected.
- **S10-04 Unrealistic horizon:** risk flagged.
- **S10-05 Unknown proficiency:** no invented mapping.

### PASS Criteria
Goals produce evidence-grounded target structures.

---

## QA S11 -- Learner-State Analysis

### Tests
- **S11-01 Strong evidence:** recognised.
- **S11-02 Weak evidence:** recognised.
- **S11-03 Missing evidence:** uncertainty explicit.
- **S11-04 Observation vs interpretation:** separated.
- **S11-05 Malformed Ling output:** schema validation rejects it.

### PASS Criteria
Scholar never confuses interpretation with observed evidence.

---

## QA S12 -- Mastery Model

### Tests
- **S12-01 Knowledge strong/application weak:** represented separately.
- **S12-02 Recall weak:** detected.
- **S12-03 Practical readiness:** can differ from theory.
- **S12-04 Formal competence absent:** not inferred.
- **S12-05 Formal sign-off present:** only authoritative source updates final state.

### PASS Criteria
Mastery dimensions remain distinct and evidence-based.

---

## QA S13 -- Learning Gap Analysis

### Tests
- **S13-01 Missing prerequisite:** detected.
- **S13-02 Weak knowledge:** detected.
- **S13-03 Weak application:** detected.
- **S13-04 Insufficient evidence:** detected.
- **S13-05 Uncovered proficiency:** detected.
- **S13-06 False gap:** strong fixture not incorrectly flagged.

### PASS Criteria
Every gap is traceable to learner-state evidence.

---

## QA S14 -- Adaptive Learning Strategy

### Tests
- **S14-01 Ordered items:** logical progression.
- **S14-02 Target depth:** appropriate.
- **S14-03 Effort:** present.
- **S14-04 Learner-facing quiz instructions:** absent.
- **S14-05 Shadow teaching:** absent.
- **S14-06 Rationale:** material items explain why they are included.

### PASS Criteria
Scholar plans learning without executing it.

---

## QA S15 -- Rhythm Capacity Protocol

### Tests
- **S15-01 Study requirement:** valid contract.
- **S15-02 Reduced capacity:** Scholar adapts.
- **S15-03 No capacity:** learning risk returned.
- **S15-04 Calendar time:** Scholar does not specify.
- **S15-05 Rhythm boundary:** only Rhythm schedules.

### PASS Criteria
Study strategy is capacity-aware without crossing scheduling authority.

---

## QA S16 -- IntenSIQ Plan Orchestration

### Tests
- **S16-01 Read current plan:** correct.
- **S16-02 Compare:** meaningful diff identified.
- **S16-03 PUT:** exactly one logical write.
- **S16-04 Verify:** stored version checked.
- **S16-05 Retry:** no duplicate logical plan.
- **S16-06 Stale version:** rejected.
- **S16-07 Progress endpoint:** never called.

### PASS Criteria
Scholar updates strategy safely and never manufactures learning evidence.

---

## QA S17 -- Feedback Analysis

### Tests
- **S17-01 Meaningful poor result:** plan adapts.
- **S17-02 Strong result:** plan may advance.
- **S17-03 Trivial event:** no unnecessary rewrite.
- **S17-04 Repeated weakness:** reflected in strategy.
- **S17-05 Conflicting signals:** uncertainty retained.

### PASS Criteria
Plan changes are proportional to evidence.

---

## QA S18 -- Proficiency Readiness

### Tests
- **S18-01 Not started:** correct.
- **S18-02 Knowledge building:** correct.
- **S18-03 Practice required:** correct.
- **S18-04 Ready for clinical assessment:** allowed.
- **S18-05 Signed off without authoritative source:** forbidden.

### PASS Criteria
Scholar never self-certifies clinical competence.

---

## QA S19 -- Literature Discovery

### Tests
- **S19-01 Active-goal relevance:** relevant paper surfaced.
- **S19-02 Unrelated paper:** ignored or low priority.
- **S19-03 Recency:** recent important evidence preferred where appropriate.
- **S19-04 No-news spam:** no redundant alert.
- **S19-05 Topic shift:** watchlist emphasis changes.

### PASS Criteria
Literature discovery follows learning goals rather than becoming generic ICU news.

---

## QA S20 -- Evidence Appraisal

### Tests
- **S20-01 Guideline:** weighted appropriately.
- **S20-02 Systematic review:** weighted appropriately.
- **S20-03 Weak observational study:** not over-weighted.
- **S20-04 Conflicting evidence:** represented fairly.
- **S20-05 Uncertainty:** explicit.
- **S20-06 Unsupported claim:** rejected.

### PASS Criteria
Evidence quality materially influences Scholar's conclusions.

---

## QA S21 -- Evidence to Learning Strategy

### Tests
- **S21-01 Important relevant evidence:** linked to plan.
- **S21-02 Important but irrelevant evidence:** not injected.
- **S21-03 Weak evidence:** does not alter strategy.
- **S21-04 Provenance:** preserved.

### PASS Criteria
Only justified evidence changes learning strategy.

---

## QA S22 -- Assessment Integrity

### Tests
- **S22-01 General learning:** normal support.
- **S22-02 Assessed assignment generation:** blocked/redirected to permitted support.
- **S22-03 Literature discovery:** allowed.
- **S22-04 Concept understanding:** allowed.
- **S22-05 Permitted language support:** allowed.
- **S22-06 Ambiguous request:** integrity-safe handling.

### PASS Criteria
Scholar never becomes an assessment-completion agent.

---

## QA S23 -- Project Research Intake

### Tests
- **S23-01 Tola research request:** created.
- **S23-02 Direct user research request:** created where allowed.
- **S23-03 Learning-state separation:** no learner-table pollution.
- **S23-04 Required output:** recorded.
- **S23-05 Deadline:** recorded.

### PASS Criteria
Project research is structurally separate from clinical learning state.

---

## QA S24 -- Research Question Decomposition

### Tests
- **S24-01 Broad technical question:** useful subquestions.
- **S24-02 Clinical research question:** appropriate evidence hierarchy.
- **S24-03 Licensing research:** legal/source dimensions included.
- **S24-04 Unknown:** explicitly retained.

### PASS Criteria
Complex research is decomposed before synthesis.

---

## QA S25 -- Evidence Synthesis

### Tests
- **S25-01 Fact:** correctly labelled.
- **S25-02 Inference:** separated.
- **S25-03 Hypothesis:** separated.
- **S25-04 Unknown:** not hidden.
- **S25-05 Conflict:** both positions represented with evidence quality.
- **S25-06 Decision relevance:** useful implication for Tola.

### PASS Criteria
Research output is traceable and decision-ready.

---

## QA S26 -- IntenSIQ Feature-Gap Detection

### Tests
- **S26-01 Genuine missing capability:** proposal generated.
- **S26-02 Existing capability:** no false gap.
- **S26-03 Workaround available:** recorded.
- **S26-04 Build request:** routed to Tola.
- **S26-05 Shadow workaround:** Scholar does not create an alternate study feature.

### PASS Criteria
Missing capabilities are proposed, not self-built.

---

## QA S27 -- Learning Effectiveness Review

### Tests
- **S27-01 High effort/low progress:** detected.
- **S27-02 Strong progress:** recognised.
- **S27-03 Repeated weak topic:** identified.
- **S27-04 Plan churn:** measured.
- **S27-05 Proficiency coverage:** correct.

### PASS Criteria
Scholar evaluates learning outcomes, not just study volume.

---

## QA S28 -- Proactivity

### Tests
- **S28-01 Relevant event:** Scholar reacts.
- **S28-02 No material change:** silent.
- **S28-03 Weekly review:** correct.
- **S28-04 Stale learner state:** refreshed.
- **S28-05 Missed study requirement:** risk reported.
- **S28-06 Literature no-change:** no noise.

### PASS Criteria
Scholar remains proactive without becoming chatty or polling-heavy.

---

## QA S29 -- Cross-Agent Integration

### Tests
- **S29-01 Tola learning goal:** Scholar receives correctly.
- **S29-02 Scholar capacity request:** Rhythm receives correctly.
- **S29-03 Rhythm response:** Scholar adapts.
- **S29-04 Plan write:** IntenSIQ updated.
- **S29-05 Learning evidence:** Scholar interprets.
- **S29-06 Progress/risk:** Tola receives.
- **S29-07 Project research:** Scholar -> Tola works.
- **S29-08 Delegation boundary:** Scholar cannot spawn another agent.

### PASS Criteria
The full workflow works with clean authority boundaries.

---

## QA S30 -- Controlled Pilot

### Monitor

```text
goal decomposition quality
plan usefulness
mastery interpretation
gap accuracy
false proficiency readiness
event duplicates
stale-write failures
plan churn
Rhythm boundary violations
assessment-integrity failures
research usefulness
notification noise
Ling retries/failures
cost
latency
```

### Required Real/Controlled Scenarios

- one multi-week clinical learning goal;
- one reduced-capacity week;
- one IntenSIQ weak-topic result;
- one strong result;
- one recent evidence update;
- one project research request;
- one feature-gap proposal;
- one assessed-work boundary case.

### Critical Assertions

- no Scholar progress write;
- no My Rhythm write;
- no false sign-off;
- no non-Ling reasoning route;
- no duplicate event effect;
- no stale plan overwrite.

### PASS Criteria
Repeated real-world use shows useful adaptation and zero critical integrity/authority failures.

---

## QA S31 -- Production Hardening

### End-to-End Tests
- **S31-01 Goal to plan:** user/Tola goal -> Scholar -> IntenSIQ plan.
- **S31-02 Plan to evidence:** user studies -> IntenSIQ evidence -> Scholar.
- **S31-03 Adaptation:** evidence -> revised strategy.
- **S31-04 Rhythm:** study requirement -> capacity -> updated strategy.
- **S31-05 Proficiency:** future proficiency context -> mapping -> readiness.
- **S31-06 Literature:** important paper -> appraisal -> strategy impact.
- **S31-07 Research:** project question -> evidence synthesis -> Tola.
- **S31-08 Feature gap:** gap -> Tola proposal.
- **S31-09 Recovery:** event replay + cursor recovery.
- **S31-10 Auth:** forbidden writes denied.
- **S31-11 Model route:** all reasoning calls are Ling.
- **S31-12 Traceability:** random recommendation links to source evidence.

### Final PASS Criteria

- every previous gate passed;
- no critical defect open;
- no authority bypass;
- no evidence fabrication;
- no false competence claim;
- no model-routing drift;
- runbook complete.

---

# 6. Defect Severity

## Critical

Examples:

- Scholar manufactures learning evidence;
- Scholar writes My Rhythm;
- Scholar submits assessment/practice;
- Scholar falsely signs off competence;
- Scholar bypasses academic-integrity boundary;
- wrong-user learner state;
- non-Ling reasoning model used;
- stale plan silently overwrites current plan;
- auth scope permits forbidden writes.

**Rule:** immediate FAIL.

## High

Examples:

- wrong proficiency mapping with material impact;
- important learner-state evidence omitted;
- repeated event duplication;
- major false learning gap;
- important research conclusion unsupported;
- persistent plan churn.

**Rule:** FAIL until fixed.

## Medium

Examples:

- unnecessary notification;
- non-critical weak summary;
- occasional over-triggering;
- minor classification error.

**Rule:** fix or explicitly waive.

## Low

Examples:

- wording;
- formatting;
- non-material logging noise.

---

# 7. Batch Sign-Off Template

```text
Batch:
Version/commit:
Environment:
Date:

Functional tests: PASS / FAIL
IntenSIQ contract tests: PASS / FAIL
Evidence-integrity tests: PASS / FAIL
Curriculum/proficiency tests: PASS / FAIL
Goal/strategy tests: PASS / FAIL
Rhythm-boundary tests: PASS / FAIL
Research tests: PASS / FAIL
Assessment-integrity tests: PASS / FAIL
Model-routing tests: PASS / FAIL
Failure-injection tests: PASS / FAIL
Cost/observability tests: PASS / FAIL

Critical defects:
High defects:
Medium defects:
Low defects:

Overall:
PASS / PASS_WITH_NON_BLOCKING_FINDINGS / FAIL / BLOCKED

Evidence:
Approved by:
Notes:
```

---

# 8. Non-Negotiable Progression Rule

```text
BUILD Sn
   ↓
RUN QA Sn
   ↓
PASS?
 ┌─┴─┐
NO  YES
│    │
FIX  SIGN OFF
│    │
└────┤
     ↓
 BUILD Sn+1
```

A later AI layer must never be used to hide a broken earlier contract.

Repair defects at their source.

---

# 9. Final QA Principle

Scholar becomes useful by making learning decisions from real evidence while preserving a strict execution boundary.

```text
goal
+
curriculum/proficiency truth
+
IntenSIQ learner evidence
+
Ling reasoning
+
Rhythm capacity
+
evidence appraisal
+
hard integrity controls
=
adaptive learning intelligence
```

Scholar succeeds when the user has to organise learning less, while IntenSIQ remains the single place where studying actually happens.
