import { createContext, useContext, useEffect, useState, FC, ReactNode } from "react";
import { useRouter } from "next/router";
import { dashragAPI } from "@/utils/dashrag-api";

export interface User {
  id: number;
  email: string;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AUTH_TOKEN_KEY = "dashrag_auth_token";
const AUTH_EMAIL_KEY = "dashrag_auth_email";

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);

  // Lazy initializers run synchronously on first render, before any child useEffects,
  // ensuring dashragAPI has the token set before children make API calls.
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    const stored = localStorage.getItem(AUTH_TOKEN_KEY);
    if (stored) dashragAPI.setAuthToken(stored);
    return stored;
  });

  const [user, setUser] = useState<User | null>(() => {
    if (typeof window === "undefined") return null;
    const email = localStorage.getItem(AUTH_EMAIL_KEY);
    return email ? { id: 0, email } : null;
  });

  const API_BASE_URL = process.env.NEXT_PUBLIC_DASHRAG_API_URL || "http://localhost:8000";

  useEffect(() => {
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    const body = new URLSearchParams();
    body.append("username", email);
    body.append("password", password);

    const res = await fetch(`${API_BASE_URL}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Login failed");
    }

    const data = await res.json();
    const accessToken: string = data.access_token;

    localStorage.setItem(AUTH_TOKEN_KEY, accessToken);
    localStorage.setItem(AUTH_EMAIL_KEY, email);
    setToken(accessToken);
    setUser({ id: 0, email });
    dashragAPI.setAuthToken(accessToken);
  };

  const register = async (email: string, password: string): Promise<void> => {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Registration failed");
    }

    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_EMAIL_KEY);
    setToken(null);
    setUser(null);
    dashragAPI.setAuthToken(null);
    router.replace("/login");
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
};
