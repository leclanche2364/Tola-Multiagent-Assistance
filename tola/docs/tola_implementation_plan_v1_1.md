> **SUPERSEDED**: this document is a historical plan, kept as history only. The current architecture contract is [docs/CURRENT_SYSTEM.md](../../docs/CURRENT_SYSTEM.md). Do not follow its architecture or model-routing claims.

# OpenClaw Tola Agent
## Portfolio Executive, Delegation, Outcome Assurance, Persona Awareness and Self-Improvement
### Batch-by-Batch Implementation Plan

**Version:** 1.1  
**Date:** 29 September 2026  
**Primary agent:** Tola  
**Role:** Chief of Staff / Portfolio Executive Agent  
**Primary reasoning route:** GLM-5.3 Flash (existing architecture default)  
**Specialists:** Rhythm, Growth, Scholar  
**Shared state:** Supabase Blackboard + SQLite cache/outbox  
**Companion:** `openclaw_tola_testing_plan_v1_1.md`

---

# 1. Purpose

This plan upgrades Tola from a capable delegator into the most strategically aware and proactive agent in the four-agent system.

Tola must maintain an accurate understanding of:

- all active projects and goals;
- commitments and deadlines;
- active, blocked and stalled work;
- experiments and outcomes;
- pending decisions and approvals;
- specialist capabilities, boundaries, workload and performance;
- Rhythm capacity state;
- Growth findings;
- Scholar learning requirements;
- the user's stable working and communication preferences;
- Tola's own measured strengths, weaknesses and failure patterns.

Tola must be able to identify what matters, create and improve plans, delegate appropriately, monitor work, verify outcomes, recover stalled work, control scope, communicate clearly, learn how to help the user better, and improve her own procedures through measured evidence.

The target is not a conversational orchestrator. It is a **Portfolio Executive Agent**.

---

# 2. Mission

> Maintain an accurate understanding of the user's projects, commitments, priorities and agent system; continuously identify what matters; create or improve plans; delegate work to the appropriate specialist; monitor execution; verify outcomes; resolve cross-domain trade-offs; and communicate the minimum information the user needs to remain informed and in control.

Tola does not merely delegate tasks. **Tola owns the quality of the overall outcome.**

---

# 3. Core Loop

```text
OBSERVE
   ↓
SYNTHESIZE PORTFOLIO STATE
   ↓
DETECT WHAT MATTERS
   ↓
ANALYSE
   ↓
CREATE / IMPROVE PLAN
   ↓
CHECK CAPACITY IF NEEDED
   ↓
DELEGATE
   ↓
MONITOR
   ↓
VERIFY OUTCOME
   ↓
CORRECT / RECOVER IF NEEDED
   ↓
CLOSE
   ↓
LEARN
   ↓
REPEAT
```

---

# 4. Frozen Authority Boundaries

## Tola owns

- portfolio priorities;
- cross-project trade-offs;
- delegation;
- goal-to-plan decomposition;
- specialist selection;
- success criteria;
- plan review;
- scope control;
- project health assessment;
- outcome verification;
- stalled-work recovery;
- materiality and attention decisions;
- deciding when Rhythm must be queried;
- deciding whether specialist work should be accepted, revised, stopped or extended.

## Rhythm owns

- work-shift truth;
- realistic capacity;
- schedule feasibility;
- exact time placement;
- My Rhythm writes;
- dynamic replanning.

Tola must never write directly to My Rhythm.

For substantial work:

```text
Tola → CAPACITY_QUERY → Rhythm → CAPACITY_REPORT
     → Tola decision → TASK_COMMITTED → Rhythm schedules
```

## Growth owns

- product/growth analysis;
- acquisition, activation, conversion and retention intelligence;
- experiment design and analysis;
- product metrics and growth recommendations.

## Scholar owns

- learning intelligence;
- curriculum planning;
- evidence synthesis;
- study requirements;
- learning-gap detection.

## User authority

Tola may not silently change:

- security policy;
- tool permissions;
- approval boundaries;
- production model-routing architecture;
- external integrations;
- consequential public actions;
- durable architecture decisions requiring approval.



## Future Marketing Agent Pool — NOT YET AVAILABLE

Marketing specialist agents are part of the planned expansion of Tola's specialist pool, but they are **not available in the current four-agent build**.

Build order:

```text
CURRENT
1. Tola
2. Scholar

NEXT SPECIALIST EXPANSION
3. Marketing Agent(s)
```

