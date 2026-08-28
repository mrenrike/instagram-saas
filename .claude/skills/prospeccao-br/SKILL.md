---
name: prospeccao-br
description: Encontra e qualifica empresas brasileiras para prospeccao B2B usando fontes publicas nacionais (CNPJ/BrasilAPI, Google Maps, Instagram, portais setoriais, vagas de emprego, licitacoes). Use quando o pedido for "buscar empresas no Brasil", "montar lista de leads", "achar clientes em <cidade/setor>", ou antes de rodar sales-prospect em um alvo brasileiro.
license: MIT
---

# Prospecção B2B no Brasil

As skills `sales-*` e `gtm-*` deste repositório foram escritas para o mercado americano: assumem
Crunchbase, ZoomInfo, Apollo, LinkedIn Sales Navigator e SEC filings. Nenhuma dessas fontes cobre
bem a PME brasileira. Esta skill substitui a etapa de **descoberta de contas** por fontes que
realmente funcionam no Brasil, e depois entrega o alvo para `sales-research` / `sales-qualify`.

## Quando usar

- "Acha 20 empresas de X em Y" / "monta uma lista de prospecção"
- "Quem no Brasil precisaria disso?"
- Antes de `sales-prospect`, quando o alvo é uma empresa brasileira e a pesquisa em inglês volta vazia

Não use para: analisar UMA empresa já conhecida (use `sales-research`), escrever a abordagem
(use `abordagem-br`), ou definir o ICP (use `sales-icp`).

---

## Fase 1 — Traduzir o ICP em critérios buscáveis

Antes de buscar, converta o ICP (de `docs/vendas/ICP.md` ou de `sales-icp`) em filtros concretos:

| Dimensão | Como fica buscável no Brasil |
|---|---|
| Setor | CNAE principal (ex.: 4781-4/00 comércio varejista de vestuário) |
| Porte | Faixa de funcionários, capital social, Simples/Lucro Presumido/Real |
| Região | UF + município (concentre: prospecção pulverizada não escala) |
| Maturidade digital | Tem site? e-commerce? Instagram ativo? usa qual plataforma? |
| Sinal de dor | Vaga aberta, reclamação recorrente, site quebrado, sem CRM |

Registre esses critérios no topo da lista de saída — sem isso a lista vira ruído.

---

## Fase 2 — Fontes de descoberta (use 3+ em combinação)

Fonte única gera lista enviesada. Cruze pelo menos três.

### 2.1 Google Maps / Places — melhor fonte para PME local
Busque `"<segmento>" "<cidade>"` e extraia: nome, endereço, telefone, site, nota, nº de avaliações.
- **Sinal de dor forte:** nota < 4.0 com muitas avaliações, ou site ausente/quebrado.
- **Sinal de porte:** nº de avaliações é o melhor proxy grátis de volume de clientes.
- Cobre exatamente o perfil que compra serviço de sistemas: comércio, clínica, escritório, academia.

### 2.2 Dados públicos de CNPJ
Use `WebFetch` nas APIs abertas para enriquecer qualquer empresa que já tenha nome ou CNPJ:
- `https://brasilapi.com.br/api/cnpj/v1/{cnpj}` — razão social, CNAE, sócios (QSA), capital social, data de abertura, situação cadastral, endereço, telefone, e-mail.
- `https://publica.cnpj.ws/cnpj/{cnpj}` — alternativa.

O **QSA (quadro societário)** é ouro: dá o nome real do decisor da PME, que é quase sempre o sócio.
`sales-contacts` procura "VP of Engineering"; na PME brasileira o decisor é o sócio-administrador.

- Empresa aberta há < 3 anos → em estruturação, compra sistema pela primeira vez.
- Capital social e CNAE secundários → indicam porte e diversificação real.
- **Situação cadastral ≠ ATIVA → descarte imediato.** Não gaste toque com baixada/inapta.

