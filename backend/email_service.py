# backend/email_service.py
import resend
from .config import get_config


def _init():
    cfg = get_config()
    resend.api_key = cfg.RESEND_API_KEY


async def send_report_email(to_email: str, username: str, html_report: str, txt_report: str) -> None:
    _init()
    cfg = get_config()

    params = {
        "from": cfg.FROM_EMAIL,
        "to": [to_email],
        "subject": f"Seu relatório @{username} está pronto 🎯",
        "html": html_report,
        "attachments": [
            {
                "filename": f"relatorio_{username}.txt",
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

    if reason == "token_expired":
        subject = "[Ação necessária] Reconecte seu Instagram"
        html = f"""<p>Olá {username},</p>
        <p>Houve um problema ao acessar sua conta Instagram: seu token de acesso expirou.</p>
        <p>Por favor, entre em contato conosco em <a href="mailto:{cfg.AGENCY_EMAIL}">{cfg.AGENCY_EMAIL}</a>
        para reprocessar seu relatório sem custo adicional.</p>"""
    else:
        subject = "[Ação necessária] Problema ao gerar seu relatório"
        html = f"""<p>Olá {username},</p>
        <p>Encontramos um problema técnico ao gerar seu relatório Instagram Analytics.</p>
        <p>Nossa equipe já foi notificada e entrará em contato em breve.
        Você não será cobrado novamente. Para agilizar, escreva para
        <a href="mailto:{cfg.AGENCY_EMAIL}">{cfg.AGENCY_EMAIL}</a>.</p>"""

    try:
        resend.Emails.send({
            "from": cfg.FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html,
        })
    except Exception:
        pass  # Best effort — admin already notified


async def send_followup_email(to_email: str, username: str, quick_wins: str) -> None:
    _init()
    cfg = get_config()
    resend.Emails.send({
        "from": cfg.FROM_EMAIL,
        "to": [to_email],
        "subject": f"@{username}, você implementou as estratégias do seu relatório? 📊",
        "html": f"""<p>Olá! Já se passaram 3 dias desde que você recebeu sua análise.</p>
        <p>Lembra dos seus <strong>3 quick wins</strong>?</p>
        <blockquote>{quick_wins}</blockquote>
        <p>Se precisar de ajuda para implementar, a <strong>{cfg.AGENCY_NAME}</strong> pode cuidar de tudo por você.</p>
        <p><a href="{cfg.AGENCY_LINK}" style="background:#6366f1;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none">
          Solicitar diagnóstico gratuito →
        </a></p>
        <p>{cfg.AGENCY_HANDLE} | {cfg.AGENCY_EMAIL}</p>""",
    })
