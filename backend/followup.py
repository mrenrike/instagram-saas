# backend/followup.py
"""
Background scheduler: every 10 minutes, scan sessions for pending follow-ups.
Sends email on D+3 after report delivery.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .session import load_session, save_session, SESSIONS_DIR
from .email_service import send_followup_email

BRT = timezone(timedelta(hours=-3))
CHECK_INTERVAL = 600  # 10 minutes


async def start_followup_scheduler() -> None:
    logging.info("Follow-up scheduler started")
    while True:
        try:
            await _check_followups()
        except Exception as e:
            logging.error(f"Follow-up scheduler error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)


async def _check_followups() -> None:
    sessions_path = Path(SESSIONS_DIR)
    if not sessions_path.exists():
        return

    now = datetime.now(BRT)

    for enc_file in sessions_path.glob("*.json.enc"):
        session_id = enc_file.stem.replace(".json", "")
        try:
            session = load_session(session_id)
        except Exception:
            continue

        if (
            session.pipeline_status == "done"
            and session.followup_scheduled_at
            and session.followup_sent_at is None
        ):
            scheduled = datetime.fromisoformat(session.followup_scheduled_at)
            if now >= scheduled:
                try:
                    await send_followup_email(
                        to_email=session.email,
                        username=session.instagram_handle,
                        quick_wins=session.quick_wins or "Verifique o relatório completo para seus quick wins personalizados.",
                    )
                    session.followup_sent_at = now.isoformat()
                    save_session(session)
                    logging.info(f"Follow-up sent for {session_id}")
                except Exception as e:
                    logging.error(f"Follow-up failed for {session_id}: {e}")
