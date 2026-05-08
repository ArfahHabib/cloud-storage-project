// frontend/src/utils/AuthContext.js
// Provides login/logout state to every component in the app.
// Uses Cognito via AWS Amplify when configured,
// OR a simple dev-mode login when Cognito is not set up yet.

import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

const POOL_ID   = process.env.REACT_APP_COGNITO_USER_POOL_ID   || '';
const CLIENT_ID = process.env.REACT_APP_COGNITO_CLIENT_ID       || '';
const IS_DEV    = !POOL_ID || POOL_ID === 'us-east-1_xxxxxxxxx';

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  // On app load, restore session from localStorage
  useEffect(() => {
    const token    = localStorage.getItem('auth_token');
    const username = localStorage.getItem('auth_username');
    if (token && username) {
      setUser({ username, token });
    }
    setLoading(false);
  }, []);

  // ── DEV MODE LOGIN (no real Cognito) ──────────────────────
  const devLogin = (username, password) => {
    if (!username || !password) {
      setError('Please enter a username and password.');
      return false;
    }
    const token = `dev-${username}`;
    localStorage.setItem('auth_token',    token);
    localStorage.setItem('auth_username', username);
    setUser({ username, token });
    setError('');
    return true;
  };

  // ── COGNITO LOGIN ──────────────────────────────────────────
  const cognitoLogin = async (username, password) => {
    try {
      // Dynamic import — only load Amplify if Cognito is configured
      const { Amplify } = await import('aws-amplify');
      const { signIn }  = await import('aws-amplify/auth');

      Amplify.configure({
        Auth: {
          Cognito: {
            userPoolId:       POOL_ID,
            userPoolClientId: CLIENT_ID,
          }
        }
      });

      const result = await signIn({ username, password });
      if (result.isSignedIn) {
        const { fetchAuthSession } = await import('aws-amplify/auth');
        const session = await fetchAuthSession();
        const token   = session.tokens?.idToken?.toString();

        localStorage.setItem('auth_token',    token);
        localStorage.setItem('auth_username', username);
        setUser({ username, token });
        setError('');
        return true;
      }
    } catch (err) {
      setError(err.message || 'Login failed');
      return false;
    }
  };

  const login = async (username, password) => {
    setError('');
    if (IS_DEV) {
      return devLogin(username, password);
    }
    return cognitoLogin(username, password);
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_username');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, error, setError, IS_DEV }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
