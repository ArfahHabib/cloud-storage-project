// frontend/src/utils/api.js
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function getToken() {
  return localStorage.getItem('auth_token') || '';
}
function authHeaders() {
  return { 'Authorization': `Bearer ${getToken()}` };
}

export async function ping() {
  const res = await fetch(`${API_URL}/api/ping`);
  return res.json();
}

export async function getHealth() {
  const res = await fetch(`${API_URL}/api/health`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function listFiles() {
  const res = await fetch(`${API_URL}/api/files`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch files');
  return res.json();
}

// Upload with two-phase progress:
//   0–80%  = actual network upload to server
//   80–99% = server-side processing (timed estimate)
//   100%   = server responded OK
export async function uploadFile(file, onProgress) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    let processingTimer = null;
    const startTime = Date.now();

    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return;
      const networkPct = Math.round((e.loaded / e.total) * 80);
      const elapsed    = (Date.now() - startTime) / 1000; // seconds
      const rateMBps   = elapsed > 0 ? (e.loaded / elapsed) / (1024 * 1024) : 0;
      const rateStr    = rateMBps > 0.1 ? `${rateMBps.toFixed(1)} MB/s` : '';
      onProgress?.(networkPct, rateStr);

      if (e.loaded === e.total) {
        let fake = 80;
        processingTimer = setInterval(() => {
          fake = Math.min(fake + 1, 99);
          onProgress?.(fake, 'processing...');
          if (fake >= 99) clearInterval(processingTimer);
        }, 300);
      }
    };

    xhr.onload = () => {
      clearInterval(processingTimer);
      onProgress?.(100);
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(100, '');
        resolve(JSON.parse(xhr.responseText));
      } else {
        const err = JSON.parse(xhr.responseText || '{}');
        reject(new Error(err.error || 'Upload failed'));
      }
    };

    xhr.onerror = () => {
      clearInterval(processingTimer);
      reject(new Error('Network error during upload'));
    };

    xhr.open('POST', `${API_URL}/api/upload`);
    xhr.setRequestHeader('Authorization', `Bearer ${getToken()}`);
    xhr.send(formData);
  });
}

export async function downloadFile(fileId, fileName) {
  const res = await fetch(`${API_URL}/api/download/${fileId}`, {
    headers: authHeaders()
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'Download failed');
  }

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

export async function deleteFile(fileId) {
  const res = await fetch(`${API_URL}/api/files/${fileId}`, {
    method: 'DELETE',
    headers: authHeaders()
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'Delete failed');
  }
  return res.json();
}

export function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1);
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}