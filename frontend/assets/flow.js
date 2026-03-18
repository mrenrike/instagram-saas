// frontend/assets/flow.js

// UTM capture: read from URL and persist in sessionStorage
(function captureUTM() {
  const params = new URLSearchParams(window.location.search);
  ['utm_source', 'utm_medium', 'utm_campaign'].forEach(k => {
    const v = params.get(k);
    if (v) sessionStorage.setItem(k, v);
  });
})();

function getUTMs() {
  return {
    utm_source: sessionStorage.getItem('utm_source') || '',
    utm_medium: sessionStorage.getItem('utm_medium') || '',
    utm_campaign: sessionStorage.getItem('utm_campaign') || '',
  };
}

function getSessionId() {
  return new URLSearchParams(window.location.search).get('session_id') || '';
}

// Polling helper: calls url every intervalMs for up to maxMs
async function poll({ url, intervalMs, maxMs, condition, onResult, onDone, onTimeout }) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    try {
      const resp = await fetch(url);
      if (resp.ok) {
        const data = await resp.json();
        onResult && onResult(data);
        if (condition(data)) { onDone && onDone(data); return; }
      }
    } catch (e) { /* network error — keep polling */ }
    await new Promise(r => setTimeout(r, intervalMs));
  }
  onTimeout && onTimeout();
}

// Build backend URL — set via config.js (window.BACKEND_URL)
const BACKEND = window.BACKEND_URL || 'https://your-app.railway.app';
