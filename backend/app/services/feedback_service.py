from __future__ import annotations

import asyncio
import logging
import uuid

import resend
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.feedback import Feedback

logger = logging.getLogger(__name__)

_TYPE_LABEL = {
    "bug": "Bug Report",
    "feature": "Feature Request",
    "general": "Feedback",
}


async def create_feedback(
    session: AsyncSession,
    *,
    feedback_type: str,
    message: str,
    page_url: str | None,
    user_id: uuid.UUID | None,
    parent_email: str | None,
    submitter_role: str,
) -> Feedback:
    fb = Feedback(
        feedback_type=feedback_type,
        message=message,
        page_url=page_url,
        user_id=user_id,
        parent_email=parent_email,
        submitter_role=submitter_role,
    )
    session.add(fb)
    await session.flush()
    return fb


def _attachment_from_screenshot(screenshot: str | None) -> dict | None:
    """Turn a base64 data URL into a Resend attachment dict, or None.

    Accepts a ``data:image/...;base64,<data>`` URL (or bare base64) and returns
    ``{"filename", "content"}`` where content is the raw base64 (no prefix).
    Returns None on anything malformed — a bad screenshot must never block the
    notification.
    """
    if not screenshot:
        return None
    data = screenshot.strip()
    ext = "jpg"
    if data.startswith("data:"):
        header, _, payload = data.partition(",")
        if not payload:
            return None
        if "image/png" in header:
            ext = "png"
        data = payload
    if not data:
        return None
    return {"filename": f"feedback-screenshot.{ext}", "content": data}


async def notify_feedback(
    *,
    submitter: str,
    submitter_role: str,
    feedback_type: str,
    message: str,
    page_url: str | None,
    screenshot: str | None = None,
) -> None:
    """Best-effort notification email. Never raises."""
    if settings.email_backend != "resend" or not settings.feedback_notify_email:
        return
    label = _TYPE_LABEL.get(feedback_type, "Feedback")
    subject = f"[InvestiKid] {label} from {submitter}"
    text = (
        f"Type: {label}\n"
        f"From: {submitter} ({submitter_role})\n"
        f"Page: {page_url or 'n/a'}\n\n"
        f"{message}\n"
    )
    try:
        resend.api_key = settings.resend_api_key
        params: resend.Emails.SendParams = {
            "from": settings.email_from,
            "to": [settings.feedback_notify_email],
            "subject": subject,
            "text": text,
        }
        attachment = _attachment_from_screenshot(screenshot)
        if attachment is not None:
            params["attachments"] = [attachment]
        await asyncio.to_thread(resend.Emails.send, params)
    except Exception:  # noqa: BLE001 — notification must never fail submission
        logger.exception("Failed to send feedback notification email")
