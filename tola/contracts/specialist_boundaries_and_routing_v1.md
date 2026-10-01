# Specialist boundaries (frozen, per implementation plan v1.1 §4)

Captured 2026-09-29 from `tola/docs/tola_implementation_plan_v1_1.md`.

## Tola owns
portfolio priorities; cross-project trade-offs; delegation; goal-to-plan
decomposition; specialist selection; success criteria; plan review; scope
control; project health assessment; outcome verification; stalled-work
recovery; materiality/attention decisions; deciding when Rhythm must be
queried; accept/revise/stop/extend decisions on specialist work.

## Rhythm owns
work-shift truth; realistic capacity; schedule feasibility; exact time
placement; My Rhythm writes; dynamic replanning.
**Tola must NEVER write directly to My Rhythm.**
Substantial-work protocol: CAPACITY_QUERY -> CAPACITY_REPORT ->
Tola decision -> TASK_COMMITTED -> Rhythm schedules.

## Growth owns
product/growth analysis; acquisition, activation, conversion and retention
intelligence; experiment design and analysis; product metrics; growth
recommendations.

## Scholar owns
learning intelligence; curriculum planning; evidence synthesis; study
requirements; learning-gap detection.

## Marketing Agent(s) — FUTURE_NOT_AVAILABLE
Not part of the current build. Registry state must remain
FUTURE_NOT_AVAILABLE until contract, capability profile, boundaries,
allowed tools, security review, batch QA and Tola delegation tests are all
complete, then availability_status -> ACTIVE. Until then: eligible
marketing work routes to Growth; ineligible work becomes
FUTURE_SPECIALIST_DEPENDENCY. Never simulated as completed.

## User authority (never silently changed)
security policy; tool permissions; approval boundaries; production
model-routing architecture; external integrations; consequential public
actions; durable architecture decisions.

## Capability registry availability states
ACTIVE | FUTURE_NOT_AVAILABLE | DISABLED | DEGRADED
Autonomous delegation allowed only to ACTIVE agents.

# Model routing (as of 2026-09-29)

- Main/router: openrouter/z-ai/glm-5.3-flash (GLM 5.3 Flash)
- Small scoped: openrouter/nvidia/nemotron-3.5-lightning:free (Lightning)
- Medium reasoning: openrouter/nex-agi/nex-n2.5-pro:free (Nex Pro)
- Fallback rule: on free-model failure retry once on the other free
  model, then report. Structural Dart edits and git push stay in main.
- Sub-agent spawn requires explicit agentId; allowed: growth, rhythm,
  scholar (defaults qwen3.8-27b:free, override per spawn).
- Model routes (current contract: docs/CURRENT_SYSTEM.md): tola/shiftlyx =
  glm-5.3-flash; rhythm/growth = qwen3.8-27b:free with ling-3.0-flash (paid)
  fallback; scholar = qwen3.8-27b:free.

# Restore manifest (T0-05)

1. OpenClaw config snapshot: ~/.openclaw-backups/config-20260929/
   contains openclaw.json, openclaw.json.bak-20260928,
   exec-approvals.json, .model-watch-state.
   Restore: cp files back to ~/.openclaw/ and restart gateway.
2. Tola persona/contract: tola/baseline/ SOUL.md, AGENTS.md,
   IDENTITY.md, USER.md. Restore: cp to ~/.openclaw/workspace/.
3. Blackboard schema: tola/baseline/blackboard_schema_v1.sql (v1
   migration; live schema already deployed on Supabase project
   jcqiokvbkocnoxgeitin).
4. Live OpenClaw config copy: tola/baseline/openclaw-config-20260929.json.
5. Skills inventory: tola/baseline/skills_inventory.txt.
6. Note: full-tree tar backups of ~/.openclaw were attempted twice and
   SIGKILLed (21 GB tree, media/node_modules excluded still too heavy).
   Targeted file-level capture used instead. Revisit with a fuller
   strategy in a later batch if needed.
