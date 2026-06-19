# Intelligent Market Content Implementation Plan (Sub-project E2.1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the admin Market Content page proactive + quality-guarded: flag un-adapted drafts (UK-residue), let the model propose market-specific modules, one-click-create them, and generate market-native (brief-grounded) lessons for them.

**Architecture:** A deterministic UK-residue check surfaced on the draft-list; a premium-model module suggester grounded in the verified brief + GB module list; a from-suggestion module+level creator; a brief-only "native" generation mode added to the existing generator; and admin UI wiring. No migration (computed flags + reused tables).

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async; React 18 + Vite + TS (admin UI). LLM via `get_llm_client("premium")` (now `reasoning_effort=minimal`, fast); safety via `moderate_output`.

**Spec:** `docs/superpowers/specs/2026-06-19-intelligent-market-content-design.md`
**Branch:** `testing`. No DB migration → no snapshot question.

---

## Existing seams reused
- `admin_content_generation_service.py`: `_system_prompt(lesson_type, module, level, *, brief=None, source_text=None)` (generic mode = neither; adapt mode = both), `_generate_one(..., brief=None, source_text=None)`, `_concat_text(content_json)`, `validate_lesson_content_json`, `moderate_output`, `LessonDraft`, `GenerationResult`.
- Admin draft endpoints + `LessonDraftOut` (`id, level_id, type, content_json, concept, moderation_safe, moderation_category, created_at`). `require_verified_brief(session, code)` (409 if not verified).
- Module/Level models + admin CRUD; `MarketBrief`.

---

### Task 1: Adaptation guard (UK-residue) + draft-list flags

**Files:** Create `backend/app/services/content_adaptation_check.py`; Modify `backend/app/schemas/admin.py`, `backend/app/routers/admin.py`; Test `backend/tests/test_adaptation_check.py`.

- [ ] **Step 1: Failing test** — `backend/tests/test_adaptation_check.py`:

```python
from app.services.content_adaptation_check import find_uk_residue


def test_detects_uk_terms():
    found = find_uk_residue("Put £500 into your ISA — the FCA regulates it.")
    assert "£" in found and "ISA" in found and "FCA" in found


def test_clean_us_text_has_no_residue():
    assert find_uk_residue("Put $500 into your Roth IRA — the SEC regulates it.") == []


def test_word_boundary_not_substring():
    # 'crisp' contains 'isp' not 'ISA'; 'nice' must not match ' NI '
    assert find_uk_residue("That was a nice crisp explanation.") == []
```

Run from `backend/`: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_adaptation_check.py -v` → FAIL.

- [ ] **Step 2: Implement the checker** — `content_adaptation_check.py`:

```python
from __future__ import annotations

import re

