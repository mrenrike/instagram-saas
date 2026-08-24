# Política de segurança

Este projeto segue o **baseline de segurança de 20 itens** usado em todos os projetos.
O kit reutilizável está em [`security-baseline/`](security-baseline/) — copie-o para
qualquer projeto novo e siga o mesmo checklist.

Para reportar uma vulnerabilidade, escreva para o e-mail em `ADMIN_EMAIL`. Não abra
issue pública.

---

## Checklist — estado neste projeto

| # | Item | Estado | Onde |
|---|------|--------|------|
| 1 | Ocultar chaves de API | ✅ | `backend/config.py`, `backend/.env.example` |
| 2 | Remover segredos do histórico do Git | ✅ | `.gitleaks.toml`, CI `security.yml` |
| 3 | Chave pública para o banco de dados | ➖ N/A | Sem banco — armazenamento em arquivo cifrado |
| 4 | Row-Level Security | ➖ N/A | Sem banco — ver item 7 |
| 5 | Criptografar dados sensíveis | ✅ | `backend/session.py` (AES-256-GCM + 0600) |
| 6 | Autenticação no lado do servidor | ✅ | `backend/deps.py`, `backend/webhook.py` |
| 7 | Restringir acesso aos registros | ✅ | `backend/security/tokens.py`, `backend/deps.py` |
| 8 | Impedir adulteração de campos | ✅ | `backend/security/validation.py` (`StrictModel`) |
| 9 | Proteger cookies de sessão | ➖ N/A* | `backend/security/cookies.py` (pronto para uso) |
| 10 | Armazenar senhas com hash | ✅ | `backend/security/secrets.py` (PBKDF2) |
| 11 | Limitar tentativas de login | ✅ | `backend/security/ratelimit.py` |
| 12 | Proteção contra bots | ✅ | `backend/security/bots.py` + honeypot |
| 13 | Consultas parametrizadas | ➖ N/A** | `backend/crm.py` (análogo: fórmulas de planilha) |
| 14 | Validar todas as entradas | ✅ | `backend/security/validation.py` |
| 15 | Escapar conteúdo do usuário | ✅ | `backend/report.py`, `backend/email_service.py`, `backend/admin.py` |
| 16 | Restringir uploads de arquivos | ✅*** | `backend/security/limits.py` |
| 17 | Retornar só o necessário na API | ✅ | `backend/security/responses.py`, `backend/admin.py` |
| 18 | Cabeçalhos de segurança | ✅ | `backend/security/headers.py`, `frontend/.htaccess` |
| 19 | Forçar HTTPS | ✅ | `backend/security/https.py`, `frontend/.htaccess` |
| 20 | Varredura de dependências | ✅ | `.github/workflows/security.yml`, Dependabot |

\* O frontend é estático e roda em outro domínio (Hostinger) do backend (Railway).
Um cookie cross-site exigiria `SameSite=None`, o que reabre CSRF. Em vez disso a
sessão viaja num token HMAC no header `X-Session-Token`. `cookies.py` está pronto
para projetos que rodam frontend e API no mesmo site.

\*\* Não há SQL. O análogo direto é a planilha do CRM: `valueInputOption="RAW"` +
`sanitize_for_spreadsheet()` impedem que um nome como `=IMPORTXML(...)` execute como
fórmula quando alguém abre a planilha.

\*\*\* Não há upload de arquivos. O que existe é limite de tamanho de corpo de
requisição; `validate_upload()` está pronto para quando houver.

---

## O que cada item significa aqui

### 1. Ocultar chaves de API
Nenhum segredo tem valor padrão no código. `backend/config.py` levanta `ConfigError`
com o nome da variável na inicialização quando falta algo — falhar no boot é melhor
que subir para produção com um placeholder. O `config.js` do frontend é público por
natureza: nada secreto pode entrar nele.

### 2. Remover segredos do histórico do Git
Um segredo apagado no último commit continua exposto em todos os anteriores. O
gitleaks roda no CI com `fetch-depth: 0` (histórico completo). Varredura feita neste
repositório: **nenhum segredo real no histórico** — o único match é uma chave RSA
falsa de 8 bytes numa fixture de teste (`backend/tests/test_crm.py`).

Se um segredo real for commitado: **rotacione primeiro**, reescreva o histórico
depois. O histórico já foi clonado e indexado; reescrever não desfaz o vazamento.

### 5. Criptografar dados sensíveis
Cada sessão é um blob AES-256-GCM. O `session_id` entra como *associated data*, então
um arquivo renomeado para outro id não decifra. Arquivos gravados com `0600` dentro
de um diretório `0700`, via arquivo temporário + `os.replace` (gravação atômica).

### 7. Restringir acesso aos registros
Um id imprevisível **não é** controle de acesso: ids vazam por log, histórico do
navegador, `Referer` e links compartilhados. Todo endpoint de sessão exige um token
HMAC assinado, com prazo, amarrado àquele id específico. Token de outra sessão dá 404
— o mesmo 404 de sessão inexistente, para o endpoint não virar um oráculo de ids.

### 8. Impedir adulteração de campos
Todo corpo de requisição herda de `StrictModel`, que rejeita campos desconhecidos.
Enviar `{"discount_applied": 6700}` retorna 422, não é ignorado em silêncio. O preço
nunca vem do cliente: é calculado a partir de `REPORT_PRICE_BRL` e do cupom validado
no servidor.

### 11. Limitar tentativas
`RateLimiter` é uma janela deslizante em memória — sem Redis, sem dependência extra.
A contrapartida: a janela é **por processo**. Com N workers o limite efetivo é N×.
Com mais de uma instância, troque o armazenamento por Redis.

### 15. Escapar conteúdo do usuário
Inclui o texto gerado pelo modelo. A resposta de um LLM não é output confiável: ela
reflete legendas, handles e contexto que o usuário escreveu, então `<img src=x
onerror=...>` chega ao template pelo modelo tão facilmente quanto por um formulário.

### 18/19. Cabeçalhos e HTTPS
A CSP do backend nega tudo por padrão (`default-src 'none'`) porque a API só devolve
JSON. O frontend usa `script-src 'self'` — **zero script inline**; todo JS de página
está em `frontend/assets/page-*.js`.

**Relaxamento conhecido:** `style-src` inclui `'unsafe-inline'` porque as páginas usam
atributos `style=`. É bem mais fraco que script inline. Para remover: mover os estilos
inline para classes em `style.css`.

---

## Antes de cada deploy

```bash
pip-audit -r backend/requirements.txt --strict   # item 20
bandit -c pyproject.toml -r backend -ll          # item 20
gitleaks detect --config .gitleaks.toml          # itens 1, 2
pytest backend/tests -q                          # inclui os testes de segurança
```

Confira também:

- [ ] `ALLOWED_ORIGINS` lista os domínios reais (nunca `*`)
- [ ] `ADMIN_SECRET_HASH` configurado (não `ADMIN_SECRET` em claro)
- [ ] `FRONTEND_BASE_URL` apontando para o domínio de produção
- [ ] `frontend/.htaccess` com o `connect-src` do backend real, não o placeholder
- [ ] `TURNSTILE_SECRET` configurado antes de rodar tráfego pago
- [ ] Service account do Google com acesso **apenas** à planilha do CRM
