// Questionnaire page.
'use strict';
(function () {
  const sessionId = getSessionId();
  if (!sessionId || !getSessionToken()) { window.location.href = '/'; return; }

  const form = document.getElementById('form');
  const btn = document.getElementById('submit-btn');
  const errorEl = document.getElementById('error-msg');

  function showError(message) {
    // textContent, not innerHTML: the API's `detail` is a string we render as text.
    errorEl.textContent = message;
    errorEl.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Continuar para o pagamento →';
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    btn.disabled = true;
    btn.textContent = 'Enviando...';
    errorEl.style.display = 'none';

    const fd = new FormData(e.target);
    const competitors = (fd.get('competitors') || '')
      .split(',').map(s => s.trim()).filter(Boolean).slice(0, 10);

    const body = {
      name: fd.get('name'),
      email: fd.get('email'),
      niche: fd.get('niche'),
      goal: fd.get('goal'),
      audience: fd.get('audience'),
      tone: fd.get('tone'),
      management_style: fd.get('management_style'),
      competitors,
      extra_context: fd.get('extra_context') || '',
      coupon_code: fd.get('coupon_code') || null,
      // Item 12: the honeypot travels as-is. A real user never fills it in; the
      // server rejects the submission when it arrives non-empty.
      website: fd.get('website') || '',
      captcha_token: (window.turnstile && form.querySelector('[name=cf-turnstile-response]')
        ? form.querySelector('[name=cf-turnstile-response]').value
        : ''),
    };

    try {
      const resp = await apiFetch(`/questionnaire/${encodeURIComponent(sessionId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        showError(typeof data.detail === 'string' ? data.detail : 'Erro ao enviar.');
        return;
      }
      goTo('checkout.html');
    } catch (err) {
      showError('Erro de conexão. Tente novamente.');
    }
  });
})();
