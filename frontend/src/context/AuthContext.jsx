import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setAuthLoading(false));
  }, []);

  const requestSignupOtp = useCallback(async (email, password, name) => {
    return api.requestSignupOtp({ email, password, name });
  }, []);

  const verifySignupOtp = useCallback(async (email, otp) => {
    const u = await api.verifySignupOtp({ email, otp });
    setUser(u);
    return u;
  }, []);

  const login = useCallback(async (email, password) => {
    const u = await api.login({ email, password });
    setUser(u);
    return u;
  }, []);

  const loginWithGoogle = useCallback(async (credential) => {
    const u = await api.loginWithGoogle(credential);
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, authLoading, requestSignupOtp, verifySignupOtp, login, loginWithGoogle, logout }}
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
