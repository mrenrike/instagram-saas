# backend/report.py
"""
Assembles HTML and TXT reports from Claude analysis + metrics.
Includes agency upsell block at the end.
"""
from .config import get_config


def build_html_report(
    username: str,
    claude_analysis: str,
    metrics: dict,
    charts: dict,
    user_info: dict,
) -> str:
    cfg = get_config()
    charts_html = ""
    for chart_b64 in charts.values():
        charts_html += f'<img src="data:image/png;base64,{chart_b64}" style="max-width:100%;margin:16px 0;" />'

    upsell_html = f"""
    <div style="border:2px solid #6366f1;border-radius:12px;padding:24px;margin:32px 0;background:#f8f7ff">
      <h2 style="color:#6366f1;margin-top:0">🚀 Quer resultados sem fazer tudo sozinho?</h2>
      <p>A <strong>{cfg.AGENCY_NAME}</strong> gerencia o Instagram de marcas como a sua —
      criação de conteúdo, estratégia, agendamento e análise de dados.</p>
      <p><a href="{cfg.AGENCY_LINK}" style="background:#6366f1;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700">
        Solicitar diagnóstico gratuito →
      </a></p>
      <p style="color:#666;font-size:0.9em">{cfg.AGENCY_HANDLE} &nbsp;|&nbsp; {cfg.AGENCY_EMAIL}</p>
    </div>
    """

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório Instagram — @{username}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 24px; color: #1e1e2e; }}
  h1 {{ color: #6366f1; }} h2 {{ color: #4338ca; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; }}
  pre {{ background: #f3f4f6; padding: 12px; border-radius: 8px; white-space: pre-wrap; }}
</style>
</head>
<body>
<h1>📊 Relatório Instagram Analytics</h1>
<p><strong>@{username}</strong> &nbsp;|&nbsp; {metrics.get('total_posts', 0)} posts analisados</p>
{charts_html}
<div>{claude_analysis.replace(chr(10), '<br>')}</div>
{upsell_html}
<p style="color:#999;font-size:0.8em;margin-top:32px">Gerado por Instagram Analytics SaaS · Dados via Meta Graph API</p>
</body>
</html>"""


def build_txt_report(username: str, claude_analysis: str, metrics: dict) -> str:
    cfg = get_config()
    return f"""RELATÓRIO INSTAGRAM ANALYTICS — @{username}
{"="*60}
Total de posts analisados: {metrics.get('total_posts', 0)}
Engajamento médio: {metrics.get('avg_engagement_all', 0)}

{claude_analysis}

{"="*60}
🚀 QUER AJUDA PARA IMPLEMENTAR?
{cfg.AGENCY_NAME} gerencia o seu Instagram.
→ {cfg.AGENCY_LINK}
{cfg.AGENCY_HANDLE} | {cfg.AGENCY_EMAIL}
"""
