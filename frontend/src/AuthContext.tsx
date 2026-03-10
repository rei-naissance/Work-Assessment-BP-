import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api, { setAccessToken } from './api';

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  isAdmin: boolean;
  email: string;
  login: (accessToken: string) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

function decodeToken(token: string): { email: string; is_admin: boolean; exp?: number } {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return { email: payload.email || '', is_admin: payload.is_admin || false, exp: payload.exp };
  } catch {
    return { email: '', is_admin: false };
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [email, setEmail] = useState('');

  const login = useCallback((accessToken: string) => {
    setAccessToken(accessToken);
    const { email: e, is_admin } = decodeToken(accessToken);
    setEmail(e);
    setIsAdmin(is_admin);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch { /* ignore */ }
    setAccessToken(null);
    setIsAuthenticated(false);
    setIsAdmin(false);
    setEmail('');
  }, []);

  // Restore session on mount via refresh token cookie
  useEffect(() => {
    api.post('/auth/refresh')
      .then((res) => {
        login(res.data.access_token);
      })
      .catch(() => {
        setAccessToken(null);
        setIsAuthenticated(false);
        setIsAdmin(false);
        setEmail('');
      })
      .finally(() => setIsLoading(false));
  }, [login]);

  // Listen for 401 events from the API interceptor
  useEffect(() => {
    const handleUnauthorized = () => {
      setAccessToken(null);
      setIsAuthenticated(false);
      setIsAdmin(false);
      setEmail('');
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, isAdmin, email, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
