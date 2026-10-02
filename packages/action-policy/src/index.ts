export {
  ACTION_CATALOG,
  evaluateAction,
  stripModelSuppliedPolicy,
  verifyApprovedPayload,
  consumeEnvelope,
  DEFAULT_POLICY_CONFIG,
} from "./policy.ts";
export type {
  Decision,
  ActionDomain,
  Consequence,
  ActionDef,
  PolicyResult,
  PreAuthorisation,
  PolicyConfig,
} from "./policy.ts";

export {
  hashAction,
  FakeApprovalExecutor,
  type ApprovalExecutor,
  type ApprovalRecord,
  type ApprovalState,
  type ExecutionOutcome,
  type ApprovalRequestParams,
  type ExecuteAllowedParams,
  type ExecuteApprovedParams,
  redactApprovalScope,
  // Two-tier state machine (Growth G01)
  type Tier,
  type TierRecord,
  type TwoTierState,
  createTwoTierState,
  validateTwoTier,
} from "./executor.ts";