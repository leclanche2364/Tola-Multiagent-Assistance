# QA T11 Signoff Draft — Cross-Agent Synthesis
# Generated 2026-09-29
# Plain ASCII.

## Summary

Batch T11 implements cross-agent synthesis for the Tola
portfolio decision engine. Evidence from multiple specialists
(Growth, Rhythm, Scholar, Deadlines) is combined into a
portfolio decision while preserving source attribution,
specialist boundaries, and uncertainty.

## Files Created

- tola/synthesis/__init__.py
- tola/synthesis/attribution.py
- tola/synthesis/synthesizer.py
- tola/tests/test_t11_synthesis.py
- tola/reports/qa_t11_signoff_draft.md

## Rules Implemented

1. Growth opportunities constrained by Rhythm capacity
   (shortfall noted, opportunity not suppressed).
2. Scholar protected requirements preserved verbatim, never
   outweighed.
3. Conflicting evidence surfaced in unresolved_conflicts;
   decision says "conflict unresolved", never fabricates
   certainty.
4. Missing specialist input generates structured request
   (agent_id + what_is_needed), never a guess.
5. Decision and rationale lines carry source attribution.

## Per-Case Results

### T11-01: Growth opportunity constrained by Rhythm capacity
- Status: PASS
- Capacity shortfall is noted in decision text.
- Growth opportunities are preserved (not suppressed).
- Rationale includes capacity constraint reference.

### T11-02: Scholar protected requirement preserved
- Status: PASS
- Protected requirements appear verbatim in decision.
- Protected requirements are never removed or outweighed.

### T11-03: Growth + Scholar + Rhythm competing needs synthesized
- Status: PASS
- Decision references growth, scholar, and rhythm domains.
- Rationale includes evidence from all three specialists.

### T11-04: Conflicting evidence surfaced not fabricated
- Status: PASS
- Conflicts between growth opportunities and scholar
  requirements appear in unresolved_conflicts.
- Decision text contains "conflict unresolved".
- No certainty phrases (definitely, certainly, guaranteed)
  appear in decisions.

### T11-05: Missing specialist input generates request not guess
- Status: PASS
- Missing specialist (e.g. rhythm=None) produces an entry
  in missing_inputs with agent_id and what_is_needed.
- Decision does not fabricate missing specialist data.

### T11-06: Source attribution remains traceable
- Status: PASS
- Attribution lines contain agent_id, claim, and source
  tags in bracket format.
- Tags (e.g. growth:ref-123) survive through synthesis
  output.
- Rationale lines reference specialist tags.

## Deviations

None. All six QA T11 test cases pass. All five synthesis
rules are implemented as named constants with test coverage.

## Concerns

None. The implementation uses only Python stdlib, is
deterministic, and does not write to My Rhythm or any
external service.