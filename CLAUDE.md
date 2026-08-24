# Instagram Analytics SaaS

Funil de venda única: o usuário conecta o Instagram via OAuth da Meta, responde um
questionário, paga R$67 via Pix, e recebe por e-mail um relatório gerado com a API da
Anthropic a partir dos últimos 60 posts.

## Estrutura

```
backend/            FastAPI (Railway)
  security/         Baseline de segurança reutilizável — copiável para outros projetos
  tools/            Utilitários de operação (geração de segredos)
frontend/           HTML/CSS/JS estático (Hostinger) — sem build step
security-baseline/  Kit portátil: skill, templates, auditoria
```

O fluxo é: `oauth` → `questionnaire` → `checkout` → `webhook` → `pipeline` →
`email_service` + `crm` → `followup` (D+3).

## Comandos

```bash
pytest backend/tests -q                        # testes
ruff check backend/                            # lint
bandit -c pyproject.toml -r backend -ll        # análise estática de segurança
pip-audit -r backend/requirements.txt --strict # CVEs nas dependências
./security-baseline/audit.sh .                 # checklist dos 20 itens
```

Rodar local: copie `backend/.env.example` para `backend/.env`, gere as chaves com
`python -m backend.tools.hash_secret --key`, e `uvicorn backend.main:app --reload`.

## Segurança — leia antes de mexer

Este projeto segue o baseline de 20 itens. **`SECURITY.md` tem o estado de cada item**
e `security-baseline/skill/SKILL.md` tem o raciocínio por trás de cada um.

Regras que não se negociam neste código:

- **Segredo só via ambiente**, sem valor padrão. `backend/config.py` falha no boot
  quando falta variável — não adicione fallback.
- **Todo endpoint de sessão passa por `Depends(authorized_session)`.** O `session_id`
  sozinho não autoriza nada; é preciso o token assinado que acompanha aquele id.
- **Todo corpo de requisição herda de `StrictModel`** e tem teto de tamanho por campo.
  Preço, status de pagamento e desconto são decididos no servidor.
- **Todo id que vira caminho passa por `validate_session_id`** antes de tocar o
  filesystem.
- **Escape tudo que entra em HTML** — incluindo a resposta do modelo, que reflete
  texto escrito pelo usuário.
- **Nada de `'unsafe-inline'` em `script-src`.** O JS de página fica em
  `frontend/assets/page-*.js`, nunca inline.
- **Erro para o cliente é categoria + mensagem genérica.** O detalhe vai para o log;
  `session.pipeline_error` nunca sai numa resposta HTTP.

Ao adicionar endpoint, formulário, upload ou integração, aplique o checklist e
atualize a tabela em `SECURITY.md`.

## Convenções

- Python 3.11, FastAPI, sem ORM (sessões são arquivos AES-GCM em disco).
- Horários do produto em BRT (UTC-3); timestamps de sessão em UTC.
- Valores monetários em centavos, sempre `int`.
- Mensagens ao usuário em pt-BR; comentários e nomes de código em inglês.