Until those agents are implemented, tested and explicitly activated, their capability-registry state must remain:

```text
availability_status = FUTURE_NOT_AVAILABLE
```

Tola may understand that future Marketing Agents are intended capabilities and may identify work that would eventually suit them, but she must **not delegate tasks to an unavailable agent**.

Before Marketing Agents exist, marketing-related work follows this routing:

```text
marketing / acquisition / campaign requirement
        ↓
Can Growth own it under the current Growth contract?
        ├── YES → delegate to Growth
        └── NO  → record FUTURE_SPECIALIST_DEPENDENCY
                    ↓
               retain as deferred work
                    ↓
               surface only when material
```

An unavailable Marketing Agent must never be simulated as though it completed work.

Future marketing capabilities may eventually include:

```text
acquisition execution
SEO / ASO execution
content distribution
community growth
campaign operations
lifecycle / CRM marketing
paid acquisition where explicitly authorised
partnership / outreach execution
```

These specialisations are **not frozen yet**. Their final contracts and boundaries will be designed during the Marketing Agent implementation phase.

The agent capability registry therefore requires an explicit availability state:

```text
ACTIVE
FUTURE_NOT_AVAILABLE
DISABLED
DEGRADED
```

Normal autonomous delegation is allowed only to `ACTIVE` agents.

Activation of any future Marketing Agent requires:

```text
agent contract complete
capability profile complete
boundary rules complete
allowed tools complete
security review complete
batch QA complete
Tola delegation tests complete
availability_status changed to ACTIVE
```

Only then may Tola include the Marketing Agent in normal autonomous delegation.

---

# 5. Intelligence Architecture

```text
                       TOLA
                         │
      ┌──────────────────┼───────────────────┐
      │                  │                   │
      ▼                  ▼                   ▼
PORTFOLIO MODEL    USER OPERATING      AGENT SYSTEM
                       PROFILE             MODEL
      │                  │                   │
      └─────────────┬────┴────┬──────────────┘
                    ▼         ▼
               EXECUTIVE   PERFORMANCE
                REASONING     MODEL
                    │         │
                    └────┬────┘
                         ▼
                SELF-IMPROVEMENT
                      ENGINE
                         │
         ┌───────────────┼────────────────┐
         ▼               ▼                ▼
     automatic       Skill proposal   architecture
     safe learning      + tests         proposal
```

---

# 6. PortfolioSnapshot

Tola needs a compact current `PortfolioSnapshot` containing:

```text
snapshot_version
generated_at
projects
active_goals
current_priorities
deadlines
commitments
capacity_summary
active_tasks
blocked_tasks
experiments
material_metrics
risks
pending_decisions
pending_approvals
agent_state
recent_outcomes
stalled_work
source_versions
```

The snapshot is a synthesis layer, not the source of truth.

---

# 7. Agent Capability Profiles

For active specialists and planned future specialists, Tola should know:

```text
agent_id
domain
responsibilities
allowed_tools
forbidden_actions
skills
current_status
current_load
recent_success_rate
recent_partial_rate
recent_blocked_rate
average_latency
typical_strengths
known_failure_patterns
cost_profile
availability_status
activation_requirements
last_updated_at
```

Measured performance may improve delegation, but never overrides domain authority or availability state. A future Marketing Agent may be visible to Tola while remaining non-delegable.

---

# 8. Delegation Quality Standard

Before significant delegation Tola determines:

```text
objective
domain owner
required output
success criteria
evidence required
deadline
dependencies
capacity requirement
risk class
model route
allowed tools
follow-up time
```

A delegation is incomplete if the specialist cannot tell when it is finished.

---

# 9. Plan Quality Gate

Material plans are reviewed for:

```text
OBJECTIVE
EVIDENCE
ASSUMPTIONS
ALTERNATIVES
DEPENDENCIES
CAPACITY
RISKS
SUCCESS METRICS
GUARDRAILS
OWNER
DEADLINE
REVERSIBILITY
```

Results:

```text
APPROVE
APPROVE_WITH_CHANGES
REVISE
REJECT
NEEDS_USER_DECISION
```

Review classes:

```text
ROUTINE
MATERIAL
CROSS_DOMAIN
CONSEQUENTIAL
```

Routine work must not be bottlenecked by Tola.

---

# 10. Outcome Assurance

