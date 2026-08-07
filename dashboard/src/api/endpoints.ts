import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import {
  PaginatedListResponse,
  StatusResponse,
  HistoryResponse,
  VerifyResponse,
  ModeResponse,
  RegisterRequest,
  RegisterResponse,
  TransitionRequest,
  TransitionResponse,
  ForkRequest,
  ForkResponse,
  AgentListResponse,
  AgentResponse,
  AgentHistoryResponse,
  AgentReputationResponse,
  AgentRegisterRequest,
  AgentAttestRequest,
  AgentValidateRequest,
  AgentDeprecateRequest,
  AdminPublicKeyRequest,
  AdminPublicKeyResponse,
  TaskListResponse,
  TaskStatus,
  TaskDetail,
  TaskCreateRequest,
  TaskCreateResponse,
  TaskActionResponse,
  TaskClaimRequest,
  TaskSubmitRequest,
  TaskValidateRequest,
  TaskCloseRequest,
  RuntimeStatusResponse,
  TrustDiversityResponse,
  CheckpointApproveResponse,
  LoginRequest,
  LoginResponse,
  TaskTransitionsResponse,
  RolesResponse,
} from '@/api/types';
import { POLL_INTERVAL } from '@/utils/constants';
import { useAuthStore } from '@/store/authStore';
import { decodeJwtPayload } from '@/utils/jwt';

// ---------------------------------------------------------------------------
// Auth (AUTH_ENABLED deployments)
// ---------------------------------------------------------------------------

/**
 * Exchange an API-key credential for a signed JWT (`POST /api/v1/auth/token`).
 *
 * The backend uses the OAuth2 password flow: `password` must be one of the
 * configured API keys. On success the JWT (and decoded user identity) is
 * persisted to the auth store, then all cached queries are invalidated so
 * role-gated data (e.g. admin trust settings) refreshes with the new token.
 */
export function useLogin(): ReturnType<
  typeof useMutation<LoginResponse, unknown, LoginRequest>
> {
  const queryClient = useQueryClient();
  return useMutation<LoginResponse, unknown, LoginRequest>({
    mutationFn: async (data: LoginRequest) => {
      const form = new URLSearchParams();
      form.append('username', data.username);
      form.append('password', data.password);
      const response = await apiClient.post<LoginResponse>(
        '/api/v1/auth/token',
        form,
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        },
      );
      return response.data;
    },
    onSuccess: (data: LoginResponse) => {
      const payload = decodeJwtPayload(data.access_token);
      useAuthStore.getState().login(data.access_token, {
        identity: payload?.sub ?? 'user',
        role: payload?.role ?? 'user',
      });
      queryClient.invalidateQueries();
    },
  });
}

/**
 * Probe whether auth is enabled on the backend.
 *
 * `POST /api/v1/auth/token` returns 400 when `auth_enabled=False` and 401
 * when auth is enabled but the credential is invalid. We send a deliberately
 * invalid credential and interpret the status code.
 */
export async function probeAuthStatus(): Promise<'enabled' | 'disabled' | 'unknown'> {
  try {
    await apiClient.post(
      '/api/v1/auth/token',
      new URLSearchParams({ username: '__probe__', password: '__probe__' }),
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      },
    );
    return 'enabled';
  } catch (error) {
    const status = (error as { status_code?: number }).status_code;
    if (status === 400) {
      return 'disabled';
    }
    if (status === 401) {
      return 'enabled';
    }
    return 'unknown';
  }
}

// ---------------------------------------------------------------------------
// Meta (state-machine single source of truth)
// ---------------------------------------------------------------------------

/** Fetch the legal task-transition map from the backend state machine. */
export function useTaskTransitions(): ReturnType<
  typeof useQuery<TaskTransitionsResponse>
> {
  return useQuery<TaskTransitionsResponse>({
    queryKey: ['meta', 'task-transitions'],
    queryFn: async () => {
      const response = await apiClient.get<TaskTransitionsResponse>(
        '/api/v1/meta/task-transitions',
      );
      return response.data;
    },
    staleTime: 5 * 60_000,
    retry: 1,
  });
}

/** Fetch the role registry (allowed tools, validation policy, prompts). */
export function useRoles(
  enabled: boolean = true,
): ReturnType<typeof useQuery<RolesResponse>> {
  return useQuery<RolesResponse>({
    queryKey: ['meta', 'roles'],
    queryFn: async () => {
      const response = await apiClient.get<RolesResponse>('/api/v1/meta/roles');
      return response.data;
    },
    staleTime: 5 * 60_000,
    retry: 1,
    enabled,
  });
}

