"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, errorMessage, setCsrfToken, type User } from "./api";

type AuthState =
  | { status: "loading"; user: null }
  | { status: "signed_out"; user: null }
  | { status: "signed_in"; user: User };

type AuthContextValue = AuthState & {
  login: (email: string, password: string) => Promise<{ ok: true; user: User } | { ok: false; message: string }>;
  /** Ends the session. Resolves false if the server couldn't, so the UI never
   * shows a signed-out state while the session is still live. */
  logout: () => Promise<boolean>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading", user: null });

  useEffect(() => {
    let cancelled = false;
    api.GET("/api/auth/me").then(({ data }) => {
      if (cancelled) return;
      if (data) {
        setCsrfToken(data.csrf_token);
        setState({ status: "signed_in", user: data.user });
      } else {
        setCsrfToken(null);
        setState({ status: "signed_out", user: null });
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data, error, response } = await api.POST("/api/auth/login", {
      body: { email, password },
    });
    if (!data) {
      const fallback =
        response.status === 429 ? "Too many attempts. Please wait and try again." : "Sign-in failed.";
      return { ok: false as const, message: errorMessage(error, fallback) };
    }
    setCsrfToken(data.csrf_token);
    setState({ status: "signed_in", user: data.user });
    return { ok: true as const, user: data.user };
  }, []);

  const logout = useCallback(async () => {
    let status: number;
    try {
      status = (await api.POST("/api/auth/logout")).response.status;
    } catch {
      return false;
    }
    // 401 means the session had already ended, which is what we wanted.
    if (status !== 204 && status !== 401) return false;
    setCsrfToken(null);
    setState({ status: "signed_out", user: null });
    return true;
  }, []);

  const value = useMemo(() => ({ ...state, login, logout }), [state, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
