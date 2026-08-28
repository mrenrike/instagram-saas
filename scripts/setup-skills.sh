#!/usr/bin/env bash
# Disponibiliza as skills de vendas deste repo para Claude Code e Antigravity.
#
# Fonte única: .claude/skills/  — todo o resto é link (ou cópia, se link não der).
# Nunca edite as cópias: rode este script de novo depois de mexer na fonte.
#
#   ./scripts/setup-skills.sh                 # workspace: Claude Code + Antigravity
#   ./scripts/setup-skills.sh --global        # + instala no Antigravity do usuário
#   ./scripts/setup-skills.sh --legacy        # usa .agent/skills (Antigravity antigo)
#   ./scripts/setup-skills.sh --check         # só verifica, não escreve
#   ./scripts/setup-skills.sh --uninstall     # remove o que este script criou

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/.claude/skills"
GLOBAL_AGY="$HOME/.gemini/antigravity/skills"

WS_DIR="$ROOT/.agents/skills"
DO_GLOBAL=0; CHECK=0; UNINSTALL=0
for a in "$@"; do case "$a" in
  --global)    DO_GLOBAL=1 ;;
  --legacy)    WS_DIR="$ROOT/.agent/skills" ;;
  --check)     CHECK=1 ;;
  --uninstall) UNINSTALL=1 ;;
  -h|--help)   sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "opção desconhecida: $a" >&2; exit 2 ;;
esac; done

G="\033[32m"; Y="\033[33m"; R="\033[31m"; D="\033[2m"; N="\033[0m"
ok(){ printf "  ${G}✓${N} %s\n" "$1"; }
warn(){ printf "  ${Y}!${N} %s\n" "$1"; }
err(){ printf "  ${R}✗${N} %s\n" "$1"; }

[ -d "$SRC" ] || { err "não achei $SRC — rode a partir do repositório"; exit 1; }
SKILLS=(); for d in "$SRC"/*/; do [ -f "$d/SKILL.md" ] && SKILLS+=("$(basename "$d")"); done
[ ${#SKILLS[@]} -gt 0 ] || { err "nenhuma skill com SKILL.md em $SRC"; exit 1; }

if [ "$UNINSTALL" = 1 ]; then
  echo "Removendo:"
  for p in "$ROOT/.agents/skills" "$ROOT/.agent/skills"; do
    [ -e "$p" ] && { rm -rf "$p"; ok "$p"; }
  done
  for s in "${SKILLS[@]}"; do
    p="$GLOBAL_AGY/$s"
    [ -L "$p" ] && { rm -f "$p"; ok "$p"; }
    [ -d "$p" ] && [ -f "$p/.from-instagram-saas" ] && { rm -rf "$p"; ok "$p"; }
  done
  echo "A fonte em .claude/skills/ não foi tocada."
  exit 0
fi

# Espelha $1 em $2: symlink quando possível, cópia como fallback (Windows sem symlink).
mirror() {
  local from="$1" to="$2" label="$3"
  if [ "$CHECK" = 1 ]; then
    if [ -L "$to" ]; then ok "$label (link)"
    elif [ -d "$to" ]; then
      if diff -rq "$from" "$to" >/dev/null 2>&1; then ok "$label (cópia em dia)"
      else warn "$label (cópia DESATUALIZADA — rode sem --check)"; DRIFT=1; fi
    else warn "$label (ausente)"; DRIFT=1; fi
    return
  fi
  rm -rf "$to"; mkdir -p "$(dirname "$to")"
  if ln -s "$from" "$to" 2>/dev/null; then ok "$label (link)"
  else
    cp -r "$from" "$to"; : > "$to/.from-instagram-saas"
    ok "$label (cópia — symlink indisponível)"
  fi
}

DRIFT=0
echo
echo "Skills encontradas em .claude/skills/: ${#SKILLS[@]}"
echo
echo "Claude Code (workspace)"
ok ".claude/skills/ — é a fonte, nada a fazer"
[ -d "$ROOT/.claude/agents" ] && ok ".claude/agents/ — $(ls "$ROOT/.claude/agents"/*.md 2>/dev/null | wc -l | tr -d ' ') subagentes"

echo
echo "Antigravity / Gemini / Codex (workspace → $(basename "$(dirname "$WS_DIR")")/skills)"
for s in "${SKILLS[@]}"; do mirror "$SRC/$s" "$WS_DIR/$s" "$s"; done

if [ "$DO_GLOBAL" = 1 ]; then
  echo
  echo "Antigravity do usuário ($GLOBAL_AGY)"
  mkdir -p "$GLOBAL_AGY"
  for s in "${SKILLS[@]}"; do mirror "$SRC/$s" "$GLOBAL_AGY/$s" "$s"; done
fi

echo
if [ "$CHECK" = 1 ]; then
  [ "$DRIFT" = 0 ] && { echo "Tudo em dia."; exit 0; }
  echo "Há diferenças. Rode: ./scripts/setup-skills.sh"; exit 1
fi
echo "Pronto. Antigravity: reabra o workspace para ele reindexar as skills."
echo -e "${D}Editou algo em .claude/skills/? Rode este script de novo.${N}"
