// Batch 12 Gate C — Isolation denials.
// Assert all 5 denial cases return DENY with clear reasons.

import { evaluateAction } from "../packages/action-policy/src/policy.ts";

const results: string[] = [];
let allDenied = true;

function check(label: string, action: string, payload: unknown, expectedDenyReason: string) {
  const result = evaluateAction(action, payload);
  const pass = result.decision === "DENY" && result.reason.includes(expectedDenyReason);
  results.push(`${label}: ${result.decision} (${result.reason}) — ${pass ? "PASS" : "FAIL"}`);
  if (!pass) allDenied = false;
}

// 1. Spawn action (specialist attempting to spawn another specialist)
check("Spawn action", "delegation.spawnSpecialist", { agentId: "sub-specialist", prompt: "do work" }, "permanent_deny");

// 2. Another specialist's tool (specialist trying to use a different specialist's tool)
check("Other specialist tool", "delegation.sendToSpecialist", { agentId: "other-specialist", taskId: "x" }, "permanent_deny");

// 3. Generic exec/SQL action (not in catalog)
check("Generic exec action", "exec.run", { command: "rm -rf /" }, "unknown_action");

// 4. Self-approve (security.permanent_deny)
check("Self-approve", "security.selfApprove", { reason: "I approve myself" }, "permanent_deny");

// 5. Oversized payload (exceeds 16KB envelope)
const bigPayload = { data: "x".repeat(20_000) };
check("Oversized payload", "blackboard.createTask", { title: "big", data: bigPayload.data }, "oversized_payload");

// 6. Non-allowlisted action (not in catalog at all)
check("Non-allowlisted action", "unknown.action", { anything: true }, "unknown_action");

results.push(`All denials: ${allDenied ? "PASS" : "FAIL"}`);
console.log(results.join("\n"));
if (!allDenied) process.exit(1);
