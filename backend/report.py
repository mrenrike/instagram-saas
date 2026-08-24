"""Report assembly.

Item 15 — every value interpolated into the HTML is escaped, including the model's
          analysis text. An LLM response is *not* trusted output: it can echo back a
          caption, a competitor handle or an "extra context" note that the user wrote,
          so `<img src=x onerror=...>` reaches this template through the model just as
          easily as through a form field.
"""
from .config import get_config
from .security import escape_html


def _analysis_to_html(analysis: str) -> str:
    """Escape the analysis, then re-introduce only line breaks as markup."""
    return escape_html(analysis).replace("\n", "<br>")


def build_html_report(
    username: str,
    claude_analysis: str,
    metrics: dict,
    charts: dict,
    user_info: dict,
) -> str:
    cfg = get_config()

    # Charts are produced by matplotlib in this process, so the base64 is ours — but it
    # still goes through a strict allowlist so a future change cannot slip a URL in.
    charts_html = ""
    for chart_b64 in charts.values():
        if not isinstance(chart_b64, str) or not chart_b64.replace("+", "").replace("/", "").replace("=", "").isalnum():
            continue
        charts_html += (
            f'<img src="data:image/png;base64,{chart_b64}" '
            f'style="max-width:100%;margin:16px 0;" alt="Gráfico do relatório" />'
        )

    safe_username = escape_html(username)
    agency_name = escape_html(cfg.AGENCY_NAME)
    agency_link = escape_html(cfg.AGENCY_LINK)
    agency_handle = escape_html(cfg.AGENCY_HANDLE)
    agency_email = escape_html(cfg.AGENCY_EMAIL)
    total_posts = int(metrics.get("total_posts", 0) or 0)

    upsell_html = f"""
    <div style="border:2px solid #6366f1;border-radius:12px;padding:24px;margin:32px 0;background:#f8f7ff">
      <h2 style="color:#6366f1;margin-top:0">🚀 Quer resultados sem fazer tudo sozinho?</h2>
      <p>A <strong>{agency_name}</strong> gerencia o Instagram de marcas como a sua —
      criação de conteúdo, estratégia, agendamento e análise de dados.</p>
      <p><a href="{agency_link}" style="background:#6366f1;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700">
        Solicitar diagnóstico gratuito →
      </a></p>
      <p style="color:#666;font-size:0.9em">{agency_handle} &nbsp;|&nbsp; {agency_email}</p>
    </div>
    """

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório Instagram — @{safe_username}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 24px; color: #1e1e2e; }}
  h1 {{ color: #6366f1; }} h2 {{ color: #4338ca; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; }}
  pre {{ background: #f3f4f6; padding: 12px; border-radius: 8px; white-space: pre-wrap; }}
</style>
</head>
<body>
<h1>📊 Relatório Instagram Analytics</h1>
<p><strong>@{safe_username}</strong> &nbsp;|&nbsp; {total_posts} posts analisados</p>
{charts_html}
<div>{_analysis_to_html(claude_analysis)}</div>
{upsell_html}
<p style="color:#999;font-size:0.8em;margin-top:32px">Gerado por Instagram Analytics SaaS · Dados via Meta Graph API</p>
</body>
</html>"""


def build_txt_report(username: str, claude_analysis: str, metrics: dict) -> str:
    """Plain text — no escaping needed, but keep it plain: never inline HTML here."""
    cfg = get_config()
    return f"""RELATÓRIO INSTAGRAM ANALYTICS — @{username}
{"=" * 60}
Total de posts analisados: {metrics.get('total_posts', 0)}
Engajamento médio: {metrics.get('avg_engagement_all', 0)}

{claude_analysis}

{"=" * 60}
🚀 QUER AJUDA PARA IMPLEMENTAR?
{cfg.AGENCY_NAME} gerencia o seu Instagram.
→ {cfg.AGENCY_LINK}
{cfg.AGENCY_HANDLE} | {cfg.AGENCY_EMAIL}
"""
