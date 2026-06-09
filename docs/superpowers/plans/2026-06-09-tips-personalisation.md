# Personalised Investing Tips (Items 3.2+3.3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 2 holdings/level-tailored tips to the generic set, with a per-child cache + "New tips" refresh, moderated fail-closed and rate-limited. Free; no DB migration.

**Architecture:** Extract tip logic into `app/services/tips_service.py` (generic generator + new personalised generator + caches). `GET /market/tips` gains `session`/`current_user`/`request`, `@limiter.limit`, and `?refresh=`, composing personalised-first + generic (cap 6). FE adds a "New tips" button + "For you" badge to `InvestingTips`.

**Tech Stack:** FastAPI + SQLAlchemy async + the project LLM client (`app.services.llm_client.get_llm_client`, tier "lite") + `moderate_output`; pytest; React 18 + TS + TanStack Query; vitest + vitest-axe.

**Conventions:** TDD. Explicit `git add <paths>` only — never `git add -A`; leave the unrelated working-tree `.gitignore` + uncommitted iOS build files alone. Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Verify — backend (from `backend/`): `/Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/pytest`; frontend (from `frontend/`): `npx tsc -b && npm run lint && npm run test && npm run build`. No `cap sync`. Work on `testing`; do NOT promote.

**Verified facts:**
- `app/routers/simulator.py`: imports `from app.services.llm_client import LLMError, get_llm_client` (l.53), `from app.services.moderation import moderate_output` (l.54), `from app.core.rate_limit import limiter` (l.13), `from app.models.simulator import Holding, Portfolio, Trade` (l.15), `AuditLog` is imported (used at l.236). Current tips block l.531-622: `_FALLBACK_TIPS` (3 `InvestingTipOut`), `_TIPS_PROMPT`, `_tips_cache: dict[str, tuple[float, list[InvestingTipOut]]]`, `_TIPS_CACHE_TTL = 3600`, `async def _generate_tips()` (global cache, moderates joined text, falls back), `@router.get("/market/tips", response_model=list[InvestingTipOut])` `get_investing_tips(_current: User = Depends(get_current_user))` → `await _generate_tips()`.
- `news-summary` template (l.171-243): `@limiter.limit("20/hour")`, `async def get_news_summary(request: Request, current_user=Depends(get_current_user), session=Depends(get_session), provider=...)`; holdings via `select(Holding).where(Holding.portfolio_id == portfolio.id)`; age `= (date.today() - current_user.dob).days // 365`; on unsafe writes `session.add(AuditLog(user_id=current_user.id, event_type="moderation_block", metadata_json={"surface": "...", "category": _mod.category})); await session.commit()`.
- `InvestingTipOut` (`app/schemas/simulator.py:139`): `id, title, description, example_ticker, example_exchange` (all `str`).
- Completed-lesson count pattern (`app/services/recommendation_service.py:429`): `select(func.count(LessonCompletion.id)).where(LessonCompletion.user_id == user.id)`. `LessonCompletion` imported from `app.models.content`.
- Existing tips tests in `tests/test_simulator.py`: `test_tips_returns_list` (l.165, hits `/market/tips`), `test_generate_tips_falls_back_when_model_unsafe` (l.251, `from app.routers.simulator import _FALLBACK_TIPS, _generate_tips`, `import app.routers.simulator as simulator`, `simulator._tips_cache.clear()`, `patch("app.routers.simulator.get_llm_client", return_value=mock_client)`), `test_generate_tips_returns_safe_model_tips` (l.278, same shape). Mock pattern: `mock_client = MagicMock(); mock_client.complete = AsyncMock(return_value=<json str>)`.
- FE `frontend/src/api/simulator.ts`: `getInvestingTips: () => apiFetch<InvestingTip[]>('/market/tips')`; `InvestingTip` type has `id,title,description,example_ticker,example_exchange`. `InvestingTips.tsx` (post-3.1): collapsible SectionCard, auto-rotate, play/pause in body, `useQuery(['investing-tips'])`. Tests: `frontend/src/components/child/simulator/__tests__/InvestingTips.test.tsx`.

---

