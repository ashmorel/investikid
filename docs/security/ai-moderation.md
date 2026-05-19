# AI Output Moderation — Kid-Safe Seam (sub-project 4a)

## Purpose

This document describes the unified kid-safe AI output moderation seam. It
closes finding **LLM-03** ("Kid-safety of model output") from the 2026-05
security audit: previously the only output filter was a narrow advice-only
regex duplicated across the tutor and chart-coach services, with the quiz and
investing-tips surfaces having no filter at all. Every piece of LLM-generated
text shown to a child now passes through one auditable seam before display.

## The single seam

All moderation goes through one function in
`backend/app/services/moderation.py`:

```python
async def moderate_output(text: str, *, surface: str) -> ModerationResult
```

`ModerationResult` is a frozen dataclass with three fields:

- `safe: bool` — whether the text may be shown to the child.
- `category: str | None` — the block reason when `safe` is `False`, else `None`.
- `text: str` — the original text when safe, or the surface-specific safe
  fallback copy when blocked. Callers always render `result.text`, so an unsafe
  response is never echoed.

The seam is pure: it performs no database access and no I/O other than the
escalation classifier call. Callers that hold a DB session are responsible for
writing the audit row (see Audit behaviour).

## The four surfaces and their fallback copy

`surface` selects the kid-friendly redirect shown instead of blocked output.
The supported surfaces and their fallback copy (`_SAFE_FALLBACKS`) are:

| Surface | Caller | Fallback copy |
|---|---|---|
| `tutor` | `tutor_service.chat` | "That's a great question! Let's get back to your lesson — ask a parent or teacher about real money decisions. 😊" |
| `chart_coach` | `chart_coach_service.chart_coach_chat` | "Let's look at the chart together — what do you notice about the line going up or down?" |
| `quiz` | `ai_content_service.generate_practice_quiz` | "Let's review the lesson and try a practice question from there." |
| `tips` | `simulator._generate_tips` | "Keep learning with your lessons — you're doing great!" |

An unknown surface falls back to a generic "Let's get back to learning!"
(`_DEFAULT_FALLBACK`), so the seam fails safe even if mis-called.

## Categories and what each blocks

The deterministic prefilter blocks the following categories. The first match
wins; `financial_advice` is checked first.

- **financial_advice** — imperative buy/sell/invest/trade directions
  ("you should buy/sell/invest/trade …") and named-asset directions
  ("buy/sell/invest in <Capitalised name or TICKER>"). This is the
  precision-tuned successor to the old duplicated advice regex: the named-asset
  arm requires a leading capital so it does not fire on generic phrasing such
  as "buy something" or "sell them".
- **sexual** — sexual or explicit-content terms.
- **violence** — kill/murder/stab/shoot/bomb/weapon and threats to hurt or
  attack a person.
- **hate** — dehumanising or hateful phrasing ("subhuman", "inferior race",
  "should be hated", slur references).
- **self_harm** — explicitly self-directed harm ("hurt yourself",
  "kill yourself", "end your life", "self-harm", "suicide"). Deliberately
  scoped so investing language ("lose money", "a loss") does not match.
- **illegal_dangerous** — explicit illicit instructions (buying illegal drugs,
  making a bomb or explosive, how to steal, hacking into a system).
- **pii** — email addresses, phone-like number runs, and street-address
  patterns, so the model cannot surface contact details to a child.
