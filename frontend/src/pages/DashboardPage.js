// frontend/src/pages/DashboardPage.js
import React, { useState, useEffect, useCallback } from 'react';
import Navbar      from '../components/Navbar';
import UploadZone  from '../components/UploadZone';
import FileList    from '../components/FileList';
import { listFiles, formatBytes } from '../utils/api';
import { useAuth } from '../utils/AuthContext';

export default function DashboardPage() {
  const { user }              = useAuth();
  const [files,    setFiles]  = useState([]);
  const [loading,  setLoading] = useState(true);
  const [fetchErr, setFetchErr] = useState('');

  const loadFiles = useCallback(async () => {
    setLoading(true);
    setFetchErr('');
    try {
      const data = await listFiles();
      // Sort newest first
      const sorted = (data.files || []).sort((a, b) =>
        new Date(b.uploadedAt) - new Date(a.uploadedAt)
      );
      setFiles(sorted);
    } catch (err) {
      setFetchErr(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadFiles(); }, [loadFiles]);

  const handleUploaded = (result) => {
    // Reload the file list after a new upload
    loadFiles();
  };

  const handleDeleted = (fileId) => {
    setFiles(prev => prev.filter(f => f.fileId !== fileId));
  };

  // Stats
  const totalSize   = files.reduce((sum, f) => sum + (f.fileSize || 0), 0);
  const totalShards = files.reduce((sum, f) => sum + (f.totalShards || 0), 0);

  const page  = { minHeight:'100vh', background:'var(--bg-deep)' };
  const main  = { maxWidth:'1100px', margin:'0 auto', padding:'32px 24px' };
  const stats = { display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:'16px', marginBottom:'32px' };

  const stat = (label, value, sub) => (
    <div key={label} style={{
      padding:'20px 24px', background:'var(--bg-card)',
      border:'1px solid var(--border)', borderRadius:'var(--radius)',
    }}>
      <div style={{ fontSize:'24px', fontWeight:700, fontFamily:'var(--font-mono)', color:'var(--accent)' }}>
        {value}
      </div>
      <div style={{ fontSize:'13px', color:'var(--text-secondary)', marginTop:'4px' }}>{label}</div>
      {sub && <div style={{ fontSize:'11px', color:'var(--text-muted)', fontFamily:'var(--font-mono)', marginTop:'2px' }}>{sub}</div>}
    </div>
  );

  return (
    <div style={page}>
      <Navbar />
      <div style={main}>
        {/* Header */}
        <div style={{ marginBottom:'28px' }}>
          <h1 style={{ fontSize:'22px', fontWeight:700, fontFamily:'var(--font-mono)', color:'var(--text-primary)' }}>
            Welcome back, {user?.username}
          </h1>
          <p style={{ color:'var(--text-muted)', fontSize:'13px', marginTop:'4px' }}>
            Your files are encrypted with AES-256-GCM and distributed across 2 AWS regions.
          </p>
        </div>

        {/* Stats */}
        <div style={stats}>
          {stat('Total Files',   files.length, 'in your vault')}
          {stat('Storage Used',  formatBytes(totalSize), 'across both regions')}
          {stat('Total Shards',  totalShards, 'distributed in S3')}
        </div>

        {/* Upload */}
        <div style={{
          background:'var(--bg-card)', border:'1px solid var(--border)',
          borderRadius:'var(--radius)', padding:'24px', marginBottom:'24px',
        }}>
          <h2 style={{ fontSize:'15px', fontWeight:600, marginBottom:'16px', color:'var(--text-primary)' }}>
            🔐 Upload & Encrypt a File
          </h2>
          <UploadZone onUploadSuccess={handleUploaded} />
        </div>

        {/* File list */}
        <div>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'12px' }}>
            <h2 style={{ fontSize:'15px', fontWeight:600, color:'var(--text-primary)' }}>
              📂 Your Files
            </h2>
            <button
              onClick={loadFiles}
              style={{
                padding:'5px 12px', borderRadius:'6px', fontSize:'12px',
                fontFamily:'var(--font-mono)', background:'transparent',
                border:'1px solid var(--border)', color:'var(--text-secondary)', cursor:'pointer',
              }}
            >
              ⟳ Refresh
            </button>
          </div>

          {fetchErr && (
            <div style={{
              padding:'12px 16px', marginBottom:'12px',
              background:'rgba(255,71,87,0.08)', border:'1px solid var(--danger)',
              borderRadius:'var(--radius-sm)', color:'var(--danger)',
              fontSize:'13px', fontFamily:'var(--font-mono)',
            }}>
              ❌ {fetchErr} — Is the backend running? Check that <code>python -m backend.app</code> is running.
            </div>
          )}

          <FileList files={files} loading={loading} onDeleted={handleDeleted} />
        </div>
      </div>
    </div>
  );
}
