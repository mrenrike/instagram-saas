// Error page: render a message from a fixed table, never from the URL.
'use strict';
(function () {
  const agencyEmail = (window.APP_CONFIG && window.APP_CONFIG.AGENCY_EMAIL) || 'contato@agencia.com.br';
  document.getElementById('contact-link').href = 'mailto:' + encodeURIComponent(agencyEmail);

  const params = new URLSearchParams(window.location.search);
  const reason = params.get('reason') || '';

  // Item 15: the message comes from this allowlist. Echoing `reason` into the page
  // would let anyone craft a link that displays arbitrary text on your domain.
  const msgs = {
    personal_account: 'Sua conta Instagram é pessoal. O produto requer conta Business ou Creator.',
    oauth_denied: 'A conexão com o Instagram foi cancelada.',
    token_exchange_failed: 'Não foi possível concluir a conexão com o Instagram.',
    graph_api_failed: 'Não foi possível ler os dados da sua conta agora.',
    token_expired: 'Seu token de acesso Instagram expirou.',
    graph_error: 'Não foi possível ler os dados da sua conta agora.',
    analysis_error: 'Não foi possível gerar a análise agora.',
    payment_error: 'Não foi possível criar a cobrança agora.',
    timeout: 'O processamento demorou mais que o esperado.',
  };
  document.getElementById('error-detail').textContent =
    msgs[reason] || 'Erro técnico no processamento.';
})();
