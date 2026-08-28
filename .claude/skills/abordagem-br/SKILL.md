---
name: abordagem-br
description: Escreve abordagem fria (cold outreach) para empresas brasileiras em portugues — e-mail, WhatsApp, Instagram DM e LinkedIn — com tom e cadencia que funcionam no Brasil e conformidade com a LGPD. Use quando o pedido for "escreve o e-mail pra esse lead", "monta a cadencia", "manda mensagem pra essa empresa", ou depois de rodar prospeccao-br.
license: MIT
---

# Abordagem fria no Brasil

`sales-outreach` e `gtm-cold-email-copywriting` têm bons frameworks de copy, mas assumem
inbox americana: e-mail como canal único, tom direto de SDR, referências a funding rounds.
No Brasil o canal dominante é WhatsApp, a relação é mais pessoal e a LGPD é mais restritiva
que o CAN-SPAM. Esta skill adapta a copy; use os frameworks daquelas skills como base.

## Fase 1 — LGPD antes da copy

Prospecção B2B fria **é legal** no Brasil, mas com condições. Não pule esta fase.

**Base legal:** legítimo interesse (Lei 13.709/2018, art. 7º, IX) para contato profissional
B2B. Isso NÃO é consentimento — é uma base própria, e ela exige contrapartidas:

1. **Dado profissional público apenas.** E-mail comercial no site, telefone da empresa,
   perfil corporativo. Nunca WhatsApp pessoal, CPF, ou dado de pessoa física obtido fora
   do contexto profissional.
2. **Proveniência registrada.** Você precisa saber e conseguir provar de onde veio cada
   contato. `prospeccao-br` já exige fonte + data por linha — mantenha.
3. **Identificação clara.** Toda mensagem diz quem é você, qual empresa, e por que está
   falando com aquela pessoa especificamente.
4. **Opt-out em todo toque, e que funcione.** Uma frase basta: "Se não fizer sentido, me
   avisa que eu não te procuro mais." Honre em 100% dos casos, imediatamente e para sempre.
5. **Direito do titular.** Se pedirem acesso, correção ou exclusão dos dados, atenda.
   Mantenha um canal (o e-mail de contato do rodapé serve) e uma lista de supressão.
6. **Sem dado sensível.** Nunca use saúde, opinião política, religião ou origem racial
   como critério de segmentação ou como gancho.

**Lista de supressão:** quem pediu para sair entra em `docs/vendas/supressao.md` e nunca
mais é contatado — nem em campanha nova, nem por outro canal, nem "só uma última vez".

## Fase 2 — Escolha de canal

| Canal | Quando usar | Cuidado |
|---|---|---|
| **E-mail** | Sempre. É o canal com base legal mais sólida e mais escalável. | Sem infraestrutura (SPF/DKIM/DMARC, aquecimento), vai para spam. Ver `gtm-email-deliverability`. |
| **WhatsApp Business** | Só em número comercial divulgado publicamente pela empresa. | Número pessoal = não. Volume alto de frio = banimento. Trate como canal de 2º toque, não de 1º. |
| **Instagram DM** | Forte quando você vende serviço ligado a Instagram — é o seu caso. | Limite baixo de volume. Vale por ser altamente contextual, não por escala. |
| **LinkedIn** | Decisor de empresa média/grande, cargo formal. | Cobertura fraca em PME e em cidade do interior. |
| **Telefone** | Melhor canal para PME brasileira, e o mais subutilizado. | Exige roteiro. Ligue depois do e-mail, não antes. |

Regra: **primeiro toque por e-mail**, sempre. Os outros canais entram como reforço depois,
nunca como abertura fria — abertura fria em WhatsApp queima o número e a marca.

## Fase 3 — Copy que funciona em português

### O que muda em relação ao template americano

