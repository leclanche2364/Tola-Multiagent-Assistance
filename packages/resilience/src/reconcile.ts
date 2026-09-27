// reconcileTaskState — before replaying a mutation after gateway restart,
// verify task state vs external evidence ref; only replay if evidence confirms incomplete.
// Pure logic with injected interfaces.

export interface EvidenceRef {
  taskId: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'blocked';
  evidence: Record<string, unknown>;
}

export interface BlackboardLike {
  getTask(taskId: string): Promise<{ status: string } | null>;
}

export function reconcileTaskState(
  blackboard: BlackboardLike,
  evidenceRef: EvidenceRef,
): { replay: boolean; reason: string } {
  // Evidence shows completed → skip replay
  if (evidenceRef.status === 'completed') {
    return { replay: false, reason: `Evidence confirms task ${evidenceRef.taskId} is already completed; replay skipped` };
  }
  // Evidence shows failed/blocked → skip replay (terminal states)
  if (evidenceRef.status === 'failed' || evidenceRef.status === 'blocked') {
    return { replay: false, reason: `Evidence shows terminal state ${evidenceRef.status}; replay skipped` };
  }
  // Evidence confirms incomplete → replay allowed
  return { replay: true, reason: `Evidence confirms incomplete state ${evidenceRef.status}; replay permitted` };
}
