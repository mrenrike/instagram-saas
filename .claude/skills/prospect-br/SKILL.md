---
name: prospect-br
description: Analise completa de um prospect brasileiro a partir de site, nome+cidade, CNPJ ou @instagram. Consulta dados publicos de CNPJ (QSA, CNAE, situacao cadastral), mapeia o socio decisor, qualifica a oportunidade e gera a abordagem em portugues com LGPD. Use para "analisa essa empresa", "vale a pena prospectar X", "pesquisa esse lead" quando o alvo for empresa brasileira. Versao nacional da sales-prospect.
license: MIT
---

# Análise de prospect — Brasil

Versão brasileira da `sales-prospect`. Mesma arquitetura (descoberta → 5 subagentes em
paralelo → síntese pontuada), com quatro mudanças que a original não comporta:

1. **Aceita alvo sem site.** A original exige URL e aborta se o site não carrega. A maior
   parte da PME brasileira não tem site — tem Instagram e ficha no Google Maps. Aqui isso
   é caminho normal, não erro.
2. **CNPJ como espinha dorsal.** Razão social, CNAE, capital social, data de abertura,
   situação cadastral e **QSA** vêm de fonte pública e oficial. Nada disso é inferência.
3. **O decisor é o sócio.** A original procura "VP of Engineering". Na PME brasileira quem
   assina é o sócio-administrador, e o QSA entrega o nome dele.
4. **Pontuação recalibrada e saída em português**, com R$ e e-mail pronto sob LGPD.

Use `sales-prospect` (original) para alvo estrangeiro. Para alvo brasileiro, use esta.

---

## Fase 0 — Resolver a identidade do alvo

A entrada pode vir em quatro formatos. Normalize antes de qualquer coisa.

| Entrada | O que fazer |
|---|---|
| URL (`site.com.br`) | `WebFetch` na home. Procure CNPJ no rodapé, na política de privacidade ou nos termos de uso — quase todo site brasileiro publica. |
| CNPJ | Caminho mais curto. Vá direto para 0.2. |
| Nome + cidade | `WebSearch` por `"<nome>" "<cidade>" CNPJ`. Confirme a identidade por endereço antes de seguir. |
| `@perfil` do Instagram | Busque site na bio. Sem site, busque o nome comercial + cidade. Se não achar CNPJ, siga assim mesmo — marque `CNPJ: não localizado` e reduza a confiança. |

**Nunca invente um CNPJ, e nunca associe um CNPJ a uma empresa por semelhança de nome.**
Filial, matriz, holding e nome fantasia se confundem o tempo todo. Sem confirmação por
endereço ou por sócio, registre `não confirmado` e siga.

### 0.1 Sem site é caso normal

Se não há site, monte a descoberta com o que existe: ficha do Google Maps (endereço,
telefone, nota, nº de avaliações, fotos, horário), perfil do Instagram, página do Facebook,
cadastro em marketplace, associação setorial. Anote `Site: inexistente` — para quem vende
sistema, **isso é sinal de compra, não obstáculo**.

### 0.2 Consulta de CNPJ (fonte primária)

```
WebFetch https://brasilapi.com.br/api/cnpj/v1/{cnpj}
```
Alternativa se falhar: `https://publica.cnpj.ws/cnpj/{cnpj}`.

Extraia e registre:

| Campo | Para que serve |
|---|---|
| `razao_social`, `nome_fantasia` | Identidade formal vs. como o mercado conhece |
| `descricao_situacao_cadastral` | **Gate rígido — ver abaixo** |
| `cnae_fiscal` + descrição, CNAEs secundários | Setor real e diversificação |
| `data_inicio_atividade` | Maturidade. < 3 anos = compra sistema pela 1ª vez |
| `capital_social` | Proxy de porte, junto com nº de funcionários |
| `qsa[]` (nome + qualificação) | **O decisor.** Sócio-administrador é quem assina |
| `porte`, `opcao_pelo_simples` | Regime tributário e faixa de faturamento |
| `ddd_telefone_1`, `email`, endereço | Contato oficial declarado à Receita |

