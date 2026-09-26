# OpenClaw Four-Agent System
## Architecture, Skills, Batch-by-Batch Implementation and QA Plan

**Version:** 1.1  
**Date:** 25 September 2026  
**Supersedes:** Architecture Plan v1.0, Implementation Plan v1.0 and Testing/Iteration Plan dated 24 September 2026

**Initial build scope:** Tola + Rhythm + Growth + Scholar  
**Existing system retained:** Shiftlyx agent  
**Existing integrations retained:** Telegram Tola, Telegram Shiftlyx, tested My Rhythm API, tested IntenSIQ API

**Primary objective:** Build a reliable, inexpensive, inspectable and progressively improving multi-agent personal operating system on OpenClaw without creating an uncontrolled agent swarm.

---

# 1. Executive decisions

These decisions are fixed for V1 unless implementation or testing proves one technically unsound.

1. **Tola is the command-centre operator / Chief of Staff.** Tola is the only general delegator in V1.
2. **Only four organisational agents are built initially:** Tola, Rhythm, Growth and Scholar.
3. **The existing Shiftlyx agent remains separate.** It is not merged into Tola or Rhythm.
4. **Discord is the human-facing control room.** Each organisational agent gets its own channel: `#command-centre`, `#rhythm`, `#growth`, and `#scholar`.
5. **Telegram Tola and Telegram Shiftlyx remain working during migration.**
6. **Discord is not the internal agent message bus.** Agent coordination happens through controlled OpenClaw delegation and Blackboard state.
7. **Tola is the only agent allowed to spawn specialists.**
8. **Rhythm, Growth and Scholar are leaf agents.** They may not spawn or freely message one another.
9. **Delegation uses explicit `sessions_spawn` with named `agentId`.**
10. **Shared organisational truth lives in the Blackboard, not chat transcripts.**
11. **Supabase is authoritative Blackboard state.**
12. **Supabase is the only persistence layer.** No local cache/outbox database in V1 (amended 2026-09-26); reads may use short-lived in-memory caches only.
13. **OpenClaw native agent memory is separate from Blackboard organisational state.**
14. **Agents never receive generic SQL access or raw database credentials.**
15. **Agents use narrow typed tools.**
16. **My Rhythm remains the authoritative work/scheduling source in V1.**
17. **IntenSIQ remains the authoritative detailed learning-content store.**
18. **Growth decisions must use real data sources such as GA4, Search Console and product/UTM analytics.**
19. **No MCP server is required in V1.** OpenClaw typed plugins/wrappers remain the preferred integration surface.
20. **Model routing is semantic and explicit.** OpenClaw fallbacks are recovery mechanisms, not our intelligence ladder.
21. **No free model endpoint is a production dependency.**
22. **Skills are first-class architectural objects.**
23. **External skills are never trusted merely because they are popular or open source.**
24. **External skills are vendored, inspected, adapted, pinned and tested before activation.**
25. **OpenClaw self-learning must explicitly run in `propose` mode.** Do not permit silent production skill mutation.
26. **No organisational agent may silently modify or install its own production skills.**
27. **Ordinary authorised tool calls do not require human approval.** Reads, research, analytics, typed API calls, Blackboard writes, My Rhythm planning actions within Rhythm's contract and IntenSIQ actions within Scholar's contract remain autonomous.
28. **Human approval is concentrated at durable or consequential boundaries:** skill installation/activation/modification, applying self-learning proposals, public/external posting, consequential external communication, spending, destructive irreversible operations, security/permission changes, credential changes and production infrastructure changes.
29. **Every build batch has tests, rollback criteria and an explicit go/no-go gate.**
30. **A fifth agent is added only after the four-agent pilot proves a real bottleneck.**

---

# 2. Verified OpenClaw capability baseline

Before implementation, re-check the installed OpenClaw version against official documentation. The architecture assumes the following current mechanisms are available.

| Capability | OpenClaw mechanism | Design use |
|---|---|---|
| Route a Discord channel to one agent | `bindings` with channel peer match | One channel per agent |
| Tola spawns a named specialist | `sessions_spawn(agentId=...)` | Controlled delegation |
| Per-spawn model override | `sessions_spawn.model` | R1-R4 execution routing |
| Restrict spawn targets | `subagents.allowAgents` | Tola can invoke only Rhythm/Growth/Scholar |
| Require explicit specialist selection | `subagents.requireAgentId` | Prevent ambiguous delegation |
| Keep specialists as leaves | `subagents.maxSpawnDepth: 1` | No recursive agent tree |
| Bound parallel children | `subagents.maxConcurrent`, `maxChildrenPerAgent` | Maximum three specialists |
| Narrow session access | `tools.sessions.visibility: "tree"` | Tola sees its children, not everything |
| Disable ordinary cross-agent access | `tools.agentToAgent.enabled: false` | No hidden agent chat bus |
| Per-agent tool restrictions | `agents.entries.*.tools.allow/deny` | Enforced least privilege |
| Typed tool plugin | OpenClaw Plugin SDK | Blackboard/My Rhythm/IntenSIQ/Growth tools |
| Model allowlist | `modelPolicy.allow` | Restrict production models |
| Cheap internal utility model | `utilityModel` | Low-cost internal tasks |
| Persistent scheduling | OpenClaw Automations/cron | Proven recurring workflows |
| Native Skills | `SKILL.md` skill bundles | Repeatable operating procedures |
| Skill proposal workflow | Skill Workshop | Governed learning |
| Self-learning control | `off / propose / auto` | Production policy = `propose` |
| Per-agent memory | Workspace memory + session state | Non-authoritative learned context |
| Verified backup | `openclaw backup create --verify` | Rollback boundary |
| Security validation | `openclaw security audit --deep` | Post-change check |
| Config diagnosis | `openclaw doctor` | Health/config troubleshooting |

**Security warning:** do not trust permissive defaults. Session visibility, cross-agent access, tool policies and self-learning mode must be explicitly configured.

---

# 3. V1 system architecture

```text
                              USER
                                |
                    Discord / Telegram
                                |
                                v
                              TOLA
                     Chief of Staff / Router
                                |
                    structured task envelope
                                |
                +---------------+---------------+
                |               |               |
                v               v               v
             RHYTHM           GROWTH          SCHOLAR
                |               |               |
                v               v               v
         My Rhythm API      GA4 / GSC       IntenSIQ API
                           UTM/Product
                            Analytics

                ALL FOUR ORGANISATIONAL AGENTS
                                |
                                v
                     Typed Blackboard Tools
                                |
                                v
                     BlackboardRepository
                                |
                                v
                            Supabase
                          (authority)

                                |
                                v
                           MODEL ROUTER

               R0       R1        R2       R3       R4
             Code      Ling    Nemotron  DeepSeek   GLM

                                |
                                v
                         Skills Layer
                 approved per-agent skills only

                                |
                                v
                         Skill Workshop
                       PROPOSE MODE ONLY
```

Existing Shiftlyx agent remains separate and is not counted as one of the four agents.

---

# 4. Agent contracts

## 4.1 Tola - Chief of Staff

### Mission
Convert the user's goals into coordinated work across projects, personal planning, growth and learning.

### Tola owns
- portfolio priorities;
- cross-project trade-offs;
- goal decomposition;
- delegation;
- task assignment;
- model-route selection;
- specialist result review;
- dependency sequencing;
- final synthesis;
- approval escalation;
- weekly portfolio review.

### Tola does not own
- detailed scheduling execution;
- SEO analysis execution;
- learning-content execution;
- direct My Rhythm writes;
- direct IntenSIQ writes;
- raw database access;
- security configuration;
- credentials;
- arbitrary shell access.

### Candidate external skills for adaptation
- Addy Osmani: `planning-and-task-breakdown` - decompose goals into bounded work, dependencies, acceptance criteria, parallelisation and verification.
- Magnus919: `product-shaping` - borrow appetite, circuit-breaker and scope-reduction ideas for stopping runaway work.

These are source skills to review and adapt, not live upstream production dependencies.

## 4.2 Rhythm - Life Planning and Scheduling

### Mission
Turn priorities into a realistic schedule that respects work dates, fatigue/recovery, available time, cognitive load, deadlines, task duration and preferred work periods.

### Rhythm owns
- time allocation;
- conflict detection;
- work/recovery-aware scheduling;
- flexible planning blocks;
- schedule feasibility;
- overload detection;
- planning constraints.

### Rhythm does not own
- strategic project priority;
- learning curriculum;
- growth strategy;
- cross-agent delegation.

