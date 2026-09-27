// Fault envelopes — Batch 15
export type FaultKind =
  | 'supabase-offline'
  | 'myrhythm-unavailable'
  | 'intensiq-unavailable'
  | 'datasource-partial'
  | 'provider-timeout'
  | 'malformed-result'
  | 'skill-tamper'
  | 'approval-denied';

export class UnavailableError extends Error {
  public readonly code = 'UNAVAILABLE';
  public readonly kind: FaultKind;
  constructor(kind: FaultKind, message: string) {
    super(message);
    this.kind = kind;
    this.name = 'UnavailableError';
  }
}

export class ApprovalDeniedError extends Error {
  public readonly code = 'APPROVAL_DENIED';
  constructor(message: string = 'Approval denied — execution prevented') {
    super(message);
    this.name = 'ApprovalDeniedError';
  }
}

export class TamperDetectedError extends Error {
  public readonly code = 'TAMPER_DETECTED';
  constructor(message: string = 'Skill directory tampering detected') {
    super(message);
    this.name = 'TamperDetectedError';
  }
}