/** Fetch paginated list of capability IDs */
export function useCapabilities(
  offset: number = 0,
  limit: number = 20,
): ReturnType<typeof useQuery<PaginatedListResponse>> {
  return useQuery<PaginatedListResponse>({
    queryKey: ['capabilities', { offset, limit }],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedListResponse>(
        '/api/v1/consensus/list',
        { params: { offset, limit } },
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
  });
}

/** Fetch status of a single capability */
export function useStatus(
  adlId: string,
): ReturnType<typeof useQuery<StatusResponse>> {
  return useQuery<StatusResponse>({
    queryKey: ['status', adlId],
    queryFn: async () => {
      const response = await apiClient.get<StatusResponse>(
        `/api/v1/consensus/status/${adlId}`,
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
    enabled: !!adlId,
  });
}

/** Fetch history of events for a capability */
export function useHistory(
  adlId: string,
): ReturnType<typeof useQuery<HistoryResponse>> {
  return useQuery<HistoryResponse>({
    queryKey: ['history', adlId],
    queryFn: async () => {
      const response = await apiClient.get<HistoryResponse>(
        `/api/v1/consensus/history/${adlId}`,
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
    enabled: !!adlId,
  });
}

/** Verify chain integrity */
export function useVerify(
  adlId: string,
): ReturnType<typeof useQuery<VerifyResponse>> {
  return useQuery<VerifyResponse>({
    queryKey: ['verify', adlId],
    queryFn: async () => {
      const response = await apiClient.get<VerifyResponse>(
        `/api/v1/consensus/verify/${adlId}`,
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
    enabled: !!adlId,
  });
}

/** Fetch current system mode */
export function useMode(): ReturnType<typeof useQuery<ModeResponse>> {
  return useQuery<ModeResponse>({
    queryKey: ['mode'],
    queryFn: async () => {
      const response = await apiClient.get<ModeResponse>(
        '/api/v1/consensus/mode',
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
  });
}

/** Register a new capability */
export function useRegister(): ReturnType<typeof useMutation<RegisterResponse, unknown, RegisterRequest>> {
  const queryClient = useQueryClient();
  return useMutation<RegisterResponse, unknown, RegisterRequest>({
    mutationFn: async (data: RegisterRequest) => {
      const response = await apiClient.post<RegisterResponse>(
        '/api/v1/consensus/register',
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['capabilities'] });
    },
  });
}

/** Transition capability status */
export function useTransition(
  adlId: string,
): ReturnType<typeof useMutation<TransitionResponse, unknown, TransitionRequest>> {
  const queryClient = useQueryClient();
  return useMutation<TransitionResponse, unknown, TransitionRequest>({
    mutationFn: async (data: TransitionRequest) => {
      const response = await apiClient.post<TransitionResponse>(
        '/api/v1/consensus/transition',
        {
          adl_id: adlId,
          to_status: data.to_status,
          actor: data.actor,
          reason: data.reason,
          payload: data.payload || {},
        },
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['status', adlId] });
      queryClient.invalidateQueries({ queryKey: ['history', adlId] });
      queryClient.invalidateQueries({ queryKey: ['capabilities'] });
    },
  });
}

/** Fork a capability */
export function useFork(
  adlId: string,
): ReturnType<typeof useMutation<ForkResponse, unknown, ForkRequest>> {
  const queryClient = useQueryClient();
  return useMutation<ForkResponse, unknown, ForkRequest>({
    mutationFn: async (data: ForkRequest) => {
      const forkId = data.fork_id || `${adlId}-fork-${Date.now()}`;
      const response = await apiClient.post<ForkResponse>(
        '/api/v1/consensus/fork',
        {
          original_id: adlId,
          fork_id: forkId,
          actor: data.actor,
          reason: data.reason,
        },
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['status', adlId] });
      queryClient.invalidateQueries({ queryKey: ['history', adlId] });
      queryClient.invalidateQueries({ queryKey: ['capabilities'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Agents (M1a)
// ---------------------------------------------------------------------------

/** Fetch paginated list of agents */
export function useAgents(
  offset: number = 0,
  limit: number = 20,
  scope?: string,
): ReturnType<typeof useQuery<AgentListResponse>> {
  return useQuery<AgentListResponse>({
    queryKey: ['agents', { offset, limit, scope }],
    queryFn: async () => {
      const response = await apiClient.get<AgentListResponse>(
        '/api/v1/agents',
        { params: { offset, limit, scope } },
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
  });
}

/** Fetch a single agent by DID */
export function useAgent(
  did: string,
): ReturnType<typeof useQuery<AgentResponse>> {
  return useQuery<AgentResponse>({
    queryKey: ['agent', did],
    queryFn: async () => {
      const response = await apiClient.get<AgentResponse>(
        `/api/v1/agents/${did}`,
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
    enabled: !!did,
  });
}

/** Fetch the event history of an agent */
export function useAgentHistory(
  did: string,
): ReturnType<typeof useQuery<AgentHistoryResponse>> {
  return useQuery<AgentHistoryResponse>({
    queryKey: ['agent-history', did],
    queryFn: async () => {
      const response = await apiClient.get<AgentHistoryResponse>(
        `/api/v1/agents/${did}/history`,
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
    enabled: !!did,
  });
}

/** Fetch the reputation metrics of an agent */
export function useAgentReputation(
  did: string,
): ReturnType<typeof useQuery<AgentReputationResponse>> {
  return useQuery<AgentReputationResponse>({
    queryKey: ['agent-reputation', did],
    queryFn: async () => {
      const response = await apiClient.get<AgentReputationResponse>(
        `/api/v1/agents/${did}/reputation`,
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
    enabled: !!did,
  });
}

/** Register a new agent */
export function useAgentRegister(): ReturnType<
  typeof useMutation<AgentResponse, unknown, AgentRegisterRequest>
> {
  const queryClient = useQueryClient();
  return useMutation<AgentResponse, unknown, AgentRegisterRequest>({
    mutationFn: async (data: AgentRegisterRequest) => {
      const response = await apiClient.post<AgentResponse>(
        '/api/v1/agents/register',
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

/** Attest an agent */
export function useAgentAttest(
  did: string,
): ReturnType<typeof useMutation<AgentResponse, unknown, AgentAttestRequest>> {
  const queryClient = useQueryClient();
  return useMutation<AgentResponse, unknown, AgentAttestRequest>({
    mutationFn: async (data: AgentAttestRequest) => {
      const response = await apiClient.post<AgentResponse>(
        `/api/v1/agents/${did}/attest`,
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent', did] });
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

/** Validate an agent as a validator */
export function useAgentValidate(
  did: string,
): ReturnType<typeof useMutation<AgentResponse, unknown, AgentValidateRequest>> {
  const queryClient = useQueryClient();
  return useMutation<AgentResponse, unknown, AgentValidateRequest>({
    mutationFn: async (data: AgentValidateRequest) => {
      const response = await apiClient.post<AgentResponse>(
        `/api/v1/agents/${did}/validate`,
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent', did] });
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      queryClient.invalidateQueries({ queryKey: ['agent-reputation', did] });
    },
  });
}

/** Deprecate an agent */
export function useAgentDeprecate(
  did: string,
): ReturnType<typeof useMutation<AgentResponse, unknown, AgentDeprecateRequest>> {
  const queryClient = useQueryClient();
  return useMutation<AgentResponse, unknown, AgentDeprecateRequest>({
    mutationFn: async (data: AgentDeprecateRequest) => {
      const response = await apiClient.post<AgentResponse>(
        `/api/v1/agents/${did}/deprecate`,
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent', did] });
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      queryClient.invalidateQueries({ queryKey: ['agent-reputation', did] });
    },
  });
}

/** Admin-sign an agent into the trust root (P0-1 bootstrap path). */
export function useAgentAdminValidate(
  did: string,
): ReturnType<typeof useMutation<AgentResponse, unknown, AgentValidateRequest>> {
  const queryClient = useQueryClient();
  return useMutation<AgentResponse, unknown, AgentValidateRequest>({
    mutationFn: async (data: AgentValidateRequest) => {
      const response = await apiClient.post<AgentResponse>(
        `/api/v1/agents/${did}/admin-validate`,
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent', did] });
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      queryClient.invalidateQueries({ queryKey: ['agent-reputation', did] });
    },
  });
}

/** Register an admin DID public key (P0-3 API-key ↔ DID-signature binding). */
export function useAdminPublicKey(): ReturnType<
  typeof useMutation<AdminPublicKeyResponse, unknown, AdminPublicKeyRequest>
> {
  return useMutation<AdminPublicKeyResponse, unknown, AdminPublicKeyRequest>({
    mutationFn: async (data: AdminPublicKeyRequest) => {
      const response = await apiClient.post<AdminPublicKeyResponse>(
        '/api/v1/admin/public-key',
        data,
      );
      return response.data;
    },
  });
}

// ---------------------------------------------------------------------------
// Tasks (M2)
// ---------------------------------------------------------------------------

/** Fetch paginated list of tasks, optionally filtered by status */
export function useTasks(
  status: TaskStatus | 'all' = 'all',
  offset: number = 0,
  limit: number = 20,
): ReturnType<typeof useQuery<TaskListResponse>> {
  return useQuery<TaskListResponse>({
    queryKey: ['tasks', { status, offset, limit }],
    queryFn: async () => {
      const response = await apiClient.get<TaskListResponse>('/api/v1/tasks', {
        params: {
          status: status === 'all' ? undefined : status,
          offset,
          limit,
        },
      });
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
  });
}

/** Fetch a single task by ID */
export function useTask(
  taskId: string,
): ReturnType<typeof useQuery<TaskDetail>> {
  return useQuery<TaskDetail>({
    queryKey: ['task', taskId],
    queryFn: async () => {
      const response = await apiClient.get<TaskDetail>(
        `/api/v1/tasks/${taskId}`,
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
    enabled: !!taskId,
  });
}

/** Create a new task */
export function useTaskCreate(): ReturnType<
  typeof useMutation<TaskCreateResponse, unknown, TaskCreateRequest>
> {
  const queryClient = useQueryClient();
  return useMutation<TaskCreateResponse, unknown, TaskCreateRequest>({
    mutationFn: async (data: TaskCreateRequest) => {
      const response = await apiClient.post<TaskCreateResponse>(
        '/api/v1/tasks/create',
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

/** Claim a task */
export function useTaskClaim(
  taskId: string,
): ReturnType<typeof useMutation<TaskActionResponse, unknown, TaskClaimRequest>> {
  const queryClient = useQueryClient();
  return useMutation<TaskActionResponse, unknown, TaskClaimRequest>({
    mutationFn: async (data: TaskClaimRequest) => {
      const response = await apiClient.post<TaskActionResponse>(
        `/api/v1/tasks/${taskId}/claim`,
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['runtime-status'] });
    },
  });
}

/** Submit a task result */
export function useTaskSubmit(
  taskId: string,
): ReturnType<typeof useMutation<TaskActionResponse, unknown, TaskSubmitRequest>> {
  const queryClient = useQueryClient();
  return useMutation<TaskActionResponse, unknown, TaskSubmitRequest>({
    mutationFn: async (data: TaskSubmitRequest) => {
      const response = await apiClient.post<TaskActionResponse>(
        `/api/v1/tasks/${taskId}/submit`,
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
    },
  });
}

/** Validate a submitted task */
export function useTaskValidate(
  taskId: string,
): ReturnType<typeof useMutation<TaskActionResponse, unknown, TaskValidateRequest>> {
  const queryClient = useQueryClient();
  return useMutation<TaskActionResponse, unknown, TaskValidateRequest>({
    mutationFn: async (data: TaskValidateRequest) => {
      const response = await apiClient.post<TaskActionResponse>(
        `/api/v1/tasks/${taskId}/validate`,
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
    },
  });
}

/** Close a task */
export function useTaskClose(
  taskId: string,
): ReturnType<typeof useMutation<TaskActionResponse, unknown, TaskCloseRequest>> {
  const queryClient = useQueryClient();
  return useMutation<TaskActionResponse, unknown, TaskCloseRequest>({
    mutationFn: async (data: TaskCloseRequest) => {
      const response = await apiClient.post<TaskActionResponse>(
        `/api/v1/tasks/${taskId}/close`,
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
    },
  });
}

// ---------------------------------------------------------------------------
// Runtime / Trust (M3 / M4)
// ---------------------------------------------------------------------------

/** Fetch runtime status (pending backlog, queue depth, agent states) */
export function useRuntimeStatus(): ReturnType<
  typeof useQuery<RuntimeStatusResponse>
> {
  return useQuery<RuntimeStatusResponse>({
    queryKey: ['runtime-status'],
    queryFn: async () => {
      const response = await apiClient.get<RuntimeStatusResponse>(
        '/api/v1/runtime/status',
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
  });
}

/** Fetch the trust diversity toggle state (admin) */
export function useTrustDiversity(): ReturnType<
  typeof useQuery<TrustDiversityResponse>
> {
  return useQuery<TrustDiversityResponse>({
    queryKey: ['trust-diversity'],
    queryFn: async () => {
      const response = await apiClient.get<TrustDiversityResponse>(
        '/api/v1/admin/trust/diversity',
      );
      return response.data;
    },
    refetchInterval: POLL_INTERVAL,
  });
}

/** Toggle the trust diversity setting (admin). Mutates with `enabled: boolean`. */
export function useToggleTrustDiversity(): ReturnType<
  typeof useMutation<TrustDiversityResponse, unknown, boolean>
> {
  const queryClient = useQueryClient();
  return useMutation<TrustDiversityResponse, unknown, boolean>({
    mutationFn: async (enabled: boolean) => {
      const response = await apiClient.post<TrustDiversityResponse>(
        '/api/v1/admin/trust/diversity',
        null,
        { params: { enabled: enabled ? 'true' : 'false' } },
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trust-diversity'] });
    },
  });
}

/** Approve a task checkpoint (admin) */
export function useApproveCheckpoint(
  taskId: string,
): ReturnType<typeof useMutation<CheckpointApproveResponse, unknown, void>> {
  const queryClient = useQueryClient();
  return useMutation<CheckpointApproveResponse, unknown, void>({
    mutationFn: async () => {
      const response = await apiClient.post<CheckpointApproveResponse>(
        `/api/v1/checkpoints/${taskId}/approve`,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
    },
  });
}
