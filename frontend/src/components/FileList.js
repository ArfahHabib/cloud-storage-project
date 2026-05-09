// frontend/src/components/FileList.js
import React, { useState } from 'react';
import { downloadFile, deleteFile, formatBytes, formatDate } from '../utils/api';

function FileIcon({ name }) {
  const ext = name?.split('.').pop()?.toLowerCase() || '';
  const icons = {
    pdf:'📄', doc:'📝', docx:'📝', txt:'📃',
    jpg:'🖼', jpeg:'🖼', png:'🖼', gif:'🖼',
    zip:'📦', rar:'📦', tar:'📦',
    mp4:'🎬', mov:'🎬', avi:'🎬',
    mp3:'🎵', wav:'🎵',
    py:'🐍', js:'📜', html:'🌐', css:'🎨',
    xlsx:'📊', csv:'📊',
  };
  return <span style={{ fontSize:'20px' }}>{icons[ext] || '📁'}</span>;
}

function FileRow({ file, onDeleted }) {
  const [dlState,   setDlState]   = useState(null); // null | 'waiting' | 'done'
  const [elapsed,   setElapsed]   = useState(0);
  const [deleting,  setDeleting]  = useState(false);
  const [confirmDel,setConfirmDel]= useState(false);
  const [error,     setError]     = useState('');
  const timerRef = React.useRef(null);

  const busy = dlState !== null || deleting;

  const handleDownload = async () => {
    setDlState('waiting');
    setElapsed(0);
    setError('');
    timerRef.current = setInterval(() => setElapsed(s => s + 1), 1000);
    try {
      await downloadFile(file.fileId, file.fileName);
      setDlState('done');
    } catch (err) {
      setError(err.message);
      setDlState(null);
    } finally {
      clearInterval(timerRef.current);
      setTimeout(() => setDlState(null), 1500);
    }
  };

  const handleDelete = async () => {
    if (!confirmDel) { setConfirmDel(true); return; }
    setDeleting(true);
    try {
      await deleteFile(file.fileId);
      onDeleted(file.fileId);
    } catch (err) {
      setError(err.message);
      setDeleting(false);
      setConfirmDel(false);
    }
  };

  const row = {
    display: 'grid',
    gridTemplateColumns: '32px 1fr 90px 90px 110px 100px',
    alignItems: 'center',
    gap: '16px',
    padding: '14px 20px',
    borderBottom: '1px solid var(--border)',
    transition: 'background 0.15s',
  };

  const btn = (color) => ({
    padding: '5px 12px', borderRadius: '6px', fontSize: '12px',
    fontFamily: 'var(--font-mono)', cursor: busy ? 'default' : 'pointer',
    background: color === 'accent' ? 'var(--accent)'
               : confirmDel && color === 'danger' ? 'var(--danger)' : 'transparent',
    color: color === 'accent' ? '#fff'
         : color === 'danger' ? (confirmDel ? '#fff' : 'var(--danger)') : 'var(--text-secondary)',
    border: color === 'danger' && !confirmDel ? '1px solid var(--danger)' : 'none',
    opacity: busy ? 0.6 : 1,
    transition: 'all 0.2s',
    minWidth: '90px',
  });

  return (
    <div>
      <div
        style={row}
        onMouseEnter={e => e.currentTarget.style.background='var(--bg-elevated)'}
        onMouseLeave={e => e.currentTarget.style.background='transparent'}
      >
        <FileIcon name={file.fileName} />

        <div>
          <div style={{ fontSize:'14px', fontWeight:500, color:'var(--text-primary)', wordBreak:'break-all' }}>
            {file.fileName}
          </div>
          <div style={{ fontSize:'12px', color:'var(--text-muted)', fontFamily:'var(--font-mono)', marginTop:'2px' }}>
            {file.totalShards} shards · {formatDate(file.uploadedAt)}
          </div>

          {/* Download status */}
          {dlState === 'waiting' && (
            <div style={{ marginTop:'6px' }}>
              <div style={{ height:'3px', borderRadius:'2px', overflow:'hidden', background:'var(--bg-elevated)' }}>
                <div style={{
                  height:'100%', width:'40%',
                  background:'linear-gradient(90deg, var(--accent), var(--success))',
                  borderRadius:'2px',
                  animation:'pulse-bar 1.2s ease-in-out infinite',
                }} />
              </div>
              <div style={{ fontSize:'11px', color:'var(--text-muted)', fontFamily:'var(--font-mono)', marginTop:'3px' }}>
                Decrypting & downloading... {elapsed}s
              </div>
            </div>
          )}
          {dlState === 'done' && (
            <div style={{ fontSize:'11px', color:'var(--success)', fontFamily:'var(--font-mono)', marginTop:'6px' }}>
              ✓ Download complete
            </div>
          )}
        </div>

        <span style={{ fontSize:'13px', color:'var(--text-secondary)', fontFamily:'var(--font-mono)' }}>
          {formatBytes(file.fileSize)}
        </span>

        <div style={{ display:'flex', alignItems:'center', gap:'4px' }}>
          <span style={{ width:'6px', height:'6px', borderRadius:'50%', background:'var(--success)', display:'inline-block' }} />
          <span style={{ fontSize:'12px', color:'var(--success)', fontFamily:'var(--font-mono)' }}>encrypted</span>
        </div>

        <button style={btn('accent')} onClick={handleDownload} disabled={busy}>
          {dlState === 'waiting' ? 'Decrypting...' : dlState === 'done' ? '✓ Done' : '⬇ Download'}
        </button>

        <button style={btn('danger')} onClick={handleDelete} disabled={busy}
          onMouseLeave={() => setTimeout(() => setConfirmDel(false), 2000)}>
          {deleting ? '...' : confirmDel ? '⚠ Confirm' : '🗑 Delete'}
        </button>
      </div>

      {error && (
        <div style={{ padding:'6px 20px', fontSize:'12px', color:'var(--danger)', fontFamily:'var(--font-mono)', background:'rgba(255,71,87,0.05)' }}>
          Error: {error}
        </div>
      )}
    </div>
  );
}

