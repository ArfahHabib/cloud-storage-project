// frontend/src/utils/AuthContext.js
// Provides login/logout/signup state to every component in the app.
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

  // ── DEV MODE LOGIN ─────────────────────────────────────────
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

  // ── DEV MODE SIGNUP ────────────────────────────────────────
  const devSignup = (username, password) => {
    if (!username || !password) {
      setError('Please fill in all fields.');
      return { success: false };
    }
    const token = `dev-${username}`;
    localStorage.setItem('auth_token',    token);
    localStorage.setItem('auth_username', username);
    setUser({ username, token });
    setError('');
    return { success: true };
  };

  // ── COGNITO LOGIN ──────────────────────────────────────────
  const cognitoLogin = async (username, password) => {
    try {
      const { Amplify } = await import('aws-amplify');
      const { signIn, signOut } = await import('aws-amplify/auth');

      Amplify.configure({
        Auth: { Cognito: { userPoolId: POOL_ID, userPoolClientId: CLIENT_ID } }
      });

      // Always clear any stale Amplify session first.
      // Without this, Amplify throws "There is already a signed in user"
      // if a previous session wasn't cleanly terminated (e.g. tab closed,
      // token expired, or logout only cleared localStorage).
      try { await signOut(); } catch (_) { /* no active session — that's fine */ }

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

  // ── COGNITO SIGNUP ─────────────────────────────────────────
  const cognitoSignup = async (username, password, email) => {
    try {
      const { Amplify } = await import('aws-amplify');
      const { signUp }  = await import('aws-amplify/auth');

      Amplify.configure({
        Auth: { Cognito: { userPoolId: POOL_ID, userPoolClientId: CLIENT_ID } }
      });

      await signUp({
        username,
        password,
        options: { userAttributes: { email } },
      });

      setError('');
      return { success: true, needsConfirmation: true };
    } catch (err) {
      setError(err.message || 'Signup failed');
      return { success: false };
    }
  };

  // ── COGNITO CONFIRM SIGNUP (verify email code) ─────────────
  const confirmSignup = async (username, code) => {
    try {
      const { confirmSignUp } = await import('aws-amplify/auth');
      await confirmSignUp({ username, confirmationCode: code });
      setError('');
      return { success: true };
    } catch (err) {
      setError(err.message || 'Confirmation failed');
      return { success: false };
    }
  };

  const login = async (username, password) => {
    setError('');
    if (IS_DEV) return devLogin(username, password);
    return cognitoLogin(username, password);
  };

  const signup = async (username, password, email) => {
    setError('');
    if (IS_DEV) return devSignup(username, password);
    return cognitoSignup(username, password, email);
  };

  // ── LOGOUT ─────────────────────────────────────────────────
  const logout = async () => {
    // Clear our own state first
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_username');
    setUser(null);

    // Also tell Amplify to sign out so its internal session is fully cleared.
    // Without this, the next login attempt hits "There is already a signed in user".
    if (!IS_DEV) {
      try {
        const { signOut } = await import('aws-amplify/auth');
        await signOut();
      } catch (_) { /* already signed out — ignore */ }
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, signup, confirmSignup, loading, error, setError, IS_DEV }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}