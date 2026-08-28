# instagram-saas

SaaS que gera relatório pago de analytics de Instagram (R$ 67) com upsell de agência.
Funciona também como base de prospecção B2B: o relatório barato é a isca de diagnóstico
que qualifica o lead antes da venda maior de serviços de sistemas.

## Stack

- **Backend:** FastAPI + uvicorn (`backend/`), Python 3. Entrada: `backend.main:app`
- **Frontend:** HTML/CSS/JS estático (`frontend/`), sem build
- **Integrações:** Meta OAuth (Instagram), OpenPix (Pix), Resend (e-mail),
  Google Sheets (CRM), Anthropic API (análise), matplotlib (gráficos)
- **Deploy:** Railway via Nixpacks (`nixpacks.toml`, `Procfile`, `railway.json`)

## Comandos

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload          # servir local
python -m pytest backend/tests -q          # testes
```

Configuração vem toda de variáveis de ambiente — veja `backend/.env.example`.
`backend/config.py` falha na importação se uma variável obrigatória faltar; isso é
proposital, não conserte "tornando opcional".

## Skills de vendas

`.claude/skills/` é a **fonte única** das 23 skills de prospecção e vendas.

Para Antigravity, Gemini CLI ou Codex, rode uma vez:

```bash
./scripts/setup-skills.sh            # espelha em .agents/skills/
./scripts/setup-skills.sh --global   # + instala no Antigravity do usuário
./scripts/setup-skills.sh --check    # verifica se o espelho está em dia
python3 scripts/check-skills.py      # valida frontmatter e links antes de commitar
```

`.agents/` é gerado e não versionado. Editou algo em `.claude/skills/`? Rode o script
de novo. As skills brasileiras (`prospect-br`, `prospeccao-br`, `abordagem-br`) funcionam
com ou sem subagentes — veja `docs/vendas/AVALIACAO-SKILLS.md`.

## Convenções

- Código e comentários em inglês; **texto voltado ao usuário final em português-BR**
  (relatórios, e-mails, páginas, mensagens de erro visíveis)
- Fuso de referência: America/Sao_Paulo (`BRT` em `backend/crm.py`)
- Valores monetários em centavos nos inteiros (`REPORT_PRICE_BRL = 6700` = R$ 67,00)
- Nunca commitar credencial. `frontend/assets/config.js` e `backend/coupons.json`
  são gerados e ignorados pelo git
- Dado de prospecção: só fonte pública e contato profissional, com proveniência
  registrada (LGPD — ver skill `abordagem-br`)