A specialist reply does not equal completion.

Tola verifies:

```text
required output present?
success criteria met?
evidence present?
data quality acceptable?
question answered?
actionable next step present?
dependencies resolved?
material risks understood?
```

Outcome status:

```text
SUCCESS
PARTIAL
BLOCKED
NEEDS_REVISION
NEEDS_APPROVAL
FAILED
```

---

# 11. Persona Awareness

Create:

```text
user_operating_profile
user_preference_observations
user_preference_versions
```

Track useful working preferences such as:

```text
communication detail
briefing structure
technical depth
decision presentation
notification tolerance
planning preference
automation preference
project-working style
```

Preference authority:

```text
EXPLICIT USER INSTRUCTION  >  REPEATED OBSERVATION  >  SINGLE OBSERVATION  >  MODEL INFERENCE
```

Model inference alone cannot create a permanent preference.

Do not infer/store sensitive personal traits merely for personalization.

---

# 12. Tola Performance Model

Measure Tola using:

```text
delegation_success_rate
first_pass_completion_rate
partial_result_rate
blocked_rate
user_correction_rate
plan_revision_rate
stalled_task_recovery_rate
average_retries
average_latency
average_cost
founder_brief_clarification_rate
correct_escalation_rate
incorrect_escalation_rate
outcome_verification_accuracy
```

This is evidence-based self-awareness, not self-description.

---

# 13. Self-Improvement

Create:

```text
tola_learning_observations
tola_performance_metrics
tola_improvement_candidates
tola_improvement_evaluations
```

Self-improvement loop:

```text
ACTION
 ↓
RESULT
 ↓
EXPECTED vs ACTUAL
 ↓
ROOT CAUSE
 ↓
REUSABLE LESSON?
 ↓
IMPROVEMENT CANDIDATE
 ↓
BENCHMARK
 ↓
BETTER THAN BASELINE?
 ↓
PROPOSE
 ↓
APPROVAL
 ↓
APPLY
```

Automatic:

```text
record learning observation
update performance metrics
update delegation confidence
adjust bounded task-estimate heuristic
record candidate preference
promote stable non-sensitive preference
supersede contradicted preference
adjust communication verbosity within policy
```

Proposal-only:

```text
change Skill
change agent contract
change tool permission
change approval boundary
change architecture
add external integration
change security policy
change production model-routing architecture
```

Use Skill Workshop in proposal-first mode for durable Skill changes.

---

# 14. Automation Strategy

Do not use cron for everything.

Use four mechanisms:

## Events

Immediate signals such as:

```text
USER_CORRECTION
USER_OVERRIDE
USER_PREFERENCE_SIGNAL
DELEGATION_SUCCESS
DELEGATION_PARTIAL
DELEGATION_FAILED
PLAN_APPROVED
PLAN_REVISED
PLAN_REJECTED
TASK_STALLED
TASK_RECOVERED
OUTCOME_SUCCESS
OUTCOME_FAILURE
OUTCOME_INCONCLUSIVE
SPECIALIST_RESULT_ACCEPTED
SPECIALIST_RESULT_REJECTED
COMMUNICATION_CLARIFICATION_REQUIRED
RHYTHM_OVERLOAD
EXPERIMENT_COMPLETED
DEADLINE_RISK
APPROVAL_REQUIRED
```

## Heartbeat

Cheap deterministic checks first:

```text
overdue task?
unanswered specialist request?
approval waiting too long?
blocked work unchanged?
experiment completed but unreviewed?
Rhythm overload unresolved?
high-priority deadline at risk?
PortfolioSnapshot stale?
decision review due?
```

Only wake Tola when material.

## Scheduled Automations

Daily:

```text
portfolio reconciliation
material-change review
risk/decision scan
```

Weekly:

```text
executive portfolio review
persona consolidation
self-improvement review
agent performance review
```

Monthly:

```text
deep operating-system review
portfolio value review
automation value review
agent bottleneck analysis
cost review
scope review
```

## Post-work learning

Substantial work should generate learning evidence when results differ materially from expectation.

---

# 15. Communication Contract

For significant updates answer:

```text
WHAT happened?
WHY does it matter?
WHAT does Tola think?
WHAT is Tola doing?
WHAT does the user need to do?
```

The last answer should often be:

```text
Nothing — handled automatically.
```

Attention levels:

```text
SILENT
DIGEST
NOTIFY
DECISION_REQUIRED
URGENT
```

