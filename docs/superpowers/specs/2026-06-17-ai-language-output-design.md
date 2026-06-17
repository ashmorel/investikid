# AI Language Output — Design Spec (Sub-project B)

**Date:** 2026-06-17
**Status:** Approved (design); ready for implementation plan
**Programme:** Multi-language + multi-market localization (Sub-project B)

---

## Programme context

This is **Sub-project B** of the localization programme. Predecessors live in prod:
- **A (i18n foundation):** per-user `users.language` (`en`, `es`, `fr`, `de`, `zh-Hant`, `zh-Hans`), language switcher, fully-extracted UI.
- **0 (Gemini lineup):** lite = Gemini 2.5 Flash-Lite, standard = Gemini 2.5 Flash, premium + quiz verifier = gpt-5-mini, Together fallback. All validated live.

B makes the language switch *visibly pay off*: every LLM surface responds in the user's selected language. It is the first feature to consume `users.language` on the AI side.

**Locked decision (kids'-safety posture):** Standard — rely on the existing (now multilingual) output moderation to gate all languages, proven by cross-language safety regression tests. No per-language model escalation. Authored fallback content stays English until Sub-project E.

## Goal

Thread each user's `language` preference into every LLM surface so the model replies entirely in that language, via a single central injection point, with no behavior change for English users and the existing safety moderation still gating all languages.

## Non-goals (YAGNI)

- No translation of the authored curriculum or stored content (that is Sub-project E). Authored **fallback** quiz questions remain English.
- No UI-string translation (Sub-project A, already shipped).
- No new model tiers or per-language model escalation (Standard posture).
- No change to which surfaces use the LLM; only what language they answer in.

---

## Architecture

### Unit 1 — Language directive (`app/core/languages.py`)

Extend the existing supported-languages registry with a `prompt_name` per language and add a pure helper:

- `prompt_name` values: `en`→"English", `es`→"Spanish", `fr`→"French", `de`→"German", `zh-Hant`→"Traditional Chinese (繁體中文)", `zh-Hans`→"Simplified Chinese (简体中文)".
- `language_directive(code: str) -> str`:
  - Returns `""` for `en` or any unknown/empty code (**no-op** — no behavior or token change for English users; unknown codes degrade safely to English).
  - Otherwise returns a directive string, e.g.:
    > `"Always respond entirely in {prompt_name}. Translate all examples and explanations into {prompt_name}. Keep proper nouns, company names, and ticker symbols unchanged. Respond in {prompt_name} regardless of the language the user writes in."`

**Interface:** `language_directive(code) -> str`. Depends only on the registry. The set language is authoritative — the AI answers in it regardless of the input language.

### Unit 2 — Central injection (`app/services/guardrails.py`)

Change the universal chokepoint:

```python
def with_guardrail_preamble(system_prompt: str, *, language: str = "en") -> str:
    directive = language_directive(language)
    body = f"{GUARDRAIL_PREAMBLE}\n\n{system_prompt}"
    return f"{body}\n\n{directive}" if directive else body
```

- Default `language="en"` makes the change backward-compatible: any caller not yet passing a language is unaffected (English no-op).
- The directive is appended **after** the safety preamble and the surface's own system prompt, so it never weakens the safety/topical guardrails — it only constrains output language.

### Unit 3 — Threading `language` to call sites

Every `with_guardrail_preamble(...)` call passes the user's language. There are **11** call sites across 7 modules, in two groups:

**Already have the `User` object** — pass `user.language`:
- `tutor_service.py` (Coach Penny) — has `user`.
- `coach_service.py` (home Coach) — has `user`.
- `chart_coach_service.py` (simulator coach) — has `user`.
- `ai_content_service.generate_practice_quiz` (quiz + Revise generation) — has `user`.

**Need a `language` parameter threaded from the router** (sourced from `current_user.language`):
- `home_greeting_service.generate_home_greeting(...)` — add `language: str` param; caller passes `current_user.language` (1 call site).
- `tips_service.generate_personalised_tips(...)` and `generate_generic_tips(...)` — add `language: str`; callers pass `current_user.language` (2 call sites).
- `simulator.py` — the 4 LLM call sites build the system prompt in the endpoint where `current_user` is in scope; pass `current_user.language` (4 call sites).

(Group totals: 4 already-have-`user` + 7 threaded = 11 call sites.)

No call site constructs the directive itself; they only forward the code into `with_guardrail_preamble`.

### Unit 4 — Moderation (unchanged code, new tests)

`moderate_output(text, *, surface)` is **not changed**. Rationale: the moderation model is now multilingual (Gemini Flash), so it classifies unsafe content in any language. We prove this with regression tests (Unit 6).

**Documented limitation:** the input-side `screen_input` (prompt-injection / off-topic screening) is English-centric (keyword/pattern based). Output moderation is the authoritative safety net and is language-agnostic, so unsafe model output is still blocked in any language. Hardening `screen_input` for non-English input is out of scope for B (candidate follow-up).

---

## Data flow

```
Request → router has current_user (current_user.language)
        → service builds system_prompt
        → with_guardrail_preamble(system_prompt, language=current_user.language)
             = SAFETY_PREAMBLE + system_prompt + language_directive(language)
        → LLM (Gemini/gpt-5-mini) replies in the target language
        → moderate_output(reply, surface=...) gates it (multilingual)
        → reply served, or safe fallback on block
```

## Error handling / edge cases

- **English / unknown code:** `language_directive` returns `""` → no directive → identical to today.
- **Authored fallback (non-English user):** when LLM generation fails/unverified and `_safe_cached_or_fallback` serves the authored English question, the child sees one English question. Accepted; resolved by Sub-project E.
- **Moderation block in another language:** the existing safe-fallback path runs as today (the fallback text is currently English — same boundary as above, acceptable for B).
- **Premium home greeting:** it is hardcoded premium for all users; the language directive applies there too (greeting in the user's language).

## Testing strategy

- **Directive unit tests:** `language_directive("en") == ""`; `language_directive("es")` contains "Spanish"; `zh-Hant` contains "Traditional"; unknown code → `""`.
- **Injection test:** `with_guardrail_preamble(p, language="es")` contains the Spanish directive and still contains the safety preamble; `language="en"` equals the old output exactly (no-op regression).
- **Per-surface threading tests:** for each of the 9 call sites, assert (with the LLM client mocked) that the system prompt passed to the client contains the language directive when the user's language is non-English. Mirror existing service tests.
- **Cross-language moderation regression:** unsafe Spanish and unsafe Chinese model output is still blocked by `moderate_output` (mock the moderation model to classify unsafe, assert block + audit). Confirms the safety net holds across languages.
- **Full backend suite + `ruff` green;** CI's full run is authoritative.

## Definition of done

1. A user with `language != "en"` receives AI responses (Coach Penny, home Coach, quiz/Revise generation, tips, greeting, simulator coach) in that language.
2. English users see byte-identical behavior to before (no-op directive).
3. The directive is injected from one place (`with_guardrail_preamble`); no surface constructs it independently.
4. Output moderation still blocks unsafe content in non-English languages (regression tests prove it).
5. All backend tests + ruff green; promoted testing → staging → main.

## Rollout / safety

- Backend-only, **no DB migration** (language column already exists from Sub-project A) → no prod snapshot needed.
- Behaviorally inert for the current all-English user base (directive is a no-op for `en`); activates per user as languages are selected.
- Promote testing → staging → main on green CI per the standard flow.
