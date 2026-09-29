# Scholar Baseline Restore Manifest

## What Constitutes the Scholar Baseline

The Scholar baseline (Batch S0) includes:

1. This document (RESTORE_MANIFEST.md)
2. The implementation plan: scholar/docs/scholar_implementation_plan_v1_0.md
3. The testing plan: scholar/docs/scholar_testing_plan_v1_0.md
4. The directory skeleton: scholar/{contracts,curriculum,goals,learner_state,mastery,intensiq,research,evidence,literature,integrity,events,skills,tests,fixtures,docs,reports}
5. Frozen contracts:
   - contracts/boundaries.md
   - contracts/model_routing.md
   - contracts/intensiq_handover.md
6. Frozen skills list: skills/FROZEN_SKILLS.md
7. S0 test suite: tests/test_s0_baseline.py
8. QA signoff draft: reports/qa_s0_signoff_draft.md

## Restore Procedure

1. Verify the four-agent repo is present at the expected path.
2. Copy the directory skeleton into scholar/.
3. Copy all contract files into scholar/contracts/.
4. Copy skills/FROZEN_SKILLS.md into scholar/skills/.
5. Copy tests/test_s0_baseline.py into scholar/tests/.
6. Run the S0 test suite to verify the baseline.
7. Review reports/qa_s0_signoff_draft.md for signoff.

## Architecture Source of Truth

The restorable architecture is documented in the four-agent repo:

- agents/tola.md -- Tola agent boundaries and delegation rules
- openclaw_four_agent_system_v1_1.md -- Four-agent system architecture, skills, batch plan, and QA gates

These two documents define the architecture that this baseline captures and freezes.

## Config/Architecture Snapshot Summary

- Primary agent: Scholar
- Primary model: inclusionai/ling-3.0-flash (R1 reasoning only)
- Deterministic layer: R0 code (validation, calculations, event handling, state integrity)
- Learning execution platform: IntenSIQ
- Scheduling authority: Rhythm (My Rhythm writes only)
- Portfolio priority authority: Tola
- Shared coordination state: Supabase Blackboard + SQLite cache/outbox where required
- Companion QA document: scholar_testing_plan_v1_0.md
- Frozen skills: 22 V1 Skills (see skills/FROZEN_SKILLS.md)
- Explicitly excluded skills: 6 (see skills/FROZEN_SKILLS.md)
- Scholar non-responsibilities: 18 items (see contracts/boundaries.md)
- IntenSIQ integration additions: 3 (learner-state read, versioned learning plan GET/PUT, durable events outbox)
- Batch sequence: S0 through S31
