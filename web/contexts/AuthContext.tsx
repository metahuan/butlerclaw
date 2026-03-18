'use client';

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { User } from '@/lib/auth-types';

const STORAGE_KEY = 'openclaw_hub_token';

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const t = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (!t) {
      setToken(null);
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.ok) {
        const data = await res.json();
        setToken(t);
        setUser({
          userId: data._id ?? data.userId,
          username: data.username,
          email: data.email,
          avatar: data.avatar,
          role: data.role ?? 'user',
          membershipLevel: data.membershipLevel ?? 'free',
          membershipExpireAt: data.membershipExpireAt ?? null,
        });
      } else {
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
        setUser(null);
      }
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (t) {
      setToken(t);
      refreshUser();
    } else {
      setLoading(false);
    }
  }, [refreshUser]);

  const login = useCallback((newToken: string, newUser: User) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, newToken);
    }
    setToken(newToken);
    setUser(newUser);
  }, []);

  const logout = useCallback(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY);
    }
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
