// frontend/src/pages/LoginPage.js
import React, { useState, useMemo } from 'react';
import { useAuth } from '../utils/AuthContext';

// Password rules — must match Cognito User Pool policy
const RULES = [
  { label: 'At least 8 characters',  test: p => p.length >= 8 },
  { label: 'Uppercase letter (A-Z)', test: p => /[A-Z]/.test(p) },
  { label: 'Lowercase letter (a-z)', test: p => /[a-z]/.test(p) },
  { label: 'Number (0-9)',           test: p => /[0-9]/.test(p) },
  { label: 'Symbol (!@#$…)',         test: p => /[^A-Za-z0-9]/.test(p) },
];

// Possible screens: 'login' | 'signup' | 'confirm'
export default function LoginPage() {
  const { login, signup, confirmSignup, error, setError, IS_DEV } = useAuth();

  const [screen,   setScreen]   = useState('login');
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [confirm,  setConfirm]  = useState('');
  const [code,     setCode]     = useState('');
  const [loading,  setLoading]  = useState(false);
  const [pwFocused, setPwFocused] = useState(false);

  const switchTo = (s) => { setError(''); setScreen(s); };

  // Live rule evaluation
  const ruleResults = useMemo(() => RULES.map(r => ({ ...r, passed: r.test(password) })), [password]);
  const allRulesPassed = ruleResults.every(r => r.passed);

  // ── Submit handlers ────────────────────────────────────────────

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    await login(email, password);
    setLoading(false);
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    if (!allRulesPassed) {
      setError('Password does not meet the requirements below.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    const result = await signup(email, password, email);
    setLoading(false);
    if (result?.success && result?.needsConfirmation) switchTo('confirm');
  };

  const handleConfirm = async (e) => {
    e.preventDefault();
    setLoading(true);
    const result = await confirmSignup(email, code);
    setLoading(false);
    if (result?.success) switchTo('login');
  };

  // ── Shared styles ──────────────────────────────────────────────

  const page = {
    minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'radial-gradient(ellipse at 50% 0%, rgba(45,106,255,0.08) 0%, var(--bg-deep) 60%)',
    padding: '24px',
  };

  const card = {
    width: '100%', maxWidth: '400px',
    background: 'var(--bg-card)', border: '1px solid var(--border)',
    borderRadius: '16px', padding: '40px',
    boxShadow: 'var(--shadow), var(--shadow-glow)',
  };

  const inputStyle = {
    width: '100%', padding: '12px 14px',
    background: 'var(--bg-elevated)', border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
    fontFamily: 'var(--font-body)', fontSize: '14px',
    outline: 'none', transition: 'border 0.2s',
    boxSizing: 'border-box',
  };

  const btnStyle = (disabled) => ({
    width: '100%', padding: '13px',
    background: disabled ? 'var(--text-muted)' : 'var(--accent)',
    border: 'none', borderRadius: 'var(--radius-sm)',
    color: '#fff', fontFamily: 'var(--font-body)', fontSize: '15px',
    fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'background 0.2s', marginTop: '8px',
  });

  const field = (label, type, value, onChange, placeholder, onFocus, onBlur) => (
    <div style={{ marginBottom: '16px' }}>
      <label style={{ display:'block', fontSize:'13px', color:'var(--text-secondary)', marginBottom:'6px', fontWeight:500 }}>
        {label}
      </label>
      <input
        type={type} value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} style={inputStyle} required
        onFocus={e => { e.target.style.borderColor='var(--accent)'; onFocus && onFocus(); }}
        onBlur={e => { e.target.style.borderColor='var(--border)'; onBlur && onBlur(); }}
      />
    </div>
  );

  const switchLink = (label, target) => (
    <p style={{ textAlign:'center', marginTop:'20px', fontSize:'13px', color:'var(--text-muted)' }}>
      {label}{' '}
      <span onClick={() => switchTo(target)} style={{ color:'var(--accent)', cursor:'pointer', fontWeight:500 }}>
        {target === 'login' ? 'Sign in' : 'Create one'}
      </span>
    </p>
  );

  const errorBox = error && (
    <div style={{
      padding:'10px 14px', marginBottom:'16px',
      background:'rgba(255,71,87,0.1)', border:'1px solid var(--danger)',
      borderRadius:'var(--radius-sm)', fontSize:'13px',
      color:'var(--danger)', fontFamily:'var(--font-mono)',
    }}>
      {error}
    </div>
  );

  // Password strength checklist shown while typing
  const passwordChecklist = (pwFocused || password.length > 0) && screen === 'signup' && (
    <div style={{
      marginTop: '-8px', marginBottom: '16px',
      padding: '12px 14px',
      background: 'var(--bg-elevated)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-sm)',
    }}>
      {ruleResults.map(r => (
        <div key={r.label} style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          fontSize: '12px', fontFamily: 'var(--font-mono)',
          color: r.passed ? 'var(--success, #2ecc71)' : 'var(--text-muted)',
          marginBottom: '4px', transition: 'color 0.2s',
        }}>
          <span style={{ fontSize: '10px' }}>{r.passed ? '✓' : '○'}</span>
          {r.label}
        </div>
      ))}
    </div>
  );

  // ── Render ─────────────────────────────────────────────────────

  return (
    <div style={page}>
      <div style={card} className="fade-in">

        {/* Logo */}
        <div style={{ textAlign:'center', marginBottom:'32px' }}>
          <div style={{ fontFamily:'var(--font-mono)', fontSize:'28px', color:'var(--accent)', fontWeight:700, letterSpacing:'-1px' }}>
            ⬡ SecureVault
          </div>
          <div style={{ color:'var(--text-muted)', fontSize:'13px', marginTop:'6px' }}>
            Decentralized Privacy-First Cloud Storage
          </div>
          <div style={{ color:'var(--text-muted)', fontSize:'11px', fontFamily:'var(--font-mono)', marginTop:'2px' }}>
            CS-308 Cloud Computing Project
          </div>
        </div>

        {/* Dev mode badge */}
        {IS_DEV && (
          <div style={{
            padding:'8px 12px', marginBottom:'20px',
            background:'rgba(255,183,3,0.1)', border:'1px solid var(--warning)',
            borderRadius:'var(--radius-sm)', fontSize:'12px', fontFamily:'var(--font-mono)',
            color:'var(--warning)',
          }}>
            ⚠ DEV MODE — Cognito not configured. Enter any email + password.
          </div>
        )}

        {/* ── LOGIN ── */}
        {screen === 'login' && (
          <>
            <form onSubmit={handleLogin}>
              {field('Email', 'email', email, setEmail, 'you@university.edu')}
              <div style={{ marginBottom:'24px' }}>
                <label style={{ display:'block', fontSize:'13px', color:'var(--text-secondary)', marginBottom:'6px', fontWeight:500 }}>
                  Password
                </label>
                <input
                  type="password" value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••" style={inputStyle} required
                  onFocus={e => e.target.style.borderColor='var(--accent)'}
                  onBlur={e => e.target.style.borderColor='var(--border)'}
                />
              </div>
              {errorBox}
              <button type="submit" style={btnStyle(loading)} disabled={loading}>
                {loading ? 'Signing in...' : 'Sign In →'}
              </button>
            </form>
            {switchLink("Don't have an account?", 'signup')}
          </>
        )}

        {/* ── SIGNUP ── */}
        {screen === 'signup' && (
          <>
            <form onSubmit={handleSignup}>
              {field('Email', 'email', email, setEmail, 'you@university.edu')}

              {/* Password field with live checklist */}
              <div style={{ marginBottom: '8px' }}>
                <label style={{ display:'block', fontSize:'13px', color:'var(--text-secondary)', marginBottom:'6px', fontWeight:500 }}>
                  Password
                </label>
                <input
                  type="password" value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••" style={inputStyle} required
                  onFocus={e => { e.target.style.borderColor='var(--accent)'; setPwFocused(true); }}
                  onBlur={e => { e.target.style.borderColor='var(--border)'; setPwFocused(false); }}
                />
              </div>

              {/* Live password rules checklist */}
              {passwordChecklist}

              <div style={{ marginBottom:'24px' }}>
                {field('Confirm Password', 'password', confirm, setConfirm, '••••••••')}
              </div>

              {errorBox}
              <button type="submit" style={btnStyle(loading)} disabled={loading}>
                {loading ? 'Creating account...' : 'Create Account →'}
              </button>
            </form>
            {switchLink('Already have an account?', 'login')}
          </>
        )}

        {/* ── CONFIRM EMAIL ── */}
        {screen === 'confirm' && (
          <>
            <div style={{ textAlign:'center', marginBottom:'20px', fontSize:'14px', color:'var(--text-secondary)' }}>
              A verification code was sent to <strong style={{ color:'var(--text-primary)' }}>{email}</strong>.
              Enter it below to activate your account.
            </div>
            <form onSubmit={handleConfirm}>
              {field('Verification Code', 'text', code, setCode, '123456')}
              {errorBox}
              <button type="submit" style={btnStyle(loading)} disabled={loading}>
                {loading ? 'Verifying...' : 'Verify Email →'}
              </button>
            </form>
            {switchLink('Wrong account?', 'login')}
          </>
        )}

        {/* Security labels */}
        <div style={{ display:'flex', justifyContent:'center', gap:'16px', marginTop:'24px' }}>
          {['AES-256-GCM', 'AWS KMS', 'Multi-Region'].map(tag => (
            <span key={tag} style={{
              fontSize:'11px', fontFamily:'var(--font-mono)', color:'var(--text-muted)',
              padding:'3px 8px', background:'var(--bg-elevated)',
              border:'1px solid var(--border)', borderRadius:'4px',
            }}>
              {tag}
            </span>
          ))}
        </div>

      </div>
    </div>
  );
}