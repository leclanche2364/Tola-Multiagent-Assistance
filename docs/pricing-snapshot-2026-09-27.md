# Pricing snapshot — T6.6 (2026-09-27)

Source: OpenRouter models API (`https://openrouter.ai/api/v1/models`), pulled 2026-09-27.
Prices are USD per token. Re-check at every provider/model change (§10.5: do not hard-code long-term price assumptions into architecture).

| Route | Model | Prompt $/tok | Completion $/tok |
|---|---|---|---|
| R0 | deterministic code (no model) | — | — |
| R1 | `inclusionai/ling-3.0-flash` | 0.000000021 | 0.000000063 |
| R2 | `nvidia/nemotron-3.5-lightning` | 0.00000008 | 0.0000002 |
| R3 | `deepseek/deepseek-v4-flash-0731` | 0.000000021 | 0.00000032 |
| R4 | `z-ai/glm-5.3-flash` | 0.000000045 | 0.00000014 |
| router | `typesafe/jev-router` | pricing not exposed via API (−1) | −1 |

Notes:
- Jev Router (`typesafe/jev-router`) reports no public per-token pricing; do not route production spend through it until pricing and the T6.1 accuracy gate are both pinned (§10.4 amendment).
- Cost reconciliation (T6.5) computes expected cost as `input_tokens × prompt_price + output_tokens × completion_price` from this table and compares directionally against recorded `model_runs.cost_usd`.
