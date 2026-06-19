from __future__ import annotations

import re

# UK-specific terms whose presence in a "localised" draft signals it was NOT
# adapted away from the UK source. Word-boundary matched, case-insensitive.
UK_RESIDUE_TERMS = [
    "ISA", "Junior ISA", "FCA", "HMRC", "National Insurance",
    "Premium Bonds", "NS&I", "Help to Save", "GBP", "pence", "pound", "pounds",
    "NHS", "Student Finance England", "Child Trust Fund",
]
_PATTERNS = [(t, re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE)) for t in UK_RESIDUE_TERMS]
_POUND = re.compile(r"£")


def find_uk_residue(text: str) -> list[str]:
    """Return the UK-specific terms present in `text` (deduped, order-stable).
    Used to flag drafts that may be un-adapted GB content."""
    if not text:
        return []
    found: list[str] = []
    if _POUND.search(text):
        found.append("£")
    for term, pat in _PATTERNS:
        if pat.search(text):
            found.append(term)
    return found
