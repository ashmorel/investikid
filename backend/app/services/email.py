import asyncio
import logging
import uuid
from typing import Protocol

import resend
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import SentEmail

logger = logging.getLogger(__name__)


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
    if template == "weekly_digest":
        return _render_weekly_digest_text(context)
    raise ValueError(f"Unknown template: {template}")


def _join_names(names: list[str]) -> str:
    if len(names) <= 1:
        return names[0] if names else "your child"
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def premium_variant(parent_email: str) -> str:
    """Stable copy-variant assignment for the digest premium line ('a'|'b'|'c').

    Deterministic on the email (no storage); tagged onto the digest_sent
    analytics event so variants can be compared against trial starts.
    """
    import hashlib

    digest = hashlib.sha256(parent_email.lower().encode()).digest()
    return "abc"[digest[0] % 3]


def _premium_line_html(context: dict, dashboard_url: str, variant: str) -> str:
    name = _premium_child_name(context)
    mastered = sum(len(c.get("masteries") or []) for c in context.get("children", []))
    link = f'<a href="{dashboard_url}" style="color:#2563eb;">See your options</a>'
    if variant == "b" and mastered > 0:
        body = (
            f"{name} mastered {mastered} skill{'s' if mastered != 1 else ''} this week. "
            f"Premium unlocks the full curriculum + AI coach. {link}."
        )
    elif variant == "c":
        body = (
            f"Want the full picture of what {name} can do with money? "
            f"Premium adds the complete curriculum + AI coach. {link}."
        )
    else:  # 'a' (and 'b' fallback on a no-mastery week)
        body = (
            f"Premium unlocks the next levels — deeper skills like the ones "
            f"{name} just mastered. {link}."
        )
    return (
        '<p style="margin:24px 0 0;font-size:14px;line-height:1.6;color:#374151;">'
        + body
        + "</p>"
    )


def _premium_child_name(context: dict) -> str:
    """Name to personalise the premium nudge: first child with a mastery, else first child."""
    children = context.get("children", [])
    for child in children:
        if child.get("masteries"):
            return child["name"]
    return children[0]["name"] if children else "your child"


def _render_weekly_digest_text(context: dict) -> str:
    from app.core.config import settings

    dashboard_url = f"{settings.app_base_url}/parent"
    names = _join_names([c["name"] for c in context.get("children", [])])
    parts = [f"Hi,\n\nHere's what {names} got up to on InvestiKid this week."]

    for child in context.get("children", []):
        lines = []
        for mastery in child.get("masteries", []):
            objectives = mastery.get("objectives") or []
            line = f"{child['name']} mastered {mastery['module_title']} · {mastery['level_title']}"
            if objectives:
                line += f" — they can now {objectives[0]}"
            lines.append(line)
            lines.extend(f"  - {extra}" for extra in objectives[1:])
        lines.append(
            f"This week: {child['lessons_completed']} lessons · {child['streak']}-day streak"
        )
        if child.get("weak_topic"):
            lines.append(f"Worth practising: {child['weak_topic']}")
        rec = child.get("next_recommendation")
        if rec:
            up_next = rec["module_title"]
            if rec.get("level_title"):
                up_next += f" — {rec['level_title']}"
            lines.append(f"Up next: {up_next}")
        if child.get("conversation_prompt"):
            lines.append(f"Talk about it: {child['conversation_prompt']}")
        parts.append("\n".join(lines))

    if not context.get("parent_subscribed"):
        parts.append(
            f"Premium unlocks the next levels — deeper skills like the ones "
            f"{_premium_child_name(context)} just mastered. See your options: {dashboard_url}"
        )

    parts.append(
        f"See the full picture in your parent dashboard: {dashboard_url}\n"
        "Manage email preferences in your dashboard settings."
    )
    return "\n\n".join(parts) + "\n"


