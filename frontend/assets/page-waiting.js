// Pipeline progress page.
'use strict';
(function () {
  const sessionId = getSessionId();
  if (!sessionId) { window.location.href = '/'; return; }

  const steps = ['Coletando dados', 'Calculando métricas', 'Analisando com IA', 'Gerando relatório', 'Enviando e-mail'];
  const stepPercent = [20, 40, 60, 80, 100];

  poll({
    path: `/pipeline/status/${encodeURIComponent(sessionId)}`,
    intervalMs: 5000,
    maxMs: 600000,
    condition: d => d.status === 'done' || d.status === 'error',
    onResult: d => {
      const step = Math.max(0, Math.min(d.step - 1, steps.length - 1));
      if (d.step > 0) {
        document.getElementById('progress').style.width = stepPercent[step] + '%';
        document.getElementById('step-label').textContent = steps[step] + '...';
      }
    },
    onDone: d => {
      if (d.status === 'done') {
        goTo('success.html');
      } else {
        // The API returns a category, never a raw error string (item 17); pass only
        // that category on, and let error.html map it to a message it controls.
        const reason = encodeURIComponent(d.error || 'internal');
        window.location.href = `/error.html?session_id=${encodeURIComponent(sessionId)}&reason=${reason}`;
      }
    },
    onTimeout: () => {
      window.location.href = `/error.html?session_id=${encodeURIComponent(sessionId)}&reason=timeout`;
    },
  });
})();
