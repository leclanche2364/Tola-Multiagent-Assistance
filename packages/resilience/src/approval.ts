// approval gate stub — publishAttempt requires approved=true;
// denial throws ApprovalDeniedError and prevents execution.

import { ApprovalDeniedError } from './faults.ts';

export interface PublishAttempt {
  approved: boolean;
  action: () => Promise<void>;
}

export async function publishAttempt(attempt: PublishAttempt): Promise<void> {
  if (!attempt.approved) {
    throw new ApprovalDeniedError('A3 public-post attempt blocked — approval denied');
  }
  // Approved — execute the action
  await attempt.action();
}
