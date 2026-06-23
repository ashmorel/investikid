"""Meta-test: every generative LLM surface must route its system prompt through a
guardrail/framing helper so no surface can silently ship an unframed prompt.
Interactive surfaces (the child types) use with_guardrail_preamble (anti-injection
+ topical scope); non-interactive, app-generated surfaces use with_generation_framing
(content safety + data-injection resistance, no anti-jailbreak scaffolding). A
source-level scan is intentional — it catches a NEW surface that forgets framing,
which a per-surface unit test would not."""
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]

SURFACE_FILES = [
    "app/services/tutor_service.py",
    "app/services/coach_service.py",
    "app/services/chart_coach_service.py",
    "app/services/tips_service.py",
    "app/services/home_greeting_service.py",
    "app/services/ai_content_service.py",
    "app/routers/simulator.py",
]


@pytest.mark.parametrize("relpath", SURFACE_FILES)
def test_surface_uses_guardrail_preamble(relpath):
    src = (BACKEND / relpath).read_text()
    assert "with_guardrail_preamble(" in src or "with_generation_framing(" in src, (
        f"{relpath} builds an LLM system prompt but does not apply a guardrail "
        "framing (with_guardrail_preamble or with_generation_framing)"
    )
