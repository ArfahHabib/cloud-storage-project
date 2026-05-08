// frontend/src/pages/HealthPage.js
import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import { getHealth } from '../utils/api';

function StatusDot({ ok }) {
  return (
    <span style={{
      display: 'inline-block', width:'10px', height:'10px', borderRadius:'50%',
      background: ok ? 'var(--success)' : 'var(--danger)',
      boxShadow: ok ? '0 0 8px var(--success)' : '0 0 8px var(--danger)',
      animation: ok ? 'pulse 2s ease infinite' : 'none',
    }} />
  );
}

function BucketCard({ name, info }) {
  const ok = info?.available;
  const card = {
    padding: '24px', background: 'var(--bg-card)',
    border: `1px solid ${ok ? 'rgba(0,214,143,0.3)' : 'rgba(255,71,87,0.3)'}`,
    borderRadius: 'var(--radius)',
    transition: 'all 0.3s',
  };
  const row = { display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'8px' };

  return (
    <div style={card}>
      <div style={row}>
        <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
          <StatusDot ok={ok} />
          <span style={{ fontFamily:'var(--font-mono)', fontSize:'14px', fontWeight:700, color:'var(--text-primary)' }}>
            {name.toUpperCase()} REGION
          </span>
        </div>
        <span style={{
          padding:'3px 10px', borderRadius:'12px', fontSize:'12px', fontFamily:'var(--font-mono)',
          background: ok ? 'rgba(0,214,143,0.1)' : 'rgba(255,71,87,0.1)',
          color: ok ? 'var(--success)' : 'var(--danger)',
          border: `1px solid ${ok ? 'var(--success)' : 'var(--danger)'}`,
        }}>
          {ok ? 'HEALTHY' : 'DOWN'}
        </span>
      </div>

      <div style={{ borderTop:'1px solid var(--border)', paddingTop:'12px', marginTop:'4px' }}>
        {[
          ['Bucket',  info?.bucket  || '—'],
          ['Region',  info?.region  || '—'],
          ['Status',  info?.status  || '—'],
        ].map(([label, val]) => (
          <div key={label} style={{ display:'flex', justifyContent:'space-between', marginBottom:'6px' }}>
            <span style={{ fontSize:'12px', color:'var(--text-muted)' }}>{label}</span>
            <span style={{ fontSize:'12px', fontFamily:'var(--font-mono)', color:'var(--text-secondary)' }}>{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function HealthPage() {
  const [health,   setHealth]   = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState('');
  const [lastCheck, setLastCheck] = useState(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getHealth();
      setHealth(data);
      setLastCheck(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const page = { minHeight:'100vh', background:'var(--bg-deep)' };
  const main = { maxWidth:'900px', margin:'0 auto', padding:'32px 24px' };

  const allOk = health?.buckets?.primary?.available && health?.buckets?.secondary?.available;

  return (
    <div style={page}>
      <Navbar />
      <div style={main}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'28px' }}>
          <div>
            <h1 style={{ fontSize:'22px', fontWeight:700, fontFamily:'var(--font-mono)', color:'var(--text-primary)' }}>
              System Health Monitor
            </h1>
            <p style={{ color:'var(--text-muted)', fontSize:'13px', marginTop:'4px' }}>
              Real-time status of your AWS infrastructure
              {lastCheck && ` · Last checked: ${lastCheck}`}
            </p>
          </div>
          <button
            onClick={fetchHealth}
            disabled={loading}
            style={{
              padding:'8px 16px', borderRadius:'var(--radius-sm)', fontSize:'13px',
              fontFamily:'var(--font-mono)', cursor: loading ? 'not-allowed' : 'pointer',
              background:'var(--accent)', border:'none', color:'#fff', opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? '⟳ Checking...' : '⟳ Refresh'}
          </button>
        </div>

        {/* Overall status banner */}
        {!loading && !error && health && (
          <div style={{
            padding: '16px 20px', marginBottom:'24px', borderRadius:'var(--radius)',
            background: allOk ? 'rgba(0,214,143,0.08)' : 'rgba(255,71,87,0.08)',
            border: `1px solid ${allOk ? 'var(--success)' : 'var(--danger)'}`,
            display:'flex', alignItems:'center', gap:'12px',
          }}>
            <span style={{ fontSize:'24px' }}>{allOk ? '✅' : '⚠️'}</span>
            <div>
              <div style={{ fontWeight:600, color: allOk ? 'var(--success)' : 'var(--danger)', fontSize:'15px' }}>
                {allOk ? 'All systems operational' : 'One or more systems are unavailable'}
              </div>
              <div style={{ fontSize:'12px', color:'var(--text-muted)', fontFamily:'var(--font-mono)', marginTop:'2px' }}>
                {allOk ? 'Both AWS regions are healthy. Files can be uploaded and downloaded.' : 'Check your AWS credentials and bucket names in your .env file.'}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div style={{
            padding:'16px', marginBottom:'24px', borderRadius:'var(--radius)',
            background:'rgba(255,71,87,0.08)', border:'1px solid var(--danger)',
            color:'var(--danger)', fontFamily:'var(--font-mono)', fontSize:'13px',
          }}>
            ❌ {error} — Make sure the backend is running: <code>python -m backend.app</code>
          </div>
        )}

        {/* Bucket cards */}
        {loading ? (
          <div style={{ textAlign:'center', padding:'60px', color:'var(--text-muted)', fontFamily:'var(--font-mono)' }}>
            Checking AWS infrastructure...
          </div>
        ) : health?.buckets ? (
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'20px', marginBottom:'32px' }}>
            <BucketCard name="Primary"   info={health.buckets.primary} />
            <BucketCard name="Secondary" info={health.buckets.secondary} />
          </div>
        ) : null}

        {/* Architecture diagram */}
        <div style={{
          padding:'24px', background:'var(--bg-card)', border:'1px solid var(--border)',
          borderRadius:'var(--radius)',
        }}>
          <h2 style={{ fontSize:'14px', fontFamily:'var(--font-mono)', color:'var(--text-secondary)', marginBottom:'20px', textTransform:'uppercase', letterSpacing:'1px' }}>
            System Architecture
          </h2>
          <div style={{ fontFamily:'var(--font-mono)', fontSize:'13px', color:'var(--text-secondary)', lineHeight:'2' }}>
            <div style={{ display:'flex', alignItems:'center', gap:'8px', flexWrap:'wrap' }}>
              {[
                { label:'React Frontend', color:'var(--accent)' },
                '→',
                { label:'Flask API (port 5000)', color:'var(--warning)' },
                '→',
                { label:'AES-256-GCM Encrypt', color:'var(--success)' },
                '→',
                { label:'Shard into 4 pieces', color:'var(--success)' },
              ].map((item, i) =>
                typeof item === 'string' ? (
                  <span key={i} style={{ color:'var(--text-muted)' }}>{item}</span>
                ) : (
                  <span key={i} style={{ padding:'4px 10px', borderRadius:'4px', background:'var(--bg-elevated)', color: item.color, border:`1px solid ${item.color}44` }}>
                    {item.label}
                  </span>
                )
              )}
            </div>
            <div style={{ margin:'12px 0 0 0', paddingLeft:'24px', borderLeft:'2px solid var(--border)' }}>
              <div>├── Shards 0, 2 → S3 us-east-1 (Primary)</div>
              <div>└── Shards 1, 3 → S3 eu-west-1 (Secondary)</div>
              <div style={{ marginTop:'8px' }}>Metadata (encrypted DEK, nonce, shard manifest) → DynamoDB</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
