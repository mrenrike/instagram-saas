#!/usr/bin/env python3
"""Valida as skills de vendas antes de commitar.

Pega o que quebra silenciosamente: frontmatter que impede a skill de carregar,
e link para arquivo que não existe (o agente tenta ler e falha no meio da tarefa).

    python3 scripts/check-skills.py          # sai 1 se achar problema
    python3 scripts/check-skills.py -q       # só o resumo
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS, AGENTS = ROOT / ".claude/skills", ROOT / ".claude/agents"
QUIET = "-q" in sys.argv
REF = re.compile(r'`((?:references|scripts|templates|assets)/[\w./-]+\.\w+)`')
ABS = re.compile(r'`(\.claude/[\w./-]+\.\w+)`')

problemas = []


def frontmatter(path):
    """(dados, erro). Usa PyYAML quando disponível; senão, parser próprio."""
    txt = path.read_text(encoding="utf-8")
    if not txt.startswith("---"):
        return None, "sem frontmatter YAML — o harness não vai descobrir esta skill"
    try:
        bloco = txt.split("---", 2)[1]
    except IndexError:
        return None, "frontmatter não fechado"
    try:
        import yaml
        d = yaml.safe_load(bloco)
        if not isinstance(d, dict):
            return None, "frontmatter não é um mapa de chave/valor"
        return {k: str(v) for k, v in d.items()}, None
    except ImportError:
        pass
    except Exception as e:
        return None, f"YAML inválido: {e}"
    # Sem PyYAML: parser próprio. Só o nível raiz interessa (name, description);
    # blocos aninhados como 'metadata:' são pulados, não são erro.
    dados, chave, buf = {}, None, []
    def fechar():
        if chave:
            dados[chave] = " ".join(buf).strip()
    for linha in bloco.splitlines():
        indentada = linha.startswith((" ", "\t"))
        if not linha.strip():
            if chave: buf.append("")
            continue
        if indentada:
            if chave: buf.append(linha.strip())   # continuação de escalar de bloco
            continue                              # senão: filho de mapa aninhado, ignora
        if m := re.match(r'^(\w[\w-]*):\s*(.*)$', linha):
            fechar()
            valor = m.group(2).strip()
            if valor in (">", ">-", ">+", "|", "|-", "|+"):
                chave, buf = m.group(1), []       # abre escalar de bloco
            else:
                chave, buf = None, []
                if valor:
                    dados[m.group(1)] = valor.strip('"\'')
        elif not linha.startswith(("-", "#")):
            return None, f"linha inválida no frontmatter: {linha!r}"
    fechar()
    return dados, None


def checar_frontmatter(path, rotulo):
    dados, erro = frontmatter(path)
    if erro:
        problemas.append(f"{rotulo}: {erro}")
        return
    desc = dados.get("description", "").strip('"\'')
    if not desc:
        problemas.append(f"{rotulo}: falta 'description' — obrigatório em Claude Code e Antigravity")
    elif len(desc) > 1024:
        problemas.append(f"{rotulo}: description com {len(desc)} chars (limite 1024)")
    elif not QUIET and len(desc) < 40:
        print(f"  aviso  {rotulo}: description curta ({len(desc)} chars) — pode não ativar bem")


def checar_links(path, base_skill):
    txt = path.read_text(encoding="utf-8")
    rotulo = path.relative_to(ROOT)
    for ref in REF.findall(txt):
        if not (base_skill / ref).exists() and not (path.parent / ref).exists():
            problemas.append(f"{rotulo}: link quebrado → {ref}")
    for ref in ABS.findall(txt):
        if not (ROOT / ref).exists():
            problemas.append(f"{rotulo}: link quebrado → {ref}")


if not SKILLS.is_dir():
    sys.exit(f"não achei {SKILLS}")

skills = sorted(d for d in SKILLS.iterdir() if (d / "SKILL.md").is_file())
for d in skills:
    checar_frontmatter(d / "SKILL.md", f"skill {d.name}")
    for md in d.rglob("*.md"):
        checar_links(md, d)

agentes = sorted(AGENTS.glob("*.md")) if AGENTS.is_dir() else []
for a in agentes:
    checar_frontmatter(a, f"agente {a.stem}")
    checar_links(a, AGENTS)

orfas = [d.name for d in SKILLS.iterdir() if d.is_dir() and not (d / "SKILL.md").is_file()]
for o in orfas:
    problemas.append(f"pasta {o}/ sem SKILL.md — não será carregada")

print(f"\n{len(skills)} skills · {len(agentes)} agentes")
if problemas:
    print(f"\n{len(problemas)} problema(s):")
    for p in problemas:
        print(f"  ✗ {p}")
    sys.exit(1)
print("Tudo válido.")
