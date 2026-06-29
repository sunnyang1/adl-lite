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
} from '@/api/types';
import { POLL_INTERVAL } from '@/utils/constants';

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