_SUBJECT = {
    "consent_request": "Approve your child's InvestiKid account",
    "parent_magic_link": "Sign in to InvestiKid",
    "verify_email": "Confirm your InvestiKid email",
    "password_reset": "Reset your InvestiKid password",
    "admin_llm_alert": "⚠️ InvestiKid system alert",
    "premium_request": "Your child would love InvestiKid Premium",
    "trial_ending": "Your InvestiKid trial ends soon",
    "weekly_digest": "What your child learned this week 🌟",
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
    elif template == "weekly_digest":
        return _render_weekly_digest_html(context)
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


def _render_weekly_digest_html(context: dict) -> str:
    from app.core.config import settings

    dashboard_url = f"{settings.app_base_url}/parent"
    names = _join_names([c["name"] for c in context.get("children", [])])

    sections: list[str] = []
    for child in context.get("children", []):
        rows: list[str] = []
        for mastery in child.get("masteries", []):
            objectives = mastery.get("objectives") or []
            line = (
                f"{child['name']} mastered <strong>{mastery['module_title']} · "
                f"{mastery['level_title']}</strong>"
            )
            if objectives:
                line += f" — they can now {objectives[0]}"
            rows.append(f'<p style="margin:0 0 8px;font-size:15px;line-height:1.6;color:#374151;">{line}</p>')
            if objectives[1:]:
                items = "".join(
                    f'<li style="margin:0 0 4px;">{extra}</li>' for extra in objectives[1:]
                )
                rows.append(
                    f'<ul style="margin:0 0 8px;padding-left:20px;font-size:14px;'
                    f'line-height:1.6;color:#374151;">{items}</ul>'
                )
        rows.append(
            f'<p style="margin:0 0 8px;font-size:14px;color:#374151;">'
            f"This week: {child['lessons_completed']} lessons · "
            f"{child['streak']}-day streak</p>"
        )
        if child.get("weak_topic"):
            rows.append(
                f'<p style="margin:0 0 8px;font-size:14px;color:#374151;">'
                f"Worth practising: {child['weak_topic']}</p>"
            )
        rec = child.get("next_recommendation")
        if rec:
            up_next = rec["module_title"]
            if rec.get("level_title"):
                up_next += f" — {rec['level_title']}"
            rows.append(
                f'<p style="margin:0 0 8px;font-size:14px;color:#374151;">'
                f"Up next: {up_next}</p>"
            )
        if child.get("conversation_prompt"):
            rows.append(
                f'<p style="margin:0 0 8px;font-size:14px;color:#374151;">'
                f"Talk about it: {child['conversation_prompt']}</p>"
            )
        sections.append(
            f'<h2 style="margin:24px 0 8px;font-size:16px;color:#111827;">{child["name"]}</h2>'
            + "".join(rows)
        )

    premium_html = ""
    if not context.get("parent_subscribed"):
        variant = premium_variant(context.get("parent_email", ""))
        premium_html = _premium_line_html(context, dashboard_url, variant)

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
        f'<h1 style="margin:0 0 16px;font-size:20px;color:#111827;">'
        f"What {names} learned this week &#x1F31F;</h1>"
        + "".join(sections)
        + premium_html
        + '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px auto 0;">'
        '<tr><td align="center" style="border-radius:6px;background-color:#2563eb;">'
        f'<a href="{dashboard_url}" target="_blank" '
        'style="display:inline-block;padding:12px 24px;font-size:15px;'
        'font-weight:600;color:#ffffff;text-decoration:none;">Open parent dashboard</a>'
        "</td></tr></table>"
        f'<p style="margin:16px 0 0;font-size:14px;color:#374151;">'
        f'<a href="{dashboard_url}" style="color:#2563eb;text-decoration:underline;">'
        f"Manage {names} &amp; preferences →</a></p>"
        '<p style="margin:8px 0 0;font-size:13px;color:#6b7280;">'
        "Manage email preferences in your dashboard settings.</p>"
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

        # Send via Resend — best-effort. A provider outage must NOT roll back the
        # caller's transaction (account creation, parental consent, etc.) or 500
        # the request: the caller commits regardless and the audit row above
        # records the attempt. Log the failure (no recipient address — that's PII)
        # so operators can detect and replay.
        resend.api_key = self._api_key
        params: resend.Emails.SendParams = {
            "from": self._from_email,
            "to": [to],
            "subject": subject,
            "html": html,
            "text": plain,
        }
        try:
            await asyncio.to_thread(resend.Emails.send, params)
        except Exception:
            logger.exception(
                "Resend send failed (best-effort): template=%s subject_id=%s",
                template, subject_id,
            )


def get_email_sender() -> EmailSender:
    from app.core.config import settings
    if settings.email_backend == "resend":
        return ResendEmailSender(
            api_key=settings.resend_api_key,
            from_email=settings.email_from,
        )
    return LoggingEmailSender()
