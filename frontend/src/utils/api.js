// frontend/src/utils/api.js
// All HTTP calls to the Flask backend go through here.

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// ── Get the stored auth token ────────────────────────────────
function getToken() {
  return localStorage.getItem('auth_token') || '';
}

function authHeaders() {
  return {
    'Authorization': `Bearer ${getToken()}`
  };
}

// ── Ping (no auth needed) ────────────────────────────────────
export async function ping() {
  const res = await fetch(`${API_URL}/api/ping`);
  return res.json();
}

// ── Get S3 bucket health ─────────────────────────────────────
export async function getHealth() {
  const res = await fetch(`${API_URL}/api/health`, {
    headers: authHeaders()
  });
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

// ── List all files for current user ─────────────────────────
export async function listFiles() {
  const res = await fetch(`${API_URL}/api/files`, {
    headers: authHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch files');
  return res.json();
}

// ── Upload a file ────────────────────────────────────────────
export async function uploadFile(file, onProgress) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();

    // Track upload progress
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        const err = JSON.parse(xhr.responseText || '{}');
        reject(new Error(err.error || 'Upload failed'));
      }
    };

    xhr.onerror = () => reject(new Error('Network error during upload'));

    xhr.open('POST', `${API_URL}/api/upload`);
    xhr.setRequestHeader('Authorization', `Bearer ${getToken()}`);
    xhr.send(formData);
  });
}

// ── Download a file ──────────────────────────────────────────
export async function downloadFile(fileId, fileName) {
  const res = await fetch(`${API_URL}/api/download/${fileId}`, {
    headers: authHeaders()
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'Download failed');
  }

  // Convert response to a downloadable blob
  const blob = await res.blob();
  const url  = window.URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

// ── Delete a file ────────────────────────────────────────────
export async function deleteFile(fileId) {
  const res = await fetch(`${API_URL}/api/files/${fileId}`, {
    method:  'DELETE',
    headers: authHeaders()
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'Delete failed');
  }
  return res.json();
}

// ── Format bytes to human readable ──────────────────────────
export function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

// ── Format ISO date to readable ──────────────────────────────
export function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}
