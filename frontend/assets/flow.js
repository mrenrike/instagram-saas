// frontend/assets/flow.js
'use strict';

// --- Session credentials -----------------------------------------------------
// The API requires the session id *and* a signed access token for that exact id
// (item 7). The OAuth callback hands both over in the query string; we move the token
// into sessionStorage immediately and strip it from the visible URL so it does not end
// up in the browser history, in a screenshot, or in a Referer header.
const SESSION_KEY = 'ig_session_id';
const TOKEN_KEY = 'ig_session_token';

(function adoptCredentialsFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get('session_id');
  const token = params.get('t');

  if (sessionId) sessionStorage.setItem(SESSION_KEY, sessionId);
  if (token) sessionStorage.setItem(TOKEN_KEY, token);

  if (token) {
    params.delete('t');
    const query = params.toString();
    window.history.replaceState(
      {},
      '',
      window.location.pathname + (query ? '?' + query : '')
    );
  }
})();

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
  return (
    sessionStorage.getItem(SESSION_KEY) ||
    new URLSearchParams(window.location.search).get('session_id') ||
    ''
  );
}

function getSessionToken() {
  return sessionStorage.getItem(TOKEN_KEY) || '';
}

// Send the token in a header rather than the query string: query strings are written
// to access logs and leak through Referer, headers are not.
function authHeaders(extra) {
  return Object.assign({ 'X-Session-Token': getSessionToken() }, extra || {});
}

function apiFetch(path, options) {
  const opts = Object.assign({}, options);
  opts.headers = authHeaders(opts.headers);
  opts.credentials = 'omit'; // no ambient cookies cross-site
  return fetch(`${BACKEND}${path}`, opts);
}

// Internal navigation carries the session id only; the token stays in sessionStorage.
function goTo(page) {
  window.location.href = `/${page}?session_id=${encodeURIComponent(getSessionId())}`;
}

// Polling helper: calls path every intervalMs for up to maxMs
async function poll({ path, intervalMs, maxMs, condition, onResult, onDone, onTimeout }) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    try {
      const resp = await apiFetch(path);
      if (resp.ok) {
        const data = await resp.json();
        onResult && onResult(data);
        if (condition(data)) { onDone && onDone(data); return; }
      } else if (resp.status === 404 || resp.status === 401) {
        // The session is gone or the token is invalid — polling will never succeed.
        onTimeout && onTimeout();
        return;
      }
    } catch (e) { /* network error — keep polling */ }
    await new Promise(r => setTimeout(r, intervalMs));
  }
  onTimeout && onTimeout();
}

// Build backend URL — set via config.js (window.BACKEND_URL). Refuse anything but
// HTTPS in production so a misconfigured deploy cannot send the session token in the
// clear (item 19).
const BACKEND = (function resolveBackend() {
  const configured = window.BACKEND_URL || '';
  const isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);
  if (configured && !configured.startsWith('https://') && !isLocal) {
    console.error('BACKEND_URL must use https://');
    return '';
  }
  return configured.replace(/\/$/, '');
})();
