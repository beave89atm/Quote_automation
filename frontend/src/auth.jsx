import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

const AuthContext = createContext(null);
export const TOKEN_KEY = "kannon_quote_token";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [ready, setReady] = useState(false);

  const value = useMemo(
    () => ({
      token,
      ready,
      setSession(next) {
        setToken(next);
        if (next) localStorage.setItem(TOKEN_KEY, next);
        else localStorage.removeItem(TOKEN_KEY);
      },
      logout() {
        setToken("");
        localStorage.removeItem(TOKEN_KEY);
      },
    }),
    [token, ready]
  );

  useEffect(() => {
    let alive = true;
    (async () => {
      const existing = localStorage.getItem(TOKEN_KEY);
      if (!existing) {
        if (alive) setReady(true);
        return;
      }
      try {
        const res = await fetch("/api/rates", {
          headers: { "X-App-Token": existing },
        });
        if (!res.ok) {
          localStorage.removeItem(TOKEN_KEY);
          if (alive) setToken("");
        }
      } catch {
        localStorage.removeItem(TOKEN_KEY);
        if (alive) setToken("");
      } finally {
        if (alive) setReady(true);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  if (!ready) {
    return (
      <div className="login-wrap">
        <p className="muted">Checking session…</p>
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
