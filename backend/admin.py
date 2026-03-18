# backend/admin.py
import resend
from fastapi import APIRouter, Header, HTTPException

from .config import get_config
from .session import load_session, save_session, SessionNotFound

router = APIRouter()


async def notify_admin_error(session_id: str, error_msg: str) -> None:
    cfg = get_config()
    resend.api_key = cfg.RESEND_API_KEY
    try:
        session = load_session(session_id)
        client_info = f"Cliente: {session.name} ({session.email}), {session.instagram_handle}"
    except SessionNotFound:
        client_info = "(sessão não encontrada)"

    retry_link = f"POST /admin/retry/{session_id}  (Authorization: {cfg.ADMIN_SECRET})"

    try:
        resend.Emails.send({
            "from": cfg.FROM_EMAIL,
            "to": [cfg.ADMIN_EMAIL],
            "subject": f"[ERRO] Pipeline falhou — {session_id[:8]}",
            "html": f"""<h2>Erro no pipeline</h2>
            <p><strong>Session:</strong> {session_id}</p>
            <p><strong>Erro:</strong> {error_msg}</p>
            <p><strong>{client_info}</strong></p>
            <p><strong>Para reprocessar:</strong><br><code>{retry_link}</code></p>""",
        })
    except Exception:
        pass  # Best effort


@router.post("/admin/retry/{session_id}")
async def admin_retry(session_id: str, authorization: str = Header(...)):
    cfg = get_config()
    if authorization != cfg.ADMIN_SECRET:
        raise HTTPException(401, "Unauthorized")

    try:
        session = load_session(session_id)
    except SessionNotFound:
        raise HTTPException(404, "Session not found")

    if session.payment_status != "paid":
        raise HTTPException(400, "Session not paid — cannot retry")

    import asyncio
    from .pipeline import run_pipeline

    session.pipeline_status = "queued"
    session.pipeline_error = None
    save_session(session)

    asyncio.create_task(run_pipeline(session_id))
    return {"status": "queued", "session_id": session_id}


@router.get("/pipeline/status/{session_id}")
async def pipeline_status(session_id: str):
    try:
        session = load_session(session_id)
    except SessionNotFound:
        raise HTTPException(404, "Session not found")

    return {
        "status": session.pipeline_status,
        "step": {
            "waiting_payment": 0, "queued": 0,
            "fetching_data": 1, "analyzing": 2,
            "building_report": 3, "sending_email": 4,
            "done": 5, "error": -1,
        }.get(session.pipeline_status, 0),
        "error": session.pipeline_error,
    }
