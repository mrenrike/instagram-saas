"""Item 17 — return only the data the caller needs."""
from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)

# Client-facing text for each internal failure class. Raw exception strings leak file
# paths, library versions, SQL fragments, API keys embedded in URLs and account ids.
PUBLIC_ERROR_MESSAGES: dict[str, str] = {
    "token_expired": "Sua conexão com o Instagram expirou. Refaça a conexão.",
    "graph_error": "Não foi possível ler os dados da sua conta agora.",
    "analysis_error": "Não foi possível gerar a análise agora.",
    "email_error": "Não foi possível enviar o e-mail agora.",
    "timeout": "O processamento demorou mais que o esperado.",
    "payment_error": "Não foi possível criar a cobrança agora.",
    "internal": "Erro técnico no processamento.",
}


def public_error(kind: str, detail: object = "", *, log: bool = True) -> dict:
    """Log the real error, return a sanitised one plus a correlation id.

    The id is what a user quotes to support; the detail stays in the server log where
    only operators can read it.
    """
    incident_id = uuid.uuid4().hex[:12]
    if log:
        logger.error("incident=%s kind=%s detail=%s", incident_id, kind, detail)
    return {
        "error": kind if kind in PUBLIC_ERROR_MESSAGES else "internal",
        "message": PUBLIC_ERROR_MESSAGES.get(kind, PUBLIC_ERROR_MESSAGES["internal"]),
        "incident_id": incident_id,
    }