**Gate rígido:** se a situação cadastral não for `ATIVA` (baixada, inapta, suspensa),
**pare a análise**. Pontuação 0, motivo `situação cadastral: <situação>`, e não passe para
a Fase 2. Prospectar CNPJ inativo é queimar toque e credibilidade.

Se a consulta falhar (API fora, CNPJ inexistente), registre `consulta de CNPJ indisponível`,
reduza a confiança em um nível e continue com fontes abertas.

---

## Fase 1 — Descoberta

### 1.1 Coletar as fontes disponíveis

Do que existir, colete e guarde o conteúdo bruto para os subagentes:
site (home, sobre, serviços/produtos, preços, contato, blog, trabalhe conosco), Google Maps,
Instagram, LinkedIn da empresa, vagas abertas (Gupy, Vagas.com, InfoJobs, LinkedIn Jobs),
Reclame Aqui, notícias locais.

### 1.2 Classificar o tipo de empresa

As categorias da original (SaaS, Startup, Enterprise) quase não ocorrem no seu funil.
Use estas:

| Tipo | Sinais | Foco da análise |
|---|---|---|
| **Comércio local** | Loja física, Maps com avaliações, catálogo no Instagram, venda por WhatsApp | Pedido manual, controle de estoque, emissão de nota, PDV |
| **Clínica / consultório** | CNAE de saúde, agendamento, convênios, corpo clínico | Agenda, prontuário, confirmação de consulta, faturamento de convênio |
| **Serviços profissionais** | Escritório de contabilidade, advocacia, engenharia, arquitetura | Gestão de processos e prazos, portal do cliente, honorários recorrentes |
| **Indústria / distribuidora** | CNAE industrial, catálogo B2B, representantes, galpão | Pedido de representante, integração com ERP, logística, tabela de preço |
| **E-commerce** | Loja virtual, checkout, marketplaces | Plataforma, integração de marketplace, frete, pós-venda |
| **Franquia (franqueado ou franqueadora)** | Marca conhecida, várias unidades, padrão visual | Padronização, consolidação multiunidade, repasse de royalties |
| **Prestador de serviço com agenda** | Academia, salão, oficina, pet shop | Agendamento, recorrência, fidelização, cobrança |
| **Startup / tech** | Produto digital, investidores, blog técnico | Aqui a `sales-prospect` original serve melhor |

### 1.3 Vertical pelo CNAE

Use o CNAE fiscal como fonte da verdade do setor, não o que o site diz. Site fala em
"soluções integradas"; o CNAE diz se é comércio varejista, indústria ou serviço. Quando
divergirem, **registre os dois** — divergência costuma indicar que o negócio mudou e o
cadastro não acompanhou, o que por si só é gancho de conversa.

### 1.4 Extração automatizada (se houver site)

```bash
python3 .claude/skills/sales/scripts/analyze_prospect.py --url <url> --output json
```
Falhou ou não há site: registre `extração automatizada indisponível` e siga com o manual.
O script engole erro de rede em silêncio e devolve resultado vazio — **vazio não prova
ausência**. Confirme no navegador antes de concluir que a empresa não tem página de equipe.

### 1.5 Briefing de descoberta

Monte e passe para todos os 5 subagentes:

```
BRIEFING DE DESCOBERTA
======================
Alvo (como veio): <...>
Razão social / Nome fantasia: <...>
CNPJ: <...>  | Situação cadastral: ATIVA
CNAE principal: <código — descrição>  | Secundários: <...>
Aberta em: <data>  | Capital social: R$ <...>  | Porte: <...>  | Simples: sim/não
QSA: <nome — qualificação>, ...
Tipo de empresa: <categoria da 1.2>
Site: <url ou "inexistente">
Instagram / Maps / LinkedIn: <...>
Conteúdo coletado: <home, sobre, preços, vagas, avaliações...>
Vagas abertas: <...>
Sinais iniciais: <observações da descoberta>
Lacunas: <o que não foi possível obter>
```

