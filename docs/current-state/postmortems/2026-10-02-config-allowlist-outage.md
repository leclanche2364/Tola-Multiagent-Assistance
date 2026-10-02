# Postmortem — 2026-10-02 live config apply outage

## What happened

During application of the Batch 08 hardened config to the live gateway, per-agent `tools.allow` allowlists were merged into `~/.openclaw/openclaw.json`. `tools.allow` in the live runtime is a global deny-by-default allowlist over ALL tools, not a scoping block for Blackboard/task tool routing. Result: tola, rhythm and growth lost exec/message/read/spawn and could not work or reply. The gateway validated the config, restarted, and ran it. Habeeb diffed against the pre-change backup and reverted at 16:37 the same day. No data was lost.

## Root causes

1. **Semantic misread.** The Batch 08 candidate spec treated `tools.allow` as blackboard-tool scoping. In the live runtime it gates every tool. Schema validation passed because the field is real and well-formed; it validated shape, not effect.
2. **No post-restart smoke test.** The apply was verified with `openclaw config validate` and reported as success. No test message or task was sent through any agent after the restart. "It validates" repeated the "it connected" credential fallacy.
3. **QA-08 validated on paper only.** Lint/tests/secret scans gave false confidence; nothing rehearsed the config against real gateway tool-resolution semantics.

## Standing rules (binding)

1. **`tools.allow` is a full deny-by-default gate.** Any allowlist on a live agent must include every base tool that agent needs (exec, message, read, spawn, gateway, cron) or the agent locks itself out. Prefer deny-lists or narrow scoped blocks for hardening.
2. **Schema-valid is not semantically safe.** Validation is a floor, never evidence of correctness.
3. **Mandatory smoke test after any live config restart that touches agents/tools:** spawn one trivial task per affected agent (exec + read check) and confirm PASS in the transcripts before reporting success. This is the check that was skipped on 2026-10-02.
4. **Never merge per-agent caps/allowlists from a candidate file without independently confirming the runtime semantics of each key against live docs or a disposable agent.**
5. **Keep the pre-apply backup** (`openclaw.json.backup-<date>`) for every live config write, and record the path in the session report. Revert is the first response to post-apply malfunction, not further debugging.

## Fixes applied

- Live config reverted to pre-hardening state (Habeeb, 2026-10-02 16:37); broken version preserved at `openclaw.json.broken-batch08-20261002`.
- All four specialists verified working post-revert (exec + read PASS per agent, 2026-10-02 18:22).
- `config-candidate/openclaw.json`: per-agent `tools.allow` blocks removed (see candidate `README-NOTE` in this folder) so the candidate can never be applied as-is again.
