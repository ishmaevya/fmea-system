import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { fetchCurrentUser, loginRequest } from "../api/auth";
import { requestTokenRefresh } from "../api/client";
import {
  AUTH_EXPIRED_EVENT,
  clearTokens,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "../api/session";
import type { Role, User } from "../api/types";
import { AuthContext, type AuthContextValue } from "./AuthContext";

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const handleExpired = () => {
      if (!cancelled) {
        setUser(null);
      }
    };

    window.addEventListener(AUTH_EXPIRED_EVENT, handleExpired);

    const restore = async () => {
      if (!getRefreshToken()) {
        if (!cancelled) {
          setInitializing(false);
        }
        return;
      }

      try {
        await requestTokenRefresh();
        const currentUser = await fetchCurrentUser();
        if (!cancelled) {
          setUser(currentUser);
        }
      } catch {
        clearTokens();
        if (!cancelled) {
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setInitializing(false);
        }
      }
    };

    void restore();

    return () => {
      cancelled = true;
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleExpired);
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await loginRequest({ email, password });
    setAccessToken(data.access);
    setRefreshToken(data.refresh);
    setUser(data.user);
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const hasRole = useCallback(
    (...roles: Role[]) => Boolean(user && roles.includes(user.role)),
    [user],
  );

  const value = useMemo<AuthContextValue>(
    () => ({ user, initializing, login, logout, hasRole }),
    [user, initializing, login, logout, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
