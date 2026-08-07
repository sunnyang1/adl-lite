import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/store/authStore';

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach the persisted JWT (if any) to every outgoing request.
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.set('Authorization', `Bearer ${token}`);
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  },
);

export interface ErrorResponse {
  detail: string;
  status_code: number;
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorResponse>) => {
    const status: number = error.response?.status ?? 500;
    const url: string = error.config?.url ?? '';

    // A 401 on any non-login call means the stored token is stale/revoked.
    // Clear it so subsequent calls stop sending an invalid credential.
    // The auth/token endpoint itself returns 401 for bad credentials — that
    // must NOT wipe an existing session.
    const isAuthTokenRequest = url.includes('/auth/token');
    if (status === 401 && !isAuthTokenRequest) {
      const { token, logout } = useAuthStore.getState();
      if (token) {
        logout();
      }
    }

    const message: string =
      error.response?.data?.detail ??
      error.message ??
      'An unexpected error occurred';
    const errorResponse: ErrorResponse = {
      detail: message,
      status_code: status,
    };
    return Promise.reject(errorResponse);
  },
);

export default apiClient;