### Skill strategy
Do not make generic GitHub productivity skills authoritative. Rhythm should mainly use custom skills built around My Rhythm and actual workload/recovery data.

Initial custom skills:
- `shift-aware-day-planning`
- `recovery-aware-week-planning`
- `deadline-conflict-resolution`
- `overload-detection`
- `workday-task-allocation`
- `weekly-rebalance`

## 4.3 Growth - Growth Intelligence

### Mission
Measure acquisition, search performance, attribution and conversion; identify material changes and propose evidence-backed experiments.

### Growth owns
- Search Console analysis;
- GA4 analysis;
- UTM attribution;
- conversion analysis;
- SEO diagnosis;
- growth experiments;
- anomaly detection;
- onboarding/activation diagnosis.

### Growth does not own
- autonomous publishing;
- ad spending;
- project priority;
- scheduling;
- cross-agent delegation.

### External skill strategy
Primary source candidate: **Corey Haines `marketingskills`**. Candidate V1 skills for adaptation:
- `analytics`
- `attribution`
- `seo-audit`
- `cro`
- `ab-testing`
- `onboarding`
- `signup`
- `aso` when relevant

Do not install the whole repository. Do not bring in social posting, ad-spend or broad write-capable workflows in V1. Adapt every retained skill to use our typed tools such as `growth_ga4_*`, `growth_gsc_*`, `growth_utm_*` and `blackboard_growth_*`.

## 4.4 Scholar - Research and Learning

### Mission
Determine what the user needs to learn, research it properly, teach it at the appropriate level, create useful learning content and write detailed learning material into IntenSIQ.

### Scholar owns
- learning objectives;
- curriculum decisions;
- evidence synthesis;
- explanation;
- quizzes;
- study content;
- IntenSIQ learning writes.

### Scholar does not own
- scheduling;
- project priority;
- Growth analysis;
- My Rhythm writes;
- cross-agent delegation.

### External skill strategy
Primary source candidate: **K-Dense Scientific Agent Skills**. Strong candidates for careful adaptation:
- `scientific-critical-thinking`
- paper lookup/provenance methodology
- evidence appraisal
- claim verification

Do not install large dependency-heavy research workflows unchanged. Extract useful methodology into our own bounded Scholar skills.

Initial Scholar skills:
- `evidence-search`
- `paper-provenance`
- `scientific-critical-thinking`
- `claim-verification`
- `teaching-synthesis`
- `quiz-generation`

---

# 5. Autonomy and approval model

## 5.1 Principle

**Capability boundaries should provide most safety.** If an agent is explicitly trusted to use a narrow typed tool, ordinary use of that tool should normally execute without interruption.

Human approval protects durable or consequential boundaries, not routine work.

## 5.2 Risk classes

| Class | Meaning | Default behaviour |
|---|---|---|
| **A0** | Read-only analysis/research | Automatic |
| **A1** | Internal, reversible state change | Automatic + audit |
| **A2** | Pre-authorised private external action through a narrow typed tool | Automatic + audit |
| **A3** | Durable capability change or consequential external action | Human approval |

### A0 examples
- read Blackboard;
- query GA4 or Search Console;
- read My Rhythm;
- read IntenSIQ;
- web research;
- calculations and analysis.

### A1 examples
- create internal tasks;
- update own task status;
- record metric;
- record decision;
- write internal planning metadata.

### A2 examples
- Rhythm creates/updates a permitted flexible My Rhythm planning block;
- Scholar creates IntenSIQ learning material or quizzes;
- approved reversible private workflow actions.

These do **not** require repeated approval popups.

### A3 examples
- install, activate or modify a skill;
- apply a Skill Workshop/self-learning proposal;
- public social-media post;
- public website publication;
- consequential external message;
- spending/payment;
- destructive data deletion;
- credential change;
- security/permission change;
- production infrastructure change.

Where possible, OpenClaw/plugin-level permission requests should enforce these boundaries at execution time.

---

# 6. Skill governance

## 6.1 Fundamental rule

A Skill is not merely another prompt. It can change how an agent behaves repeatedly across future tasks. Therefore skill mutation is a higher-risk action than most ordinary tool calls.

## 6.2 Skill lifecycle

```text
DISCOVER
   |
   v
IMPORT TO QUARANTINE
   |
   v
SOURCE + LICENCE REVIEW
   |
   v
BEHAVIOURAL REVIEW
   |
   v
DEPENDENCY / SCRIPT REVIEW
   |
   v
ADAPT TO OUR TOOL CONTRACTS
   |
   v
STATIC TEST
   |
   v
BASELINE EVALUATION
   |
   v
HUMAN APPROVAL
   |
   v
PIN VERSION / COMMIT
   |
   v
INSTALL
   |
   v
OBSERVE
   |
   v
AUTOMATE ONLY AFTER PROVEN
```

No external skill skips this lifecycle.

## 6.3 External-skill manifest

Every external skill must record at least:
- skill name;
- source repository;
- source path;
- exact source commit SHA;
- source version/tag when available;
- licence;
- date reviewed;
- reviewer;
- included files;
- presence of scripts;
- dependencies;
- network access;
- secret requirements;
- allowed tools;
- local modifications;
- evaluation results;
- approved agent(s);
- approved content hash/revision.

## 6.4 No direct upstream execution

Production agents do not track live GitHub branches.

```text
GitHub upstream
      |
      v
quarantine/review
      |
      v
our repository
      |
      v
pinned revision
      |
      v
test/evaluate
      |
      v
production
```

## 6.5 No giant global skill library

Do not install entire "awesome skills" collections globally. Excessive skills increase overlap, trigger ambiguity, dependencies and security surface.

Prefer a small number of strong, tested skills per agent.

## 6.6 Self-learning policy

Before self-learning is enabled, explicitly configure:

```text
skills.workshop.autonomous.mode = "propose"
```

Agents may create a proposal but may not apply a production behavioural change themselves.

```text
successful work / user correction
           |
           v
      Skill Workshop
           |
           v
        proposal
           |
      human review
        /     \
   reject    approve
               |
               v
            active
```

## 6.7 Skill -> Automation rule

Never automate an unproven workflow.

```text
manual task
   |
   v
repeated successful execution
   |
   v
skill
   |
   v
skill evaluation
   |
   v
approved production skill
   |
   v
stable on-demand use
   |
   v
automation
```

## 6.8 Skill evaluation

Material skills must be evaluated against a baseline rather than assumed to be helpful.

Minimum initial evaluation:
- 10-20 representative prompts;
- positive trigger cases;
- negative/non-trigger cases;
- edge cases;
- failure cases.

Measure:
- task success;
- factual accuracy;
- tool-selection accuracy;
- boundary violations;
- human correction rate;
- token use;
- latency;
- output consistency;
- trigger precision;
- trigger recall.

A skill that does not improve the agent should be removed even if it appears sophisticated.

---

# 7. Memory policy

## 7.1 Blackboard

Blackboard stores shared organisational truth:
- projects;
- goals;
- tasks;
- task dependencies;
- metrics;
- decisions;
- approvals;
- schedule constraints;
- task/run state.

## 7.2 Native agent memory

OpenClaw native memory stores non-authoritative agent-specific working knowledge and lessons.

Examples:
- Tola: delegation lessons, recurring coordination preferences, useful decomposition patterns;
- Growth: analytics quirks, recurring data-quality issues, successful diagnostic patterns;
- Rhythm: planning lessons and non-authoritative behavioural preferences;
- Scholar: teaching preferences and research-process lessons.

## 7.3 Memory rule

Do not store authoritative project truth only in conversational/native memory. Do not clutter Blackboard with every transient agent thought or learning note.

---

# 8. Delegation protocol

## 8.1 Task envelope

Every delegated task receives a structured record before spawn.

```json
{
  "task_id": "uuid",
  "idempotency_key": "uuid",
  "parent_task_id": null,
  "requested_by": "tola",
  "assigned_to": "growth",
  "goal_id": "goal_uuid",
  "project_id": "project_uuid",
  "title": "Investigate decline in organic conversion",
  "instructions": "Compare Search Console, GA4 and UTM data and identify evidence-backed causes.",
  "context_refs": [
    "blackboard:project:...",
    "blackboard:metric:..."
  ],
  "required_output": "Diagnosis, evidence, uncertainty and recommended next experiment.",
  "success_criteria": [
    "Uses real data",
    "Separates observation from hypothesis",
    "Produces at least one measurable next step"
  ],
  "risk_class": "A0",
  "model_route": "R3",
  "allowed_tools": [
    "growth_*",
    "blackboard_read_*",
    "blackboard_update_own_task"
  ],
  "timeout_seconds": 600,
  "deadline": null,
  "created_at": "ISO-8601"
}
```

