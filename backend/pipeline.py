# backend/pipeline.py
"""
Async pipeline: fetching_data → analyzing → building_report → sending_email → done.
SLA: 5 minutes total. Any unhandled exception sets pipeline_status=error.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import anthropic

from .admin import notify_admin_error
from .analyzer import calc_metrics, make_charts
from .config import get_config
from .crm import append_to_crm
from .email_service import send_error_email, send_report_email
from .instagram import TokenExpiredError, fetch_posts, fetch_user_info
from .report import build_html_report, build_txt_report
from .session import SessionNotFound, load_session, save_session

logger = logging.getLogger(__name__)

BRT = timezone(timedelta(hours=-3))
SLA_SECONDS = 300  # 5 minutes


async def call_claude(posts: list, metrics: dict, questionnaire: dict, user_info: dict) -> str:
    cfg = get_config()
    client = anthropic.AsyncAnthropic(api_key=cfg.ANTHROPIC_API_KEY)

    prompt = f"""Você é um especialista em marketing digital e Instagram.

Analise os dados abaixo e gere um relatório completo em português (BR):

## Dados da conta
- @{user_info.get('username', 'N/A')}
- {user_info.get('followers_count', 0)} seguidores
- {metrics.get('total_posts', 0)} posts analisados
- Engajamento médio: {metrics.get('avg_engagement_all', 0)}

## Nicho: {questionnaire.get('niche', '')}
## Objetivo: {questionnaire.get('goal', '')}
## Público-alvo: {questionnaire.get('audience', '')}
## Tom de voz: {questionnaire.get('tone', '')}
## Concorrentes: {', '.join(questionnaire.get('competitors', []))}
## Contexto extra: {questionnaire.get('extra_context', '')}

## Métricas por formato:
{metrics.get('format_stats', {})}

## Melhores horários (BRT): {metrics.get('best_hours_brt', [])}h
## Melhores dias: {metrics.get('best_days', [])}

## Top 5 posts mais engajados:
{metrics.get('top5_posts', [])}

---

Gere um relatório completo com:
1. Diagnóstico geral (pontos fortes, fracos, oportunidades)
2. Análise por formato com recomendações específicas
3. Por que os top 5 posts funcionaram (padrões virais)
4. Melhores horários e dias para postar (BRT)
5. Estratégia de conteúdo + mix ideal semanal
6. Calendário dia a dia por 30 dias (a partir de hoje, específico para o nicho)
7. 5 roteiros prontos para usar (Reels, Carrossel, etc.)
8. Hashtag strategy (30 hashtags por formato principal)
9. 3 quick wins para implementar hoje
"""

    for attempt in range(3):
        try:
            msg = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except anthropic.RateLimitError:
            if attempt < 2:
                await asyncio.sleep(2 ** (attempt + 1))
            else:
                raise
        except anthropic.APIStatusError as e:
            if e.status_code in (500, 529) and attempt < 2:
                await asyncio.sleep(2 ** (attempt + 1))
            else:
                raise


async def run_pipeline(session_id: str) -> None:
    try:
        await asyncio.wait_for(_run(session_id), timeout=SLA_SECONDS)
    except TimeoutError:
        try:
            session = load_session(session_id)
            session.pipeline_status = "error"
            session.pipeline_error = "Pipeline timeout (>5min)"
            session.pipeline_error_kind = "timeout"
            save_session(session)
        except SessionNotFound:
            pass
        await notify_admin_error(session_id, "Pipeline timeout")


async def _run(session_id: str) -> None:
    session = load_session(session_id)

    try:
        # Step 1: Fetch data
        session.pipeline_status = "fetching_data"
        save_session(session)

        user_info = await fetch_user_info(session.access_token)
        posts = await fetch_posts(user_info["id"], session.access_token)

    except TokenExpiredError:
        session.pipeline_status = "error"
        session.pipeline_error = "Token expirado"
        session.pipeline_error_kind = "token_expired"
        save_session(session)
        await send_error_email(session.email, session.instagram_handle, reason="token_expired")
        await notify_admin_error(session_id, "Token expired")
        return
    except Exception as e:
        # Item 17 — the detail is kept for operators; the client only ever sees the kind.
        logger.exception("Graph API failure for session %s", session_id)
        session.pipeline_status = "error"
        session.pipeline_error = str(e)
        session.pipeline_error_kind = "graph_error"
        save_session(session)
        await send_error_email(session.email, session.instagram_handle, reason="graph_error")
        await notify_admin_error(session_id, f"Graph API error: {e}")
        return

    try:
        # Step 2: Analyze
        session.pipeline_status = "analyzing"
        save_session(session)

        metrics = calc_metrics(posts)
        charts = make_charts(metrics)
        analysis = await call_claude(posts, metrics, session.questionnaire.__dict__, user_info)

        # Step 3: Build report
        session.pipeline_status = "building_report"
        save_session(session)
        html_report = build_html_report(
            username=user_info.get("username", session.instagram_handle),
            claude_analysis=analysis,
            metrics=metrics,
            charts=charts,
            user_info=user_info,
        )
        txt_report = build_txt_report(
            username=user_info.get("username", session.instagram_handle),
            claude_analysis=analysis,
            metrics=metrics,
        )

    except Exception as e:
        logger.exception("Analysis failure for session %s", session_id)
        session.pipeline_status = "error"
        session.pipeline_error = str(e)
        session.pipeline_error_kind = "analysis_error"
        save_session(session)
        await send_error_email(session.email, session.instagram_handle, reason="analysis_error")
        await notify_admin_error(session_id, f"Analysis/Claude error: {e}")
        return

    try:
        # Step 4: Send email
        session.pipeline_status = "sending_email"
        save_session(session)

        await send_report_email(
            to_email=session.email,
            username=user_info.get("username", session.instagram_handle),
            html_report=html_report,
            txt_report=txt_report,
        )

    except Exception as e:
        logger.error("Email send failed for %s: %s", session_id, e)
        await notify_admin_error(session_id, f"Email send failed: {e}")

    # Step 5: Done + schedule follow-up
    now_brt = datetime.now(BRT)
    session.pipeline_status = "done"
    session.report_generated_at = now_brt.isoformat()
    session.quick_wins = txt_report[:600]  # first 600 chars stored for D+3 follow-up
    session.followup_scheduled_at = (now_brt + timedelta(days=3)).isoformat()
    save_session(session)

    # CRM capture
    await append_to_crm(session)
