import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import SentEmail
from app.models.parent_preferences import ParentPreferences
from app.models.subscription import Subscription
from app.models.user import User
from app.services.email import get_email_sender
from app.services.premium_config import PREMIUM_BENEFITS, TRIAL_ENDING_REMINDER_DAYS

# Same namespace used for household_token (deterministic, stable across runs).
_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")
_MANAGE_HINT = "Open InvestiKid and go to your parent dashboard to manage your family's plan."


def _reminder_subject_id(subscription_id: uuid.UUID, period_end: datetime) -> uuid.UUID:
    """Deterministic id so re-runs dedupe against the SentEmail ledger."""
    return uuid.uuid5(_NAMESPACE, f"trial_ending:{subscription_id}:{period_end.date().isoformat()}")


async def run(session: AsyncSession) -> dict:
    now = datetime.now(UTC)
    cutoff = now + timedelta(days=TRIAL_ENDING_REMINDER_DAYS)

    subs = (await session.scalars(
        select(Subscription).where(
            Subscription.provider == "stripe",
            Subscription.status == "trialing",
            Subscription.current_period_end.is_not(None),
            Subscription.current_period_end > now,
            Subscription.current_period_end <= cutoff,
        )
    )).all()

    sender = get_email_sender()
    sent = 0
    skipped = 0
    for sub in subs:
        subject_id = _reminder_subject_id(sub.id, sub.current_period_end)

        already = await session.scalar(
            select(SentEmail.id).where(SentEmail.subject_id == subject_id).limit(1)
        )
        if already is not None:
            skipped += 1
            continue

        pref = await session.get(ParentPreferences, sub.parent_email)
        if pref is not None and pref.trial_reminder_opt_out:
            skipped += 1
            continue

        usernames = (await session.scalars(
            select(User.username).where(User.parent_email == sub.parent_email)
        )).all()
        child_label = ", ".join(usernames) if usernames else "your child"

        await sender.send(
            session,
            to=sub.parent_email,
            template="trial_ending",
            context={
                "child_label": child_label,
                "trial_end": sub.current_period_end.strftime("%A %-d %B"),
                "benefits": list(PREMIUM_BENEFITS),
                "manage_hint": _MANAGE_HINT,
            },
            subject_id=subject_id,
        )
        sent += 1

    await session.commit()
    return {"sent": sent, "skipped": skipped}
