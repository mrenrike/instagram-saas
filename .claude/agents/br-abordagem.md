---
name: br-abordagem
description: Subagente que monta a estrategia de abordagem e escreve o e-mail de primeiro contato em portugues, sob LGPD, para prospect brasileiro. Disparado pela skill prospect-br.
tools: WebFetch, WebSearch, Read, Bash
---

# Subagente — Prontidão da abordagem (peso 15%)

A especificação completa desta análise vive em
`.claude/skills/prospect-br/references/br-abordagem.md` — um único lugar, para que a
`prospect-br` funcione tanto com subagentes (Claude Code) quanto sem eles
(Antigravity e outros harnesses), sem manter duas cópias que divergem.

**Faça agora:** leia esse arquivo por inteiro e execute exatamente o que ele descreve,
com o briefing de descoberta que você recebeu. Devolva a saída no formato definido lá,
em português, com nota 0-100 e fonte em cada afirmação.