# UK-specific terms whose presence in a "localised" draft signals it was NOT
# adapted away from the UK source. Word-boundary matched, case-insensitive.
UK_RESIDUE_TERMS = [
    "ISA", "Junior ISA", "FCA", "HMRC", "National Insurance", "NI",
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
```

Run the test → PASS. Ruff.

- [ ] **Step 3: Wire into `LessonDraftOut` + the draft-list endpoint**

In `backend/app/schemas/admin.py`, add:

```python
class AdaptationFlags(BaseModel):
    uk_residue: list[str] = []
    suspect: bool = False
```

Add `adaptation_flags: AdaptationFlags = AdaptationFlags()` to `LessonDraftOut`. (Keep `from_attributes`; the field is set explicitly by the endpoint, not from the ORM.)

In `backend/app/routers/admin.py` `list_lesson_drafts`, build each `LessonDraftOut` with the flags (use `_concat_text` from the generation service to get the draft's text):

```python
from app.services.admin_content_generation_service import _concat_text
from app.services.content_adaptation_check import find_uk_residue
from app.schemas.admin import AdaptationFlags

# in the comprehension/loop:
def _draft_out(d):
    residue = find_uk_residue(_concat_text(d.content_json or {}))
    out = LessonDraftOut.model_validate(d)
    out.adaptation_flags = AdaptationFlags(uk_residue=residue, suspect=bool(residue))
    return out
return [_draft_out(d) for d in rows]
```

Apply the same to any other place that returns `LessonDraftOut` lists if cheap; the draft-list is the key one.

- [ ] **Step 4: Run + ruff + commit** — full `find_uk_residue` test + the existing draft tests green.
```bash
cd /Users/leeashmore/investikid && git add backend/app/services/content_adaptation_check.py backend/app/schemas/admin.py backend/app/routers/admin.py backend/tests/test_adaptation_check.py && git commit -m "feat(market): UK-residue adaptation guard on lesson drafts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Market-native lesson generation (brief-only mode)

**Files:** Modify `backend/app/services/admin_content_generation_service.py`, `backend/app/routers/admin.py`, `backend/app/schemas/admin.py`; Test `backend/tests/test_native_generation.py`.

- [ ] **Step 1: Failing test** — `backend/tests/test_native_generation.py`: a US module+level (`market_code="US"`) + verified US brief; patch `get_llm_client` with a spy returning a valid card JSON. Call `generate_native_level_lessons(session, us_level, brief=us_brief, concepts=["Saving for college with a 529 plan"], types=["card"])` → asserts a `LessonDraft` is created, and the spy's system prompt **contains the brief facts AND the concept but NOT a GB source lesson**. Also assert the GENERIC path (`_system_prompt` with brief=None, source_text=None) is unchanged (byte-identical base prompt). Run → FAIL.

- [ ] **Step 2: Native prompt mode** — in `_system_prompt`, after the existing `if brief is not None and source_text is not None:` block, add:

```python
    elif brief is not None and source_text is None:
        prompt += (
            f"\n\nWrite this as a MARKET-NATIVE lesson for the market '{module.market_code}', "
            f"grounded in these verified market facts: {json.dumps(brief, ensure_ascii=False)}. "
            f"Use the market's real products, regulators, currency and age-appropriate local "
            f"examples. This is NOT a UK lesson — do not reference UK-specific products, "
            f"regulators or currency."
        )
```

(Generic mode — both None — and adapt mode — both present — are unchanged.)

- [ ] **Step 3: Native generator + endpoint** — add to `admin_content_generation_service.py`:

```python
async def generate_native_level_lessons(session, level, *, brief, concepts, types=None) -> GenerationResult:
    """Generate market-NATIVE lessons (brief-grounded, no GB source) for `level`,
    one per concept. The caller passes a verified brief."""
    module = await session.get(Module, level.module_id)
    type_cycle = types or ["card", "quiz"]
    result = GenerationResult()
    for i, concept in enumerate(concepts):
        draft = await _generate_one(
            session, level=level, module=module, concept=concept,
            lesson_type=type_cycle[i % len(type_cycle)],
            brief=brief.brief_json, source_text=None,
        )
        if draft is None:
            result.skipped += 1
        else:
            result.created.append(draft)
    await session.commit()
    return result
```

In `schemas/admin.py` add `GenerateNativeLessonsRequest { concepts: list[str]; types: list[str] | None = None }`. In `admin.py` add `POST /admin/levels/{level_id}/generate-native` (admin-gated, `@limiter.limit("5/minute")` + `request: Request`): load level (404) + module → `require_verified_brief(module.market_code)` → `generate_native_level_lessons(...)` → `GenerateLessonsResponse`.

- [ ] **Step 4: Run + ruff + regression** — new test + existing `test_market_content_generation.py` + `test_admin_content_generation.py` green (generic + adapt modes unchanged). Commit:
```bash
cd /Users/leeashmore/investikid && git add backend/app/services/admin_content_generation_service.py backend/app/routers/admin.py backend/app/schemas/admin.py backend/tests/test_native_generation.py && git commit -m "feat(market): market-native (brief-grounded) lesson generation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Module suggester

**Files:** Create `backend/app/services/market_module_suggester.py`; Modify `backend/app/routers/admin.py`, `backend/app/schemas/admin.py`; Test `backend/tests/test_module_suggester.py`.

- [ ] **Step 1: Failing test** — `backend/tests/test_module_suggester.py` (`admin_client` + seeded GB modules + verified US brief; patch `app.services.market_module_suggester.get_llm_client` with a mock returning a JSON list of suggestions):
  - `POST /admin/markets/US/module-suggestions` → 200, returns a list of `{title, topic, rationale, action, replaces, suggested_concepts}`.
  - Without a verified brief (e.g. AU draft) → 409.
  - Malformed LLM output → 200 with `[]` (graceful).
  Run → FAIL.

- [ ] **Step 2: Service** — `market_module_suggester.py`:

```python
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Module
from app.models.market import Market
from app.services.llm_client import get_llm_client
from app.services.market_brief_service import require_verified_brief

logger = logging.getLogger(__name__)


async def suggest_modules(session: AsyncSession, market: Market) -> list[dict]:
    brief = await require_verified_brief(session, market.code)  # 409 if not verified
    gb_titles = (await session.scalars(
        select(Module.title).where(Module.market_code == "GB").order_by(Module.order_index)
    )).all()
    system = (
        f"You design youth financial-education curricula. The base (UK) curriculum has these "
        f"modules: {json.dumps(list(gb_titles), ensure_ascii=False)}. Using these verified facts "
        f"about the market '{market.name}' ({market.code}): {json.dumps(brief.brief_json, ensure_ascii=False)}, "
        f"propose modules this market NEEDS that the UK set lacks, and flag UK-specific modules to "
        f"replace. Reply ONLY with a JSON array; each item: "
        f'{{"title": str, "topic": str, "rationale": str (one line), "action": "add"|"replace", '
        f'"replaces": str|null (a UK module title when action=replace), "suggested_concepts": [str, 3-5]}}.'
    )
    try:
        raw = await get_llm_client("premium").complete(
            system_prompt=system,
            messages=[{"role": "user", "content": f"Suggest modules for {market.name}."}],
            temperature=0.4, max_tokens=1500, response_format="json",
        )
        parsed = json.loads(raw)
        items = parsed if isinstance(parsed, list) else parsed.get("modules", parsed.get("suggestions", []))
        out: list[dict] = []
        for it in items:
            if isinstance(it, dict) and isinstance(it.get("title"), str):
                out.append({
                    "title": it["title"], "topic": str(it.get("topic", "")),
                    "rationale": str(it.get("rationale", "")),
                    "action": "replace" if it.get("action") == "replace" else "add",
                    "replaces": it.get("replaces") if isinstance(it.get("replaces"), str) else None,
                    "suggested_concepts": [str(c) for c in (it.get("suggested_concepts") or []) if c][:5],
                })
        return out
    except Exception as exc:  # noqa: BLE001 — any failure → no suggestions, never 500 the page
        logger.warning("module suggestion failed for %s: %s", market.code, exc)
        return []
```

> `response_format="json"` returns an object; the prompt asks for an array, so OpenAI may wrap it (`{"modules":[...]}`) — the `items` extraction handles both. (If JSON-object mode rejects a top-level array, the wrapper-key path covers it.)

- [ ] **Step 3: Schemas + endpoint** — `ModuleSuggestion` (+ list response) in `schemas/admin.py`; `POST /admin/markets/{code}/module-suggestions` (admin-gated, rate-limited) → 404 if market absent; `suggest_modules`; return the list.

- [ ] **Step 4: Run + ruff + commit**
```bash
cd /Users/leeashmore/investikid && git add backend/app/services/market_module_suggester.py backend/app/routers/admin.py backend/app/schemas/admin.py backend/tests/test_module_suggester.py && git commit -m "feat(market): per-market module suggester (brief-grounded add/replace)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: "Create this module" from a suggestion

**Files:** Modify `backend/app/routers/admin.py`, `backend/app/schemas/admin.py`; Test `backend/tests/test_module_from_suggestion.py`.

- [ ] **Step 1: Failing test** — `backend/tests/test_module_from_suggestion.py` (`admin_client`): `POST /admin/markets/US/modules/from-suggestion` body `{title, topic, suggested_concepts, action, replaces}` → 200; assert a US `Module` created (market_code US, the title/topic, order_index after existing) + exactly one starter `Level`, no lessons, `has_content` untouched; response includes the new `module_id` + `level_id` (+ echoes `suggested_concepts`). 404 for an unknown market. Run → FAIL.

- [ ] **Step 2: Endpoint** — in `admin.py`:

```python
@router.post("/markets/{code}/modules/from-suggestion", response_model=ModuleFromSuggestionResult)
async def create_module_from_suggestion(
    code: str, body: CuratedModuleSuggestion, session: AsyncSession = Depends(get_session),
):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "market not found")
    max_order = await session.scalar(
        select(func.max(Module.order_index)).where(Module.market_code == code)
    )
    module = Module(
        topic=body.topic or "general", title=body.title, country_codes=[], market_code=code,
        is_premium=False, order_index=(max_order or -1) + 1, icon="🧭", prerequisite_ids=[],
    )
    session.add(module)
    await session.flush()
    level = Level(module_id=module.id, title="Level 1", order_index=0, is_premium=False, pass_threshold=0.7)
    session.add(level)
    await session.commit()
    return ModuleFromSuggestionResult(
        module_id=module.id, level_id=level.id, suggested_concepts=body.suggested_concepts,
    )
```

Add `CuratedModuleSuggestion` (title, topic, suggested_concepts, action, replaces — accept the suggester's shape) + `ModuleFromSuggestionResult { module_id, level_id, suggested_concepts }` to `schemas/admin.py`. Verify `Module`/`Level` required fields (icon, pass_threshold) against the models.

- [ ] **Step 3: Run + ruff + commit**
```bash
cd /Users/leeashmore/investikid && git add backend/app/routers/admin.py backend/app/schemas/admin.py backend/tests/test_module_from_suggestion.py && git commit -m "feat(market): one-click create module + starter level from a suggestion

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Frontend — proactive suggestions + create + native-generate + residue badge

**Files:** Modify `frontend/src/api/admin.ts`, `frontend/src/components/admin/MarketContent.tsx`, the draft-review component (`LessonDraftReview`/`LevelLessonList` — grep), `frontend/src/locales/en/admin.json`; Test `frontend/src/components/admin/__tests__/MarketContent.test.tsx` (extend).

- [ ] **Step 1: Failing test** — extend the MarketContent test: mock the new hooks so "Suggest modules" renders a suggestion with a "Create this module" button; assert clicking it calls the create mutation; assert a generated draft with `adaptation_flags.suspect` shows the "may not be fully adapted" badge in the draft review (test that component if separate). Run → FAIL.

- [ ] **Step 2: API client** — in `frontend/src/api/admin.ts` add types + hooks: `useSuggestModules(code)` (POST module-suggestions), `useCreateModuleFromSuggestion(code)` (POST from-suggestion), `useGenerateNativeLessons(levelId)` (POST generate-native). Add `adaptation_flags?: { uk_residue: string[]; suspect: boolean }` to the `LessonDraft` type.

- [ ] **Step 3: UI** — in `MarketContent.tsx` add a **"Suggest modules"** section (enabled when brief verified): button → list of suggestion cards (title, topic, rationale, add/replace chip, replaces); each card a **"Create this module"** button → on success, surface the created module's level with a **"Generate lessons"** (native) control wired to `useGenerateNativeLessons(levelId)` with the suggestion's `suggested_concepts` → feeds the existing draft review. In the draft-review component, render a **"⚠ {t('marketContent.adaptation.suspect')}"** badge (listing `uk_residue`) when `draft.adaptation_flags?.suspect`. All strings i18n'd (`admin` namespace).

- [ ] **Step 4: Verify + commit** — `cd frontend && npx tsc -b && npm run lint && npx vitest run src/components/admin/__tests__/MarketContent.test.tsx` + existing admin tests green.
```bash
cd /Users/leeashmore/investikid && git add frontend/src/api/admin.ts frontend/src/components/admin frontend/src/locales/en/admin.json && git commit -m "feat(market): proactive module suggestions + create + native-gen + adaptation badge

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Full verification + promote

- [ ] **Step 1: Backend** — `cd backend && ruff check . && pytest -q`. All green. Regression: generic + GB-adapt generation byte-identical (only the native `elif` added); draft-list still works.
- [ ] **Step 2: Frontend** — `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`. Green; `no-literal-string` clean.
- [ ] **Step 3: iOS sync** — `cd frontend && npm run build && npx cap sync ios` (admin UI is web; keep the bundle synced).
- [ ] **Step 4: Push + green CI** — `git push origin testing`.
- [ ] **Step 5: Promote** — **No migration → no snapshot question.** Merge testing → staging → main on green CI; then the manual Vercel prod deploy for the admin UI. Verify `/health` 200. Operator note: the suggester + native gen + adaptation badge are live in the admin Market Content page.

---

## Self-Review

**Spec coverage:**
- Unit 1 adaptation guard (residue) → Task 1. ✓
- Unit 2 module suggester → Task 3. ✓
- Unit 3 create-from-suggestion → Task 4. ✓
- Unit 4 market-native generation → Task 2. ✓
- Unit 5 frontend → Task 5. ✓
- Non-goals: no auto-publish/auto-delete (replace just creates + flags); GB-adapt + generic modes unchanged; no migration. ✓
- Rollout: no migration, admin-only, testing→staging→main, Vercel → Task 6. ✓

**Placeholder scan:** Full code for the residue checker, native prompt mode + generator, suggester, and create endpoint; the draft-list flag wiring + frontend are precise read-then-mirror against named seams (`_concat_text`, `LessonDraftOut`, the existing draft-review component). No TBDs.

**Type/name consistency:** `find_uk_residue` (Task 1) used in the draft-list (Task 1) + frontend badge (Task 5). `AdaptationFlags`/`adaptation_flags` (Task 1) ↔ frontend type (Task 5). `_system_prompt` native `elif` (Task 2) consumed by `generate_native_level_lessons` (Task 2) ↔ `generate-native` endpoint ↔ `useGenerateNativeLessons` (Task 5). `suggest_modules`/`ModuleSuggestion` (Task 3) ↔ `from-suggestion`/`CuratedModuleSuggestion` (Task 4) ↔ frontend hooks (Task 5). `require_verified_brief` gates suggester + native gen. No migration.