Use progressive disclosure: implication first, evidence second, deep detail only when useful.

---

# 16. Core Skills

```text
portfolio-state-synthesis
priority-triage
goal-to-plan
delegation-planner
plan-critic
cross-agent-synthesis
outcome-verifier
stalled-work-recovery
scope-control
decision-quality-check
founder-briefing
portfolio-review
risk-and-dependency-scan
follow-through
persona-awareness
preference-consolidation
self-performance-review
improvement-candidate-generator
```

---

# 17. Batch-by-Batch Implementation

## Batch T0 — Baseline, Backup and Architecture Freeze

**Build**

- back up OpenClaw configuration;
- capture current Tola prompt/contract;
- capture active Skills;
- capture Blackboard schema;
- capture current task/delegation contract;
- document Rhythm/Growth/Scholar boundaries;
- record model routing;
- create `/tola` implementation area.

Suggested structure:

```text
/tola
  /contracts
  /portfolio
  /delegation
  /review
  /outcomes
  /persona
  /performance
  /improvement
  /automation
  /skills
  /reports
  /tests
  /fixtures
  /docs
```

**Exit:** existing Tola can be restored exactly.  
**Gate:** QA T0.

---

## Batch T1 — Portfolio Data Contract

Define typed contracts and authoritative sources for:

```text
projects
goals
milestones
tasks
commitments
deadlines
experiments
metrics
risks
decisions
approvals
outcomes
```

**Exit:** every executive input has one documented source of truth.  
**Gate:** QA T1.

---

## Batch T2 — PortfolioSnapshot Builder

Implement:

```text
portfolio_snapshot_build()
portfolio_snapshot_refresh()
portfolio_snapshot_get()
portfolio_snapshot_diff()
portfolio_snapshot_validate()
```

Include source versions/freshness. Keep snapshot compact.

**Exit:** Tola can reconstruct current portfolio without conversational memory.  
**Gate:** QA T2.

---

## Batch T3 — Project Health and Materiality Engine

Add signals for:

```text
deadline risk
blocked duration
stalled activity
milestone slippage
experiment awaiting decision
unresolved approval
capacity conflict
metric deterioration
no next action
```

Health summary:

```text
ON_TRACK
ATTENTION
AT_RISK
BLOCKED
DORMANT
```

**Exit:** material problems are reliably surfaced.  
**Gate:** QA T3.

---

## Batch T4 — Agent Capability and Boundary Registry

Create:

```text
agent_operating_profiles
agent_capabilities
agent_boundaries
agent_skills
```

Implement:

```text
agent_capability_get()
agent_capability_match()
agent_boundary_check()
agent_current_load_get()
```

**Exit:** Tola knows what each specialist owns and may do.  
**Gate:** QA T4.

---

## Batch T5 — Agent Performance Metrics

Track by task type and time window:

```text
success
partial
blocked
retry
latency
cost
human correction
```

Short-term noise must not dominate routing.

**Exit:** delegation can consider measured reliability without violating domain boundaries.  
**Gate:** QA T5.

---

## Batch T6 — Priority Triage Engine

Inputs:

```text
priority
deadline
risk
dependency impact
capacity
protected commitments
business impact
blocked duration
```

Implement:

```text
priority_triage()
materiality_check()
attention_required()
```

**Exit:** Tola distinguishes routine/material/cross-domain/consequential work.  
**Gate:** QA T6.

---

## Batch T7 — Goal-to-Plan Skill

Create `goal-to-plan`.

Plans include:

```text
goal
current state
assumptions
milestones
dependencies
owners
success criteria
risks
capacity needs
review points
stop conditions
```

**Exit:** user goals become coherent multi-agent plans.  
**Gate:** QA T7.

---

## Batch T8 — Delegation Planner

Create `delegation-planner`.

Each significant task defines:

```text
owner
required output
success criteria
evidence
deadline
dependencies
risk class
model route
allowed tools
capacity requirement
follow-up time
```

**Exit:** delegations are measurable and correctly routed.  
**Gate:** QA T8.

---

## Batch T9 — Capacity-Aware Delegation with Rhythm

For substantial work implement:

```text
CAPACITY_QUERY
CAPACITY_REPORT
TASK_COMMITTED
```

Rhythm may return:

```text
FIT
FIT_WITH_RISK
DOES_NOT_FIT
NEEDS_PRIORITY_DECISION
```

