/** Status of an ADL capability */
export type AdlStatus = 'provisional' | 'validated' | 'deprecated' | 'forked' | 'archived';

/** Mode of the ADL system */
export type SystemMode = 'strict' | 'moderate' | 'lenient';

/** Paginated list of capability IDs */
export interface PaginatedListResponse {
  capabilities: string[];
  total: number;
  count: number;
  offset: number;
  limit: number;
}

/** Current status of a single ADL */
export interface StatusResponse {
  adl_id: string;
  status: AdlStatus;
  confidence: number;
  validators: string[];
  dev_mode: boolean;
}

/** History of events for a single ADL */
export interface HistoryResponse {
  adl_id: string;
  events: EventDict[];
}

/** A single event in the ADL chain */
export interface EventDict {
  event_id: string;
  concept_id: string;
  event_type: string;
  actor: string;
  reasoning: string;
  timestamp: string;
  payload: Record<string, unknown>;
  previous_event_id: string;
  hash: string;
}

/** Integrity verification result */
export interface VerifyResponse {
  adl_id: string;
  integrity_ok: boolean;
}

/** Current system mode */
export interface ModeResponse {
  mode: SystemMode;
  n_min: number;
  dev_mode: boolean;
}

/** Register a new capability */
export interface RegisterRequest {
  concept_id: string;
  initial_validator?: string;
}

/** Register response */
export interface RegisterResponse {
  adl_id: string;
  event_id: string;
  status: AdlStatus;
}

/** Transition a capability to a new status */
export interface TransitionRequest {
  adl_id: string;
  to_status: AdlStatus;
  actor: string;
  reason: string;
  payload?: Record<string, unknown>;
}

/** Transition response */
export interface TransitionResponse {
  adl_id: string;
  event_id: string;
  previous_status: AdlStatus;
  new_status: AdlStatus;
}

/** Fork a capability */
export interface ForkRequest {
  original_id: string;
  fork_id: string;
  actor: string;
  reason: string;
}

/** Fork response */
export interface ForkResponse {
  original_adl_id: string;
  forked_adl_id: string;
  fork_event_id: string;
}

/** Summary view of a capability (computed from status) */
export interface CapabilitySummary {
  adl_id: string;
  status: AdlStatus;
  confidence: number;
  validators: string[];
  validator_count: number;
  confidence_color: string;
}

/** Health overview stats */
export interface HealthStats {
  total: number;
  active: number;
  deprecated: number;
  avg_confidence: number;
  mode: SystemMode;
  dev_mode: boolean;
}

/** EWMA curve data point */
export interface EwmaPoint {
  timestamp: string;
  raw: number;
  smoothed: number;
}

/** Fork tree node */
export interface ForkTreeNode {
  adl_id: string;
  event_type: string;
  children: ForkTreeNode[];
}

/** Validator vote detail */
export interface ValidatorVote {
  validator: string;
  event_id: string;
  timestamp: string;
  reasoning: string;
}

// ---------------------------------------------------------------------------
// Agents (M1a)
// ---------------------------------------------------------------------------

/** Role of a consensus agent */
export type AgentRole =
  | 'discoverer'
  | 'reviewer'
  | 'skeptic'
  | 'merger'
  | 'librarian'
  | 'planner';

/** Lifecycle status of an agent */
export type AgentStatus = 'pending' | 'active' | 'deprecated';

/** A single consensus agent */
export interface Agent {
  did: string;
  role: AgentRole;
  name: string;
  status: AgentStatus;
  validator_count: number;
  scope: string;
}

/** Paginated agent list response */
export interface AgentListResponse {
  agents: Agent[];
  total: number;
  offset: number;
  limit: number;
}

/** Response shape for agent registration/attestation/validation/deprecation */
export type AgentResponse = Agent;

/** Register a new agent */
export interface AgentRegisterRequest {
  name: string;
  role: AgentRole;
  scope?: string;
  did?: string;
  model?: string;
  capabilities?: string[];
  org_id?: string;
  public_key?: string;
  genesis_signature?: string;
}

/** Attest an agent with a signature */
export interface AgentAttestRequest {
  signature: string;
  proof?: string;
}

/** Validate an agent as a validator */
export interface AgentValidateRequest {
  validator_did: string;
  reason?: string;
  confidence?: number;
  signature?: string;
}

/** Deprecate an agent */
export interface AgentDeprecateRequest {
  actor: string;
  reason?: string;
}

