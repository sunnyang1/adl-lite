import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
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
    const message: string =
      error.response?.data?.detail ??
      error.message ??
      'An unexpected error occurred';
    const status: number = error.response?.status ?? 500;
    const errorResponse: ErrorResponse = {
      detail: message,
      status_code: status,
    };
    return Promise.reject(errorResponse);
  },
);

export default apiClient;
