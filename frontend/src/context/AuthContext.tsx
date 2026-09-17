import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import axios from 'axios';
import type { UserResponse } from '../types';

interface AuthContextType {
  user: UserResponse | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, role: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = import.meta.env.VITE_API_URL ?? '';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('pharmaflow_token'));

  // Configure axios default auth header
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('pharmaflow_token', token);
      // Fetch me
      axios
        .get(`${API_BASE}/api/auth/me`)
        .then((res) => setUser(res.data))
        .catch(() => {
          // Token invalid or expired
          logout();
        });
    } else {
      delete axios.defaults.headers.common['Authorization'];
      localStorage.removeItem('pharmaflow_token');
      setUser(null);
    }
  }, [token]);

  const login = async (username: string, password: string) => {
    const res = await axios.post(`${API_BASE}/api/auth/login`, { username, password });
    setToken(res.data.access_token);
    setUser(res.data.user);
  };

  const register = async (username: string, email: string, password: string, role: string) => {
    const res = await axios.post(`${API_BASE}/api/auth/register`, { username, email, password, role });
    setToken(res.data.access_token);
    setUser(res.data.user);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('pharmaflow_token');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        register,
        logout,
        isAuthenticated: !!user,
        isAdmin: user?.role === 'ADMIN',
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
