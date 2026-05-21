# Kid-Safe AI Output Moderation Design (Sub-project 4a — closes LLM-03)

## Goal

Add a single, auditable moderation seam that every piece of LLM-generated text passes through before it reaches a child, replacing the two duplicated narrow advice-only regex filters and covering the surfaces that currently have no filter at all. This closes the deferred **LLM-03** finding (High: model output shown to children has no genuine kid-safe moderation).

This is sub-project 4a of the programme. Sub-projects 1 (Compliance), 2 (Security), 3 (Tier system) are shipped. Engagement features (topic-path personalisation, AI-refreshed content, premium content depth) are sub-project **4b** and are explicitly out of scope here — 4a ships first so every new AI surface in 4b is automatically moderated.

## Motivation

Current state (verified): `tutor_service.py` and `chart_coach_service.py` each have a *duplicated* `_ADVICE_PATTERNS` regex + `safety_filter`/`_safety_filter` that only catches financial-advice phrasing and rewrites it; `ai_content_service.py` (quiz generation) and the investing-tips path have **no** output moderation. For a children's financial-education app, model output reaching a child with no coverage for sexual / violent / hateful / self-harm / illegal / PII content is a real safety gap (LLM-03, rated High, deferred from sub-project 2 with an explicit "prioritise early in 4" instruction).

## Locked Decisions

| Decision | Choice |
|---|---|
| Mechanism | Hybrid: cheap deterministic prefilter blocks obvious unsafe output instantly; only *ambiguous* output escalates to a moderation-model call; results cached |
| Failure mode | **Fail-closed** — on classification doubt OR moderation-step error/timeout, suppress model output and return a safe canned fallback |
| Chokepoint | **Single seam over ALL model output** — tutor chat, chart-coach chat, ai_content quiz, investing tips, and any future 4b surface |
| Categories | Full kid-safety set: sexual, violence/graphic, hate/harassment, self-harm, illegal/dangerous acts, PII solicitation/leakage, off-topic/prompt-injection elicitation, and the existing "no real financial advice" (subsumed at behavioural parity) |
| Architecture | **Approach A** — dedicated `app/services/moderation.py` with an explicit `moderate_output()` seam |

## Architecture

### Approach A: dedicated moderation service + explicit seam

A single module, `app/services/moderation.py`, owns all kid-safety policy. Every AI service calls it on the model's output before returning to the caller. Kid-safety policy stays in a dedicated, testable, auditable safety module — not buried in generic transport (`llm_client`) and not hidden behind a decorator.

```python
@dataclass(frozen=True)
class ModerationResult:
    safe: bool
    category: str | None        # the blocking category when not safe, else None
    text: str                   # original text if safe, else the surface safe-fallback

def moderate_output(text: str, *, surface: str) -> ModerationResult: ...
```

- **Prefilter** (in-process, no network): per-category compiled lexicons/regexes. Any match → `safe=False`, `category=<name>`, `text=<surface fallback>`. No model call.
- **Escalation**: if the prefilter is clean but the text trips an *ambiguity heuristic* (contains risky-but-context-dependent tokens, or anomalous structure), call a moderation-model pass reusing the existing OpenAI key/`llm_client` infra (no new dependency). Cache the verdict by `(sha256(text), surface)` with a TTL (mirrors the existing 1-hour investing-tips cache pattern).
- **Fail-closed**: any exception in prefilter, any escalation error/timeout/garbled verdict → `safe=False`, `category="error"`, `text=<surface fallback>`.

`surface` ∈ `{"tutor", "chart_coach", "quiz", "tips"}` (extensible). It selects the kid-friendly fallback copy and is recorded in the audit row.

**Why A:** matches the locked decisions exactly (single explicit seam); removes the duplicated `_ADVICE_PATTERNS`; covers the currently-unmoderated quiz/tips; keeps safety policy auditable and unit-testable in isolation; no layering smell (transport stays generic); structured-output (quiz JSON) and per-surface fallbacks need surface-awareness that a generic `llm_client` wrapper or opaque decorator shouldn't carry.

## Components

### §1 Moderation core — `app/services/moderation.py` (Create)