Required properties:
- `task_id` generated before spawn;
- `idempotency_key` prevents duplicate effects;
- `assigned_to` must match Tola's allowlist;
- `context_refs` point to Blackboard/app data rather than dumping unrelated transcripts;
- required output is explicit;
- success criteria are testable;
- risk class controls action authority;
- model route records Tola's routing decision;
- allowed tools are descriptive in the envelope, while OpenClaw tool policy is the real enforcement layer.

## 8.2 Specialist result envelope

Allowed statuses:
- `SUCCESS`
- `PARTIAL`
- `BLOCKED`
- `NEEDS_APPROVAL`
- `FAILED`

Example:

```json
{
  "task_id": "uuid",
  "status": "SUCCESS",
  "summary": "Organic traffic increased but CTR and onboarding conversion fell.",
  "outputs": [],
  "evidence_refs": [],
  "tool_actions": [],
  "blackboard_updates_proposed": [],
  "blockers": [],
  "approval_request_id": null,
  "verification": {
    "required_output_present": true,
    "success_criteria_met": true
  }
}
```

## 8.3 No self-certified completion

A specialist returning `SUCCESS` does not automatically close a task. Tola verifies required output, success criteria, evidence, external-write evidence and policy compliance before marking the organisational task complete.

## 8.4 Cross-specialist work

Specialists do not directly spawn or message one another in V1.

Example:

```text
Scholar
  |
  | needs a 45-minute schedule block
  v
returns requirement to Tola
  |
  v
Tola delegates to Rhythm
```

## 8.5 Concurrency

Tola may run up to three independent specialist jobs concurrently. Do not parallelise directly dependent tasks.

Target settings:

```text
requireAgentId = true
maxSpawnDepth = 1
maxConcurrent = 3
maxChildrenPerAgent = 3
```

## 8.6 Retry policy

Same execution/model: maximum one retry.

Retry only on:
- provider error;
- timeout;
- transient API failure;
- clearly correctable schema/format error.

Do not retry:
- policy denial;
- missing credential;
- human approval block;
- deterministic business-rule failure.

Semantic escalation remains a Tola decision and must be logged.

---

# 9. Blackboard architecture

## 9.1 Authority rule

```text
Supabase = authoritative organisational state
```

No local database exists in V1. Reads go straight to Supabase, optionally through short-lived in-memory caches (§9.6). There is no second store, so competing truth is impossible by construction.

## 9.2 Supabase tables

V1 schema:
1. `agents`
2. `projects`
3. `goals`
4. `tasks`
5. `task_dependencies`
6. `task_runs`
7. `decisions`
8. `approvals`
9. `metrics`
10. `schedule_constraints`
11. `agent_events`
12. `model_runs`
13. `external_refs`
14. `skill_registry`
15. `skill_evaluations`

### Core mutable entity requirements
- UUID primary keys where appropriate;
- unique idempotency key for tasks/operations;
- `version` integer for optimistic concurrency;
- foreign keys;
- constrained status/type fields;
- timestamps;
- useful indexes for active tasks and agent/status lookups.

## 9.3 `skill_registry`

Suggested fields:
- `skill_id`
- `skill_name`
- `owner_agent_id`
- `origin_type`
- `source_repository`
- `source_commit`
- `source_version`
- `licence`
- `local_revision`
- `status`
- `approved_by`
- `approved_at`
- `content_hash`
- `created_at`
- `updated_at`

Statuses:
- `quarantined`
- `reviewing`
- `testing`
- `approved`
- `active`
- `rejected`
- `retired`

## 9.4 `skill_evaluations`

Suggested fields:
- `evaluation_id`
- `skill_id`
- `agent_id`
- `baseline_revision`
- `candidate_revision`
- `fixture_set`
- `task_success_before`
- `task_success_after`
- `boundary_violations`
- `trigger_precision`
- `trigger_recall`
- `avg_tokens_before`
- `avg_tokens_after`
- `avg_latency_before`
- `avg_latency_after`
- `human_correction_before`
- `human_correction_after`
- `decision`
- `notes`
- `created_at`

## 9.5 Local cache/outbox (removed, amendment 2026-09-26)

Amendment 2026-09-26: the SQLite cache/outbox layer is removed from V1. Supabase is the single persistence layer. Rationale: Supabase outages are not the operator's actual failure mode, and the outbox was a distributed-systems surface with nine dedicated test cases that paid for itself only under sustained Supabase unavailability. Revisit only if real outage data justifies it.

## 9.6 Read policy

Initial in-memory read-cache policy (no local database; caches live in process memory only):
- active tasks: about 60 seconds;
- project/goal metadata: about 5 minutes;
- schedule constraints: about 60 seconds during active planning, otherwise up to 5 minutes;
- approval state: authoritative read;
- security/permission state: never cache as authority.

Tune these after pilot measurements.

## 9.7 Write policy

Online:

```text
validate input
   |
   v
generate operation/idempotency ID
   |
   v
write Supabase authority
   |
   v
append audit event
```

If Supabase is unavailable, the operation fails explicitly. Nothing queues automatically in V1 (amendment 2026-09-26). Return `BLOCKED: AUTHORITATIVE_STORE_UNAVAILABLE` and let the operator or the retrying agent re-issue the operation; idempotency keys make retries safe (§9.8).

## 9.8 Replay and conflict protection

Operation semantics unchanged (no outbox, amendment 2026-09-26):
- creates use stable client-generated IDs;
- updates use optimistic concurrency;
- duplicate operation IDs are idempotent;
- stale writes become explicit conflicts;
- a retried write can never produce a duplicate authoritative effect.

---

# 10. Production model routing

## 10.1 Routes

| Route | Model/mechanism | Main job |
|---|---|---|
| **R0** | deterministic code | arithmetic, date logic, comparison, validation, sorting, deduplication |
| **R1** | `inclusionai/ling-3.0-flash` | cheap extraction, transformation, summarisation |
| **R2** | `nvidia/nemotron-3.5-lightning` | fast structured tool/API execution |
| **R3** | `deepseek/deepseek-v4-flash-0731` | inexpensive multi-step agentic work, investigation and iteration |
| **R4** | `z-ai/glm-5.3-flash` | orchestration, ambiguous reasoning, synthesis and planning |

## 10.2 Routing decision order

1. Can deterministic code solve it reliably? -> **R0**
2. Primarily extraction/transformation/summarisation? -> **R1**
3. Strict, well-defined tool/API operation? -> **R2**
4. Multi-step autonomous investigation or tool loop? -> **R3**
5. Ambiguous planning, prioritisation or synthesis? -> **R4**
6. Genuinely uncertain? -> **R4**

## 10.3 Routing rules

- Input length is not complexity.
- No free endpoint is a production dependency.
- Tola's normal conversational/orchestration model is R4 GLM-5.3 Flash.
- `utilityModel` should use paid Ling where appropriate.
- Model allowlist contains only approved V1 routes.
- OpenClaw model fallbacks are not semantic routing.
- Provider-level failover may remain OpenRouter's responsibility.
- Same-route retry maximum: one.
- Semantic escalation maximum: two route steps before Tola reports the task blocked/failed.
- Deep/agentic run concurrency is bounded by Tola's child limits.

## 10.4 Routing decision model (amendment, 2026-09-26): Jev Router

Route classification moves from Tola's conversational judgement to **`typesafe/jev-router`** (TypeSafe structured decision model, served via OpenRouter). Jev receives the task's application state plus a typed question (`route: R0|R1|R2|R3|R4`) and returns a typed choice with probabilities. Tola (R4 GLM) remains the fallback decision-maker.

Rules for the Jev amendment:

- Jev classifies routes only; it never executes tasks or touches the Blackboard write path.
- Fallback order: Jev -> R4 (GLM) decides as today. Low Jev confidence or unavailable model falls back to R4.
- Every Jev decision is recorded in `model_runs` with `model_route` set to the decided route and `model_id = typesafe/jev-router` (no new schema needed).
- Confidence threshold and retry policy are set during the routing batch and pinned before activation.
- Jev becomes the default router only after the routing batch's accuracy gate passes: on a recorded task set, Jev's route assignments must match Tola's manual baseline, with discrepancies reviewed before promotion.
- Until that gate passes, R4 makes routing decisions exactly as specified in 10.2/10.3.

## 10.4 Proposed route timeouts