## File Structure
- **Create** `backend/app/services/tips_service.py` — `_FALLBACK_TIPS`, `_TIPS_PROMPT`, generic generator, `learning_stage`, `generate_personalised_tips`, caches.
- **Modify** `backend/app/schemas/simulator.py` — `InvestingTipOut.personalised: bool = False`.
- **Modify** `backend/app/routers/simulator.py` — remove inline tips block; import from `tips_service`; rewrite the endpoint.
- **Modify** `backend/tests/test_simulator.py` — repoint the 3 existing tips tests to `tips_service`.
- **Create** `backend/tests/test_tips_personalisation.py` — stage bucketing, personalised generator, endpoint tests.
- **Modify** `frontend/src/api/simulator.ts` — `getInvestingTips(refresh?)` + `personalised?` on `InvestingTip`.
- **Modify** `frontend/src/components/child/simulator/InvestingTips.tsx` — "New tips" button + "For you" badge.
- **Modify** `frontend/src/components/child/simulator/__tests__/InvestingTips.test.tsx` — new-tips + badge tests.

---

## Task 1: Backend — extract `tips_service.py`, add `personalised` field, repoint existing tests

**Files:** Create `backend/app/services/tips_service.py`; Modify `backend/app/schemas/simulator.py`, `backend/app/routers/simulator.py`, `backend/tests/test_simulator.py`.

- [ ] **Step 1: Add the schema field** — in `app/schemas/simulator.py`, add to `InvestingTipOut`:

```python
    personalised: bool = False
```

- [ ] **Step 2: Create `app/services/tips_service.py`** — move the generic tip logic verbatim out of the router (copy `_FALLBACK_TIPS`, `_TIPS_PROMPT`, `_tips_cache`, `_TIPS_CACHE_TTL` exactly), renaming `_generate_tips` → `generate_generic_tips`:

```python
import json
import time

from app.schemas.simulator import InvestingTipOut
from app.services.llm_client import get_llm_client
from app.services.moderation import moderate_output

_FALLBACK_TIPS = [
    # ... copy the 3 existing InvestingTipOut entries verbatim from the router ...
]

_TIPS_PROMPT = (
    # ... copy the existing _TIPS_PROMPT string verbatim ...
)

_generic_cache: dict[str, tuple[float, list[InvestingTipOut]]] = {}
_GENERIC_TTL = 3600


async def generate_generic_tips() -> list[InvestingTipOut]:
    cache_key = "global"
    now = time.time()
    cached = _generic_cache.get(cache_key)
    if cached and (now - cached[0]) < _GENERIC_TTL:
        return cached[1]
    try:
        llm = get_llm_client(tier="lite")
        raw = await llm.complete(
            system_prompt=_TIPS_PROMPT,
            messages=[{"role": "user", "content": "Generate 6 fresh investing tips for young learners."}],
            temperature=0.9,
            max_tokens=800,
            response_format="json",
        )
        items = json.loads(raw)
        tips = [InvestingTipOut(**item) for item in items]
        joined = " ".join(f"{t.title} {t.description}" for t in tips)
        _mod = await moderate_output(joined, surface="tips")
        if not _mod.safe:
            return list(_FALLBACK_TIPS)
        if len(tips) >= 3:
            _generic_cache[cache_key] = (now, tips)
            return tips
    except Exception:
        pass
    return list(_FALLBACK_TIPS)
```

- [ ] **Step 3: Thin the router** — in `app/routers/simulator.py`, DELETE the inline `_FALLBACK_TIPS`, `_TIPS_PROMPT`, `_tips_cache`, `_TIPS_CACHE_TTL`, and `_generate_tips`. Add `from app.services.tips_service import generate_generic_tips` (with the other service imports). Temporarily keep the endpoint working:

```python
@router.get("/market/tips", response_model=list[InvestingTipOut])
async def get_investing_tips(
    _current: User = Depends(get_current_user),
):
    return await generate_generic_tips()
```

(The full endpoint rewrite happens in Task 4.)

