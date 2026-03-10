import axios, { AxiosError } from 'axios';

// Error response structure from backend
export interface ApiError {
  code: string;
  message: string;
  detail?: string;
  status?: number;
  path?: string;
}

// Custom error class for API errors
export class ApiRequestError extends Error {
  public code: string;
  public detail?: string;
  public status: number;

  constructor(error: ApiError, status: number) {
    super(error.message);
    this.name = 'ApiRequestError';
    this.code = error.code;
    this.detail = error.detail;
    this.status = status;
  }
}

// Extract user-friendly error message from API response
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    // Handle standardized error format
    if (data?.message) {
      return data.message;
    }
    // Handle FastAPI default format
    if (data?.detail) {
      if (typeof data.detail === 'string') {
        return data.detail;
      }
      if (data.detail.message) {
        return data.detail.message;
      }
    }
    // Network errors
    if (error.code === 'ECONNABORTED') {
      return 'Request timed out. Please try again.';
    }
    if (!error.response) {
      return 'Unable to connect to server. Please check your internet connection.';
    }
    return 'An unexpected error occurred. Please try again.';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred. Please try again.';
}

const apiBaseUrl = import.meta.env.VITE_API_URL || '/api';

// In-memory token storage — not persisted to localStorage (XSS-safe)
let _accessToken: string | null = null;

export const getAccessToken = (): string | null => _accessToken;

export const setAccessToken = (token: string | null) => {
  _accessToken = token;
};

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000, // 30 second timeout
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err: AxiosError<ApiError | { detail: ApiError | string }>) => {
    // Handle 401 - clear token and notify via event (ProtectedRoute handles redirect)
    if (err.response?.status === 401) {
      _accessToken = null;
      window.dispatchEvent(new Event('auth:unauthorized'));
    }

    // Transform error to our custom error type for easier handling
    const data = err.response?.data;
    if (data && err.response?.status) {
      // Handle standardized format
      if ('code' in data && 'message' in data) {
        return Promise.reject(new ApiRequestError(data as ApiError, err.response.status));
      }
      // Handle FastAPI detail format where detail is our error object
      if ('detail' in data && typeof data.detail === 'object' && data.detail && 'code' in data.detail) {
        return Promise.reject(new ApiRequestError(data.detail as ApiError, err.response.status));
      }
    }

    return Promise.reject(err);
  }
);

export default api;
