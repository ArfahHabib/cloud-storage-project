// frontend/src/components/Navbar.js
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../utils/AuthContext';

const styles = {
  nav: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '0 32px', height: '60px',
    background: 'var(--bg-card)',
    borderBottom: '1px solid var(--border)',
    position: 'sticky', top: 0, zIndex: 100,
  },
  logo: {
    fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700,
    color: 'var(--accent)', textDecoration: 'none', letterSpacing: '-0.5px',
  },
  links: { display: 'flex', alignItems: 'center', gap: '8px' },
  link: (active) => ({
    padding: '6px 14px', borderRadius: '6px', fontSize: '14px', fontWeight: 500,
    color: active ? 'var(--accent)' : 'var(--text-secondary)',
    background: active ? 'var(--accent-dim)' : 'transparent',
    textDecoration: 'none', transition: 'all 0.2s',
  }),
  user: {
    display: 'flex', alignItems: 'center', gap: '12px',
    fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-secondary)',
  },
  logout: {
    padding: '5px 12px', borderRadius: '6px', fontSize: '13px',
    background: 'transparent', border: '1px solid var(--border)',
    color: 'var(--text-secondary)', cursor: 'pointer', transition: 'all 0.2s',
  },
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();

  return (
    <nav style={styles.nav}>
      <Link to="/" style={styles.logo}>⬡ SecureVault</Link>

      <div style={styles.links}>
        <Link to="/"       style={styles.link(pathname === '/')}>Files</Link>
        <Link to="/health" style={styles.link(pathname === '/health')}>Health</Link>
      </div>

      <div style={styles.user}>
        <span>{user?.username}</span>
        <button
          style={styles.logout}
          onClick={logout}
          onMouseEnter={e => { e.target.style.borderColor='var(--danger)'; e.target.style.color='var(--danger)'; }}
          onMouseLeave={e => { e.target.style.borderColor='var(--border)'; e.target.style.color='var(--text-secondary)'; }}
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
