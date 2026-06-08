import asyncio
import uuid
from typing import Protocol

import resend
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import SentEmail


class EmailSender(Protocol):
    async def send(
        self,
        session: AsyncSession,
        to: str,
        template: str,
        context: dict,
        subject_id: uuid.UUID | None = None,
    ) -> None: ...


def _render(template: str, context: dict) -> str:
    if template == "consent_request":
        return (
            f"Hi,\n\n"
            f"{context['child_username']} signed up for InvestiKid and listed you as their parent.\n"
            f"They are {context['age']} years old in {context['country_code']}.\n"
            f"To approve their account, click: {context['link']}\n\n"
            f"If you did not expect this, you can ignore this email — the account will stay inactive.\n"
            f"Link expires in 24 hours."
        )
    if template == "parent_magic_link":
        return (
            f"Click to sign in to your InvestiKid parent dashboard: {context['link']}\n\n"
            f"Link expires in 15 minutes."
        )
    if template == "verify_email":
        return (
            f"Hi {context['username']},\n\n"
            f"Please confirm your InvestiKid email address by clicking: {context['link']}\n\n"
            f"If you didn't create an account you can ignore this email.\n"
            f"Link expires in 24 hours."
        )
    if template == "password_reset":
        return (
            f"We received a request to reset the password for an InvestiKid account.\n"
            f"Click to choose a new password: {context['link']}\n\n"
            f"If you didn't request this, you can ignore this email.\n"
            f"Link expires in 1 hour."
        )
    if template == "admin_llm_alert":
        return (
            f"InvestiKid system alert\n\n"
            f"{context['headline']}\n\n"
            f"Detail: {context['detail']}\n"
            f"Time (UTC): {context['timestamp']}\n\n"
            f"This is an automated alert."
        )
    if template == "premium_request":
        child = context["child_username"]
        label = context["context_label"]
        benefits = "\n".join(f"- {b}" for b in context.get("benefits", []))
        return (
            f"Hi! {child} just found something in InvestiKid that needs Premium "
            f"(\"{label}\").\n\nPremium includes:\n{benefits}\n\n"
            "Open InvestiKid and go to your parent dashboard to manage your family's plan.\n"
        )
    if template == "trial_ending":
        child = context["child_label"]
        benefits = "\n".join(f"- {b}" for b in context.get("benefits", []))
        return (
            f"Hi!\n\n{child}'s InvestiKid free trial ends on {context['trial_end']}. "
            f"After that, Premium keeps unlocking:\n\n{benefits}\n\n"
            f"{context['manage_hint']}\n"
        )
    raise ValueError(f"Unknown template: {template}")


_SUBJECT = {
    "consent_request": "Approve your child's InvestiKid account",
    "parent_magic_link": "Sign in to InvestiKid",
    "verify_email": "Confirm your InvestiKid email",
    "password_reset": "Reset your InvestiKid password",
    "admin_llm_alert": "⚠️ InvestiKid system alert",
    "premium_request": "Your child would love InvestiKid Premium",
    "trial_ending": "Your InvestiKid trial ends soon",
}


def _email_subject(template: str) -> str:
    return _SUBJECT.get(template, "InvestiKid")


