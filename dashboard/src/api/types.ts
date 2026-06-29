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
