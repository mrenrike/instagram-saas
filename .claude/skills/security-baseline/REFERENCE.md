# Baseline de segurança — kit portátil

Os 20 itens que todo projeto nosso implementa antes de ir ao ar, mais o código
reutilizável que os implementa.

Este diretório existe para ser **copiado**. A implementação de referência em Python é
`backend/security/` deste repositório; os templates aqui cobrem o resto (CI, ignore,
headers de servidor web) e valem para qualquer stack.

---

## Instalar como padrão em todos os projetos

```bash
./security-baseline/install.sh
```

Isso instala a skill `security-baseline` em `~/.claude/skills/`, onde ela vale para
**todos os projetos** abertos naquela máquina — não só este. A partir daí, ao pedir
uma feature nova, o Claude aplica o checklist sem você precisar lembrar dele.

Para instalar só neste repositório (versionado, vale para toda a equipe):

```bash
./security-baseline/install.sh --project
```

Desinstalar: `rm -rf ~/.claude/skills/security-baseline`.

---

## Aplicar a um projeto existente

1. **Copie o módulo** (projetos Python/FastAPI):
   ```bash
   cp -r backend/security /caminho/do/projeto/backend/security
   ```
   Ele só depende de stdlib + starlette + pydantic. Não arrasta nada novo.

2. **Copie os templates que se aplicam:**
   ```bash
   cp security-baseline/templates/gitignore-python /projeto/.gitignore
   cp security-baseline/templates/github-workflows/security-python.yml \
      /projeto/.github/workflows/security.yml
   cp security-baseline/templates/gitleaks.toml /projeto/.gitleaks.toml
   cp security-baseline/templates/web/.htaccess /projeto/frontend/.htaccess
   ```

3. **Rode a auditoria** e preencha o checklist:
   ```bash
   ./security-baseline/audit.sh /caminho/do/projeto
   ```

4. **Copie `SECURITY.md`** e marque o estado real de cada item. Um item marcado
   "N/A" precisa de uma frase dizendo por quê — "não se aplica" sem justificativa é
   como esse tipo de checklist morre.

---

## Os 20 itens

| # | Item | O que significa na prática |
|---|------|----------------------------|
| 1 | Ocultar chaves de API | Segredo só via variável de ambiente. Sem valor padrão. Falha no boot se faltar. |
| 2 | Remover segredos do histórico | gitleaks com histórico completo no CI. Vazou? Rotacione antes de reescrever. |
| 3 | Chave pública para o banco | A chave `anon`/pública no cliente; a `service_role` **nunca** sai do servidor. |
| 4 | Row-Level Security | RLS ligado em toda tabela com dado de usuário, com policy por `auth.uid()`. |
| 5 | Criptografar dados sensíveis | AEAD (AES-GCM) em repouso, permissões restritas no arquivo. |
| 6 | Autenticação no servidor | Nenhuma decisão de autorização no cliente. Comparação de segredo em tempo constante. |
| 7 | Restringir acesso aos registros | Id imprevisível não é autorização. Token assinado, com prazo, por recurso. |
| 8 | Impedir adulteração de campos | Rejeitar campos desconhecidos. Preço e papel decididos no servidor. |
| 9 | Proteger cookies de sessão | `HttpOnly` + `Secure` + `SameSite`. `None` só com CSRF token. |
| 10 | Senhas com hash | Argon2/bcrypt para usuários; PBKDF2 para segredo de máquina. Nunca em claro. |
| 11 | Limitar tentativas | Rate limit por IP e por conta em login, checkout, webhooks e recuperação de senha. |
| 12 | Proteção contra bots | Captcha verificado **no servidor** + honeypot + rate limit. |
| 13 | Consultas parametrizadas | Sempre bind de parâmetro. Nunca f-string em SQL. Vale para planilha e NoSQL também. |
| 14 | Validar todas as entradas | Allowlist de formato, teto de tamanho, tipo explícito. Especialmente ids que viram caminho. |
| 15 | Escapar conteúdo do usuário | Escapar na saída, por contexto. Resposta de LLM conta como entrada de usuário. |
| 16 | Restringir uploads | Extensão + tipo + tamanho + magic bytes. Fora da raiz web. Nome sanitizado. |
| 17 | Retornar só o necessário | Serializer explícito. Erro genérico para o cliente, detalhe no log. |
| 18 | Cabeçalhos de segurança | CSP, HSTS, nosniff, frame-ancestors, Referrer-Policy, Permissions-Policy. |
| 19 | Forçar HTTPS | Redirect 308 + HSTS. Ler `X-Forwarded-Proto` atrás de proxy. |
| 20 | Varredura de dependências | pip-audit/npm audit + Dependabot + agendamento semanal. |

Detalhe de cada item, com o raciocínio por trás: `skill/SKILL.md`.

---

## Armadilhas que já custaram caro

- **Rate limit em memória com vários workers.** O limite vira N× o configurado. Com
  mais de uma instância, use Redis.
- **`X-Forwarded-For` sem proxy na frente.** O cliente escolhe o próprio IP e passa
  por qualquer limite. Só confie no header quando algo o sobrescreve.
- **CSP com `'unsafe-inline'` em `script-src`.** Anula a proteção contra XSS. Extraia
  o script inline para um arquivo — é uma tarde de trabalho, não uma refatoração.
- **Reescrever o histórico antes de rotacionar.** O segredo já foi clonado. Rotacione
  primeiro, sempre.
- **Confiar na resposta do LLM.** Ela carrega conteúdo escrito pelo usuário. Escape.
