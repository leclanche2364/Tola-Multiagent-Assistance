# CURRENT_SYSTEM — Four-Agent System Contract

**Status: this document is the single current architecture contract.**
Any earlier document that contradicts this one is superseded (pointers added at the old locations). Historical and plan documents are retained as history, not as instructions.

## 1. Persistence

- **Supabase is the only application/Blackboard persistence.** All shared coordination state (Blackboard tables, events, task state) lives in the four-agent Supabase project (`jcqiokvbkocnoxgeitin`).
- **OpenClaw may retain internal control-plane state** for sessions, automations/cron, approvals, run history and agent directories. This is OpenClaw's own plumbing, not application state.
- Local SQLite outboxes have been **removed** from this repo (Batch 02): a failed Supabase write surfaces as an explicit `BlackboardError` and is retried later with the same `idempotency_key`; nothing is queued locally. Growth's product-intelligence local writer lives outside this repo and is a declared analytics cache, not shared persistence.

## 2. Agents, boundaries and model routes

Five real agents, each scoped to its own workspace. There are no stub agents: all five are live.

| Agent | Scope | Workspace | Primary model | Fallback |
|---|---|---|---|---|
| **Tola** | Coordinator, git ops, approval gates | `~/.openclaw/workspace` | `openrouter/z-ai/glm-5.3-flash` | — |
| **Shiftlyx** | Shiftlyx product work | `~/.openclaw/workspace-shiftlyx` | `openrouter/z-ai/glm-5.3-flash` | — |
| **Rhythm** | Time/capacity/scheduling | `~/.openclaw/workspace-rhythm` | `openrouter/qwen/qwen3.8-27b:free` | `ling-3.0-flash` (paid) |
| **Growth** | Growth/marketing/analytics | `~/.openclaw/workspace-growth` | `openrouter/qwen/qwen3.8-27b:free` | `ling-3.0-flash` (paid) |
| **Scholar** | Learning/research/evidence | `~/.openclaw/workspace-scholar` | `openrouter/qwen/qwen3.8-27b:free` | per-spawn override |

- Routing: hub-and-spoke. Requests classify to a specialist; Tola spawns the specialist with a complete task envelope; no specialist-to-specialist communication (the Blackboard is the only cross-agent channel).
- Tool access: each agent sees only the tools its channel/config grants. Credentials live in per-consumer env files; the credentials index (`~/.openclaw/workspace/CREDENTIALS_INDEX.md`) maps names only.

## 3. Deployment status

- All five agents run on the local gateway (macOS host), OpenClaw 2026.7.1-2.
- Knowledge graph: `graphify-out/` in this repo (code-only, local, no LLM key); freshness rule — any agent modifying repo files runs `graphify update .` before reporting done; query via `graphify-out/graphq.sh`.
- Growth publishing is read-only via Metricool MCP (write tools excluded); posting requires human approval.

## 4. Autonomy classes

Actions are classified into exactly one of:

1. **C1 — Automatic read/analysis.** Reads, searches, diagnostics, test runs, graph queries. Always allowed.
2. **C2 — Automatic reversible internal writes.** Local file edits, local commits, scratch work. Always allowed.
3. **C3 — Automatic pre-authorised private writes within limits.** Writes the human has explicitly pre-approved (e.g. branch pushes on `feat/autonomy-supabase-only` during this plan, propose-only API calls). Allowed only while the specific authorisation is active.
4. **C4 — Human-gated.** Always requires explicit approval before acting:
   - Public communication (publishing, posting, email, outreach, social content)
   - Spending money
   - Destructive actions (deletions, force-pushes, resets)
   - Credentials/security (token creation, secret handling beyond granted scopes)
   - Production config, plugin or skill changes
   - Automation (cron) creation or change
   - Any write to Supabase outside confirmed dev scope
   - Any push to `main` or public repos

## 5. Self-privilege prohibition

Agents can never:
- approve themselves or each other's gated actions,
- raise their own or another agent's permissions,
- choose their own risk class,
- re-enable tools excluded by config (e.g. Metricool write tools),
- bypass an approval gate by any alternative execution path.

Approval authority rests solely with the human (Habeeb). A verifier agent checks evidence independently and records PASS/FAIL; a PASS is not an approval.

## 6. Historical corrections

The following earlier statements are wrong and are corrected by this document:
- "Three specialist agent IDs are stubs for testing only" — false; all five agents are live.
- "SQLite outbox is shared coordination state" — false; Supabase is the only shared persistence; local SQLite is per-agent outbox/cache only.
- "All Scholar reasoning uses ling-3.0-flash" — false; Scholar routes to `qwen3.8-27b:free` (ling only as per-spawn override).
- Rhythm/Growth lack a paid fallback — false; `ling-3.0-flash` is their fallback.
