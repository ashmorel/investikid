# AI Language Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every LLM surface respond in the user's selected language by injecting a language directive from one central chokepoint (`with_guardrail_preamble`) and threading `language` to all 11 call sites; English is a no-op.

**Architecture:** Add `language_directive(code)` to the language registry. Extend `with_guardrail_preamble(system_prompt, *, language="en")` to append the directive (no-op for English). Thread `user.language` / `current_user.language` into all 11 call sites. Output moderation is unchanged (multilingual) and proven by cross-language regression tests.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Pydantic; pytest (async via `loop_scope="session"`). Backend only, no DB migration.

**Spec:** `docs/superpowers/specs/2026-06-17-ai-language-output-design.md`

**Branch:** `testing` (promote testing → staging → main on green CI; backend-only, **no migration → no snapshot needed**).

**Commands:** tests `/Users/leeashmore/Local Repo/.venv/bin/pytest` · lint `/Users/leeashmore/Local Repo/.venv/bin/ruff check .` (run from `backend/`).

---

## File Structure
- `backend/app/core/languages.py` — add `prompt_name` to the registry + `language_directive()`.
- `backend/app/services/guardrails.py` — `with_guardrail_preamble` gains a `language` kwarg.
- `backend/app/services/{tutor_service,coach_service,chart_coach_service,ai_content_service}.py` — pass `user.language` at the call site.
- `backend/app/services/home_greeting_service.py` + `backend/app/routers/ai.py` — greeting gains a `language` param, caller passes `current_user.language`.
- `backend/app/services/tips_service.py` + `backend/app/routers/simulator.py` — both tips functions gain a `language` param; callers pass `current_user.language`.
- `backend/app/routers/simulator.py` — 4 LLM call sites pass `current_user.language`.
- `backend/tests/test_languages_registry.py`, `tests/test_guardrails*.py`, per-service test files, `tests/test_moderation*.py` — tests.

---

### Task 1: Language directive helper

**Files:**
- Modify: `backend/app/core/languages.py`
- Test: `backend/tests/test_languages_registry.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_languages_registry.py`)

```python
from app.core.languages import language_directive


def test_language_directive_english_is_noop():
    assert language_directive("en") == ""


def test_language_directive_unknown_is_noop():
    assert language_directive("xx") == ""
    assert language_directive("") == ""


def test_language_directive_non_english_names_the_language():
    es = language_directive("es")
    assert "Spanish" in es
    assert language_directive("fr").count("French") >= 1
    assert "German" in language_directive("de")


def test_language_directive_distinguishes_chinese_scripts():
    assert "Traditional Chinese" in language_directive("zh-Hant")
    assert "Simplified Chinese" in language_directive("zh-Hans")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_languages_registry.py -q`
Expected: FAIL (`ImportError: cannot import name 'language_directive'`).

- [ ] **Step 3: Implement** — replace the registry + add the helper in `app/core/languages.py`