/** Event in an agent's history chain */
export interface AgentHistoryEvent {
  event_id: string;
  event_type: string;
  actor: string;
  reasoning: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

/** Agent history response */
export interface AgentHistoryResponse {
  adl_id: string;
  events: AgentHistoryEvent[];
}

/** Agent reputation summary */
export interface AgentReputationResponse {
  did: string;
  score_v2: number;
  validate_count: number;
  submit_count: number;
  accepted_count: number;
  task_success_rate: number;
  fork_merge_rate: number;
  deprecation_rate: number;
  note: string;
}

/** Admin public-key registration request */
export interface AdminPublicKeyRequest {
  did: string;
  public_key: string;
}

/**
 * Admin public-key registration response.
 *
 * Matches the backend implementation: `registered` is the DID that was
 * registered (a string), and `admin_public_keys` is the total count of keys.
 */
export interface AdminPublicKeyResponse {
  registered: string;
  admin_public_keys: number;
}

// ---------------------------------------------------------------------------
// Auth (AUTH_ENABLED deployments)
// ---------------------------------------------------------------------------

/** OAuth2 password-flow login request (username + password/API key). */
export interface LoginRequest {
  username: string;
  password: string;
}

/** OAuth2 password-flow token response from `POST /api/v1/auth/token`. */
export interface LoginResponse {
  access_token: string;
  token_type: string;
}

// ---------------------------------------------------------------------------
// Meta (state-machine single source of truth)
// ---------------------------------------------------------------------------

/**
 * Legal task transitions, keyed by source status.
 *
 * Example:
 * ```
 * {
 *   "open": ["assigned", "in_progress", "closed"],
 *   "assigned": ["in_progress"],
 *   "in_progress": ["in_progress", "submitted"],
 *   "submitted": ["validated", "rejected"],
 *   "rejected": ["in_progress", "closed"],
 *   "validated": ["closed"],
 *   "closed": []
 * }
 * ```
 */
export interface TaskTransitionsResponse {
  transitions: Record<string, TaskStatus[]>;
}

/** Role definition returned by `GET /api/v1/meta/roles`. */
export interface RoleDefinition {
  allowed_tools: string[];
  validation_policy: string;
  system_prompt: string;
}

/** Role registry response from `GET /api/v1/meta/roles`. */
export interface RolesResponse {
  roles: Record<string, RoleDefinition>;
}

// ---------------------------------------------------------------------------
// Tasks (M2)
// ---------------------------------------------------------------------------

/** Lifecycle status of a task */
export type TaskStatus =
  | 'open'
  | 'assigned'
  | 'in_progress'
  | 'submitted'
  | 'validated'
  | 'rejected'
  | 'closed';

/** Task row in a paginated list */
export interface TaskSummary {
  task_id: string;
  status: TaskStatus;
  objective: string;
  priority: number;
  result_ref: string | null;
}

/** Paginated task list response */
export interface TaskListResponse {
  tasks: TaskSummary[];
  total: number;
  offset: number;
  limit: number;
}

/** Full task detail */
export interface TaskDetail {
  task_id: string;
  status: TaskStatus;
  objective: string;
  result_ref: string | null;
  required_capabilities: string[];
}

/** Create a new task. Backend expects `priority` as an int (0=low, 1=medium, 2=high). */
export interface TaskCreateRequest {
  objective: string;
  capabilities?: string[];
  priority?: number;
  created_by?: string;
}

/** Common response for task actions */
export interface TaskActionResponse {
  task_id: string;
  event_type: string;
  result_ref?: string;
}

/** Create-task response (returns `status`, not `event_type`) */
export interface TaskCreateResponse {
  task_id: string;
  status: TaskStatus;
}

/** Claim a task */
export interface TaskClaimRequest {
  agent_did: string;
}

/** Submit a task result */
export interface TaskSubmitRequest {
  agent_did: string;
  result_ref: string;
  summary?: string;
  confidence?: number;
}

/** Validate a submitted task */
export interface TaskValidateRequest {
  validator_did: string;
  accepted: boolean;
  confidence?: number;
  critique?: string;
}

/** Outcome of closing a task */
export type TaskCloseOutcome = 'accepted' | 'rejected' | 'cancelled';

/** Close a task */
export interface TaskCloseRequest {
  actor: string;
  outcome: TaskCloseOutcome;
  reason?: string;
}

// ---------------------------------------------------------------------------
// Runtime / Trust (M3 / M4)
// ---------------------------------------------------------------------------

/** Per-agent runtime state */
export interface RuntimeAgentState {
  role: AgentRole;
  running: boolean;
  tasks_done: number;
}

/** Runtime status response */
export interface RuntimeStatusResponse {
  pending: number;
  queue_depth: number;
  agents: Record<string, RuntimeAgentState>;
}

/** Trust diversity toggle response */
export interface TrustDiversityResponse {
  diversity_enabled: boolean;
}

/** Checkpoint approval response */
export interface CheckpointApproveResponse {
  task_id: string;
  approved: boolean;
}
