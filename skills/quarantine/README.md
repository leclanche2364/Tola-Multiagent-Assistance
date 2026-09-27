# skills/quarantine

## Purpose

Holds all imported skill candidates before human review. Skills in quarantine are **never loaded by agents** and cannot be activated. Every candidate must be pinned to an exact upstream commit and inspected before it can graduate.

## Lifecycle Rules

- **Unreviewed imports only.** Any skill entering the system lands here first.
- **Never loaded by agents.** Quarantined skills are inert — no runtime activation.
- **Intake produces a finding checklist:** scripts/deps inspected, network/secret requirements documented, behavioural instructions reviewed, unnecessary capabilities flagged.
- **Graduation to approved** requires: licence present, commit pinned, checklist complete, evaluation fixtures exist.
- **Rejection** is permanent for malicious or overbroad candidates.
- **No auto-promotion.** Only a human can move a skill from quarantine to approved.