### 2.3 Instagram — sua vantagem injusta
Este repositório É um produto de analytics de Instagram. Use isso como fonte E como isca:
- Busque por hashtag de nicho + localização, e por quem segue concorrentes seus.
- Qualifique pelo próprio critério do produto: frequência de post, formato dominante,
  engajamento por seguidor, se responde comentários, se tem link na bio, se anuncia.
- **Perfil com bom volume de seguidores e engajamento ruim = lead quente**: dor visível,
  e você tem o diagnóstico pronto (o relatório de R$67) como porta de entrada.

### 2.4 Vagas de emprego — sinal de crescimento e de dor técnica
Gupy, Vagas.com, InfoJobs, Catho, LinkedIn Jobs.
- Vaga de dev/TI numa empresa não-tech → vai construir algo internamente: ofereça antes.
- Muitas vagas operacionais repetidas → processo manual que dá para automatizar.
- Vaga de social media / marketing → orçamento de marketing existe e está sendo alocado agora.

### 2.5 Portais setoriais e associações
Associações comerciais, sindicatos patronais, CDLs, catálogos de feiras, ABF (franquias),
ABComm (e-commerce). Listas de associados são listas de ICP já segmentadas e públicas.

### 2.6 Licitações e contratos públicos (se atender governo)
Portal Nacional de Contratações Públicas (PNCP), ComprasNet, portais de transparência estaduais.
Empresas que já venderam para o governo têm capacidade fiscal e processo comercial formalizado.

### 2.7 Reclame Aqui — dor documentada
Reclamações recorrentes sobre atendimento, prazo ou rastreio são casos de uso literais para
sistema/automação. Cite a *categoria* da dor na abordagem, nunca a reclamação específica —
mencionar reclamação nominal soa como chantagem e queima o lead.

---

## Fase 3 — Deduplicar e pontuar

Deduplique por CNPJ (não por nome — filiais e nomes fantasia se repetem).

Pontue 0-100. Sugestão de pesos, ajuste conforme feedback real do pipeline:

| Critério | Peso | Ponto máximo quando |
|---|---|---|
| Fit de CNAE/setor com o ICP | 25 | Setor central do ICP |
| Porte compatível com o ticket | 20 | Consegue pagar sem virar caso de exceção |
| Sinal de dor observável | 25 | Dor visível e datada (vaga, nota baixa, site quebrado) |
| Acessibilidade do decisor | 15 | Sócio identificado no QSA com contato público |
| Recência do gatilho | 15 | Últimos 90 dias |

- **≥ 70** → prospecção personalizada, vale `/sales prospect`
- **40-69** → cadência semi-personalizada em lote
- **< 40** → fora da lista. Não "tente mesmo assim": lista ruim destrói entregabilidade.

---

## Fase 4 — Saída

Grave em `docs/vendas/listas/<segmento>-<cidade>-<AAAA-MM>.md`:

```markdown
# Lista: <segmento> — <cidade> — <mês/ano>
Critérios de ICP aplicados: <...>
Fontes cruzadas: <...>
Gerada em: <data>

| # | Empresa | CNPJ | Decisor (QSA) | Contato público | Score | Gatilho / dor | Fonte |
|---|---------|------|---------------|-----------------|-------|---------------|-------|
```

Sempre registre **fonte e data por linha**. Sem proveniência não dá para auditar a lista depois,
e a LGPD exige que você saiba de onde veio cada dado (ver `abordagem-br`).

## Regras que não se quebram

1. **Só dado público e de contato profissional.** Nada de raspar dado pessoal de pessoa física,
   burlar login, ou comprar lista pronta de origem desconhecida.
2. **Respeite robots.txt e o termo de uso de cada fonte.** Volume alto de scraping em plataforma
   que proíbe é risco jurídico e de bloqueio, não é "growth".
3. **Situação cadastral ativa é pré-requisito**, sempre.
4. Prefira listas pequenas e certeiras. 30 contas bem pesquisadas convertem mais que 3.000 frias.
