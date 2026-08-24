#!/usr/bin/env bash
# Instala a skill `security-baseline` para que ela valha por padrão.
#
#   ./security-baseline/install.sh             # em ~/.claude/skills — vale para todos
#                                              # os projetos desta máquina
#   ./security-baseline/install.sh --project   # em .claude/skills deste repositório —
#                                              # versionado, vale para a equipe toda
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="security-baseline"

if [[ "${1:-}" == "--project" ]]; then
  REPO_ROOT="$(cd "$SOURCE_DIR/.." && pwd)"
  TARGET="$REPO_ROOT/.claude/skills/$SKILL_NAME"
  SCOPE="este repositório"
else
  TARGET="$HOME/.claude/skills/$SKILL_NAME"
  SCOPE="todos os projetos de $USER nesta máquina"
fi

if [[ ! -f "$SOURCE_DIR/skill/SKILL.md" ]]; then
  echo "erro: $SOURCE_DIR/skill/SKILL.md não encontrado" >&2
  exit 1
fi

mkdir -p "$TARGET"
cp "$SOURCE_DIR/skill/SKILL.md" "$TARGET/SKILL.md"
cp "$SOURCE_DIR/README.md" "$TARGET/REFERENCE.md"

echo "✅ Skill '$SKILL_NAME' instalada em:"
echo "   $TARGET"
echo
echo "   Escopo: $SCOPE"
echo
echo "A partir da próxima sessão do Claude Code, o baseline de 20 itens é aplicado"
echo "por padrão em endpoints, formulários, uploads, login, checkout, webhooks,"
echo "migrations e configuração de deploy."
echo
echo "Para remover:  rm -rf \"$TARGET\""
