"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { AuthUser, AuthLoginRequest, AuthRegisterRequest } from "@/types";
import {
  getCurrentUser,
  loginUser,
  registerUser,
  logoutUser,
  getAuthToken,
  removeAuthToken,
} from "@/lib/api";

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (data: AuthLoginRequest) => Promise<void>;
  register: (data: AuthRegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Refresh user data from API
  const refreshUser = useCallback(async () => {
    const storedToken = getAuthToken();
    if (!storedToken) {
      setUser(null);
      setToken(null);
      setIsLoading(false);
      return;
    }

    setToken(storedToken);
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    } catch {
      // Token invalid or expired
      removeAuthToken();
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Hydrate session on client mount
  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const handleLogin = async (data: AuthLoginRequest) => {
    setIsLoading(true);
    try {
      const response = await loginUser(data);
      setToken(response.access_token);
      setUser(response.user);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (data: AuthRegisterRequest) => {
    setIsLoading(true);
    try {
      const response = await registerUser(data);
      setToken(response.access_token);
      setUser(response.user);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    setIsLoading(true);
    try {
      await logoutUser();
    } finally {
      setUser(null);
      setToken(null);
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user,
        login: handleLogin,
        register: handleRegister,
        logout: handleLogout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
