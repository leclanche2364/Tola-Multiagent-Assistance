# Batch 15 — Live Gate Recovery Drill (Main Session)

The following shell commands are **main-session / live-gate items** — they are NOT implemented in this package. They are documented here as a reference.

## Recovery Drill Commands

```bash
openclaw backup create --output ~/Backups/openclaw --verify
openclaw security audit --deep
openclaw doctor --lint --json
openclaw health
openclaw gateway status --deep --json
```

These commands require a live OpenClaw gateway and must be run by the main session, not by this subagent. No real network, Supabase, or backup operations are performed here.

## Scope Note

This package (`packages/resilience`) uses mocks and injected fakes only. All resilience behaviours are tested with pure logic and stubbed interfaces.