- [ ] **Step 4: Repoint the existing tips tests** — in `tests/test_simulator.py`, update the two `_generate_tips` tests:
  - Change `from app.routers.simulator import _FALLBACK_TIPS, _generate_tips` → `from app.services.tips_service import _FALLBACK_TIPS, generate_generic_tips`.
  - Change `import app.routers.simulator as simulator` usages of `simulator._tips_cache.clear()` → import `app.services.tips_service as tips_service` and `tips_service._generic_cache.clear()`.
  - Change `patch("app.routers.simulator.get_llm_client", ...)` → `patch("app.services.tips_service.get_llm_client", ...)`.
  - Change calls `await _generate_tips()` → `await generate_generic_tips()`.
  - `test_tips_returns_list` (hits `/market/tips`) needs no change beyond still passing (generic path).

- [ ] **Step 5: Run** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_simulator.py -q` → PASS (the repointed tips tests + the rest). Then `ruff check app/services/tips_service.py app/routers/simulator.py app/schemas/simulator.py tests/test_simulator.py`.

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/investikid
git add backend/app/services/tips_service.py backend/app/routers/simulator.py backend/app/schemas/simulator.py backend/tests/test_simulator.py
git commit -m "$(cat <<'EOF'
refactor(simulator): extract tips_service; add personalised flag

Move generic tip generation out of the router into tips_service; add
InvestingTipOut.personalised (default false). No behaviour change yet.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Backend — learning-stage + holdings context helpers

**Files:** Modify `backend/app/services/tips_service.py`; Create `backend/tests/test_tips_personalisation.py`.

- [ ] **Step 1: Write failing tests** — Create `backend/tests/test_tips_personalisation.py`:

```python
from app.services.tips_service import learning_stage


def test_learning_stage_buckets():
    assert learning_stage(0) == "new"
    assert learning_stage(1) == "beginner"
    assert learning_stage(5) == "beginner"
    assert learning_stage(6) == "intermediate"
    assert learning_stage(15) == "intermediate"
    assert learning_stage(16) == "advanced"
    assert learning_stage(999) == "advanced"
```

- [ ] **Step 2: Run to verify it fails** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_tips_personalisation.py -q` → FAIL (ImportError).

- [ ] **Step 3: Implement** — add to `tips_service.py`:

```python
def learning_stage(completed_lessons: int) -> str:
    if completed_lessons <= 0:
        return "new"
    if completed_lessons <= 5:
        return "beginner"
    if completed_lessons <= 15:
        return "intermediate"
    return "advanced"
```

- [ ] **Step 4: Run** — `pytest tests/test_tips_personalisation.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid
git add backend/app/services/tips_service.py backend/tests/test_tips_personalisation.py
git commit -m "$(cat <<'EOF'
feat(simulator): learning_stage bucket helper for tip personalisation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Backend — personalised tips generator (LLM + moderation + per-child cache)

**Files:** Modify `backend/app/services/tips_service.py`, `backend/tests/test_tips_personalisation.py`.

- [ ] **Step 1: Write failing tests** — append to `tests/test_tips_personalisation.py`:

```python
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import tips_service
from app.services.tips_service import generate_personalised_tips

_TWO_TIPS = json.dumps([
    {"id": "p1", "title": "Your Apple Stock", "description": "Since you own Apple, here's a tip about tech.", "example_ticker": "AAPL", "example_exchange": "NASDAQ"},
    {"id": "p2", "title": "Spread It Out", "description": "You're learning diversification — try different industries.", "example_ticker": "KO", "example_exchange": "NYSE"},
])


@pytest.fixture(autouse=True)
def _clear_cache():
    tips_service._personal_cache.clear()
    yield
    tips_service._personal_cache.clear()


@pytest.mark.asyncio
async def test_personalised_tips_generated_and_flagged():
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_TWO_TIPS)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client), \
         patch("app.services.tips_service.moderate_output", new=AsyncMock(return_value=MagicMock(safe=True, text="ok", category=None))):
        tips, was_unsafe = await generate_personalised_tips(
            user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12,
        )
    assert was_unsafe is False
    assert len(tips) == 2
    assert all(t.personalised for t in tips)
    assert tips[0].example_ticker == "AAPL"


