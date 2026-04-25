from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import SentEmail


class EmailSender(Protocol):
    async def send(
        self,
        session: AsyncSession,
        to: str,
        template: str,
        context: dict,
    ) -> None: ...


def _render(template: str, context: dict) -> str:
    if template == "consent_request":
        return (
            f"Hi,\n\n"
            f"{context['child_username']} signed up for Invest-Ed and listed you as their parent.\n"
            f"They are {context['age']} years old in {context['country_code']}.\n"
            f"To approve their account, click: {context['link']}\n\n"
            f"If you did not expect this, you can ignore this email — the account will stay inactive.\n"
            f"Link expires in 24 hours."
        )
    if template == "parent_magic_link":
        return (
            f"Click to sign in to your Invest-Ed parent dashboard: {context['link']}\n\n"
            f"Link expires in 15 minutes."
        )
    raise ValueError(f"Unknown template: {template}")


class LoggingEmailSender:
    """Persists every send to sent_emails. Used for dev + tests."""

    async def send(
        self, session: AsyncSession, to: str, template: str, context: dict
    ) -> None:
        body = _render(template, context)
        session.add(SentEmail(to_email=to, template=template, body=body))
        await session.flush()


class SendGridEmailSender:
    async def send(
        self, session: AsyncSession, to: str, template: str, context: dict
    ) -> None:
        raise NotImplementedError("SendGrid backend not yet wired")


def get_email_sender() -> EmailSender:
    from app.core.config import settings
    if settings.email_backend == "sendgrid":
        return SendGridEmailSender()
    return LoggingEmailSender()