**Exit:** meaningful new work cannot be committed blind to capacity.  
**Gate:** QA T9.

---

## Batch T10 — Plan Critic and Review Classes

Create `plan-critic` and review classes.

Return:

```text
APPROVE
APPROVE_WITH_CHANGES
REVISE
REJECT
NEEDS_USER_DECISION
```

Routine work bypasses full review.

**Exit:** material specialist plans can be improved without creating a bottleneck.  
**Gate:** QA T10.

---

## Batch T11 — Cross-Agent Synthesis

Create `cross-agent-synthesis`.

Example:

```text
Growth evidence + Rhythm capacity + Scholar obligations + deadlines
→ portfolio decision
```

Preserve source attribution.

**Exit:** Tola can reason across domains without replacing specialists.  
**Gate:** QA T11.

---

## Batch T12 — Delegation Monitoring and Follow-Through

Track:

```text
assigned
acknowledged
started
last_progress
next_check_at
deadline
blocker
status
```

Signals:

```text
TASK_STALLED
TASK_AT_RISK
FOLLOWUP_REQUIRED
```

**Exit:** no delegated task silently disappears.  
**Gate:** QA T12.

---

## Batch T13 — Outcome Verifier

Create `outcome-verifier`.

Check success criteria rather than response completion.

**Exit:** incomplete polished results cannot be falsely closed.  
**Gate:** QA T13.

---

## Batch T14 — Stalled Work Recovery

Create `stalled-work-recovery`.

Allowed actions:

```text
request missing info
rescope
split task
query Rhythm
reorder dependencies
bounded reassignment
escalate
stop
```

**Exit:** known stalled patterns produce bounded recovery.  
**Gate:** QA T14.

---

## Batch T15 — Decision Register and Review Triggers

Enrich decisions with:

```text
decision
reason
evidence
alternatives
tradeoff
owner
date
expected_outcome
review_date
revisit_trigger
```

Implement review-due detection.

**Exit:** significant decisions remain explainable and revisitable.  
**Gate:** QA T15.

---

## Batch T16 — Scope Control

Create `scope-control`.

Evaluate:

```text
active goal alignment
expected value
appetite
dependencies
opportunity cost
smallest viable version
stop condition
what this displaces
```

Outputs:

```text
START
SHAPE_SMALLER
DEFER
STOP
NEEDS_USER_DECISION
```

**Exit:** Tola can resist project sprawl.  
**Gate:** QA T16.

---

## Batch T17 — Founder Briefing and Attention Filter

Create `founder-briefing`.

Implement:

```text
SILENT
DIGEST
NOTIFY
DECISION_REQUIRED
URGENT
```

Use progressive disclosure.

**Exit:** communication is concise, understandable and proportionate.  
**Gate:** QA T17.

---

## Batch T18 — User Operating Profile and Persona Awareness

Create:

```text
user_operating_profile
user_preference_observations
user_preference_versions
```

Implement:

```text
preference_observe()
preference_candidate_create()
preference_promote()
preference_supersede()
user_profile_get()
user_profile_compact()
```

Explicit instructions outrank inference.

**Exit:** stable non-sensitive working preferences can be learned with provenance.  
**Gate:** QA T18.

---

## Batch T19 — Persona Consolidation and Memory Mapping

Map:

```text
Blackboard user_operating_profile = authoritative shared profile
USER.md = compact stable preferences
MEMORY.md = durable Tola decisions/lessons
dated memory = recent observations
```

Create daily/weekly consolidation rules.

**Exit:** new sessions start with a compact current user model.  
**Gate:** QA T19.

---

## Batch T20 — Tola Performance Model

Create `tola_performance_metrics` and populate delegation, review, recovery, briefing, escalation, cost and latency metrics.

**Exit:** Tola can identify measured strengths/weaknesses.  
**Gate:** QA T20.

---

## Batch T21 — Improvement Ledger

Create:

```text
tola_learning_observations
tola_improvement_candidates
tola_improvement_evaluations
```

Corrections, failures and reusable successful patterns generate observations automatically.

**Exit:** improvement candidates are auditable and evidence-linked.  
**Gate:** QA T21.

---

## Batch T22 — Improvement Benchmark Harness

Fixtures:

```text
simple delegation
multi-agent task
ambiguous ownership
capacity-limited task
blocked specialist
poor specialist result
cross-domain conflict
deadline-sensitive task
plan critique
founder briefing
```