@pytest.mark.asyncio
async def test_personalised_tips_empty_when_no_context():
    # No holdings AND stage "new" → no LLM call, empty list, not flagged unsafe
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_TWO_TIPS)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client) as gc:
        tips, was_unsafe = await generate_personalised_tips(user_id=1, holdings=[], stage="new", age=10)
    assert tips == []
    assert was_unsafe is False
    gc.assert_not_called()


@pytest.mark.asyncio
async def test_personalised_tips_unsafe_returns_empty_flagged():
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_TWO_TIPS)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client), \
         patch("app.services.tips_service.moderate_output", new=AsyncMock(return_value=MagicMock(safe=False, text="", category="advice"))):
        tips, was_unsafe = await generate_personalised_tips(
            user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12,
        )
    # unsafe → empty list AND was_unsafe True so the endpoint can audit
    assert tips == []
    assert was_unsafe is True


@pytest.mark.asyncio
async def test_personalised_tips_error_returns_empty_not_unsafe():
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(side_effect=RuntimeError("llm down"))
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client):
        tips, was_unsafe = await generate_personalised_tips(
            user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12,
        )
    assert tips == []
    assert was_unsafe is False  # LLM/JSON error is not a moderation block


@pytest.mark.asyncio
async def test_personalised_tips_cache_hit():
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_TWO_TIPS)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client) as gc, \
         patch("app.services.tips_service.moderate_output", new=AsyncMock(return_value=MagicMock(safe=True, text="ok", category=None))):
        a, _ = await generate_personalised_tips(user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12)
        b, _ = await generate_personalised_tips(user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12)
    assert a == b
    assert gc.call_count == 1  # second call served from cache


@pytest.mark.asyncio
async def test_personalised_tips_refresh_bypasses_cache():
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_TWO_TIPS)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client) as gc, \
         patch("app.services.tips_service.moderate_output", new=AsyncMock(return_value=MagicMock(safe=True, text="ok", category=None))):
        await generate_personalised_tips(user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12)
        await generate_personalised_tips(user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12, refresh=True)
    assert gc.call_count == 2
```

Contract: `generate_personalised_tips(...) -> tuple[list[InvestingTipOut], bool]` — `(tips, was_unsafe)`. `was_unsafe` is True ONLY on the moderation-unsafe branch; False for no-context, cache, success, and LLM/JSON-error branches. The generator takes no session and writes no AuditLog — the endpoint (Task 4) audits when `was_unsafe`.

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_tips_personalisation.py -q -k personalised` → FAIL.

- [ ] **Step 3: Implement** — add to `tips_service.py`:

```python
_personal_cache: dict[str, tuple[float, list[InvestingTipOut]]] = {}
_PERSONAL_TTL = 3600


def _personal_key(user_id: int, holdings: list[tuple[str, str]], stage: str, age: int) -> str:
    sig = ",".join(sorted(t for t, _ in holdings))
    return f"{user_id}:{sig}:{stage}:{age}"


def _personal_prompt(holdings: list[tuple[str, str]], stage: str, age: int) -> str:
    owned = ", ".join(f"{name} ({ticker})" for ticker, name in holdings[:5]) or "none yet"
    return (
        f"You are writing personalised investing tips for a {age}-year-old kid who is at the "
        f"'{stage}' stage of learning about the stock market. They currently own: {owned}.\n\n"
        "Generate EXACTLY 2 short, encouraging, age-appropriate tips that connect to a stock they "
        "own and/or a concept suited to their stage. Each tip:\n"
        "- Short catchy title (under 8 words)\n"
        "- 2-3 sentence description in simple language for their age\n"
        "- Reference one of their owned tickers in example_ticker where natural (else a well-known kid-friendly stock)\n"
        "- Be educational and encouraging; NEVER give real investment advice\n\n"
        "Return JSON: [{\"id\": \"slug\", \"title\": \"...\", \"description\": \"...\", "
        "\"example_ticker\": \"AAPL\", \"example_exchange\": \"NASDAQ\"}]\n"
        "Only return the JSON array."
    )


async def generate_personalised_tips(
    *,
    user_id: int,
    holdings: list[tuple[str, str]],
    stage: str,
    age: int,
    refresh: bool = False,
) -> tuple[list[InvestingTipOut], bool]:
    """2 holdings/level-tailored tips. Returns (tips, was_unsafe). `was_unsafe`
    is True only when the model output was moderated out (so the endpoint can
    write an AuditLog); False for no-context, cache, success, and error paths.
    The generator takes no session and writes no AuditLog itself."""
    if not holdings and stage == "new":
        return [], False

    key = _personal_key(user_id, holdings, stage, age)
    now = time.time()
    if not refresh:
        cached = _personal_cache.get(key)
        if cached and (now - cached[0]) < _PERSONAL_TTL:
            return cached[1], False

    try:
        llm = get_llm_client(tier="lite")
        raw = await llm.complete(
            system_prompt=_personal_prompt(holdings, stage, age),
            messages=[{"role": "user", "content": "Generate 2 personalised tips."}],
            temperature=0.8,
            max_tokens=400,
            response_format="json",
        )
        items = json.loads(raw)[:2]
        tips = [
            InvestingTipOut(**{k: v for k, v in item.items() if k != "personalised"}, personalised=True)
            for item in items
        ]
        joined = " ".join(f"{t.title} {t.description}" for t in tips)
        _mod = await moderate_output(joined, surface="tips")
        if not _mod.safe:
            return [], True
        _personal_cache[key] = (now, tips)
        return tips, False
    except Exception:
        return [], False
```

