// Pix checkout page.
'use strict';
(function () {
  const sessionId = getSessionId();
  if (!sessionId || !getSessionToken()) { window.location.href = '/'; return; }

  const expiredMsg = document.getElementById('expired-msg');
  const qrBlock = document.getElementById('qr-block');

  document.getElementById('reload-btn').addEventListener('click', () => location.reload());

  function showExpired() {
    qrBlock.style.display = 'none';
    expiredMsg.style.display = 'block';
  }

  (async () => {
    let data;
    try {
      const resp = await apiFetch(`/checkout/${encodeURIComponent(sessionId)}`, { method: 'POST' });
      if (!resp.ok) { window.location.href = '/error.html?reason=payment_error'; return; }
      data = await resp.json();
    } catch (e) {
      window.location.href = '/error.html?reason=payment_error';
      return;
    }

    document.getElementById('loading').style.display = 'none';
    qrBlock.style.display = 'block';

    // The QR image is a data: URI produced by the payment provider. Anything else —
    // an http(s) URL, a javascript: URI — is refused rather than rendered.
    const image = data.qr_code_image || '';
    if (/^data:image\/(png|jpeg|gif);base64,[A-Za-z0-9+/=]+$/.test(image)) {
      document.getElementById('qr-img').src = image;
    }

    // .value and .textContent never parse markup, so the provider's strings cannot
    // become HTML here (item 15).
    document.getElementById('br-code').value = data.br_code || '';
    const amount = Number(data.amount) || 0;
    document.getElementById('price-label').textContent =
      `R$${(amount / 100).toFixed(2).replace('.', ',')}`;

    let remaining = Number(data.expires_in) || 900;
    const timerEl = document.getElementById('timer');
    const interval = setInterval(() => {
      remaining--;
      const m = Math.floor(remaining / 60).toString().padStart(2, '0');
      const s = (remaining % 60).toString().padStart(2, '0');
      timerEl.textContent = `${m}:${s}`;
      if (remaining <= 0) { clearInterval(interval); showExpired(); }
    }, 1000);

    await poll({
      path: `/checkout/status/${encodeURIComponent(sessionId)}`,
      intervalMs: 3000,
      maxMs: 900000,
      condition: d => d.payment_status === 'paid',
      onDone: () => { clearInterval(interval); goTo('waiting.html'); },
      onTimeout: () => { clearInterval(interval); showExpired(); },
    });
  })();
})();