| Route | Proposed timeout |
|---|---:|
| R1 Ling | 120 seconds |
| R2 Nemotron | 120 seconds |
| R3 DeepSeek V4 Flash | 600 seconds |
| R4 GLM-5.3 Flash delegated task | 900 seconds |

These are policy defaults and should be tuned after pilot data.

## 10.5 Price metadata

Do not hard-code long-term price assumptions into architecture. Re-check OpenRouter pricing at Batch 6 and whenever providers/models change.

---

# 11. Target implementation repository

```text
openclaw-personal-org/
  README.md
  docs/
    architecture.md
    implementation.md
    testing.md
    skill-policy.md
    current-state-audit.md
    runbooks/
  config/
    examples/
    policies/
  packages/
    blackboard-tools/
      src/
        index.ts
        tools/
        repository/
        adapters/
          supabase.ts
        schemas/
      tests/
      migrations/
        supabase/
    myrhythm-tools/
      src/
      tests/
    intensiq-tools/
      src/
      tests/
    growth-tools/
      src/
      tests/
  skills/
    quarantine/
    vendor/
      addyosmani/
      magnus919/
      coreyhaines31/
      kdense/
    approved/
      tola/
      rhythm/
      growth/
      scholar/
    manifests/
    evaluations/
  fixtures/
    routing/
    delegation/
    skills/
    blackboard/
    rhythm/
    growth/
    scholar/
  scripts/
    backup-check.sh
    smoke-test.sh
    export-sanitized-config.sh
    skill-review.sh
    skill-eval.sh
```

Never store secrets in the repository.

---

# 12. Batch-by-batch build and QA plan

# Batch 0 - Audit, Backup and Version Freeze

## Objective
Understand the actual current OpenClaw installation before changing it. Preserve Tola and Shiftlyx exactly as they work today.

## Work
Record:

```bash
openclaw --version
openclaw agents list --bindings
openclaw channels status --probe
openclaw status --json
openclaw doctor --lint --json
openclaw security audit --deep
```

Create a verified backup:

```bash
openclaw backup create --output ~/Backups/openclaw --verify
```

Document:
- current Tola agent ID;
- current Shiftlyx agent ID;
- workspaces and agent directories;
- current Telegram account/bindings;
- models/providers;
- tool policy;
- session visibility / agent-to-agent settings;
- current Skill configuration;
- current Skill Workshop mode;
- memory configuration;
- OpenRouter credential mechanism;
- Gateway host and startup method.

## Tests
**T0.1 Version capture** - exact installed version recorded.  
**T0.2 Agent/binding inventory** - Tola/Shiftlyx IDs and Telegram bindings identified.  
**T0.3 Existing-agent smoke test** - unique Telegram prompts reach correct agents.  
**T0.4 Verified backup** - backup verification succeeds.  
**T0.5 Security/doctor baseline** - current findings stored as baseline.

## Output
- `docs/current-state-audit.md`
- verified backup reference
- sanitized config snapshot
- no functional changes

## Gate
**NO-GO** if backup verification fails or current Tola/Shiftlyx behaviour cannot be reproduced.

---

# Batch 1 - Repository, Environment and Secret Boundaries

## Objective
Create the implementation workspace without touching live agent behaviour.

## Work
1. Create repository layout.
2. Pin Node/OpenClaw plugin prerequisites based on installed version.
3. Add lint/test/build scripts.
4. Define secret handling for Supabase, My Rhythm, IntenSIQ, GA4/Search Console.
5. OpenRouter remains managed by OpenClaw.
6. Ensure `.env*` and credential JSON are gitignored.
7. Point test/staging at the development Supabase target only.
8. Create development/staging Supabase target if practical.

## Tests
**T1.1 Clean build** - clean checkout builds/tests with declared dependencies only.  
**T1.2 Secret scan** - no credentials tracked.  
**T1.3 `.gitignore` test** - dummy `.env` does not become trackable.  
**T1.4 Environment separation** - test write appears only in development Blackboard.

### Failure injection
Remove a required environment variable.

Expected: tool/package startup fails clearly without leaking secret values or falling back to production credentials.

## Gate
No secret leakage and clean repository build/test.

---

# Batch 2 - Security, Session and Autonomy Baseline

## Objective
Narrow OpenClaw defaults before adding tools or real specialist autonomy.

## Target policy
- `tools.sessions.visibility = "tree"`
- `tools.agentToAgent.enabled = false`
- deny `sessions_send` in V1
- deny `sessions_spawn` by default; later grant only to Tola
- restrict guarded cross-context message actions
- model allowlist restricted to the four V1 model refs
- `utilityModel` = paid Ling where supported
- no generic shell/exec/file mutation tools for organisational agents unless a later tested need emerges
- explicitly set `skills.workshop.autonomous.mode = "propose"`

## Approval baseline
- A0/A1/A2 authorised typed operations: no approval interruption
- A3 capability changes or consequential actions: approval required

## Tests
**T2.1 Session visibility** - unrelated sessions inaccessible.  
**T2.2 Agent-to-agent disabled** - ordinary cross-agent send/access denied.  
**T2.3 Telegram regression** - Tola/Shiftlyx still work.  
**T2.4 Model allowlist** - unapproved model rejected.  
**T2.5 Tool deny precedence** - denied tool cannot be prompt-enabled.  
**T2.6 Workshop mode** - system reports/proves `propose`, not silent auto-apply.  
**T2.7 Autonomy sanity check** - low-risk authorised tool executes without approval popup.

### Failure injection
Create deliberately over-broad config in staging and run security audit.

Expected: audit surfaces the issue; config is not deployed.

## Gate
No new critical audit finding and existing Telegram workflows unchanged.

---

# Batch 3 - Supabase Blackboard Schema

## Objective
Create authoritative shared organisational state before new agents rely on it.

## Work
Implement migrations for:
- agents
- projects
- goals
- tasks
- task_dependencies
- task_runs
- decisions
- approvals
- metrics
- schedule_constraints
- agent_events
- model_runs
- external_refs
- skill_registry
- skill_evaluations

Required DB behaviours:
- UUID keys;
- unique idempotency keys;
- optimistic version field on mutable shared entities;
- foreign keys;
- status/type constraints;
- timestamps;
- indexes for active task and agent/status lookups.

Seed only test records for Tola/Rhythm/Growth/Scholar.

## Tests
**T3.1 Fresh migration** - all tables/constraints/indexes/FKs exist.  
**T3.2 Seed repeatability** - deterministic reset/seed without duplication.  
**T3.3 FK protection** - invalid references rejected.  
**T3.4 Unique idempotency** - duplicate logical create prevented.  
**T3.5 Versioning** - current-version update succeeds, stale update conflicts.  
**T3.6 Invalid types/statuses** - rejected.

## Gate
Clean database can be recreated with identical structure.

---

# Batch 4 - BlackboardRepository (Supabase direct)

## Objective
Build typed persistence over Supabase directly, independently of OpenClaw.

## Work
Implement repository methods including:
- get/list project;
- get/list goal/task;
- create/assign/update task;
- record decision;
- record metric;
- get schedule constraints;
- request approval;
- record agent event.

Adapters:
- Supabase authoritative adapter (the only adapter).

Implement:
- stable IDs/idempotency;
- optimistic version checks;
- explicit `CONFLICT` on stale writes.

## Tests
**T4.1 Online read-through cache**  
**T4.2 Online write: Supabase write succeeds + audit event**  
**T4.3 Duplicate operation id -> one authoritative effect**  
**T4.4 Stale-version conflict -> explicit CONFLICT, no overwrite**  
**T4.5 Approved skill without source/revision/hash metadata -> rejected by repository validation**  
**T4.6 Malformed Supabase response -> no false success**

### Failure injection
- timeout midway through Supabase operation;
- malformed Supabase response.

## Gate
No undetected failure and no duplicate authoritative effect.

---

# Batch 5 - Blackboard OpenClaw Tool Plugin

## Objective
Expose safe organisational actions without raw DB access.

## Work
Build tool-only OpenClaw plugin using installed Plugin SDK.

Start with Tola-safe tools:
- list/get projects;
- list/get goals;
- create/list/get tasks;
- assign task;
- update task status;
- record decision;
- request/get approval;
- get task run;
- record event.

Then add specialist-scoped tool names.

Requirements:
- strict schemas;
- compact structured outputs;
- credential redaction;
- no generic HTTP;
- no SQL;
- no arbitrary table/query tool;
- every mutation audited;
- caller/task correlation where practical.

