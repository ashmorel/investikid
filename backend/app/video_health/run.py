"""CLI: python -m app.video_health.run — checks lesson video health and emails admins when videos are dead."""
import asyncio
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.services.app_settings import get_alert_emails
from app.services.email import get_email_sender
from app.services.video_health_service import check_all_videos


async def send_video_alert(session: AsyncSession, headline: str, detail: str) -> None:
    recipients = await get_alert_emails(session)
    if not recipients:
        return
    sender = get_email_sender()
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    for to in recipients:
        await sender.send(
            session, to=to, template="admin_llm_alert",
            context={"headline": headline, "detail": detail, "timestamp": timestamp},
        )


async def run(session: AsyncSession) -> dict:
    summary = await check_all_videos(session)
    if summary["dead"]:
        lines = "\n".join(
            f"- {d['module_title']} → {d['lesson_title']} (youtube_id: {d['youtube_id'] or '∅'})"
            for d in summary["dead_items"]
        )
        await send_video_alert(
            session,
            headline=f"{summary['dead']} lesson video(s) are unavailable",
            detail=f"Update them in Admin → Video health.\n\n{lines}",
        )
    await session.commit()
    return summary


async def main() -> None:
    async with async_session_factory() as session:
        summary = await run(session)
    print(f"Video health check complete: {summary['ok']} ok, {summary['dead']} dead, {summary['unknown']} unknown.")


if __name__ == "__main__":
    asyncio.run(main())
