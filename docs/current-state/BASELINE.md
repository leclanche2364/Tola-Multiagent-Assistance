# Autonomy Baseline — captured 2026-10-01 (Batch 00)

Captured on branch `feat/autonomy-supabase-only`. Read-only diagnostics; no live state was modified.

## Versions
- OpenClaw: 2026.7.1-2 (0790d9f)
- Node: v25.9.0
- Python: 3.14.7 (pytest NOT installed — blocker, unittest used instead)
- Host: macOS 13.7.8 (x64)

## Agents (openclaw agents list)
| Agent | Workspace | Model |
|---|---|---|
| tola (default) | ~/.openclaw/workspace | openrouter/z-ai/glm-5.3-flash |
| shiftlyx | ~/.openclaw/workspace-shiftlyx | openrouter/z-ai/glm-5.3-flash |
| rhythm | ~/.openclaw/workspace-rhythm | openrouter/qwen/qwen3.8-27b:free |
| growth | ~/.openclaw/workspace-growth | (qwen3.8-27b:free primary; ling-3.0-flash fallback) |
| scholar | ~/.openclaw/workspace-scholar | (see agent dir) |

Agent dirs live under `~/.openclaw/agents/<id>/agent`.

## Plugins
- 56/72 enabled (stock source root: openclaw dist/extensions)
- Notable disabled: active-memory, @openclaw/admin-http-rpc
- Diagnostics command: `openclaw plugins list`

## Automations (cron)
- session-handover daily 21:00 (tola, isolated, announce telegram) — ok
- shiftlyx-daily-handover 22:00 (session:shiftlyx) — ok
- workspace-backup-8h every 8h — ok
- growth-data-pull-06 06:00 (growth) — ERROR (2x): announce target "discord" missing recipient
- Morning Handover 07:00 (tola) — ok
- revalidation-backup-c 07:10 (tola) — ok
- public-speaking-daily 07:30 (shiftlyx) — ERROR (12x)
- plus others (see `openclaw cron list`)
- Known doctor finding: ~10 blocked TaskFlows pointing at missing task IDs (inspect: `openclaw tasks flow show <flow-id>`)

## Doctor (openclaw doctor — read-only run)
- Doctor completed with warnings; recurring finding: blocked TaskFlows with missing task references. No `--fix` applied (batch rule: no live mutation).

## Test evidence
- Python (`python3 -m unittest discover -s tola/tests -t .`): **1013 tests, OK, 0 failures** (0.094s)
- TypeScript (`cd packages/openclaw-tools && node --experimental-strip-types --test --test-concurrency=1 tests/openclaw-tools.test.ts`): **9 tests, 9 pass, 0 fail, 0 skipped**
- Environmental blocker: pytest unavailable for both system Pythons (3.14/3.13) — suites run via unittest; no dependencies installed or changed, per batch rules.

## Reload mode / health
- Gateway healthy at diagnostics time (doctor completed).
- Effective exec policy: approvals enforced through native approval cards; elevated commands require explicit /approve per command.

## Redaction note
All tokens, API keys, credential URLs and environment values are excluded from this document by design. Secrets live only in `~/.openclaw/secrets/`, per-env files, and the keychain; see workspace CREDENTIALS_INDEX.md (names only).

## Preserved uncommitted work at branch point
- Branch created from `main` at `4526b39` (which includes the graphify integration commit). No user changes were altered or stashed.