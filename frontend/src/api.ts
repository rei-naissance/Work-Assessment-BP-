import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

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

// Singleton in-flight guard — prevents concurrent token expiries from
// each triggering a separate /auth/refresh call (would cause rotation conflicts).
let _refreshPromise: Promise<string | null> | null = null;
// Prevents duplicate auth:unauthorized events when multiple requests fail
// simultaneously after a refresh attempt fails.
let _unauthorizedDispatched = false;

function silentRefresh(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise;
  _unauthorizedDispatched = false;
  _refreshPromise = api
    .post<{ access_token: string }>('/auth/refresh')
    .then((res) => {
      _accessToken = res.data.access_token;
      return res.data.access_token;
    })
    .catch(() => null)
    .finally(() => { _refreshPromise = null; });
  return _refreshPromise;
}

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

// Augment config type so we can stamp retried requests.
interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

api.interceptors.response.use(
  (res) => res,
  async (err: AxiosError<ApiError | { detail: ApiError | string }>) => {
    const config = err.config as RetryConfig | undefined;
    const isRefreshCall = config?.url?.includes('/auth/refresh');

    // On 401, attempt a silent token refresh then replay the original request once.
    // Skip for refresh calls themselves (AuthContext handles those) and already-retried requests.
    if (err.response?.status === 401 && !isRefreshCall && !config?._retry) {
      const newToken = await silentRefresh();
      if (newToken && config) {
        config._retry = true;
        config.headers['Authorization'] = `Bearer ${newToken}`;
        return api.request(config);
      }
      // Refresh failed — clear token and notify so AuthContext can log out.
      // Guard against multiple concurrent callers each dispatching the event.
      _accessToken = null;
      if (!_unauthorizedDispatched) {
        _unauthorizedDispatched = true;
        window.dispatchEvent(new Event('auth:unauthorized'));
      }
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