```python
SUPPORTED_LANGUAGES: list[dict[str, str | bool]] = [
    {"code": "en", "endonym": "English", "prompt_name": "English", "available": True},
    {"code": "es", "endonym": "Español", "prompt_name": "Spanish", "available": False},
    {"code": "fr", "endonym": "Français", "prompt_name": "French", "available": False},
    {"code": "de", "endonym": "Deutsch", "prompt_name": "German", "available": False},
    {"code": "zh-Hant", "endonym": "繁體中文", "prompt_name": "Traditional Chinese (繁體中文)", "available": False},
    {"code": "zh-Hans", "endonym": "简体中文", "prompt_name": "Simplified Chinese (简体中文)", "available": False},
]

_CODES = frozenset(lang["code"] for lang in SUPPORTED_LANGUAGES)
_PROMPT_NAMES: dict[str, str] = {
    str(lang["code"]): str(lang["prompt_name"]) for lang in SUPPORTED_LANGUAGES
}


def is_supported_language(code: str) -> bool:
    return code in _CODES


def language_directive(code: str) -> str:
    """A system-prompt directive instructing the model to reply in `code`'s
    language. Returns "" for English or any unknown/empty code (no-op), so
    English users see byte-identical prompts and unknown codes degrade to English.
    """
    if code == "en":
        return ""
    name = _PROMPT_NAMES.get(code)
    if not name:
        return ""
    return (
        f"Always respond entirely in {name}. Translate all examples and "
        f"explanations into {name}. Keep proper nouns, company names, and ticker "
        f"symbols unchanged. Respond in {name} regardless of the language the "
        f"user writes in."
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_languages_registry.py -q && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check app/core/languages.py`
Expected: PASS; ruff clean. (The existing frontend-parity test still passes — it only checks codes, which are unchanged.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/languages.py backend/tests/test_languages_registry.py
git commit -m "feat(i18n): language_directive() + prompt_name in registry

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Central injection in `with_guardrail_preamble`

**Files:**
- Modify: `backend/app/services/guardrails.py`
- Test: `backend/tests/test_guardrails.py` (or wherever `with_guardrail_preamble` is tested — grep first)

- [ ] **Step 1: Write the failing test**

Find the existing guardrails test file (`grep -rl with_guardrail_preamble backend/tests`). Add:

```python
from app.services.guardrails import GUARDRAIL_PREAMBLE, with_guardrail_preamble


def test_preamble_english_is_unchanged_noop():
    # Backward-compatible: default language and explicit "en" both equal the old output.
    expected = f"{GUARDRAIL_PREAMBLE}\n\nSYS"
    assert with_guardrail_preamble("SYS") == expected
    assert with_guardrail_preamble("SYS", language="en") == expected


def test_preamble_appends_language_directive_for_non_english():
    out = with_guardrail_preamble("SYS", language="es")
    assert GUARDRAIL_PREAMBLE in out  # safety preamble still present
    assert "SYS" in out
    assert "Spanish" in out  # directive appended
    # directive comes AFTER the surface prompt
    assert out.index("SYS") < out.index("Spanish")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_guardrails.py -q` (use the real filename)
Expected: FAIL (`with_guardrail_preamble() got an unexpected keyword argument 'language'`).

- [ ] **Step 3: Implement** in `app/services/guardrails.py`

Add the import at the top (with the other imports):
```python
from app.core.languages import language_directive
```
Replace the function:
```python
def with_guardrail_preamble(system_prompt: str, *, language: str = "en") -> str:
    """Prepend the shared guardrail preamble to a surface's system prompt, and
    append a language directive so the model replies in the user's language.
    `language` defaults to "en" (no-op) for backward compatibility."""
    body = f"{GUARDRAIL_PREAMBLE}\n\n{system_prompt}"
    directive = language_directive(language)
    return f"{body}\n\n{directive}" if directive else body
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_guardrails.py -q && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check app/services/guardrails.py`
Expected: PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/guardrails.py backend/tests/test_guardrails.py
git commit -m "feat(i18n): with_guardrail_preamble injects language directive

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Thread the 4 surfaces that already have `user`

**Files:**
- Modify: `backend/app/services/tutor_service.py:175`, `coach_service.py:289`, `chart_coach_service.py:133`, `ai_content_service.py:173`
- Test: the existing test file for each service (grep e.g. `tests/test_tutor_service.py`, `tests/test_coach_service.py`, `tests/test_chart_coach*.py`, `tests/test_ai_content_service.py`)

Each of these surfaces has the authenticated `user` in scope. Add `language=user.language` to the `with_guardrail_preamble(...)` call. Exact edits:

- `tutor_service.py` (~line 175):
```python
    system_prompt = with_guardrail_preamble(
        _SYSTEM_PROMPT_TEMPLATE.format(
            skill_level_instruction=_SKILL_INSTRUCTIONS[level],
            lesson_content=json.dumps(lesson.content_json or {}),
        ) + _build_weak_concept_addendum(weak_concepts),
        language=user.language,
    )
```
- `coach_service.py` (~line 289):
```python
    system_prompt = with_guardrail_preamble(
        f"{system_prompt}\n\n{AGE_REGISTER_DIRECTIVE[user.age_tier]}",
        language=user.language,
    )
```
- `chart_coach_service.py` (~line 133):
```python
    system_prompt = with_guardrail_preamble(
        _build_system_prompt(age, ticker, name, period, stats),
        language=user.language,
    )
```
- `ai_content_service.py` (~line 173, inside `generate_practice_quiz`, which has `user`):
```python
            raw = await client.complete(
                system_prompt=with_guardrail_preamble(_SYSTEM_PROMPT, language=user.language),
                messages=[{"role": "user", "content": user_message}],
                temperature=0.3,
                max_tokens=400,
                response_format="json",
            )
```

- [ ] **Step 1: Write the failing threading tests**

For each service, add a test that spies on the surface's imported `with_guardrail_preamble` and asserts it received the user's language. Pattern (adapt to each service's existing fixtures; set the fixture user's `language = "es"`):

```python
async def test_tutor_threads_language_into_preamble(db_session, ...fixtures):
    user, lesson, ... = ...
    user.language = "es"
    with patch("app.services.tutor_service.with_guardrail_preamble",
               wraps=tutor_service.with_guardrail_preamble) as spy, \
         patch("app.services.tutor_service.get_llm_client", return_value=mock_client):
        await tutor_service.<entry_fn>(...)
    assert spy.call_args.kwargs.get("language") == "es"
```
(For `ai_content_service`, the entry is `generate_practice_quiz(..., user=user, premium=False)`; mirror the existing test setup in `tests/test_ai_content_service.py` and patch both `get_llm_client` and `get_strict_premium_client` as those tests already do, and set `user.language="es"`, then assert the spy got `language="es"`. Note generation only runs when a strict premium client exists — patch it to a mock so the LLM path runs.)

Use the real entry-point function name for each service (read the file to find it: tutor has the tutor chat entry, coach has `coach_chat`, chart_coach has `chart_coach_chat`).

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && "/Users/leeashmore/Local Repo/.venv/bin/pytest" tests/test_tutor_service.py tests/test_coach_service.py tests/test_chart_coach_service.py tests/test_ai_content_service.py -q` (use the real filenames)
Expected: FAIL (spy got `language` absent / default `"en"`, not `"es"`).

- [ ] **Step 3: Apply the 4 edits above.**

- [ ] **Step 4: Run the tests to verify they pass**

Run the same command.
Expected: PASS. Also run the FULL affected suites to confirm no regression (the added kwarg is backward-compatible).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/tutor_service.py backend/app/services/coach_service.py backend/app/services/chart_coach_service.py backend/app/services/ai_content_service.py backend/tests/
git commit -m "feat(i18n): Coach/quiz surfaces reply in user's language

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Thread the home greeting

**Files:**
- Modify: `backend/app/services/home_greeting_service.py` (signature + the `with_guardrail_preamble` call in `_build_messages`)
- Modify: `backend/app/routers/ai.py:178` (caller)
- Test: greeting service test file (grep `tests/test_home_greeting*` / `tests/test_greeting*`)

- [ ] **Step 1: Write the failing test**

```python
async def test_greeting_threads_language():
    with patch("app.services.home_greeting_service.with_guardrail_preamble",
               wraps=home_greeting_service.with_guardrail_preamble) as spy, \
         patch("app.services.home_greeting_service.get_llm_client", return_value=mock_client), \
         patch("app.services.home_greeting_service.moderate_output", <safe mock>):
        await home_greeting_service.generate_home_greeting(
            name="Sam", mode="lesson", lesson_label=None, streak_count=1,
            due_count=0, tier=<AgeTier>, language="fr",
        )
    assert spy.call_args.kwargs.get("language") == "fr"
```
(Mirror the existing greeting test setup. The function currently raises on moderation/provider failure, so mock the client + moderation to succeed.)

- [ ] **Step 2: Run it — FAIL** (`generate_home_greeting() got an unexpected keyword argument 'language'`).

- [ ] **Step 3: Implement**

In `home_greeting_service.py`, add `language: str = "en"` to the `generate_home_greeting` signature (keyword-only block, end of the params) and to `_build_messages` if that's where the preamble is built. The `_build_messages` returns `with_guardrail_preamble(system_prompt), messages` — change to:
```python
    return with_guardrail_preamble(system_prompt, language=language), messages
```
and thread `language` from `generate_home_greeting` into `_build_messages(..., language=language)`.

In `app/routers/ai.py` at the `generate_home_greeting(` call (~line 178), add `language=current_user.language,` to the kwargs (the endpoint has `current_user` in scope — confirm by reading the handler).

- [ ] **Step 4: Run the test — PASS.** Run the greeting suite + the `ai.py` route tests for the greeting endpoint to confirm no regression.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/home_greeting_service.py backend/app/routers/ai.py backend/tests/
git commit -m "feat(i18n): home greeting in user's language

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Thread the tips surfaces

**Files:**
- Modify: `backend/app/services/tips_service.py` (`generate_generic_tips` ~line 73, `generate_personalised_tips` ~line 136; their `with_guardrail_preamble` calls at ~84 and ~161)
- Modify: `backend/app/routers/simulator.py:571` (`generate_generic_tips()` caller) and `:592` (`generate_personalised_tips(...)` caller)
- Test: tips service test file (grep `tests/test_tips*`)

- [ ] **Step 1: Write the failing tests**

```python
async def test_generic_tips_threads_language():
    with patch("app.services.tips_service.with_guardrail_preamble",
               wraps=tips_service.with_guardrail_preamble) as spy, \
         patch("app.services.tips_service.get_llm_client", return_value=mock_client), \
         patch("app.services.tips_service.moderate_output", <safe mock>):
        await tips_service.generate_generic_tips(language="de")
    assert spy.call_args.kwargs.get("language") == "de"


async def test_personalised_tips_threads_language():
    with patch("app.services.tips_service.with_guardrail_preamble",
               wraps=tips_service.with_guardrail_preamble) as spy, \
         patch("app.services.tips_service.get_llm_client", return_value=mock_client), \
         patch("app.services.tips_service.moderate_output", <safe mock>):
        await tips_service.generate_personalised_tips(
            user_id=1, holdings=[("AAPL", "Apple")], stage="active", age=12, language="de",
        )
    assert spy.call_args.kwargs.get("language") == "de"
```

- [ ] **Step 2: Run them — FAIL** (unexpected `language` kwarg).

- [ ] **Step 3: Implement**

In `tips_service.py`:
- `generate_generic_tips` — add a keyword param `language: str = "en"`; change the call at ~line 84 to `with_guardrail_preamble(_TIPS_PROMPT, language=language)`.
- `generate_personalised_tips` — add `language: str = "en"` to its keyword-only params; change ~line 161 to `with_guardrail_preamble(_personal_prompt(holdings, stage, age), language=language)`.

In `app/routers/simulator.py`:
- line ~571 → `generic = await generate_generic_tips(language=current_user.language)`
- line ~592 → add `language=current_user.language,` to the `generate_personalised_tips(...)` kwargs.
(Confirm `current_user` is the parameter name in those endpoints; read the handlers.)

- [ ] **Step 4: Run the tests — PASS.** Run the tips suite + simulator route tests for the tips endpoints to confirm no regression.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/tips_service.py backend/app/routers/simulator.py backend/tests/
git commit -m "feat(i18n): daily tips in user's language

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Thread the 4 simulator LLM call sites

**Files:**
- Modify: `backend/app/routers/simulator.py:252, 327, 399, 531`
- Test: simulator route tests (grep `tests/test_simulator*` for the relevant endpoints)

At each of the 4 `with_guardrail_preamble(...)` calls in `simulator.py`, add `language=current_user.language`. First read each handler to confirm the authenticated user parameter name (likely `current_user: User = Depends(get_current_user)`). Example for line ~252:
```python
            system_prompt=with_guardrail_preamble(system_prompt, language=current_user.language),
```
Apply the same to ~327, ~399, and ~531 (the 531 call spans multiple lines — add the kwarg to the `with_guardrail_preamble(...)` call).

- [ ] **Step 1: Write the failing test(s)**

For at least one representative simulator LLM endpoint (e.g. the one at line ~252), add a route or service test that sets the user's `language="zh-Hant"`, mocks the LLM client, spies on `simulator.with_guardrail_preamble`, and asserts `language == "zh-Hant"`. If the simulator endpoints are awkward to invoke in isolation, test via the existing simulator test client fixtures (mirror existing simulator tests) and assert the spy received the language for each of the 4 endpoints you can exercise.

- [ ] **Step 2: Run it — FAIL** (spy got default `"en"`).

- [ ] **Step 3: Apply the 4 edits.**

- [ ] **Step 4: Run the tests — PASS.** Run the full simulator suite to confirm no regression (these endpoints have NaN-guard + other logic — don't disturb it).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/simulator.py backend/tests/
git commit -m "feat(i18n): simulator AI surfaces in user's language

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Cross-language moderation regression tests

**Files:**
- Test: moderation test file (grep `tests/test_moderation*`)

`moderate_output` is **not changed** — these tests prove the multilingual model still blocks unsafe non-English output (the Standard safety posture's evidence).

- [ ] **Step 1: Write the tests**

Mirror the existing `moderate_output` tests (they mock the moderation model client to return an unsafe/safe classification). Add cases where the *input text to be moderated* is Spanish and Chinese unsafe content, and the mocked model classifies it unsafe → assert `result.safe is False` and the category surfaces; and a safe non-English case → `result.safe is True`. Example shape (adapt to the real mocking the existing tests use):

```python
async def test_moderation_blocks_unsafe_spanish_output(...):
    # mock the moderation model to classify the Spanish text as unsafe
    ... 
    result = await moderate_output("Deberías comprar acciones de Apple ahora mismo.", surface="quiz")
    assert result.safe is False

async def test_moderation_blocks_unsafe_chinese_output(...):
    ...
    result = await moderate_output("你现在应该马上买苹果股票。", surface="quiz")
    assert result.safe is False
```
(The point is the pipeline handles non-ASCII text end-to-end without error and honors the model's verdict — mock the model verdict as the existing tests do; do NOT make real LLM calls.)

- [ ] **Step 2: Run them — confirm they pass** (moderation already handles arbitrary text). If a test reveals a real encoding/handling bug, fix `moderate_output` minimally and note it.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/
git commit -m "test(i18n): cross-language output moderation regression

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Full verification + promote

- [ ] **Step 1: Full backend verification**

Run: `cd backend && "/Users/leeashmore/Local Repo/.venv/bin/ruff" check . && "/Users/leeashmore/Local Repo/.venv/bin/pytest" -q`
Expected: ruff clean; full suite passes. (If the local Postgres hangs ~90s+ on a DB test, it's environmental — rely on CI.)

- [ ] **Step 2: Push + green CI**

```bash
git push origin testing
```
Watch all 6 CI jobs (backend job is the relevant one; frontend jobs path-skip on a backend-only change).

- [ ] **Step 3: Promote testing → staging → main**

Merge testing → staging (watch CI green), then staging → main (watch CI green; Railway deploys the backend). **Backend-only, no migration → no snapshot prompt needed.** After deploy, confirm prod `/health` 200.

- [ ] **Step 4: Optional live check**

Set a test child's `language` to a non-English value (or note for the user) and confirm a Coach/quiz/tip response comes back in that language. (The user can verify in-app; not required for completion.)

---

## Self-Review

**Spec coverage:**
- Unit 1 directive helper → Task 1. ✓
- Unit 2 central injection (no-op for en, backward-compatible) → Task 2. ✓
- Unit 3 threading all 11 call sites → Tasks 3 (4 user-group), 4 (greeting, 1), 5 (tips, 2), 6 (simulator, 4) = 11. ✓
- Unit 4 moderation unchanged + cross-language regression tests → Task 7. ✓
- Non-goals (no curriculum/UI translation, no model escalation) → respected (only prompt-directive + threading; no model/tier changes). ✓
- English no-op / byte-identical → Task 2 explicit no-op test. ✓
- Backend-only, no migration, promote flow → Task 8. ✓

**Placeholder scan:** Core tasks (1, 2) carry complete code; threading tasks give exact before→after edits per call site. Test bodies for the threading/moderation tasks are patterns to adapt to each service's existing fixtures (the surrounding harness varies per file) — the assertion (`spy.call_args.kwargs["language"] == <code>`) is concrete, and the implementer is told to read each file's real entry-point/fixtures. This is intentional, not a placeholder: the exact fixture wiring already exists per service and must be mirrored, not reinvented.

**Type/name consistency:** `language_directive` (Task 1) consumed by `with_guardrail_preamble(..., language=...)` (Task 2), which every call site (Tasks 3–6) passes `user.language` / `current_user.language` into. `prompt_name` added to the registry dicts in Task 1 and read by `language_directive`. Signatures `generate_home_greeting(..., language="en")`, `generate_generic_tips(language="en")`, `generate_personalised_tips(..., language="en")` defined in Tasks 4/5 and called with `current_user.language` in the same tasks. Consistent.
