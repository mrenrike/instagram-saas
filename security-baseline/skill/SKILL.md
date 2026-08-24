---
name: security-baseline
description: Baseline de segurança de 20 itens aplicado por padrão em todo projeto web (backend ou frontend). Use ao criar endpoint, formulário, upload, login, checkout, webhook, integração de pagamento, migration de banco, ou ao configurar deploy, CORS, headers e CI. Use também ao revisar código de qualquer uma dessas áreas. Cobre segredos, autenticação, autorização por registro, validação de entrada, escape de saída, rate limiting, cabeçalhos, HTTPS e varredura de dependências.
---

# Baseline de segurança

Aplique estes 20 itens por padrão, sem esperar o usuário pedir. Quando um item não se
aplica, diga em uma frase por que não — "N/A" sem justificativa é como esse checklist
morre.

Não faça auditoria de segurança de coisas que o usuário não tocou. Aplique o baseline
ao código que você está escrevendo ou revisando; se notar um problema grave fora do
escopo, mencione uma vez e siga.

---

## 1. Segredos ficam fora do código

Todo segredo vem de variável de ambiente, sem valor padrão real. Falhe no boot com o
nome da variável quando faltar — subir com placeholder é pior que não subir.

```python
def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"Variável obrigatória ausente: {name}")
    return value
```

Config de frontend (`config.js`, `NEXT_PUBLIC_*`, `VITE_*`) é **pública**. Chave de
API, webhook secret e token de admin nunca entram lá.

## 2. Histórico do Git limpo

gitleaks no CI com `fetch-depth: 0`. Um segredo apagado no último commit segue
exposto em todos os anteriores.

**Se vazou: rotacione primeiro, reescreva o histórico depois.** O repositório já foi
clonado, indexado por bots e possivelmente cacheado pelo GitHub. Reescrever não
desfaz o vazamento — só a rotação desfaz.

## 3. Chave pública para o banco

Supabase/Firebase: a chave `anon`/pública vai ao cliente. A `service_role` fica só no
servidor — ela ignora RLS por definição, então no cliente equivale a dar acesso total
ao banco.

## 4. Row-Level Security

Toda tabela com dado de usuário: RLS ligado, policy por `auth.uid()`, e teste que
prova que o usuário A não lê a linha do usuário B. Sem esse teste a policy é uma
suposição.

## 5. Criptografar dados sensíveis em repouso

AEAD (AES-GCM), com o id do registro como *associated data* para o blob não poder ser
movido entre registros. Arquivo `0600` em diretório `0700`, gravação atômica
(temp + `os.replace`).

## 6. Autenticação no lado do servidor

Nenhuma decisão de autorização no cliente. Comparação de segredo **sempre** em tempo
constante — `==` retorna no primeiro byte diferente e permite recuperar o token
caractere a caractere.

```python
hmac.compare_digest(candidato, esperado)   # sim
candidato == esperado                       # não
```

## 7. Restringir acesso aos registros

**Um id imprevisível não é controle de acesso.** Ids vazam por log de acesso,
histórico do navegador, header `Referer` e link compartilhado no WhatsApp.

Todo endpoint que lê ou altera um registro precisa provar que o chamador tem direito
a **aquele** registro: sessão autenticada + dono, ou token HMAC assinado e com prazo,
amarrado àquele id.

Responda o mesmo 404 para "não existe", "token inválido" e "expirado" — distinguir
transforma o endpoint num oráculo que confirma quais ids existem.

## 8. Impedir adulteração de campos

Rejeite campos desconhecidos no corpo (`extra="forbid"`), não os ignore. Ignorar
funciona até alguém adicionar um campo `is_admin` ao modelo meses depois.

Preço, papel, status de pagamento e id de dono são decididos no servidor. O cliente
manda o código do cupom; o servidor calcula o desconto.

## 9. Proteger cookies de sessão

`HttpOnly` + `Secure` + `SameSite=Lax`. `SameSite=None` (necessário quando frontend e
API estão em sites diferentes) reabre CSRF: exige token CSRF e allowlist de CORS
explícita. Em setup cross-site, prefira token assinado no header `Authorization`.

## 10. Senhas com hash

Argon2id ou bcrypt para senha de usuário. PBKDF2 (600k+ rounds) para segredo de
máquina. Nunca em claro, nunca SHA sem salt, nunca MD5.

## 11. Limitar tentativas