- **prompt_injection** — output echoing an override attempt ("ignore previous
  instructions", "system prompt", "you are now", "disregard the rules").

When the seam blocks via the escalation classifier rather than the prefilter,
the category is whatever the classifier returns, or `model_flagged` if it
flags unsafe without naming a category.

## Fail-closed contract

The seam fails closed. The child sees the surface fallback (never the raw
model text) in every one of these cases:

- **Empty / whitespace-only output** → blocked, `category="empty"`.
- **Any prefilter or internal error** → blocked, `category="error"`.
- **Escalation error or timeout** — the classifier raising, or exceeding the
  5-second escalation timeout → blocked, `category="error"`.
- **Ambiguous text the classifier judges unsafe** → blocked with the
  classifier's category.

Any unexpected exception anywhere in `moderate_output` is caught and converted
to a blocked `error` result with the surface fallback. There is no path that
returns raw model text on failure.

## Flow: deterministic prefilter → conservative escalation → TTL cache

1. **Empty check.** Empty or whitespace-only text is blocked immediately.
2. **Deterministic prefilter** (`_prefilter_category`). Pure regex, no
   network. The overwhelming majority of grounded educational output is
   cleared here on the fast path; obvious unsafe output is blocked here.
3. **Conservative escalation gate** (`_needs_escalation`). Only prefilter-clean
   text containing a small, deliberately narrow set of high-risk review tokens
   is escalated. The token set is intentionally minimal so normal
   finance-education lessons never escalate and stay on the deterministic fast
   path.
4. **TTL cache.** Escalation verdicts are cached by
   `(sha256(text), surface)` for one hour (`_CACHE_TTL`, mirroring the
   investing-tips cache convention). Repeated identical text is served from
   cache without a second classifier call.
5. **Escalation classifier** (`_model_moderation`). A strict-JSON
   child-safety classification using the existing `get_llm_client` infra
   (standard tier), bounded by a 5-second timeout. A non-conforming response
   raises, which the outer fail-closed handler turns into a blocked result.

## Tuning a lexicon without over-blocking finance-education content

The category lexicons and the escalation review-token set in
`moderation.py` are precision-tuned for a finance-education context. When
adjusting any pattern:

- **Never broaden a safety category so far that a known-unsafe sample passes.**
  Prefer making an unsafe pattern more specific over loosening it.
- **Guard against over-blocking with the positive corpus.** The
  finance-education positive corpus in
  `backend/tests/test_moderation.py` (`_EDU_CORPUS` →
  `test_educational_content_not_overblocked`) is the over-block guard. Every
  line in it must remain `safe=True` and pass through unchanged. It includes
  legitimate lessons about loss, debt, tax, crypto, gambling-as-risk,
  companies "dying out", and "drug store" retail — wording that a naive
  lexicon would wrongly flag.
- **Keep the genuine-block tests green.** `test_unsafe_text_blocked_with_category`
  and `test_genuine_financial_advice_still_blocked` must continue to block
  every unsafe sample with the correct category after any change.
- **Keep the escalation gate narrow.** Adding a bare finance-adjacent word to
  the review tokens would push normal lessons through escalation; in unit
  tests escalation fails closed and would wrongly block the corpus, which is
  the intended signal that the word does not belong there.

Run the full `tests/test_moderation.py` after every lexicon tweak. If a real
unsafe phrasing genuinely shares wording with an educational line, make the
unsafe pattern more specific rather than weakening the safety category.

## Audit behaviour

When the seam blocks, callers that hold a DB session write a single content-
free `AuditLog` row:

- `event_type = "moderation_block"`
- `metadata_json = {"surface": <surface>, "category": <category>}`

The row records the surface and category only. The raw model text and the
fallback copy are never stored, so no unsafe content or PII enters the audit
log.

- **tutor** and **chart_coach** write one `moderation_block` row per blocked
  response (`user_id` of the child in scope).
- **quiz** writes one row per blocked attempt. The generator regenerates once
  on the first blocked attempt and falls back to the deterministic safe quiz
  on the second; each blocked attempt is its own audit row, with
  `user_id=None` because `generate_practice_quiz` has a session but no `User`
  in scope.
- **tips** has **no audit row by design**: `_generate_tips` is a
  module-level cached generator with no DB session in scope, so tips
  moderation is best-effort — unsafe generated tips are replaced by the
  static fallback tips, but no `AuditLog` row is written.

## Out of scope

- **Input-side prompt-injection hardening.** This seam moderates model
  *output*. Hardening untrusted *input* (delimiting/escaping child free-text,
  strengthening system prompts) is finding LLM-01 and is not covered here.
- **Engagement / quota / cost features.** Per-child LLM quotas and engagement
  features (LLM-06 and related) are sub-project 4b and are out of scope for
  4a.
- **Provider-side guardrail settings and PII scrubbing of outbound child
  free-text** (LLM-02) remain separate items.