export default function FileList({ files, loading, onDeleted }) {
  const header = {
    display: 'grid',
    gridTemplateColumns: '32px 1fr 90px 90px 110px 100px',
    gap: '16px',
    padding: '10px 20px',
    background: 'var(--bg-elevated)',
    borderBottom: '1px solid var(--border)',
    borderRadius: 'var(--radius) var(--radius) 0 0',
    fontSize: '11px', fontFamily: 'var(--font-mono)',
    color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px',
  };

  if (loading) return (
    <div style={{ padding:'48px', textAlign:'center', color:'var(--text-muted)', fontFamily:'var(--font-mono)' }}>
      <div style={{ fontSize:'24px', marginBottom:'12px' }}>⟳</div>
      Loading files...
    </div>
  );

  if (!files?.length) return (
    <div style={{
      padding:'64px 24px', textAlign:'center',
      border:'1px solid var(--border)', borderRadius:'var(--radius)', marginTop:'8px'
    }}>
      <div style={{ fontSize:'40px', marginBottom:'12px' }}>🔭</div>
      <div style={{ color:'var(--text-secondary)', fontWeight:500 }}>No files yet</div>
      <div style={{ color:'var(--text-muted)', fontSize:'13px', marginTop:'6px' }}>
        Upload your first file above — it will be encrypted and distributed across 2 AWS regions.
      </div>
    </div>
  );

  return (
    <div style={{ border:'1px solid var(--border)', borderRadius:'var(--radius)', overflow:'hidden', marginTop:'8px' }}>
      <div style={header}>
        <span /><span>File Name</span><span>Size</span>
        <span>Status</span><span /><span />
      </div>
      {files.map(f => (
        <FileRow key={f.fileId} file={f} onDeleted={onDeleted} />
      ))}
    </div>
  );
}