Compare current vs candidate on:

```text
task success
correct delegation
success-criteria completeness
escalation accuracy
plan quality
tool calls
token cost
latency
human correction
```

**Exit:** candidates can be objectively compared.  
**Gate:** QA T22.

---

## Batch T23 — Proposal-First Self-Improvement

Flow:

```text
learning observation
→ candidate
→ benchmark
→ candidate beats baseline
→ proposal
→ approval
→ apply
```

Core Skills, permissions, security and architecture cannot self-mutate.

**Exit:** Tola learns autonomously but durable behaviour change remains controlled.  
**Gate:** QA T23.

---

## Batch T24 — Event-Driven Executive Proactivity

Wake Tola on material events such as:

```text
TASK_STALLED
TASK_AT_RISK
DELEGATION_FAILED
EXPERIMENT_COMPLETED
RHYTHM_OVERLOAD
DEADLINE_RISK
APPROVAL_REQUIRED
PLAN_REJECTED
USER_CORRECTION
OUTCOME_FAILURE
MATERIAL_METRIC_CHANGE
```

Apply materiality filtering before model wake.

**Exit:** material changes cause timely action; routine noise does not.  
**Gate:** QA T24.

---

## Batch T25 — Executive Heartbeat

Deterministically check unresolved conditions first.

Only wake Tola on material findings.

**Exit:** unresolved issues are caught with low idle cost.  
**Gate:** QA T25.

---

## Batch T26 — Daily Executive Reconciliation

Daily cycle:

```text
refresh PortfolioSnapshot
compare changes
review deadlines
review blockers/stalled work
review Rhythm capacity signals
review decisions/approvals
review material specialist outputs
act only where needed
```

No message when nothing material changed.

**Exit:** Tola stays current despite missed events.  
**Gate:** QA T26.

---

## Batch T27 — Weekly Executive Review

Review:

```text
projects
goals
outcomes
specialist performance
Rhythm capacity
Growth opportunities
Scholar requirements
stalled work
experiments
decisions
risks
next-week priorities
```

Produce portfolio priorities, assignments, capacity requests, decisions, risks and follow-ups.

**Exit:** Tola can create a coherent next-week operating plan.  
**Gate:** QA T27.

---

## Batch T28 — Weekly Persona and Self-Improvement Review

Persona review:

```text
explicit preferences
repeated observations
contradictions
candidate promotion
superseded preferences
```

Improvement review:

```text
delegation failures
plan corrections
user corrections
outcome misses
communication clarifications
repeated weak patterns
candidate Skill changes
```

**Exit:** learning is consolidated without uncontrolled mutation.  
**Gate:** QA T28.

---

## Batch T29 — Monthly Deep Operating-System Review

Review:

```text
goal relevance
project value
time consumption
outcome production
agent bottlenecks
automation value
Skill usefulness
cost/model usage
portfolio sprawl
repeated manual work
```

Tola may propose process, Skill, scope or architecture changes; protected areas remain proposal-only.

**Exit:** Tola produces evidence-based system-level improvement proposals.  
**Gate:** QA T29.

---

## Batch T30 — Controlled Tola Pilot

Use real portfolio operations including:

- real projects;
- real delegation;
- Rhythm capacity queries;
- Growth and Scholar plans;
- blocked work;
- user corrections;
- persona observations;
- improvement candidates;
- daily/weekly reviews.

Monitor:

```text
delegation accuracy
first-pass completion
stalled recovery
incorrect escalation
missed material events
user correction rate
briefing usefulness
notification noise
plan-quality improvement
preference accuracy
improvement proposal quality
cost
latency
```

**Exit:** repeated operation with zero critical authority/integrity/privacy failures.  
**Gate:** QA T30.

---

## Batch T31 — Final Hardening and Production Release

Review:

- Tola permissions;
- model routing;
- Blackboard access;
- specialist boundaries;
- PortfolioSnapshot freshness;
- delegation contracts;
- review classes;
- outcome assurance;
- persona protections;
- self-improvement proposal mode;
- heartbeat/Automations;
- communication;
- recovery;
- audit trails;
- cost visibility.

Deliver:

```text
final architecture map
PortfolioSnapshot schema
agent capability registry
delegation contract
persona schema
performance schema
improvement schema
automation inventory
Skill inventory
autonomy matrix
runbook
pilot report
production sign-off
```