- [ ] **Step 4: Run** — `pytest tests/test_tips_personalisation.py -q` → PASS (stage + 5 personalised tests).

- [ ] **Step 5: Lint + commit**

```bash
cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check app/services/tips_service.py tests/test_tips_personalisation.py
cd /Users/leeashmore/investikid
git add backend/app/services/tips_service.py backend/tests/test_tips_personalisation.py
git commit -m "$(cat <<'EOF'
feat(simulator): personalised tip generator (per-child cache, fail-closed)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Backend — wire `/market/tips` endpoint (session, limiter, refresh, compose, AuditLog)

**Files:** Modify `backend/app/routers/simulator.py`, `backend/tests/test_tips_personalisation.py`.

- [ ] **Step 1: Write failing endpoint tests** — append to `tests/test_tips_personalisation.py` (mirror `test_simulator.py`'s `_login` + `client`/`db_session` fixtures; copy `_login` if the file doesn't have it):

```python
from app.models.content import Lesson, LessonCompletion  # noqa
# (use the project's authed client fixture + _login helper as in test_simulator.py)


@pytest.mark.asyncio(loop_scope="session")
async def test_tips_endpoint_generic_when_no_context(client):
    await _login(client, email="tipsnoctx@example.com", username="tipsnoctx")
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_SIX_GENERIC)  # 6-tip JSON
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client), \
         patch("app.services.tips_service.moderate_output", new=AsyncMock(return_value=MagicMock(safe=True, text="ok", category=None))):
        r = await client.get("/market/tips")
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 3
    assert all(t["personalised"] is False for t in body)  # new user, no holdings


@pytest.mark.asyncio(loop_scope="session")
async def test_tips_endpoint_unsafe_personalised_audited(client, db_session):
    # A user with holdings → personalised path runs; force unsafe → slice dropped + AuditLog
    # (set up a Portfolio+Holding for the logged-in user via db_session, mirror test_simulator setup)
    ...
```

(The endpoint tests assert: (a) generic-only for a context-free user with `personalised=False` everywhere; (b) unsafe personalised output → response is generic-only AND an `AuditLog` row with `event_type="moderation_block"`, `metadata_json["surface"]=="tips"` exists — query `db_session` as `test_news_summary_falls_back_when_model_unsafe` does at `test_simulator.py:~394`. Reuse that test's holdings/portfolio setup. Define `_SIX_GENERIC` as a JSON string of 6 valid tip dicts.)

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_tips_personalisation.py -q -k endpoint` → FAIL (endpoint not yet personalised/rate-limited/session-bearing).

