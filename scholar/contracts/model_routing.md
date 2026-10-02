# Scholar Model Routing

## Routing Rule

Scholar V1 uses exactly one LLM for reasoning.

### R0 - DETERMINISTIC CODE

Schema validation
Event deduplication
Cursor processing
Progress calculations
Coverage calculations
Version checks
Plan validation
Idempotency
Freshness checks

### R1 - Ling 3.0 Flash (sole reasoning model)

All Scholar reasoning defaults to `ling-3.0-flash` with per-spawn overrides (see docs/CURRENT_SYSTEM.md, the current contract).
- learning goal decomposition
- curriculum mapping
- proficiency mapping
- learning-gap analysis
- mastery interpretation
- adaptive learning strategy
- IntenSIQ feedback analysis
- literature triage/appraisal
- project research
- evidence synthesis
- feature-gap detection
- communication with Tola/Rhythm

## Routing Policy

- No semantic model escalation.
- The routing decision is deterministic code (R0), never a model call.
- Scholar must not silently switch models under any circumstance.

## Failure Policy

```text
Ling call
  -> technical failure
  -> one retry
  -> still fails
  -> PARTIAL / BLOCKED / FAILED
```

- Never silently switch to another model on failure.
- Never escalate to a different model for "better reasoning."
- PARTIAL, BLOCKED, and FAILED are the only failure outcomes.
- Retry count is recorded; no automatic model fallback.