## Tests
**T5.1 Tool discovery** - only approved Tola tools visible.  
**T5.2 Input validation** - invalid payload rejected before mutation.  
**T5.3 Mutation audit** - valid mutation emits event.  
**T5.4 No raw query surface** - SQL/arbitrary table prompt has no capability.  
**T5.5 Error redaction** - forced auth/connection error exposes no secret.  
**T5.6 Specialist visibility** - Tola-only tools unavailable to specialist profile.

## Gate
No raw DB or generic network capability reaches any model through this plugin.

---

# Batch 6 - Model Registry, Routing and Cost Logging

## Objective
Make route selection explicit and testable before multi-agent delegation.

## Work
Create minimum 40 labelled routing fixtures:
- 10 R0
- 10 R1
- 8 R2
- 6 R3
- 6 R4

Include adversarial examples where prompt length does not match complexity.

Configure model allowlist and Tola primary/default R4 model. Set utility model to Ling where supported. Log route/model in task and model runs. Do not enable semantic fallbacks.

## Tests
**T6.1 Routing accuracy** - provisional threshold >=85% exact-route match and 100% on clearly safety/complexity-critical cases.  
**T6.2 Allowlist enforcement** - unapproved model rejected.  
**T6.3 Model log** - one task on each R1-R4 records model/route/reason.  
**T6.4 No hidden semantic fallback** - model failure remains visible.  
**T6.5 Cost reconciliation** - Blackboard usage data directionally matches OpenClaw/provider usage.  
**T6.6 Price freeze** - current provider/model pricing snapshot documented.

### Failure injection
- timeout;
- provider error;
- malformed structured output.

## Gate
No unapproved model and routing benchmark acceptable.

---

# Batch 7 - Tola Command Centre on Discord

## Objective
Promote existing Tola into Chief-of-Staff role without replacing identity or breaking Telegram.

## Work
1. Keep existing Tola agent ID/workspace.
2. Update Tola contract to own coordination/priority/delegation, use Blackboard truth, choose route and review results.
3. Grant Tola `sessions_spawn` only to future `rhythm`, `growth`, `scholar`.
4. Set explicit agent ID requirement, depth 1, max three children/concurrent runs.
5. Create Discord `#command-centre` binding to same Tola.
6. Preserve Telegram Tola.
7. Keep transient Discord/Telegram session histories separate.

Specialists may exist as inert stubs for allowlist testing only.

## Tests
**T7.1 Discord binding** - unique marker reaches Tola only.  
**T7.2 Telegram continuity** - same Tola continues there.  
**T7.3 Session separation** - transient channel details do not unexpectedly merge.  
**T7.4 Blackboard access** - Tola uses typed tool to create test task.  
**T7.5 Explicit agent ID guard** - missing ID rejected.  
**T7.6 Spawn allowlist** - unknown/unapproved agent rejected.  
**T7.7 Max depth** - child cannot spawn child.

## Gate
Same Tola works in Telegram and Discord with restricted delegation.

---

# Batch 8 - Delegation Protocol with Synthetic Specialist

## Objective
Prove delegation mechanics before real external APIs.

## Work
Flow:
1. Tola creates Blackboard task.
2. Tola chooses route/model.
3. Tola calls `sessions_spawn(agentId=...)` with task envelope.
4. Child returns structured result.
5. Tola reviews result.
6. Tola updates run/final task state.

## Tests
**T8.1 Successful delegation** - one run, one completion, correct audit.  
**T8.2 Partial result** - Tola does not mark complete.  
**T8.3 Blocked result** - blocker recorded, no blind retry.  
**T8.4 Needs approval** - approval record created where relevant.  
**T8.5 Malformed result** - invalid result, maximum one correction/retry.  
**T8.6 Timeout** - bounded retry.  
**T8.7 Duplicate spawn** - same idempotency key yields one logical effect.

### Failure injection
Kill child after a simulated external write but before result return.

Expected: reconciliation checks evidence before any retry; no double action.

## Gate
No recursive spawn, duplicate effect or automatic completion on malformed/partial result.

---

# Batch 9 - Skill Governance and Tola Skill Baseline

## Objective
Build skill governance before specialists become highly capable.

## Work
Create:
- `skills/quarantine`
- `skills/vendor`
- `skills/approved`
- `skills/manifests`
- `skills/evaluations`

Reconfirm Workshop mode = `propose`.

Import Tola candidates into quarantine:
- Addy Osmani `planning-and-task-breakdown`
- Magnus919 `product-shaping`

For each candidate:
- pin exact upstream commit;
- record licence;
- inspect scripts/dependencies;
- inspect network/secret requirements;
- inspect behavioural instructions;
- remove unnecessary capabilities;
- adapt to Tola/Blackboard/task-envelope architecture;
- create evaluation fixtures.

## Tests
**T9.1 Self-learning proposal** - Tola can propose, not silently apply.  
**T9.2 Direct skill mutation attempt** - bypass attempt cannot change approved production skill.  
**T9.3 Pinned source** - exact upstream commit stored.  
**T9.4 Licence recorded**.  
**T9.5 Malicious/overbroad skill** - deliberately unsafe candidate rejected in quarantine.  
**T9.6 Baseline evaluation** - candidate must improve targeted behaviour without boundary regression.  
**T9.7 Upstream changes** - production does not auto-update.  
**T9.8 Human activation** - only explicitly approved revision becomes active.

## Gate
Do not continue if agent behaviour can change through skills without governed review.

---

# Batch 10 - Rhythm Agent and My Rhythm Integration

## Objective
Add the first real specialist.

## Work
Create Rhythm with:
- own workspace/session history;
- GLM-5.3 Flash default;
- no delegation authority;
- only Rhythm Blackboard tools;
- only My Rhythm typed tools;
- no Growth or IntenSIQ tools.

Wrap tested My Rhythm API with typed operations conceptually equivalent to:
- get work dates/current plan;
- get available windows/constraints if supported;
- check conflict;
- create flexible block;
- update flexible block;
- remove flexible block within contract.

Use deterministic time arithmetic/conflict checks where possible.

Create/adapt custom skills:
- shift-aware-day-planning;
- recovery-aware-week-planning;
- overload-detection;
- deadline-conflict-resolution.

Create Discord `#rhythm` binding.

## Tests
**T10.1 Shift-aware planning** - high-cognitive task not placed into inappropriate post-shift recovery time without explicit user instruction.  
**T10.2 Deep-work day** - 180-minute high-cognitive task placed into suitable day-off window.  
**T10.3 Deadline conflict** - infeasible schedule is reported, not solved by silently changing project priority.  
**T10.4 My Rhythm read** - actual test work-date/plan data retrieved.  
**T10.5 Flexible-block write** - reversible test block written once and audited.  
**T10.6 Permission denial** - project priority change or spawn request unavailable.  
**T10.7 API failure** - proposal may be generated, but no false claim that plan was written.  
**T10.8 Skill baseline** - custom skill improves targeted scheduling quality.

## Gate
Rhythm behaves like a planner, not a project manager, and cannot cross domains.

---

# Batch 11 - Growth Agent, Data Tools and External Marketing Skills

## Objective
Add evidence-driven SEO/acquisition/conversion intelligence.

## Work
Create Growth with:
- own workspace;
- GLM-5.3 Flash default;
- no delegation;
- Growth Blackboard tools only;
- read-only growth data tools.

Typed adapters:
- Google Search Console;
- GA4;
- existing UTM/product analytics source.

Prefer deterministic aggregation before model calls. Return compact structured data, not huge raw dumps.

Vendor/adapt selected Corey Haines skills:
- analytics;
- attribution;
- seo-audit;
- cro;
- ab-testing;
- onboarding;
- signup;
- aso if relevant.

Do not add social posting or ad-spend tools.

Create Discord `#growth` binding.

## Tests
**T11.1 Search Console retrieval** - known range matches source within API aggregation behaviour.  
**T11.2 GA4 retrieval** - known property/range matches source.  
**T11.3 UTM attribution** - known campaign correctly attributed.  
**T11.4 Deterministic CTR** - calculation performed in code.  
**T11.5 Evidence vs hypothesis** - observed metrics separated from suspected causes.  
**T11.6 Partial API outage** - unavailable source labelled, no invented metrics.  
**T11.7 No publish/spend authority** - tools absent.  
**T11.8 External skill baseline** - each selected skill must improve relevant task set.  
**T11.9 Trigger precision** - unrelated prompts do not invoke incorrect marketing skill.  
**T11.10 Pin verification** - active skills resolve to approved local revisions only.

## Gate
Growth produces evidence-backed, materially useful output rather than generic marketing prose.

---

# Batch 12 - Scholar Agent, IntenSIQ and Scientific Skills