- [ ] **Step 3: Rewrite the endpoint** — in `app/routers/simulator.py`, add imports `from app.services.tips_service import generate_generic_tips, generate_personalised_tips, learning_stage` and `from app.models.content import LessonCompletion`, and `from sqlalchemy import func` if not present. Replace the Task-1 stub endpoint with:

```python
@router.get("/market/tips", response_model=list[InvestingTipOut])
@limiter.limit("30/hour")
async def get_investing_tips(
    request: Request,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    generic = await generate_generic_tips()

    portfolio = await session.scalar(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    holdings: list[tuple[str, str]] = []
    if portfolio:
        rows = (await session.scalars(
            select(Holding).where(Holding.portfolio_id == portfolio.id)
        )).all()
        holdings = [(h.ticker, h.name) for h in rows]

    completed = await session.scalar(
        select(func.count(LessonCompletion.id)).where(LessonCompletion.user_id == current_user.id)
    ) or 0
    stage = learning_stage(completed)
    age = (date.today() - current_user.dob).days // 365

    personalised, was_unsafe = await generate_personalised_tips(
        user_id=current_user.id, holdings=holdings, stage=stage, age=age, refresh=refresh,
    )
    if was_unsafe:
        session.add(AuditLog(
            user_id=current_user.id,
            event_type="moderation_block",
            metadata_json={"surface": "tips", "category": "personalised_tips"},
        ))
        await session.commit()

    seen = {t.id for t in personalised}
    merged = personalised + [t for t in generic if t.id not in seen]
    return merged[:6]
```

(`generate_personalised_tips` already returns the `(tips, was_unsafe)` tuple from Task 3 — no contract change needed here.)

- [ ] **Step 4: Run** — `pytest tests/test_tips_personalisation.py tests/test_simulator.py -q` → PASS. If a DB-backed test hangs ~90s it's the local Postgres (CLAUDE.md) — note it, rely on CI.

- [ ] **Step 5: Lint + commit**

```bash
cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check .
cd /Users/leeashmore/investikid
git add backend/app/routers/simulator.py backend/app/services/tips_service.py backend/tests/test_tips_personalisation.py
git commit -m "$(cat <<'EOF'
feat(simulator): /market/tips personalised+generic, rate-limited, audited

Composes 2 holdings/level-tailored tips ahead of the generic set (cap 6),
?refresh= bypasses the per-child cache, unsafe personalised output is dropped
and audited. @limiter.limit("30/hour"). Free.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Frontend — `getInvestingTips(refresh)` + "New tips" button + "For you" badge

**Files:** Modify `frontend/src/api/simulator.ts`, `frontend/src/components/child/simulator/InvestingTips.tsx`, `frontend/src/components/child/simulator/__tests__/InvestingTips.test.tsx`.

- [ ] **Step 1: Add failing tests** — append to `InvestingTips.test.tsx` (the file already mocks `simulatorApi.getInvestingTips`, uses fake timers, stubs `scrollTo`). Add a tip with `personalised: true` to a new TIPS fixture variant and:

```tsx
  it('renders a "For you" badge on personalised tips', async () => {
    vi.mocked(simulatorApi.getInvestingTips).mockResolvedValue([
      { id: 'p1', title: 'Your Apple', description: 'Since you own Apple…', example_ticker: 'AAPL', example_exchange: 'NASDAQ', personalised: true },
      ...TIPS,
    ] as never);
    await renderTips();
    expect(screen.getByText(/for you/i)).toBeInTheDocument();
  });

  it('"New tips" button refetches with refresh', async () => {
    await renderTips();
    await userEvent.click(screen.getByRole('button', { name: /new tips/i }));
    expect(simulatorApi.getInvestingTips).toHaveBeenCalledWith(true);
  });
```

(If `getInvestingTips` is currently called with no args, the new-tips test asserts the refresh call; the initial load calls `getInvestingTips()` / `getInvestingTips(false)` — make the assertion tolerant: `expect(simulatorApi.getInvestingTips).toHaveBeenLastCalledWith(true)`.)

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- InvestingTips` → new tests FAIL.

