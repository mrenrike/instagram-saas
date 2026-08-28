# Avaliação: skills de vendas no GitHub

Busca feita em 28/08/2026. Objetivo: encontrar empresas e fazer contato oferecendo
serviços de sistemas. Avaliei 5 candidatos, instalei 2 e escrevi 2 do zero.

---

## Resumo da decisão

| Repositório | ⭐ | Veredito | Motivo |
|---|---|---|---|
| [zubair-trabzada/ai-sales-team-claude](https://github.com/zubair-trabzada/ai-sales-team-claude) | ~1,1k | ✅ **Instalado (núcleo)** | Único que cobre o ciclo inteiro e roda sem API paga |
| [LeadMagic/gtm-skills](https://github.com/LeadMagic/gtm-skills) | — | ✅ **Instalado (6 de 206)** | Copy e entregabilidade são excelentes; o resto é excesso |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | ~46k | ❌ Descartado | É marketing (SEO, CRO, conteúdo), não prospecção ativa |
| [ComposioHQ lead-research-assistant](https://github.com/ComposioHQ/awesome-claude-skills/tree/master/lead-research-assistant) | — | ❌ Descartado | ~40 linhas, sem metodologia. Coberto por `sales-icp` |
| [wondelai/skills](https://github.com/wondelai/skills), [gtmagents/gtm-agents](https://github.com/gtmagents/gtm-agents) | ~2k | ❌ Descartado | Genéricos, framework de livro de negócios sem execução |

Ponto de partida da busca: [awesome-growth-hacking-skills](https://github.com/mikiarlo3/awesome-growth-hacking-skills),
que é o melhor índice curado da categoria hoje. Vale acompanhar, não instalar.

Ambos os instalados são **MIT**, então estão vendorizados em `.claude/skills/` com atribuição.

---

## Por que o `ai-sales-team` ganhou

Cobre exatamente o que você pediu — buscar empresa e entrar em contato — em 14 skills que
se encaixam: `sales-icp` → `sales-research` → `sales-qualify` (BANT/MEDDIC) → `sales-contacts`
→ `sales-outreach` → `sales-followup` → `sales-prep` → `sales-proposal` → `sales-objections`.
`/sales prospect <url>` roda 5 subagentes em paralelo e entrega um relatório pontuado com
e-mail pronto.

O que mais pesou: **não depende de nenhuma API paga**. Roda com `WebFetch`/`WebSearch` e
Python stdlib. Os concorrentes assumem Apollo, ZoomInfo ou Clay — assinaturas em dólar que
só fazem sentido com time de SDR. As instruções são específicas de verdade (tabelas de
detecção, critérios de pontuação, regras de erro), não prompts vagos.

### Defeito que corrigi

As 14 skills foram publicadas **sem frontmatter YAML**. Sem `name` e `description`, o Claude
Code não descobre skill nenhuma — instaladas pelo `install.sh` oficial, elas simplesmente não
carregam. Escrevi o frontmatter das 14, em português, com gatilhos de ativação adaptados ao
seu uso. Vale reportar upstream.

### O que testei

- `lead_scorer.py` — funciona. Com entrada bem formada devolveu BANT 60 e MEDDIC 88. O
  schema de entrada é aninhado (`budget_signals`, `authority_signals`, `need_signals`,
  `timeline_signals`); JSON plano devolve zero em tudo, sem avisar.
- `contact_finder.py` / `analyze_prospect.py` — CLI válida, mas **não consegui testar a
  busca real**: a política de rede desta sessão bloqueia requisição direta a site externo
  (403 no proxy). Rodam normalmente na sua máquina.
- Lendo o código do `contact_finder.py`, achei um problema: a linha 85 captura
  `except (URLError, OSError, Exception)` e engole qualquer erro em silêncio. Se o site
  bloquear ou cair, você recebe `{"contacts": [], "errors": []}` — resultado vazio sem
  explicação. Se ele vier vazio, teste a URL no navegador antes de concluir que a empresa
  não tem página de equipe.

### Limitações que permanecem

- Tudo em inglês, e a copy gerada sai em inglês por padrão. Peça em português explicitamente.
- `sales-contacts` procura "VP of Engineering" e "Head of Growth". Na PME brasileira o
  decisor é o sócio — resolvido pela `prospeccao-br`.
- `sales-research` busca Crunchbase e SEC filings, que não cobrem empresa brasileira.
- `sales-report-pdf` precisa de `reportlab` (`pip install reportlab beautifulsoup4 requests`).

---

## O que peguei do `gtm-skills`

206 skills é excesso — metade é sobre contratar SDR, SOC2 e captação com VC. Peguei 6:

| Skill | Por quê |
|---|---|
| `gtm-cold-email-copywriting` | Framework de 3 linhas e padrões de assunto, melhores que os do núcleo |
| `gtm-email-deliverability` | SPF/DKIM/DMARC e aquecimento de domínio. **Leia antes do primeiro disparo** |
| `gtm-multi-channel-outreach` | Coordenação e-mail + telefone + social |
| `gtm-reply-handling` | Taxonomia de 8 tipos de resposta e o que fazer com cada |
| `gtm-lead-finding` | Metodologia multi-fonte (as fontes são americanas, o método serve) |
| `gtm-signal-scoring` | Priorização por sinal de compra |

---

## As duas que faltavam, e que escrevi

Nenhum repositório da categoria cobre Brasil. Duas skills novas fecham isso:

**`prospeccao-br`** — descoberta de contas com fontes que funcionam aqui: BrasilAPI/CNPJ
(o **QSA dá o nome do sócio decisor**, que é o que `sales-contacts` não acha), Google Maps
para PME local, Instagram por hashtag e nicho, vagas no Gupy como sinal de crescimento,
associações setoriais, PNCP, Reclame Aqui como dor documentada. Mais rubrica de pontuação
0-100 e formato de lista com proveniência por linha.

**`abordagem-br`** — cold outreach em português: base legal da LGPD (legítimo interesse,
art. 7º IX) com as 6 contrapartidas que ela exige, escolha de canal (e-mail sempre primeiro;
WhatsApp só em número comercial público e nunca como abertura), o que muda na copy em
português, cadência de 5 toques em 3 semanas e horários de melhor resposta no Brasil.

---

## Como usar

```bash
pip install reportlab beautifulsoup4 requests   # só para o relatório em PDF
```

```
1. /sales icp                          # define o cliente ideal (uma vez)
2. "acha 20 <segmento> em <cidade>"    # prospeccao-br monta a lista
3. /sales prospect <url>               # análise completa de quem pontuou ≥ 70
4. "escreve a abordagem pra esse lead" # abordagem-br, em português e com LGPD
5. /sales followup                     # cadência de quem não respondeu
6. /sales report                       # estado do pipeline
```

**Antes do primeiro disparo em volume**, leia `gtm-email-deliverability` e configure
SPF/DKIM/DMARC no domínio. Disparar sem isso manda tudo para spam e queima o domínio —
e o domínio queimado leva meses para recuperar.

---

## Vantagem que você já tem

O produto deste repositório (relatório de Instagram por R$ 67 com upsell de agência) é uma
**isca de diagnóstico**: você chega no prospect com uma análise concreta do Instagram dele em
vez de um pitch, o relatório barato qualifica orçamento e intenção antes de gastar hora de
reunião, e quem compra e gosta vira lead morno para o serviço de sistemas.

Isso é melhor porta de entrada do que qualquer template de cold email. A sequência
diagnóstico → relatório → serviço está detalhada na Fase 5 da `abordagem-br`.

---

## Crédito

- `sales*` — [ai-sales-team-claude](https://github.com/zubair-trabzada/ai-sales-team-claude), MIT © 2026 Zubair Trabzada
- `gtm-*` — [gtm-skills](https://github.com/LeadMagic/gtm-skills), MIT © 2026 LeadMagic LLC
- `prospeccao-br`, `abordagem-br` — originais deste repositório
