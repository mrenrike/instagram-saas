# backend/email_service.py
import logging

import resend

from .config import get_config
from .security import escape_html

logger = logging.getLogger(__name__)


def _init():
    cfg = get_config()
    resend.api_key = cfg.RESEND_API_KEY


async def send_report_email(to_email: str, username: str, html_report: str, txt_report: str) -> None:
    _init()
    cfg = get_config()

    # The filename ends up on the recipient's disk: strip anything but a safe shape
    # so a crafted handle cannot produce "../" or a double extension (item 16).
    safe_name = "".join(c for c in username if c.isalnum() or c in "._-")[:60] or "relatorio"

    params = {
        "from": cfg.FROM_EMAIL,
        "to": [to_email],
        "subject": f"Seu relatório @{username} está pronto 🎯",
        "html": html_report,
        "attachments": [
            {
                "filename": f"relatorio_{safe_name}.txt",
                "content": list(txt_report.encode("utf-8")),
            }
        ],
    }

    for attempt in range(2):
        try:
            resend.Emails.send(params)
            return
        except Exception:
            if attempt == 0:
                continue  # retry once
            raise


async def send_error_email(to_email: str, username: str, reason: str) -> None:
    _init()
    cfg = get_config()

    # Item 15 — `username` is the handle the user connected with; escape it before
    # it lands in an HTML e-mail body.
    safe_username = escape_html(username)
    safe_agency_email = escape_html(cfg.AGENCY_EMAIL)

    if reason == "token_expired":
        subject = "[Ação necessária] Reconecte seu Instagram"
        html = f"""<p>Olá {safe_username},</p>
        <p>Houve um problema ao acessar sua conta Instagram: seu token de acesso expirou.</p>
        <p>Por favor, entre em contato conosco em <a href="mailto:{safe_agency_email}">{safe_agency_email}</a>
        para reprocessar seu relatório sem custo adicional.</p>"""
    else:
        subject = "[Ação necessária] Problema ao gerar seu relatório"
        html = f"""<p>Olá {safe_username},</p>
        <p>Encontramos um problema técnico ao gerar seu relatório Instagram Analytics.</p>
        <p>Nossa equipe já foi notificada e entrará em contato em breve.
        Você não será cobrado novamente. Para agilizar, escreva para
        <a href="mailto:{safe_agency_email}">{safe_agency_email}</a>.</p>"""

    try:
        resend.Emails.send({
            "from": cfg.FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html,
        })
    except Exception:  # noqa: BLE001 — best effort; the admin was already alerted
        logger.exception("Could not send error e-mail to the customer")


async def send_followup_email(to_email: str, username: str, quick_wins: str) -> None:
    _init()
    cfg = get_config()
    # `quick_wins` is the first 600 characters of a model-generated report, which in
    # turn reflects user-written captions and context — escape both (item 15).
    safe_username = escape_html(username)
    safe_quick_wins = escape_html(quick_wins).replace("\n", "<br>")
    safe_agency_email = escape_html(cfg.AGENCY_EMAIL)
    resend.Emails.send({
        "from": cfg.FROM_EMAIL,
        "to": [to_email],
        "subject": f"@{username}, você implementou as estratégias do seu relatório? 📊",  # plain-text header
        "html": f"""<p>Olá! Já se passaram 3 dias desde que você recebeu sua análise de @{safe_username}.</p>
        <p>Olá {safe_username}, lembra dos seus <strong>3 quick wins</strong>?</p>
        <blockquote>{safe_quick_wins}</blockquote>
        <p>Se precisar de ajuda para implementar, a <strong>{escape_html(cfg.AGENCY_NAME)}</strong> pode cuidar de tudo por você.</p>
        <p><a href="{escape_html(cfg.AGENCY_LINK)}" style="background:#6366f1;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none">
          Solicitar diagnóstico gratuito →
        </a></p>
        <p>{escape_html(cfg.AGENCY_HANDLE)} | {safe_agency_email}</p>""",
    })