- [ ] **Step 3: API client** — in `frontend/src/api/simulator.ts`: add `personalised?: boolean` to the `InvestingTip` type, and:

```ts
  getInvestingTips: (refresh = false) =>
    apiFetch<InvestingTip[]>(`/market/tips${refresh ? '?refresh=true' : ''}`),
```

- [ ] **Step 4: Component** — in `InvestingTips.tsx`:
  - Change the query to support refetch: keep `useQuery(['investing-tips'], () => simulatorApi.getInvestingTips())`; add a `refetch`-style refresh via a mutation or `queryClient`. Simplest: use the query's `refetch` won't pass refresh; instead call `simulatorApi.getInvestingTips(true)` in a handler and `queryClient.setQueryData(['investing-tips'], fresh)` (mirror Market's Refresh-prices pattern). Add a `useState` `refreshing`.
  - Add a "New tips" button in the card-body toolbar (next to play/pause): `aria-label="Get new tips"`, label text "New tips", lucide `Sparkles`; `disabled={refreshing}`; under reduced-motion don't spin the icon. On click: set refreshing, fetch with `true`, set query data, reset `activeIndex` to 0, clear refreshing.
  - "For you" badge: for each tip with `tip.personalised`, render a small chip (e.g. `rounded-full bg-brand-100 px-1.5 py-0.5 text-[10px] font-semibold text-brand-700`) reading "For you" inside the tip card header.

- [ ] **Step 5: Run** — `cd frontend && npm run test -- InvestingTips` → PASS (new + existing rotation/pause/dots/reduced-motion/axe/collapse).

- [ ] **Step 6: Typecheck + commit**

```bash
cd frontend && npx tsc -b
cd /Users/leeashmore/investikid
git add frontend/src/api/simulator.ts frontend/src/components/child/simulator/InvestingTips.tsx frontend/src/components/child/simulator/__tests__/InvestingTips.test.tsx
git commit -m "$(cat <<'EOF'
feat(simulator): InvestingTips "New tips" refresh + "For you" badge

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Full regression + close-out

**Files:** none (verification only).

- [ ] **Step 1: Backend gate** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/pytest -q` (note any local-Postgres hang as environmental).
- [ ] **Step 2: Frontend gate** — `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`.
- [ ] **Step 3: Push + report** — `cd /Users/leeashmore/investikid && git push origin testing`; report CI status (all jobs). No `cap sync`. Do NOT promote. Leave unrelated `.gitignore` + iOS build files uncommitted.

---

## Self-Review

**1. Spec coverage:** §1 schema `personalised` → Task 1. §2 context (holdings, stage bucket, age) → Tasks 2 (stage) + 4 (endpoint gathers all three). §3 hybrid compose (2 personalised + generic, cap 6, no-context→generic) → Tasks 3+4. §4 safety (moderation fail-closed, AuditLog on block, rate limit, error isolation, free) → Tasks 3 (drop on unsafe) + 4 (AuditLog + `@limiter.limit("30/hour")`). §5 per-child cache + refresh bypass → Task 3. §6 FE refresh + "For you" badge → Task 5. Testing across Tasks 2–5. ✓

**2. Placeholder scan:** Endpoint, generator, helpers, FE API, and test bodies are concrete. The two "copy verbatim" notes (generic `_FALLBACK_TIPS`/`_TIPS_PROMPT`) point at exact router lines; the endpoint-test holdings setup points at the named `test_news_summary_falls_back_when_model_unsafe` precedent. The `(tips, was_unsafe)` contract is defined once in Task 3 (implementation + unpacking tests) and consumed unchanged in Task 4. ✓

**3. Type consistency:** `generate_generic_tips() -> list[InvestingTipOut]`; `generate_personalised_tips(*, user_id, holdings: list[tuple[str,str]], stage, age, refresh) -> tuple[list[InvestingTipOut], bool]` (defined in Task 3, consumed in Task 4); `learning_stage(int) -> str`. Endpoint composes both, returns `list[InvestingTipOut]` (`personalised` flag carried through). FE `InvestingTip.personalised?: boolean`, `getInvestingTips(refresh?: boolean)`. Consistent. ✓