## Objective
Add learning/research automation using tested IntenSIQ integration and selective evidence skills.

## Work
Create Scholar with:
- own workspace;
- GLM-5.3 Flash default;
- no delegation;
- Scholar Blackboard tools;
- IntenSIQ typed tools;
- approved research/web tools.

Wrap IntenSIQ operations conceptually equivalent to:
- get learning profile/progress;
- get weak topics;
- create study plan/session;
- create learning material;
- create quiz.

Keep detailed study content in IntenSIQ; Blackboard stores only coordination metadata.

Adapt Scholar skills:
- scientific-critical-thinking;
- paper-provenance;
- evidence-search;
- claim-verification;
- teaching-synthesis;
- quiz-generation.

Do not blindly install dependency-heavy K-Dense research workflows.

Create Discord `#scholar` binding.

## Tests
**T12.1 IntenSIQ progress read** - known state reported correctly.  
**T12.2 Study session/material creation** - external record created once.  
**T12.3 Blackboard metadata only** - detailed lesson not unnecessarily duplicated.  
**T12.4 Scheduling boundary** - Scholar cannot write My Rhythm.  
**T12.5 Research quality** - stronger evidence preferred over conflicting low-quality material.  
**T12.6 Conflicting evidence** - uncertainty represented appropriately.  
**T12.7 Claim verification** - factual claims checked in a separate verification pass where relevant.  
**T12.8 IntenSIQ failure** - returns PARTIAL/BLOCKED and explicitly states save failed.  
**T12.9 No credential leakage**.  
**T12.10 Skill baseline** - scientific/evidence skills improve quality without over-triggering.

## Gate
Scholar improves learning quality without becoming an unrestricted research/computer agent.

---

# Batch 13 - Four-Agent Cross-Domain Orchestration

## Objective
Prove architecture with realistic multi-domain goals.

## Scenario A - Weekly planning

User to Tola:

> Make meaningful progress on Florence this week, keep CCN study moving, and do not overload post-shift days.

Expected:
- Tola reads goals/tasks;
- Scholar determines what learning matters;
- Rhythm determines feasible placement around work/recovery;
- results return independently;
- Tola synthesises final plan;
- only Rhythm writes planning blocks.

## Scenario B - Growth + scheduling

> Shiftlyx growth needs attention this week but I only have limited project time.

Expected:
- Growth identifies highest-value evidence-backed work;
- Rhythm estimates feasible capacity;
- Tola chooses the trade-off and records it.

## Scenario C - Parallel delegation

Tola runs Growth, Scholar and Rhythm concurrently for independent subtasks, maximum three.

## Tests
**T13.1 Weekly plan** - correct ownership and write boundaries.  
**T13.2 Growth-priority trade-off** - evidence + capacity + Tola decision.  
**T13.3 Three-child concurrency** - three run; fourth is prevented/queued per policy.  
**T13.4 Dependency sequencing** - dependent task not spawned early.  
**T13.5 Direct specialist chat isolation** - unrelated specialist transcript not automatically exposed to Tola.  
**T13.6 Wrong-domain request** - Growth asked to schedule redirects/returns requirement instead of acting as Rhythm.  
**T13.7 Traceability** - every task run has final state and evidence references.

## Gate
Zero S0/S1 defects, zero duplicate external actions, zero unapproved cross-agent spawns.

---

# Batch 14 - Proactive Automations

## Objective
Add proactive behaviour only after equivalent on-demand workflows are reliable.

## Initial automations
- Growth: daily lightweight anomaly check;
- Growth: weekly detailed review;
- Tola: weekly portfolio review;
- Scholar: weekly progress review if IntenSIQ state quality is sufficient;
- Rhythm: no autonomous weekly rewrite initially.

Each automation must:
- have one owner agent;
- invoke an approved workflow/Skill where practical;
- create/record a task run;
- be idempotent;
- use normal interactive permissions;
- perform no A3 action without approval;
- suppress no-change/noise notifications.

## Tests
**T14.1 Growth anomaly job run twice for same period** - no duplicate logical task/notification.  
**T14.2 Weekly Growth review** - correct date range and one summary.  
**T14.3 Tola weekly review** - current state read, only necessary tasks created.  
**T14.4 Scholar no-change state** - no redundant content.  
**T14.5 Gateway restart persistence** - scheduled job persists without double-run.  
**T14.6 API outage** - failure/partial state recorded, no noisy repeat loop.

## Gate
Three consecutive scheduled cycles complete without duplicate effects or noisy no-change notifications.

---

# Batch 15 - Resilience, Recovery, Security and Skill Tamper Drill

## Objective
Prove controlled failure rather than optimistic failure.

## Inject
- Supabase outage;
- SQLite outage;
- My Rhythm API failure;
- IntenSIQ API failure;
- GA4/Search Console partial outage;
- model/provider timeout;
- malformed specialist result;
- Gateway restart between task creation and result;
- stale SQLite cache conflict;
- duplicate outbox replay;
- invalid Skill proposal;
- staged skill-directory tampering;
- external-post approval denial.

## Expected behaviour

### Supabase offline
- cache only within freshness policy;
- low-risk queue only;
- authoritative/high-risk state blocked.

### SQLite unavailable
- Supabase remains authority where possible;
- local cache/outbox failure visible.

### My Rhythm unavailable
- Rhythm may propose a plan;
- no claim that blocks were written.

### IntenSIQ unavailable
- Scholar may generate content locally;
- no claim that it was saved.

### Growth data source unavailable
- partial coverage labelled with time range/source;
- no invented current metrics.

### Provider timeout
- one bounded retry;
- no recursive spawn loop.

### Gateway restart
- reconcile task state and external evidence before replaying mutation.

### Skill corruption/tampering
- unapproved/invalid revision does not become active.

### A3 public-post attempt
- blocked until human approval; denial prevents execution.

## Recovery drill
1. Create verified OpenClaw backup.
2. Restore into a fresh staging target according to official recovery guidance.
3. Restore/reconnect Blackboard development state.
4. Start Gateway in staging.
5. Run smoke tests for all four agents.
6. Verify approved skill revisions and hashes.

Run:

```bash
openclaw backup create --output ~/Backups/openclaw --verify
openclaw security audit --deep
openclaw doctor --lint --json
openclaw health
openclaw gateway status --deep --json
```

## Gate
No silent corruption, duplicate writes, privilege escalation, wrong-user delivery or uncontrolled skill activation.

---

# Batch 16 - 14-Day Controlled Pilot and Freeze

## Objective
Use the system in real life at low-risk autonomy before expanding scope.

## Pilot rules
- minimum 14 days;
- Tola + Rhythm + Growth + Scholar only;
- existing Shiftlyx agent remains available;
- no new agents;
- no autonomous public posting;
- no autonomous spending;
- no autonomous skill activation;
- no new model families unless an outage forces a documented exception;
- review failures/partial runs frequently during early pilot;
- weekly review of cost, routing, duplication and skill performance.

## Daily/near-daily review during early pilot
Record:
- tasks delegated;
- success/partial/blocked/failed count;
- manual reroutes;
- wrong-agent decisions;
- model route;
- retries;
- API failures;
- duplicate count;
- user corrections;
- skill trigger failures;
- skill proposals.

## Weekly quantitative review
Calculate:
- delegation success rate;
- reviewed routing accuracy;
- cost per successful task;
- latency by route;
- model retry rate;
- API/tool failure rate;
- duplicate-action count;
- manual schedule corrections;
- Growth insights accepted/actioned;
- Scholar content accepted/used;
- skill improvement vs baseline;
- skill false-trigger rate.

## Pilot questions
1. Does Tola reduce manual coordination?
2. Does Rhythm reduce planning effort without over-scheduling?
3. Does Rhythm respect recovery?
4. Does Growth surface material information rather than generic marketing advice?
5. Does Scholar materially improve IntenSIQ learning?
6. Are external Skills improving outcomes?
7. Which Skills should be removed?
8. Is self-learning producing useful proposals or noise?
9. Are model routes economical and reliable?
10. Are approvals concentrated at the right boundaries?
11. Is Supabase + SQLite worth the added sync complexity?
12. What measured bottleneck would a fifth agent solve?

## Release criteria
V1 can be frozen as production only if the critical testing gates pass and there is no unresolved high-severity security, duplication, skill-governance or state-consistency defect.

---

# 13. QA severity model