- **Sem "I hope this email finds you well".** O equivalente traduzido ("Espero que esteja
  bem") também não. Vá direto.
- **Você, não senhor.** Formalidade excessiva soa a cobrança ou a golpe.
- **Sem jargão importado.** "Alavancar sinergias", "dor latente", "solução end-to-end" —
  fora. Fale como um fornecedor competente falaria numa reunião.
- **Prova social local pesa mais.** "Trabalho com 3 clínicas aqui em [cidade]" vale mais
  que qualquer métrica genérica.
- **Preço cedo, não tarde.** Brasileiro desconfia de proposta sem número. Uma faixa já no
  primeiro ou segundo toque filtra melhor do que esconder até a reunião.
- **Sem urgência falsa.** "Últimas vagas", "só até sexta" em cold outreach mata a
  credibilidade. Se a urgência é real, explique por quê.

### Estrutura do primeiro e-mail (máx. 90 palavras)

```
Assunto: [algo concreto e específico do negócio dele, 4-6 palavras, sem clickbait]

[Nome],

[1 frase: a observação específica que motivou o contato — o que você viu, com dado.]
[1 frase: o que isso costuma custar/limitar em negócios parecidos.]
[1 frase: o que você faz, em linguagem de resultado, com faixa de preço ou de prazo.]
[1 pergunta de baixo atrito — não "tem 15 minutos?", e sim algo que se responde em 1 linha.]

[Assinatura: nome, empresa, site, telefone]
Se não fizer sentido, me avisa que eu não te procuro mais.
```

**A primeira frase é o teste.** Se ela pudesse ser enviada para qualquer outra empresa da
lista, você não pesquisou o suficiente — volte para `prospeccao-br` ou `sales-research`.

### Exemplo aplicado (venda de sistema/automação)

> **Assunto:** pedidos da [Empresa] pelo WhatsApp
>
> Oi [Nome],
>
> Vi que a [Empresa] recebe os pedidos pelo WhatsApp e que vocês estão com duas vagas
> abertas de atendimento no Gupy. Nas distribuidoras com que trabalho, esse fluxo manual
> costuma consumir ~3h/dia de alguém e é onde nasce a maior parte dos erros de pedido.
>
> Eu monto o sistema que recebe o pedido, joga no estoque e emite a nota — projetos assim
> ficam entre R$ X e R$ Y, de 4 a 6 semanas.
>
> Faz sentido pra vocês hoje, ou o pedido manual ainda dá conta?
>
> [assinatura]
> Se não fizer sentido, me avisa que eu não te procuro mais.

Note: a pergunta final oferece uma saída honesta. Isso aumenta resposta — inclusive "não",
que é resposta útil e limpa o pipeline.

## Fase 4 — Cadência

5 toques em 3 semanas. Cada toque traz **ângulo novo**, nunca "só dando um up".

| # | Dia | Canal | Conteúdo |
|---|-----|-------|----------|
| 1 | 0 | E-mail | Observação específica + oferta com faixa de preço |
| 2 | 3 | E-mail | Prova: caso parecido, com número real e verificável |
| 3 | 7 | Telefone ou WhatsApp comercial | Referência ao e-mail, 40 segundos |
| 4 | 12 | E-mail | Conteúdo útil sem pedir nada (diagnóstico, checklist) |
| 5 | 21 | E-mail | Encerramento: "vou parar por aqui, me chama se mudar" |

O toque 5 fecha o loop de verdade — e é, na prática, o que mais gera resposta.
Depois dele, o lead sai da cadência. Reengaje só com gatilho novo e real.

**Horário:** terça a quinta, 8h-10h ou 14h-16h (horário de Brasília). Segunda de manhã e
sexta à tarde têm a pior taxa de resposta.

## Fase 5 — Seu gancho específico

Este repositório vende relatório de analytics de Instagram (R$ 67) com upsell de agência.
Isso é uma **isca de diagnóstico** — o melhor tipo de primeiro toque que existe:

- Você chega com um diagnóstico concreto do Instagram do prospect, não com um pitch.
- O relatório barato qualifica orçamento e intenção antes de você gastar hora de reunião.
- Quem compra R$ 67 e gosta é lead qualificado para o serviço de sistemas, com confiança
  já estabelecida — a venda maior deixa de ser fria.

Use essa sequência: diagnóstico gratuito no e-mail 1 → relatório pago → serviço.
Não pule direto para o serviço de sistemas em cima de um contato frio.

## Regras que não se quebram

1. **Nunca invente dado.** Métrica, caso de cliente ou nome inventado destrói a venda no
   momento em que o lead confere. Se não pesquisou, não afirme.
2. **Personalização verificável em todo primeiro toque.** Sem exceção.
3. **Opt-out honrado imediatamente**, em qualquer canal, para sempre.
4. **Volume baixo e constante** > rajada. Rajada queima domínio e número.
5. **Não se passe por outra pessoa ou empresa**, e não use remetente enganoso.