---

## Fase 2 — 5 subagentes em paralelo

Dispare simultaneamente, cada um com o briefing completo. Todos respondem **em português**.

| # | Agente | Avalia | Peso |
|---|--------|--------|------|
| 1 | `br-empresa` | Fit da empresa com o ICP | 25% |
| 2 | `br-decisores` | Acesso ao decisor | 25% |
| 3 | `br-oportunidade` | Qualidade da oportunidade (BANT/MEDDIC) | 25% |
| 4 | `br-concorrencia` | Posição competitiva | 10% |
| 5 | `br-abordagem` | Prontidão da abordagem | 15% |

Cada um devolve nota 0-100 na sua dimensão, com justificativa e **fonte por afirmação**.

---

## Fase 3 — Síntese

### 3.1 Falha de subagente

Registre `análise de <dimensão> indisponível — <motivo>`, atribua 50 àquela dimensão,
baixe a confiança em um nível e siga. Nunca invente a dimensão que faltou.

### 3.2 Pontuação (0-100)

```
Score = Fit*0,25 + Decisor*0,25 + Oportunidade*0,25 + Concorrência*0,10 + Abordagem*0,15
```

**Por que os pesos mudaram em relação à original** (25/20/20/15/20): na PME brasileira,
achar o sócio é quase toda a venda — se você não chega no decisor, o resto não importa,
então Decisor sobe para 25%. Posição competitiva cai para 10% porque raramente existe
fornecedor incumbente sofisticado para deslocar: o concorrente real é a planilha e o
WhatsApp, o que o subagente de oportunidade já captura como dor.

| Faixa | Nota | Leitura | Ação |
|---|---|---|---|
| 85-100 | A | Quente | Aborde em 48h, personalizado, com o sócio nominalmente. Vale ligar. |
| 70-84 | B | Forte | Entra na cadência personalizada. Vale a pesquisa profunda. |
| 50-69 | C | Qualificado | Cadência semi-personalizada em lote. Acompanhe gatilhos. |
| 35-49 | D | Morno | Só nutrição. Não force. Reavalie em 60 dias. |
| 0-34 | E | Fora | Descarte. Não "tenta mesmo assim" — lista ruim destrói entregabilidade. |

**Gate:** situação cadastral ≠ ATIVA → E automático, independentemente das notas.

### 3.3 Plano de ação

Três blocos, com ações específicas e verificáveis (nunca "fazer follow-up"):
**48h** (3-5 ações), **2 semanas** (3-5), **1-3 meses** (2-3).

### 3.4 E-mail pronto

Gerado pelo `br-abordagem`, seguindo a skill `abordagem-br`: máx. 90 palavras, primeira
frase com observação específica e verificável, faixa de preço em R$, pergunta de baixo
atrito, assinatura identificando você e a empresa, e opt-out. Dois assuntos para teste.
Destinatário nominal (sócio do QSA), não "prezados".

**Copiável e colável.** Nada de `[inserir aqui]`. Se faltou dado para personalizar,
o problema é a pesquisa — volte, não preencha com placeholder.

### 3.5 Confiança

| Nível | Quando |
|---|---|
| **Alta** | CNPJ consultado e ativo, QSA obtido, 5 subagentes completos, 2+ fontes confirmando |
| **Média** | CNPJ ok, 4 de 5 subagentes, parte por inferência |
| **Baixa** | Sem CNPJ confirmado, ou ≤3 subagentes, ou fonte única |
| **Muito baixa** | Só nome e Instagram. **Pesquise à mão antes de abordar.** |

---

## Saída: `PROSPECCAO-<empresa>.md`

