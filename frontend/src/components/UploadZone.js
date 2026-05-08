// frontend/src/components/UploadZone.js
import React, { useState, useRef } from 'react';
import { uploadFile } from '../utils/api';

export default function UploadZone({ onUploadSuccess }) {
  const [dragging,  setDragging]  = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress,  setProgress]  = useState(0);
  const [status,    setStatus]    = useState('');  // success/error message
  const [isError,   setIsError]   = useState(false);
  const inputRef = useRef();

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length) handleUpload(files[0]);
  };

  const handleFileInput = (e) => {
    const files = Array.from(e.target.files);
    if (files.length) handleUpload(files[0]);
  };

  const handleUpload = async (file) => {
    setUploading(true);
    setProgress(0);
    setStatus('');
    setIsError(false);

    try {
      const result = await uploadFile(file, (pct) => setProgress(pct));
      setStatus(`✅ "${result.file_name}" encrypted and uploaded across ${result.total_shards} shards!`);
      setIsError(false);
      onUploadSuccess && onUploadSuccess(result);
    } catch (err) {
      setStatus(`❌ ${err.message}`);
      setIsError(true);
    } finally {
      setUploading(false);
      setProgress(0);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const zone = {
    border: `2px dashed ${dragging ? 'var(--accent)' : 'var(--border)'}`,
    borderRadius: 'var(--radius)',
    padding: '40px 24px',
    textAlign: 'center',
    cursor: uploading ? 'default' : 'pointer',
    background: dragging ? 'var(--accent-dim)' : 'var(--bg-card)',
    transition: 'all 0.2s',
    boxShadow: dragging ? 'var(--shadow-glow)' : 'none',
  };

  return (
    <div>
      <div
        style={zone}
        onDragOver={e => { e.preventDefault(); if (!uploading) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={!uploading ? handleDrop : undefined}
        onClick={() => !uploading && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          style={{ display: 'none' }}
          onChange={handleFileInput}
        />

        {uploading ? (
          <div>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:'13px', color:'var(--text-secondary)', marginBottom:'16px' }}>
              Encrypting & uploading... {progress}%
            </div>
            <div style={{ height:'4px', background:'var(--bg-elevated)', borderRadius:'2px', overflow:'hidden' }}>
              <div style={{
                height: '100%', width: `${progress}%`,
                background: 'linear-gradient(90deg, var(--accent), var(--success))',
                borderRadius: '2px', transition: 'width 0.3s ease',
              }} />
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: '36px', marginBottom: '12px' }}>🔐</div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
              Drop a file here or click to upload
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Files are AES-256 encrypted before leaving your browser session — max 100 MB
            </div>
          </div>
        )}
      </div>

      {status && (
        <div style={{
          marginTop: '12px', padding: '10px 16px', borderRadius: 'var(--radius-sm)',
          fontSize: '13px', fontFamily: 'var(--font-mono)',
          background: isError ? 'rgba(255,71,87,0.1)' : 'rgba(0,214,143,0.1)',
          border: `1px solid ${isError ? 'var(--danger)' : 'var(--success)'}`,
          color: isError ? 'var(--danger)' : 'var(--success)',
        }}>
          {status}
        </div>
      )}
    </div>
  );
}