- `ModerationResult` (frozen dataclass as above) and `moderate_output(text, *, surface) -> ModerationResult`.
- **Category lexicons**: a module-level dict `_CATEGORY_PATTERNS: dict[str, re.Pattern]` for: `sexual`, `violence`, `hate`, `self_harm`, `illegal_dangerous`, `pii` (email / phone / street-address / full-name-solicitation patterns), `prompt_injection` (markers like "ignore previous instructions", "system prompt", role-play escapes), and `financial_advice` (ported verbatim from the existing `_ADVICE_PATTERNS` so behaviour is preserved). Patterns must be **precision-tuned for a finance-education context** — see §6 over-block corpus.
- **Ambiguity heuristic** `_needs_escalation(text) -> bool`: conservative — returns True only when the text contains tokens that are risky-but-context-dependent (a small curated "review" lexicon) OR exceeds a structural anomaly check; the overwhelming majority of grounded educational output returns False and never triggers a model call.
- **Escalation** `_model_moderation(text) -> bool` (safe?): one call via the existing OpenAI client (the project already configures an OpenAI key/`llm_client`); a tight system prompt asking for a strict JSON verdict `{"safe": bool, "category": str|null}` over the kid-safety categories. Timeout (short, e.g. 5s) and any non-conforming/raw response ⇒ treated as unsafe (fail-closed).
- **Cache**: `_verdict_cache: dict[tuple[str,str], tuple[float, ModerationResult]]`, TTL constant (reuse the tips-cache TTL convention); key `(sha256(text).hexdigest(), surface)`. Only escalated verdicts are cached (prefilter is already fast). Cache never stores raw unsafe text beyond the hash key.
- **Fallbacks**: `_SAFE_FALLBACKS: dict[str, str]` per surface, kid-friendly redirect copy (e.g. tutor → "Let's get back to your lesson — ask me about what we're learning!"; chart_coach → "Let's look at the chart together — what do you notice about the line?"; quiz/tips → a neutral safe default).
- No raw unsafe text or PII is logged anywhere in this module.

### §2 Single-seam wiring (Modify the AI services)

- `tutor_service.py`: delete `_ADVICE_PATTERNS` + `safety_filter`; at the point it currently calls `safety_filter(raw_response)`, call `moderate_output(raw_response, surface="tutor")` and return `result.text` (the model text if safe, else the fallback). The tutor streaming path must **buffer the full response and moderate before emitting** — never stream unmoderated tokens to a child; if the surface streams, assemble then moderate then send (or send the fallback).
- `chart_coach_service.py`: delete `_ADVICE_PATTERNS` + `_safety_filter`; same replacement with `surface="chart_coach"`.
- `ai_content_service.py` (quiz): after generating the quiz, moderate the concatenated user-facing fields (question + each choice + explanation) with `surface="quiz"`. If unsafe: regenerate once; if still unsafe, return the existing deterministic safe-quiz fallback the service already has. The structured JSON is never shown raw — only validated fields, moderated.
- Investing-tips path (`ai_content_service.py` or wherever tips are produced): moderate the concatenated tip text with `surface="tips"`; on unsafe, drop to the existing hardcoded fallback tips.
- Net effect: one safety policy module; the two duplicated regex filters are gone (DRY); quiz + tips gain coverage they never had.

### §3 Categories & parity

- Document the full category set and each lexicon's intent in the module docstring + a short `docs/security/ai-moderation.md` note (what is blocked, the fail-closed contract, how to tune a lexicon, escalation/caching behaviour).
- **Financial-advice parity is a hard requirement**: the ported `financial_advice` pattern must reproduce the prior `safety_filter`/`_safety_filter` blocking behaviour so the existing tutor/chart-coach advice tests pass unchanged (the old filters *rewrote* advice to a canned line; the new seam *blocks* and returns the surface fallback — if any existing test asserts the specific old rewrite string, that test encodes superseded behaviour: update it minimally to assert the new safe-fallback contract and report it; do NOT weaken the safety assertion).

### §4 Fail-closed UX + audit

- Unsafe ⇒ the caller returns the surface's safe-fallback text, never the raw model output, with a normal 200 (the child sees a gentle redirect, not an error).
- Write one `AuditLog` row: `event_type="moderation_block"`, `metadata_json={"surface": surface, "category": category}` — **no raw text, no PII, no user message content**. (Reuse the `AuditLog.metadata_json` JSON column established in sub-project 3.) `user_id` set when the surface has an authenticated child in scope.
- Streaming: assembled-then-moderated; a blocked stream yields only the fallback.

### §5 Performance / cost