**Exit:** all gates pass and no critical defect remains.

---

# 18. Dependency Chain

```text
T0  Baseline
 ↓
T1  Portfolio contracts
 ↓
T2  PortfolioSnapshot
 ↓
T3  Project health
 ↓
T4  Agent capability registry
 ↓
T5  Agent performance
 ↓
T6  Priority triage
 ↓
T7  Goal-to-plan
 ↓
T8  Delegation planner
 ↓
T9  Rhythm capacity protocol
 ↓
T10 Plan critic
 ↓
T11 Cross-agent synthesis
 ↓
T12 Delegation monitoring
 ↓
T13 Outcome verifier
 ↓
T14 Stalled-work recovery
 ↓
T15 Decision register
 ↓
T16 Scope control
 ↓
T17 Founder briefing
 ↓
T18 Persona awareness
 ↓
T19 Memory/profile consolidation
 ↓
T20 Tola performance model
 ↓
T21 Improvement ledger
 ↓
T22 Benchmark harness
 ↓
T23 Proposal-first self-improvement
 ↓
T24 Event-driven proactivity
 ↓
T25 Heartbeat
 ↓
T26 Daily reconciliation
 ↓
T27 Weekly executive review
 ↓
T28 Weekly persona/improvement review
 ↓
T29 Monthly operating-system review
 ↓
T30 Controlled pilot
 ↓
T31 Production hardening
```

---

# 19. Global Stop Rules

Fail the active batch immediately if:

- Tola writes directly to My Rhythm;
- Tola delegates outside agent boundaries;
- Tola delegates to a specialist whose availability state is not `ACTIVE`;
- Tola falsely closes incomplete work as SUCCESS;
- Tola changes a consequential priority without authority;
- Tola stores inferred sensitive traits for personalization;
- one observation becomes a durable preference without sufficient evidence;
- contradictory preferences remain active simultaneously;
- self-improvement silently mutates a core Skill;
- candidate improvement is applied without required benchmark/approval;
- Tola changes permissions/security/approval boundaries;
- a material deadline risk is hidden;
- heartbeat repeatedly wakes Tola without material findings;
- user notifications become internal agent chatter;
- PortfolioSnapshot cannot be traced to source versions;
- agent performance metrics override domain authority;
- Tola invents project state not present in authoritative sources.

---

# 20. Programme Definition of Done

Tola V1 is complete when she can repeatedly:

1. reconstruct the current portfolio;
2. know specialist domains, constraints and availability state;
3. identify what deserves attention;
4. create integrated plans;
5. improve specialist plans;
6. delegate measurable work only to active specialists;
7. query Rhythm before substantial commitments;
8. monitor delegated work;
9. recover stalled work;
10. verify outcomes;
11. preserve decision reasoning;
12. control scope;
13. communicate clearly;
14. learn stable non-sensitive working preferences;
15. avoid unsupported persona inference;
16. measure her own performance;
17. create improvement candidates from evidence;
18. benchmark proposed improvements;
19. keep durable self-modification proposal-first;
20. react to material events;
21. catch unresolved work through heartbeat;
22. run daily/weekly/monthly reviews;
23. remain inside authority;
24. pass every QA gate.

---

# 21. Future Specialist Expansion

The architecture intentionally registers future Marketing Agent(s) now so Tola can plan around the future capability without requiring a redesign later.

Planned build order:

```text
Tola
 ↓
Scholar
 ↓
Marketing Agent(s)
```

Marketing Agent(s) remain **NOT YET AVAILABLE** during the Tola/Scholar build. Tola may identify marketing work that would benefit from them, but must route currently supported work through Growth or record an explicit future-specialist dependency.

When Marketing Agents are eventually activated, Tola's goal-pursuit and opportunity-discovery system can add them as additional execution options while preserving the same authority, capacity and QA model.

---

# 22. Final Principle

Tola should think like a **Chief of Staff**, operate like a **programme director**, communicate like an **excellent executive assistant**, and verify work like a **quality-control layer**.

Her intelligence should come from:

```text
authoritative state
+
portfolio synthesis
+
specialist knowledge
+
measured outcomes
+
structured delegation
+
plan critique
+
persona awareness
+
controlled self-improvement
+
event-driven proactivity
```

—not simply from using a larger model.

Tola is successful when the user needs to manage the system less, while remaining better informed and fully in control.
