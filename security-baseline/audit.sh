#!/usr/bin/env bash
# Auditoria rápida de um projeto contra o baseline de 20 itens.
#
#   ./security-baseline/audit.sh [caminho-do-projeto]
#
# Cada verificação é uma heurística — grep não entende contexto. Um ⚠️ é "vá olhar",
# não "está errado". A ausência de ⚠️ também não é prova de que está tudo certo.
set -uo pipefail

PROJECT="${1:-.}"
cd "$PROJECT" || { echo "diretório não encontrado: $PROJECT" >&2; exit 1; }

echo "═══ Auditoria de segurança — $(pwd)"
echo

findings=0
note() { printf '  ⚠️  %s\n' "$1"; findings=$((findings + 1)); }
ok()   { printf '  ✅ %s\n' "$1"; }
skip() { printf '  ➖ %s\n' "$1"; }

# Só código-fonte. Além das pastas de dependência e build, o próprio kit é excluído:
# a skill e este script contêm os padrões que procuram, e se casariam consigo mesmos.
src() {
  grep -rIn \
       --exclude-dir={.git,node_modules,.next,dist,build,venv,.venv,__pycache__,.worktrees,security-baseline} \
       --exclude="*.min.js" --exclude="*.map" --exclude=".gitleaks.toml" \
       --exclude="SECURITY.md" --exclude="CLAUDE.md" "$@" . 2>/dev/null
}

# Igual a src(), mas também sem testes: asserções de teste comparam segredos de
# fixture e montam SQL de propósito, e isso não é um achado.
src_app() {
  src --exclude-dir={tests,test,__tests__,spec} --exclude="test_*" --exclude="*_test.*" --exclude="*.test.*" "$@"
}

echo "── Itens 1, 2: segredos"
if [[ -f .gitignore ]] && grep -qE '^\.env$|^\.env$' .gitignore; then
  ok ".env está no .gitignore"
else
  note ".env NÃO está no .gitignore"
fi
if git ls-files 2>/dev/null | grep -qE '(^|/)\.env$'; then
  note ".env está VERSIONADO — rotacione os segredos e remova do índice"
else
  ok "nenhum .env versionado"
fi
if git ls-files 2>/dev/null | grep -q '__pycache__\|\.pyc$'; then
  note "bytecode versionado (git rm -r --cached)"
fi
if src -lE "sk-ant-[A-Za-z0-9_-]{20,}|sk_live_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----" \
     | grep -v example >/dev/null; then
  note "possível segredo no código:"
  src -lE "sk-ant-[A-Za-z0-9_-]{20,}|sk_live_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----" \
    | grep -v example | sed 's/^/       /'
else
  ok "nenhum padrão de segredo óbvio no código"
fi

echo
echo "── Itens 3, 4: banco"
if src -l "service_role" >/dev/null; then
  note "'service_role' aparece no código — confirme que não chega ao cliente:"
  src -l "service_role" | sed 's/^/       /'
fi
if src -lE "CREATE TABLE" >/dev/null && ! src -lE "ROW LEVEL SECURITY" >/dev/null; then
  note "há CREATE TABLE mas nenhum 'ROW LEVEL SECURITY' — item 4"
fi

echo
echo "── Item 6: comparação de segredos"
if src_app -nE "(secret|token|password|api_key)[a-z_]*\s*(==|!=)\s*" --include="*.py" --include="*.ts" --include="*.js" >/dev/null; then
  note "comparação de segredo com ==/!= (use compare_digest / timingSafeEqual):"
  src_app -nE "(secret|token|password|api_key)[a-z_]*\s*(==|!=)\s*" --include="*.py" --include="*.ts" --include="*.js" | head -5 | sed 's/^/       /'
else
  ok "nenhuma comparação direta de segredo encontrada"
fi

echo
echo "── Item 13: SQL"
if src_app -nE "(execute|query|raw)\(\s*f?[\"'].*(SELECT|INSERT|UPDATE|DELETE).*(\{|%s*\"|\+)" >/dev/null; then
  note "possível SQL montado por string:"
  src_app -nE "(execute|query|raw)\(\s*f?[\"'].*(SELECT|INSERT|UPDATE|DELETE).*(\{|%s*\"|\+)" | head -5 | sed 's/^/       /'
else
  ok "nenhum SQL montado por string encontrado"
fi

echo
echo "── Item 15: XSS"
if src -n "innerHTML\s*=" --include="*.js" --include="*.ts" --include="*.tsx" --include="*.html" >/dev/null; then
  note "innerHTML (prefira textContent):"
  src -n "innerHTML\s*=" --include="*.js" --include="*.ts" --include="*.tsx" --include="*.html" | head -5 | sed 's/^/       /'
else
  ok "nenhum innerHTML"
fi
if src -n "dangerouslySetInnerHTML" >/dev/null; then
  note "dangerouslySetInnerHTML — confirme que o HTML é sanitizado"
fi

echo
echo "── Itens 18, 19: CORS, headers, HTTPS"
if src -nE "allow_origins\s*=\s*\[?[\"']\*|Access-Control-Allow-Origin.*\*|origin:\s*[\"']\*" >/dev/null; then
  note "CORS aberto para '*':"
  src -nE "allow_origins\s*=\s*\[?[\"']\*|Access-Control-Allow-Origin.*\*|origin:\s*[\"']\*" | head -5 | sed 's/^/       /'
else
  ok "nenhum CORS '*'"
fi
if src -lE "Content-Security-Policy|SecurityHeaders|helmet" >/dev/null; then
  ok "há configuração de cabeçalhos de segurança"
else
  note "nenhum Content-Security-Policy / helmet encontrado — item 18"
fi
if src -lE "Strict-Transport-Security|HTTPSRedirect|hsts" >/dev/null; then
  ok "há HSTS ou redirect para HTTPS"
else
  note "nenhum HSTS / redirect HTTPS encontrado — item 19"
fi
if src -nE "http://(?!localhost|127\.0\.0\.1)" --include="*.js" --include="*.ts" --include="*.py" -P >/dev/null 2>&1; then
  note "URL http:// (não-local) no código — item 19"
fi

echo
echo "── Item 11: rate limiting"
if src -lE "RateLimit|rate_limit|slowapi|express-rate-limit|limiter" >/dev/null; then
  ok "há rate limiting"
else
  note "nenhum rate limiting encontrado — item 11"
fi

echo
echo "── Item 20: varredura de dependências"
if [[ -f .github/workflows/security.yml ]] || ls .github/workflows/*.yml >/dev/null 2>&1 && grep -rqlE "pip-audit|npm audit|gitleaks|snyk|trivy" .github/workflows/ 2>/dev/null; then
  ok "há varredura de segurança no CI"
else
  note "nenhuma varredura de dependências no CI — item 20"
fi
if [[ -f .github/dependabot.yml ]]; then
  ok "Dependabot configurado"
else
  note "sem .github/dependabot.yml — item 20"
fi

echo
if [[ -f SECURITY.md ]]; then ok "SECURITY.md presente"; else note "sem SECURITY.md"; fi

echo
echo "═══ $findings ponto(s) para revisar."
echo "    Detalhe de cada item: security-baseline/skill/SKILL.md"
