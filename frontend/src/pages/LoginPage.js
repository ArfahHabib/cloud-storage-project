// frontend/src/pages/LoginPage.js
import React, { useState } from 'react';
import { useAuth } from '../utils/AuthContext';

export default function LoginPage() {
  const { login, error, IS_DEV } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading,  setLoading]  = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    await login(username, password);
    setLoading(false);
  };

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

  const btnStyle = {
    width: '100%', padding: '13px',
    background: loading ? 'var(--text-muted)' : 'var(--accent)',
    border: 'none', borderRadius: 'var(--radius-sm)',
    color: '#fff', fontFamily: 'var(--font-body)', fontSize: '15px',
    fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
    transition: 'background 0.2s', marginTop: '8px',
  };

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
            ⚠ DEV MODE — Cognito not configured. Enter any username + password.
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom:'16px' }}>
            <label style={{ display:'block', fontSize:'13px', color:'var(--text-secondary)', marginBottom:'6px', fontWeight:500 }}>
              Username / Email
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder={IS_DEV ? 'Enter any username' : 'you@university.edu'}
              style={inputStyle}
              onFocus={e => e.target.style.borderColor='var(--accent)'}
              onBlur={e => e.target.style.borderColor='var(--border)'}
              required
            />
          </div>

          <div style={{ marginBottom:'24px' }}>
            <label style={{ display:'block', fontSize:'13px', color:'var(--text-secondary)', marginBottom:'6px', fontWeight:500 }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={IS_DEV ? 'Enter any password' : '••••••••'}
              style={inputStyle}
              onFocus={e => e.target.style.borderColor='var(--accent)'}
              onBlur={e => e.target.style.borderColor='var(--border)'}
              required
            />
          </div>

          {error && (
            <div style={{
              padding:'10px 14px', marginBottom:'16px',
              background:'rgba(255,71,87,0.1)', border:'1px solid var(--danger)',
              borderRadius:'var(--radius-sm)', fontSize:'13px',
              color:'var(--danger)', fontFamily:'var(--font-mono)',
            }}>
              {error}
            </div>
          )}

          <button type="submit" style={btnStyle} disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In →'}
          </button>
        </form>

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