- Prefilter is O(len(text)) compiled-regex, in-process — the fast path for essentially all grounded educational output (no network, sub-millisecond).
- Escalation fires only on the conservative ambiguity heuristic and is cached → the moderation-model call is rare and amortised. Reuses the existing provider/key — no new external dependency, no new secret.
- Short escalation timeout with fail-closed keeps worst-case latency bounded and safe.

### §6 Testing

- **Unit — blocking**: representative unsafe sample per category (`sexual`, `violence`, `hate`, `self_harm`, `illegal_dangerous`, `pii`, `prompt_injection`, `financial_advice`) → `safe=False`, correct `category`, `text == surface fallback`.
- **Unit — over-block guard (critical for a finance app)**: a positive corpus of legitimate educational lines that MUST pass `safe=True` unchanged — e.g. "Stocks can go down as well as up, and you can lose money.", "Diversifying means not putting all your eggs in one basket.", "A loss happens when you sell for less than you paid.", "Compound interest means your money can grow over time." Over-blocking educational content is a failure.
- **Unit — fail-closed**: monkeypatch the escalation call to raise/timeout/return garbage → result is `safe=False` with the fallback (never the raw text).
- **Unit — cache**: identical (text, surface) escalation is served from cache (escalation invoked once).
- **Parity**: the existing tutor + chart-coach advice tests pass (financial-advice still blocked); any test asserting the *old rewrite string* is minimally updated to the new safe-fallback contract and reported.
- **Integration**: tutor / chart-coach / quiz endpoints return the safe fallback (not model text) when moderation flags (inject an unsafe model response via the existing LLM mock); an `AuditLog moderation_block` row is written with surface+category and **no** sensitive content; tips path falls back to hardcoded tips on unsafe.
- **Regression**: full backend suite green; ruff clean; the `entitlements`/tier work and all prior suites unaffected.

## Error Handling / Edge Cases

- Escalation model returns malformed/empty/non-JSON → fail-closed (unsafe).
- Empty / whitespace-only model output → treated as unsafe-ish: return the surface fallback (a blank answer to a child is a poor experience; the fallback is the safe default). Document this.
- Over-block risk: the lexicons must be precision-tuned and proven against the §6 educational positive corpus; a finance lesson legitimately discusses losing money, risk, debt, tax, crypto — these must not trip `self_harm`/`illegal_dangerous`/`violence`.
- Quiz: only the validated user-facing fields are moderated; if the model returned unparseable JSON that path already falls back independently of moderation — keep that, then also moderate the fallback's dynamic parts if any.
- The audit write must never itself surface raw unsafe content (only surface + category enum).

## Out of Scope

- Input-side prompt-injection *hardening* of the prompts themselves (output moderation only here; deeper input hardening is a later/security concern).
- All sub-project 4b engagement features: topic-path personalisation, AI-refreshed non-repetitive content, premium content depth.
- Changing model providers or the tiered `llm_client` routing.
- A human moderation-review queue / dashboard (note as a future enhancement).

## File Map (indicative)

| File | Action |
|---|---|
| `backend/app/services/moderation.py` | Create — `moderate_output`, lexicons, escalation, cache, fallbacks |
| `backend/app/services/tutor_service.py` | Modify — drop `_ADVICE_PATTERNS`/`safety_filter`; route via `moderate_output(surface="tutor")`; buffer-then-moderate streaming |
| `backend/app/services/chart_coach_service.py` | Modify — drop `_ADVICE_PATTERNS`/`_safety_filter`; route via `moderate_output(surface="chart_coach")` |
| `backend/app/services/ai_content_service.py` | Modify — moderate quiz fields (`surface="quiz"`) + tips (`surface="tips"`), regenerate-once-then-fallback |
| `backend/app/models/audit.py` | Reuse (no schema change) — `moderation_block` event via existing `metadata_json` |
| `docs/security/ai-moderation.md` | Create — what's blocked, fail-closed contract, tuning/escalation/caching |
| `docs/security/audit-2026-05.md` | Modify — mark LLM-03 status Resolved (4a) |
| `backend/tests/test_moderation.py` | Create — blocking, over-block corpus, fail-closed, cache |
| `backend/tests/test_tutor_service.py` / `test_chart_coach*` / `test_ai_content_service.py` | Modify — parity + integration via existing LLM mocks |

The exact lexicon contents and the precise ambiguity heuristic are finalised in the implementation plan against the real existing `_ADVICE_PATTERNS` and the educational positive corpus.
