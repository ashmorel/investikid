"""Central, developer-tuned config for premium clarity/paywall (deploy to change).

No prices here (App Store 3.1.1 — the child app never shows price/checkout). Benefits copy is
mirrored on the frontend in src/lib/premiumConfig.ts; keep the two in sync.
"""
from fastapi import HTTPException, status

# Canonical "what Premium includes" — used by the parent email + (mirrored) the app.
PREMIUM_BENEFITS: tuple[str, ...] = (
    "Coach Penny — your AI money helper",
    "Premium lessons & advanced levels",
    "The full stock market in the simulator",
    "Bonus challenges & rewards",
)

# Don't email the same parent more than once per this window.
PREMIUM_REQUEST_COOLDOWN_HOURS: int = 24


def premium_required_error(kind: str, label: str) -> HTTPException:
    """403 with a structured body the frontend uses to open the paywall.

    FastAPI serialises this as {"detail": {...}}.
    """
    return HTTPException(
        status.HTTP_403_FORBIDDEN,
        detail={
            "message": "Premium required",
            "code": "premium_required",
            "context": {"kind": kind, "label": label},
        },
    )