```markdown
# Prospecção: <Nome fantasia> (<Razão social>)

Gerado em: <data> · Confiança: <nível> · **Score: <n>/100 — <nota> (<leitura>)**

## Resumo
<3-4 linhas: quem é, qual a dor, por que agora, qual o próximo passo.>

## Ficha
| | |
|---|---|
| CNPJ | <...> — situação **ATIVA** |
| CNAE | <código — descrição> |
| Aberta em | <data> (<n> anos) |
| Capital social | R$ <...> |
| Porte / Simples | <...> |
| Endereço | <...> |
| Site / Instagram | <...> |

## Notas por dimensão
| Dimensão | Peso | Nota | Justificativa |
|---|---|---|---|
| Fit com o ICP | 25% | <n> | <...> |
| Acesso ao decisor | 25% | <n> | <...> |
| Oportunidade | 25% | <n> | <...> |
| Concorrência | 10% | <n> | <...> |
| Prontidão da abordagem | 15% | <n> | <...> |

## Decisores (QSA + fontes abertas)
| Nome | Qualificação / cargo | Contato público | Gancho de personalização | Fonte |
|---|---|---|---|---|

## Oportunidade
### BANT | ### MEDDIC | ### Sinais de compra | ### Sinais de alerta

## Concorrência
Fornecedor/solução atual detectado, custo de troca, ângulos de posicionamento.

## Abordagem recomendada
Canal e ordem, ganchos de personalização, objeções prováveis com resposta.

## Plano de ação
### 48h | ### 2 semanas | ### 1-3 meses

## E-mail pronto
**Para:** <nome — cargo>  ·  **Assunto A:** <...>  ·  **Assunto B:** <...>
<corpo copiável e colável>

## Lacunas e o que checar à mão
<o que não foi possível confirmar e como confirmar>

## Fontes
<lista com URL e data de acesso>
```

---

## Saída no terminal

```
PROSPECÇÃO — <Nome fantasia>
CNPJ <...> · ATIVA · <CNAE resumido> · <cidade/UF>

  ✓ Empresa e fit com o ICP        <n>/100
  ✓ Acesso ao decisor              <n>/100   <nome do sócio>
  ✓ Oportunidade (BANT/MEDDIC)     <n>/100
  ✓ Concorrência                   <n>/100
  ✓ Prontidão da abordagem         <n>/100

  SCORE <n>/100 — <nota> (<leitura>)
  Ação: <recomendação em uma linha>
  Confiança: <nível>

Relatório: PROSPECCAO-<empresa>.md
```

---

## Tratamento de erro

| Situação | O que fazer |
|---|---|
| Site fora do ar | Tente com/sem `www`, `http`/`https`. Persistindo, siga por Maps + Instagram e registre. **Não aborte.** |
| CNPJ não localizado | Siga com fontes abertas, confiança no máximo Média, e sinalize no relatório. |
| Situação ≠ ATIVA | **Pare.** Score E, motivo registrado. Não gaste subagente. |
| API de CNPJ fora | Tente a alternativa. Falhando as duas, registre e siga. |
| Site só com login | Analise o público (Maps, Instagram, vagas, notícias). Registre a limitação. |
| Empresa sem pegada digital | Diga isso claramente. Confiança Muito baixa e recomendação de ligar antes de escrever. |

## Regras que não se quebram

1. **Fonte por afirmação.** Toda linha do relatório tem origem rastreável. Sem fonte, é
   inferência — e inferência vai rotulada como tal.
2. **Não invente** nome de sócio, número de faturamento, cliente ou métrica. O lead confere,
   e o erro mata a venda no primeiro contato.
3. **Só dado público e profissional.** QSA e CNAE são públicos por lei. Dado pessoal de
   pessoa física fora do contexto profissional, não.
4. **CNPJ inativo é descarte**, não "oportunidade de reativação".
5. O relatório é insumo de decisão comercial, não peça de marketing. Sinal de alerta que
   você encontrou vai no relatório, mesmo quando derruba o score.

## Encadeamento

`prospeccao-br` (lista) → **`prospect-br`** (esta, análise unitária) → `abordagem-br`
(copy e cadência) → `sales-followup` → `sales-prep` → `sales-proposal` → `sales-report`.
