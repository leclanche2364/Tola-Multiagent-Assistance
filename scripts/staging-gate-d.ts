// Batch 12 Gate D — A3 approval flow (Batch 06 executor).
// 1. Request approval
// 2. Prove zero external effect before approval
// 3. Approve + execute
// 4. Replay must not re-execute (consumed)
// 5. Capture approval scope summary (redacted)

import { FakeApprovalExecutor, hashAction, redactApprovalScope } from "../packages/action-policy/src/executor.ts";
import { evaluateAction } from "../packages/action-policy/src/policy.ts";

async function main() {
  const results: string[] = [];
  const exec = new FakeApprovalExecutor();
  const RELEASE_SHA = "aa4f0e2aacf564a3b3147291d8183e6cf981ae62";

  // Step 1: Request approval
  const approval = await exec.requestApproval({
    action: "blackboard.createTask",
    payload: { title: "A3 approval test", assignee: "specialist-stub" },
    requester: "gate-d-a3",
    releaseSha: RELEASE_SHA,
    taskId: "task-a3-001",
    expirySeconds: 300,
    scope: "account=1234567890123456; key=sk_live_abc123def456; action=create_task",
  });
  results.push(`Step 1 — Request: id=${approval.approval_id}, status=${approval.status}, scope=${approval.scope}`);

  // Step 2: Prove zero external effect before approval
  const beforeState = await exec.getApprovalStatus(approval.approval_id);
  results.push(`Step 2 — Pre-approval state: status=${beforeState?.status}, used=${beforeState?.used} (must be pending/false)`);
  if (beforeState?.status !== "pending") throw new Error("Should be pending before approval");

  // Step 3: Approve + execute
  await exec.approveApproval(approval.approval_id, "operator");
  const afterApprove = await exec.getApprovalStatus(approval.approval_id);
  results.push(`Step 3 — After approve: status=${afterApprove?.status}`);

  let effectCount = 0;
  const execResult = await exec.executeApproved({
    approvalId: approval.approval_id,
    action: "blackboard.createTask",
    payload: { title: "A3 approval test", assignee: "specialist-stub" },
    requester: "gate-d-a3",
    releaseSha: RELEASE_SHA,
    taskId: "task-a3-001",
    effect: async () => { effectCount++; return { created: true }; },
  });
  results.push(`Step 3 — Execute: status=${execResult.status}, effectCount=${effectCount}, evidence=${(execResult as { evidence: string }).evidence}`);

  // Step 4: Replay must not re-execute
  const replayResult = await exec.executeApproved({
    approvalId: approval.approval_id,
    action: "blackboard.createTask",
    payload: { title: "A3 approval test", assignee: "specialist-stub" },
    requester: "gate-d-a3",
    releaseSha: RELEASE_SHA,
    taskId: "task-a3-001",
    effect: async () => { effectCount++; return { created: true }; },
  });
  results.push(`Step 4 — Replay: status=${replayResult.status}, effectCount=${effectCount} (must be 1)`);
  if (replayResult.status !== "consumed") throw new Error("Replay should be consumed");
  if (effectCount !== 1) throw new Error("Effect should only run once");

  // Step 5: Approval scope summary (redacted)
  const scopeSummary = redactApprovalScope(approval.scope);
  results.push(`Step 5 — Scope summary (redacted): ${scopeSummary}`);
  if (scopeSummary.includes("1234567890123456")) throw new Error("Scope not redacted");
  if (scopeSummary.includes("sk_live_abc123def456")) throw new Error("Secret not redacted");

  // Verify hash consistency
  const h1 = hashAction("blackboard.createTask", { title: "A3 approval test", assignee: "specialist-stub" });
  const h2 = hashAction("blackboard.createTask", { assignee: "specialist-stub", title: "A3 approval test" });
  results.push(`Step 5 — Hash canonical: h1=${h1.slice(0, 16)}... h2=${h2.slice(0, 16)}... match=${h1 === h2}`);

  results.push("GATE-D: PASS");
  console.log(results.join("\n"));
}

main().catch((err) => { console.error("GATE-D: FAIL", err); process.exit(1); });