| Severity | Definition | Batch consequence |
|---|---|---|
| **S0 Critical** | Data corruption, secret exposure, permission escape, uncontrolled destructive action, wrong-user delivery | Immediate rollback |
| **S1 High** | Duplicate external action, wrong-agent routing, uncontrolled spawn loop, authoritative-state conflict, unapproved skill activation | Stop batch; fix before continuing |
| **S2 Medium** | Wrong model route, failed cache refresh, recoverable API error mishandled, misleading status, skill false-trigger | Fix before next dependent batch |
| **S3 Low** | Cosmetic wording/layout issue, non-critical latency | May defer with logged issue |

---

# 14. Global testing rules

## 14.1 Test environments

Use at least two logical environments.

### Development/staging
- test Blackboard records only;
- test Discord/private channel set;
- non-production My Rhythm/IntenSIQ targets if available;
- otherwise explicit reversible test records;
- GA4/Search Console remain read-only.

### Pilot/production
- enabled only after batch gates pass;
- existing Telegram Tola/Shiftlyx remain fallback during initial pilot.

Never run destructive fault injection against live production data.

## 14.2 Pre-batch checkpoint

Before any batch changing OpenClaw config, plugins, skills or live state:

```bash
openclaw backup create --output ~/Backups/openclaw --verify
```

Record:
- backup reference;
- OpenClaw version;
- Git commit for custom tools/skills;
- sanitized config hash/commit;
- date/time;
- batch number.

Backup failure = batch does not start.

## 14.3 Post-batch health checks

Run as appropriate:

```bash
openclaw doctor --lint --json
openclaw security audit --deep
openclaw health
openclaw gateway status --deep --json
```

Any new critical security finding is an automatic no-go.

## 14.4 Mandatory negative testing

For every new permission, also test denial.

Examples:
- Tola can spawn Growth -> Tola cannot spawn arbitrary agent;
- Rhythm can write a flexible My Rhythm block -> Growth cannot call that tool;
- Scholar can write IntenSIQ -> Rhythm cannot see/call the schema;
- agent can propose a Skill -> agent cannot activate it itself;
- approved Skill can run -> quarantined Skill cannot;
- Growth can analyse social strategy -> Growth cannot publish.

## 14.5 Iteration loop

```text
BUILD
  |
UNIT TEST
  |
INTEGRATION TEST
  |
NEGATIVE / PERMISSION TEST
  |
FAILURE INJECTION
  |
OBSERVE LOGS / STATE
  |
FIX
  |
RE-RUN FULL AFFECTED SUITE
  |
GO / NO-GO
```

Do not test only the single failed test after a change. Re-run the full affected batch and earlier regression suites.

---

# 15. Regression matrix

| Change | Required regression |
|---|---|
| OpenClaw config/bindings | B0, B2, B7 |
| Blackboard schema/sync | B3, B4, B5, B8 |
| Blackboard plugin | B4, B5 + permission tests |
| Model/routing change | B6 + affected specialist suites |
| Skill change | B9 + owning-agent suite |
| My Rhythm wrapper | B10 + B13 weekly-plan scenario |
| Growth connector/skill | B11 + B13 Growth scenario |
| IntenSIQ/Scholar skill | B12 + B13 weekly-plan scenario |
| Automation | B14 + underlying agent suite |
| OpenClaw upgrade | core B0/B2/B7/B8 + smoke tests for all agents |

---

# 16. Test fixture library

```text
fixtures/
  routing/
    r0.jsonl
    r1.jsonl
    r2.jsonl
    r3.jsonl
    r4.jsonl
  delegation/
    success.json
    partial.json
    blocked.json
    malformed.json
  skills/
    positive-triggers.jsonl
    negative-triggers.jsonl
    malicious-skill/
    baseline-evals/
  rhythm/
    post_shift.json
    deep_work_day.json
    infeasible_week.json
  growth/
    traffic_up_conversion_down.json
    partial_api.json
    utm_campaign.json
  scholar/
    weak_topic.json
    conflicting_evidence.json
    intensiq_write_failure.json
```

Do not put secrets, identifiable patient information, private emails or credentials into fixtures.

---

# 17. Model evaluation rule

Models may change behaviour even when an ID remains similar. Re-run routing and specialist smoke suites when:
- model provider routing mode changes;
- OpenRouter model ref/version changes;
- agent contract/system prompt changes materially;
- a material Skill changes;
- tool schemas change;
- OpenClaw upgrades alter tool/session semantics.

The production question is not "Which model benchmarks highest?" It is:

> Does the model reliably complete this agent's real tool workflow at acceptable cost and latency without violating boundaries?

---

# 18. Observability and cost controls

For every delegated task record:
- task ID;
- assigning agent;
- specialist;
- chosen route;
- exact model ref;
- routing reason;
- OpenClaw run ID / child session key;
- start/end time;
- status;
- retry count;
- tools called;
- external writes;
- approval state;
- Skill IDs used;
- Skill revision hashes;
- token usage where available;
- estimated/actual cost where available;
- latency;
- failure code.

Do not store full private prompts or full external payloads merely for observability. Prefer references and compact summaries.

Cost controls:
- model allowlist = four approved V1 models;
- paid utility model;
- max three concurrent children;
- same-model retry max one;
- route-specific timeouts;
- no free production endpoint;
- no uncontrolled fallbacks that hide routing defects;
- soft daily/weekly alert thresholds during pilot.

---

# 19. Pilot metrics

Track:
- routing accuracy on labelled/reviewed tasks;
- task success by route/model;
- delegation success rate;
- retry rate;
- average latency;
- cost per successful task;
- tool-call failure rate;
- duplicate-execution count;
- manual correction count;
- permission-denied attempts;
- percentage of Tola delegations accepted as correct;
- Rhythm plan correction rate;
- Growth insights actioned;
- Scholar content used;
- Skill trigger precision;
- Skill false positives;
- Skill improvement vs baseline;
- self-learning proposal usefulness.

---

# 20. Build stop rules

Stop and fix before moving forward if any of these occurs:
- existing Tola or Shiftlyx Telegram behaviour breaks;
- verified backup cannot be created;
- an agent sees a tool outside its contract;
- a specialist can spawn/send to another agent;
- free-form cross-agent access reappears;
- Blackboard produces unexplained competing truth;
- queued mutation replays twice;
- an agent claims an external write succeeded when it failed;
- router selects an unapproved model;
- Discord message lands in wrong agent;
- security audit introduces a new critical finding;
- an unapproved Skill becomes active;
- an agent modifies an approved production Skill without review;
- public content is posted without approval.

---

# 21. What Codex/OpenClaw must not improvise

During implementation, do not silently:
- replace hybrid Blackboard with SQLite-only or Supabase-only;
- add MCP servers;
- add Redis/Kafka/custom message bus;
- add free-form agent-to-agent messaging;
- add more agents;
- make Rhythm/Growth/Scholar delegators;
- expose generic HTTP/SQL tools;
- expose broad shell/file mutation capability;
- use a free model endpoint in production;
- add unrelated model families;
- merge Tola and Shiftlyx;
- remove Telegram before Discord proves stable;
- enable production publishing/spending/deployment tools;
- change Skill Workshop to `auto`;
- auto-install GitHub skills;
- auto-update external skills;
- globally install whole skill collections;
- let Growth post publicly;
- let Growth spend money;
- let Scholar schedule in My Rhythm;
- let Rhythm change strategic project priority.

Any such change requires an explicit architecture revision.

---

# 22. External Skill adoption matrix

| Agent | Source | V1 decision |
|---|---|---|
| Tola | Addy Osmani `planning-and-task-breakdown` | Adapt + test |
| Tola | Magnus919 `product-shaping` | Adapt concepts + test |
| Rhythm | Generic productivity skill packs | Do not install initially |
| Growth | Corey Haines `analytics` | Adapt + test |
| Growth | Corey Haines `attribution` | Adapt + test |
| Growth | Corey Haines `seo-audit` | Adapt + test |
| Growth | Corey Haines `cro` | Adapt + test |
| Growth | Corey Haines `ab-testing` | Adapt + test |
| Growth | Corey Haines `onboarding` | Adapt + test |
| Growth | Corey Haines `signup` | Adapt + test |
| Growth | Corey Haines `aso` | Adapt + test if relevant |
| Scholar | K-Dense `scientific-critical-thinking` | Strong candidate |
| Scholar | K-Dense paper lookup methodology | Adapt carefully |
| Scholar | K-Dense dependency-heavy research workflows | Do not install unchanged |
| All | Giant skill collections | Reject as global installs |

---

# 23. Skill update policy

An existing production Skill may be updated only through:

```text
new upstream revision / self-learning proposal
                    |
                    v
               quarantine
                    |
                    v
                  diff
                    |
                    v
             security review
                    |
                    v
           regression evaluation
                    |
                    v
             human approval
                    |
                    v
               activation
```