def _render_html(template: str, context: dict) -> str:
    if template == "consent_request":
        heading = f"Approve {context['child_username']}'s InvestiKid account"
        body_text = (
            f"{context['child_username']} (age {context['age']}, {context['country_code']}) "
            f"signed up for InvestiKid and listed you as their parent."
        )
        cta_label = "Approve Account"
        cta_url = context["link"]
        footer = "If you didn't expect this, you can ignore this email. Link expires in 24 hours."
    elif template == "parent_magic_link":
        heading = "Sign in to InvestiKid"
        body_text = "Click below to access your parent dashboard."
        cta_label = "Sign In"
        cta_url = context["link"]
        footer = "Link expires in 15 minutes."
    elif template == "verify_email":
        heading = "Confirm your email"
        body_text = f"Hi {context['username']}, please confirm your InvestiKid email address."
        cta_label = "Confirm Email"
        cta_url = context["link"]
        footer = "If you didn't create an account, ignore this email. Link expires in 24 hours."
    elif template == "password_reset":
        heading = "Reset your password"
        body_text = "Click below to choose a new password for your InvestiKid account."
        cta_label = "Reset Password"
        cta_url = context["link"]
        footer = "If you didn't request this, ignore this email. Link expires in 1 hour."
    elif template == "admin_llm_alert":
        return (
            '<!DOCTYPE html>'
            '<html lang="en">'
            "<head>"
            '<meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "</head>"
            "<body style=\"margin:0;padding:0;background-color:#f4f4f5;"
            "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;\">"
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            '<tr><td align="center" style="padding:40px 20px;">'
            '<table role="presentation" width="100%"'
            ' style="max-width:480px;background:#ffffff;border-radius:8px;overflow:hidden;">'
            '<tr><td style="padding:32px 24px;">'
            '<h1 style="margin:0 0 16px;font-size:20px;color:#111827;">&#x26A0;&#xFE0F; InvestiKid system alert</h1>'
            f'<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#374151;">{context["headline"]}</p>'
            f'<p style="margin:0 0 8px;font-size:14px;line-height:1.6;color:#6b7280;">'
            f'<strong>Detail:</strong> {context["detail"]}</p>'
            f'<p style="margin:0 0 24px;font-size:13px;color:#6b7280;">'
            f'<strong>Time (UTC):</strong> {context["timestamp"]}</p>'
            '<p style="margin:24px 0 0;font-size:13px;color:#6b7280;">This is an automated alert.</p>'
            "</td></tr></table>"
            "</td></tr></table>"
            "</body></html>"
        )
    elif template == "premium_request":
        from app.core.config import settings

        child = context["child_username"]
        label = context["context_label"]
        benefit_items = "".join(
            f"<li style=\"margin:0 0 6px;\">{b}</li>"
            for b in context.get("benefits", [])
        )
        heading = f"{child} wants to unlock Premium"
        body_text = (
            f"{child} found something in InvestiKid that needs Premium "
            f"(&ldquo;{label}&rdquo;). Premium includes:"
            f"<ul style=\"margin:12px 0 0;padding-left:20px;\">{benefit_items}</ul>"
        )
        cta_label = "Open parent dashboard"
        cta_url = f"{settings.app_base_url}/parent"
        footer = "Manage your family's plan from your parent dashboard in InvestiKid."
    elif template == "trial_ending":
        from app.core.config import settings

        child = context["child_label"]
        benefit_items = "".join(
            f"<li style=\"margin:0 0 6px;\">{b}</li>"
            for b in context.get("benefits", [])
        )
        heading = "Your InvestiKid trial ends soon"
        body_text = (
            f"{child}'s free trial ends on {context['trial_end']}. "
            f"After that, Premium keeps unlocking:"
            f"<ul style=\"margin:12px 0 0;padding-left:20px;\">{benefit_items}</ul>"
        )
        cta_label = "Open parent dashboard"
        cta_url = f"{settings.app_base_url}/parent"
        footer = context["manage_hint"]
    else:
        raise ValueError(f"Unknown template: {template}")

    return (
        '<!DOCTYPE html>'
        '<html lang="en">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "</head>"
        "<body style=\"margin:0;padding:0;background-color:#f4f4f5;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;\">"
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        '<tr><td align="center" style="padding:40px 20px;">'
        '<table role="presentation" width="100%"'
        ' style="max-width:480px;background:#ffffff;border-radius:8px;overflow:hidden;">'
        '<tr><td style="padding:32px 24px;">'
        f'<h1 style="margin:0 0 16px;font-size:20px;color:#111827;">{heading}</h1>'
        f'<p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#374151;">{body_text}</p>'
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">'
        '<tr><td align="center" style="border-radius:6px;background-color:#2563eb;">'
        f'<a href="{cta_url}" target="_blank" '
        'style="display:inline-block;padding:12px 24px;font-size:15px;'
        f'font-weight:600;color:#ffffff;text-decoration:none;">{cta_label}</a>'
        "</td></tr></table>"
        f'<p style="margin:24px 0 0;font-size:13px;color:#6b7280;">{footer}</p>'
        "</td></tr></table>"
        "</td></tr></table>"
        "</body></html>"
    )


class LoggingEmailSender:
    """Persists every send to sent_emails. Used for dev + tests."""

    async def send(
        self, session: AsyncSession, to: str, template: str, context: dict,
        subject_id: uuid.UUID | None = None,
    ) -> None:
        body = _render(template, context)
        session.add(SentEmail(to_email=to, template=template, body=body, subject_id=subject_id))
        await session.flush()


class ResendEmailSender:
    """Sends real emails via Resend API. Also persists to sent_emails for audit."""

    def __init__(self, api_key: str, from_email: str) -> None:
        self._api_key = api_key
        self._from_email = from_email

    async def send(
        self, session: AsyncSession, to: str, template: str, context: dict,
        subject_id: uuid.UUID | None = None,
    ) -> None:
        plain = _render(template, context)
        html = _render_html(template, context)
        subject = _email_subject(template)

        # Persist audit record (same as LoggingEmailSender)
        session.add(SentEmail(to_email=to, template=template, body=plain, subject_id=subject_id))
        await session.flush()

        # Send via Resend
        resend.api_key = self._api_key
        params: resend.Emails.SendParams = {
            "from": self._from_email,
            "to": [to],
            "subject": subject,
            "html": html,
            "text": plain,
        }
        await asyncio.to_thread(resend.Emails.send, params)


def get_email_sender() -> EmailSender:
    from app.core.config import settings
    if settings.email_backend == "resend":
        return ResendEmailSender(
            api_key=settings.resend_api_key,
            from_email=settings.email_from,
        )
    return LoggingEmailSender()