Rate limit em login, recuperação de senha, checkout, webhook e qualquer endpoint que
mande e-mail ou SMS. Por IP **e** por conta — só por IP não segura contra botnet, só
por conta permite enumerar usuários.

Duas armadilhas:
- **Em memória com vários workers**, o limite vira N× o configurado.
- **`X-Forwarded-For` sem proxy na frente**: o cliente escolhe o próprio IP.

## 12. Proteção contra bots

Captcha (Turnstile/hCaptcha) verificado **no servidor**, contra o provedor. O callback
do widget no cliente não prova nada. Tokens são de uso único: não cacheie o resultado.

Complemente com honeypot (campo escondido por CSS que bot preenche) e rate limit.
Honeypot sozinho não segura script direcionado.

## 13. Consultas parametrizadas

Sempre bind de parâmetro. Nunca f-string, `%` ou concatenação em SQL — nem "só nessa
query interna".

```python
db.execute("SELECT * FROM users WHERE email = :email", {"email": email})   # sim
db.execute(f"SELECT * FROM users WHERE email = '{email}'")                  # não
```

Vale para o análogo em outros destinos: planilha (`valueInputOption="RAW"` e prefixar
`'` em células que começam com `= + - @`), NoSQL (operadores `$` vindos do cliente),
LDAP, comandos de shell.

## 14. Validar todas as entradas

Allowlist de formato, teto de tamanho, tipo explícito. Em especial: **todo id que vira
caminho de arquivo ou de URL**. Validar por forma, não tentar limpar caracteres ruins.

```python
if not UUID_RE.match(session_id):
    raise InvalidIdentifier()
path = SESSIONS_DIR / f"{session_id}.enc"   # agora é seguro
```

Sem isso, `../../etc/passwd` sai do diretório.

## 15. Escapar conteúdo do usuário

Escape na saída, no contexto certo: HTML, atributo, URL, JS, SQL — cada um tem regra
própria. Em template de e-mail e relatório, escape **tudo** que é interpolado.

**A resposta do LLM conta como entrada de usuário.** Ela reflete legendas, nomes e
contexto que o usuário escreveu.

No frontend: `textContent`, não `innerHTML`.

## 16. Restringir uploads

Extensão + tipo declarado + tamanho + magic bytes. Guarde fora da raiz web, com nome
gerado por você (nunca o nome enviado). Sirva por endpoint que verifica autorização,
não por caminho estático.

Limite o tamanho do corpo da requisição antes de bufferizar.

## 17. Retornar só o que a tela precisa

Serializer explícito, nunca `return objeto_do_banco`. Um `SELECT *` serializado
entrega hash de senha, token e e-mail de terceiro.

Erro para o cliente é genérico + id de correlação; o detalhe vai para o log. Mensagem
de exceção carrega caminho de arquivo, versão de biblioteca, fragmento de SQL e
chave de API embutida em URL.

Em produção: não publique `/docs` nem o schema OpenAPI.

## 18. Cabeçalhos de segurança

```
Content-Security-Policy: default-src 'none'; script-src 'self'; ...
Strict-Transport-Security: max-age=63072000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

**Nunca `'unsafe-inline'` em `script-src`** — anula a proteção contra XSS. Extraia o
script inline para arquivo. Em `style-src` é um relaxamento bem mais fraco e às vezes
aceitável; documente quando usar.

CORS com allowlist explícita. `allow_origins=["*"]` deixa qualquer site da internet
chamar sua API com o navegador do visitante.

## 19. Forçar HTTPS

Redirect 308 + HSTS. Atrás de proxy (Railway, Nginx, Cloudflare) leia
`X-Forwarded-Proto` — `request.url.scheme` diz "http" mesmo numa requisição segura.

Só redirecione métodos seguros; um POST em HTTP deve ser recusado, não redirecionado
(o corpo se perde ou é reenviado em claro).

## 20. Varredura de dependências

`pip-audit` / `npm audit` no CI, Dependabot ligado, e **agendamento semanal** — uma
CVE nova aparece sem ninguém dar push.

Some análise estática do próprio código: bandit, semgrep, `ruff --select S`.

---

## Ao terminar

Deixe um `SECURITY.md` com o estado real de cada item. Marque ✅ só o que está
implementado e testado; para N/A, escreva a frase que explica.

Escreva teste para o controle de segurança, não só para o caminho feliz: token de
outro usuário dá 404, campo desconhecido dá 422, id com `../` é recusado, o erro
bruto não aparece na resposta.