No floating "latest" production version.

---

# 24. Automation policy

Automation should reference a known workflow/Skill rather than a vague prompt whenever practical.

Preferred:

```text
Growth
  -> growth-weekly-review v1.3
  -> Monday automation
```

Avoid:

```text
"Every Monday improve growth somehow."
```

Conceptually:
- **Agent contract** defines who and authority.
- **Skill** defines how.
- **Automation** defines when.
- **Blackboard** defines shared organisational state.

---

# 25. Failure and recovery matrix

| Failure | Expected behaviour |
|---|---|
| Supabase offline | Cache only within freshness policy; low-risk queue; high-risk/authoritative changes blocked |
| SQLite unavailable | Supabase remains authority where possible; local cache/outbox failure visible |
| My Rhythm 500/timeout | Rhythm may propose but cannot claim write |
| IntenSIQ 500/timeout | Scholar returns partial/blocked; no saved claim |
| Search Console down | Growth labels partial data and does not invent SEO metrics |
| GA4 down | Growth labels missing coverage and avoids false zeroes |
| OpenRouter/model timeout | One bounded retry; no spawn loop |
| Malformed child result | Reject/repair once; never auto-complete |
| Gateway restart | Reconcile task/external evidence before retry |
| Stale outbox update | Conflict, no overwrite |
| Duplicate operation replay | Idempotent one effect |
| Skill proposal invalid | Remains quarantined/rejected |
| Skill directory tampered | Hash/revision mismatch prevents trusted activation |
| Public-post approval denied | External action does not execute |

---

# 26. Final V1 target architecture

```text
                                USER
                                  |
                        Discord / Telegram
                                  |
                                  v
                                TOLA
                 Chief of Staff / Model Router
                                  |
                        Delegation Protocol
                                  |
                     sessions_spawn only
                 +----------------+----------------+
                 |                |                |
                 v                v                v
              RHYTHM            GROWTH           SCHOLAR
                 |                |                |
              Skills           Skills           Skills
                 |                |                |
                 v                v                v
          My Rhythm API     GA4/GSC/UTM       IntenSIQ
                 |                |                |
                 +----------------+----------------+
                                  |
                         Blackboard Tools
                                  |
                         BlackboardRepository
                           /              \
                      SQLite             Supabase
                   cache/outbox          authority

                   OpenClaw Native Memory
                         per-agent only

                         Skill Workshop
                         PROPOSE ONLY
                              |
                       Human approval
                              |
                        approved skills

                    MODEL EXECUTION LAYER
        R0 Code / R1 Ling / R2 Nemotron / R3 DeepSeek / R4 GLM
```

---

# 27. Expansion gate

Do not add Forge, Studio, Ledger, Sentinel or any other specialist until:
- at least 14 days of stable pilot;
- no unresolved S0/S1 issue;
- no duplicate-action defect;
- no permission leak;
- routing performance understood;
- Skill triggering stable;
- Blackboard conflicts low and understood;
- user supervision burden is lower than before;
- system provides measurable benefit;
- a specific bottleneck clearly justifies another agent.

The next agent is chosen from evidence, not the original wishlist.

---

# 28. Final release checklist

- [ ] Verified OpenClaw backup exists.
- [ ] OpenClaw version and config are documented.
- [ ] `doctor --lint` is acceptable.
- [ ] `security audit --deep` has no unresolved critical finding.
- [ ] Telegram Tola still works.
- [ ] Existing Telegram Shiftlyx still works.
- [ ] Discord routes all four channels correctly.
- [ ] Tola can spawn only Rhythm/Growth/Scholar.
- [ ] Explicit `agentId` is required.
- [ ] Specialists cannot spawn or send cross-agent messages.
- [ ] Session visibility is deliberately restricted.
- [ ] Model allowlist contains only approved V1 models.
- [ ] No free endpoint is a production dependency.
- [ ] Blackboard migration tests pass.
- [ ] SQLite/outbox tests pass.
- [ ] Duplicate replay is idempotent.
- [ ] Stale-version conflict is detected.
- [ ] My Rhythm failures never produce false success.
- [ ] IntenSIQ failures never produce false success.
- [ ] Growth failures never produce fabricated current metrics.
- [ ] Skill Workshop explicitly uses `propose`.
- [ ] Approved Skills are pinned to local revisions/source commits.
- [ ] External Skill licences are recorded.
- [ ] No global skill dump is installed.
- [ ] Skill evaluation fixtures pass.
- [ ] No agent can silently mutate production Skills.
- [ ] Ordinary authorised tool calls remain autonomous.
- [ ] Public/external posting requires approval.
- [ ] Payments/destructive/security operations require approval.
- [ ] Automations invoke proven workflows where practical.
- [ ] Automations are idempotent and quiet.
- [ ] Four-agent orchestration scenarios pass.
- [ ] Recovery drill succeeds in staging.
- [ ] 14-day pilot has no unresolved S0/S1 defect.

---

# 29. Source references

## OpenClaw official documentation

- Agent bindings: https://docs.openclaw.ai/concepts/agent-bindings
- Session tools / `sessions_spawn`: https://docs.openclaw.ai/concepts/session-tool
- Session/subagent controls: https://docs.openclaw.ai/gateway/config-tools/sessions-and-subagents
- Agent entries / multi-agent configuration: https://docs.openclaw.ai/gateway/config-agents/entries-and-multi-agent
- Tool policy: https://docs.openclaw.ai/gateway/config-tools/tool-policy
- Tool/agent permissions: https://docs.openclaw.ai/gateway/security/tool-permissions
- Models / allowlists / utility model: https://docs.openclaw.ai/concepts/models
- Tool plugins: https://docs.openclaw.ai/plugins/tool-plugins
- Plugin permission requests: https://docs.openclaw.ai/plugins/plugin-permission-requests
- Skills: https://docs.openclaw.ai/tools/skills
- Skill Workshop: https://docs.openclaw.ai/tools/skill-workshop
- Self-learning: https://docs.openclaw.ai/tools/self-learning
- Memory: https://docs.openclaw.ai/concepts/memory
- Automations / cron: https://docs.openclaw.ai/cli/cron
- Backup: https://docs.openclaw.ai/cli/backup
- Security audit: https://docs.openclaw.ai/gateway/security/running-the-audit
- Doctor: https://docs.openclaw.ai/doctor
- Rollback/recovery: https://docs.openclaw.ai/install/updating/rollback-and-recovery

## External Skill sources to review/adapt

- Addy Osmani Agent Skills: https://github.com/addyosmani/agent-skills
- Magnus919 Agent Skills: https://github.com/magnus919/agent-skills
- Corey Haines Marketing Skills: https://github.com/coreyhaines31/marketingskills
- K-Dense Scientific Agent Skills: https://github.com/K-Dense-AI/scientific-agent-skills
- Anthropic Skill Creator reference: https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md

## Model references

- Ling 3.0 Flash: https://openrouter.ai/inclusionai/ling-3.0-flash
- Nemotron 3.5 Lightning: https://openrouter.ai/nvidia/nemotron-3.5-lightning
- DeepSeek V4 Flash 0731: https://openrouter.ai/deepseek/deepseek-v4-flash-20260731/
- GLM-5.3 Flash: https://openrouter.ai/z-ai/glm-5.3-flash

---

# 30. Final implementation rule

This document is the architecture and implementation contract.

Codex/OpenClaw may determine exact code structure, TypeScript implementation, adapters, schemas, tests and commands required by the installed OpenClaw version. It may **not silently change architectural principles**.

If implementation reveals a conflict:

```text
STOP
 |
record conflict
 |
verify installed OpenClaw version/docs
 |
explain impact
 |
revise architecture explicitly
 |
continue
```

Never hide an architecture change inside an implementation workaround.

---

# 31. Core philosophy

The goal is **not maximum autonomy**.

The goal is:

> **Maximum useful autonomy inside narrow, observable, reversible and testable authority boundaries.**

Agents should be free to:
- think;
- research;
- analyse;
- delegate within contract;
- use approved Skills;
- call authorised tools;
- write internal state;
- write approved private integrations;
- retry bounded failures;
- create plans and drafts;
- learn by proposing improvements.

Agents should not autonomously control:
- their own permanent behavioural rules;
- their own permissions;
- public communication;
- money;
- security;
- credentials;
- irreversible destruction.

**Skills make the agents better. Typed tools make them capable. Tool policy makes them bounded. Blackboard makes them coordinated. Tola makes them organised. Testing makes them trustworthy.**
