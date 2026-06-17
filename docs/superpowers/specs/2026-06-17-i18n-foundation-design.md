# i18n Foundation — Design Spec (Sub-project A)

**Date:** 2026-06-17
**Status:** Approved (design); ready for implementation plan
**Programme:** Multi-language + multi-market localization

---

## Programme context (why this sub-project exists)

InvestiKid is going global. The agreed end-state spans three pillars:

1. **Language** — a global, user-selectable display language, independent of market.
2. **Multi-market content + per-market progress** — each market (UK, US, AU, CA, IE, ES, FR, DE, HK, SG) is its own financial curriculum (currency, products, regs, compliance), and a user can study several markets with progress tracked per market and aggregated globally.
3. **Cross-market rewards** — completing/adding markets earns achievements / bonus XP.

**Key model decisions (locked):**
- **Market = the money axis** (currency, products, regulations, compliance regime). **Language = the words axis**, a global user preference.
- Each market's financial content is **expert-reviewed** in its **natural languages** (e.g. UK→en; Spain→es+en; Hong Kong→en+zh-Hant; Singapore→en+zh-Hans).
- A user may select **any supported language regardless of market**. **Curated** market×language pairs use reviewed translations; **non-curated** pairings are **Gemini auto-translated on top of the reviewed source, labelled as auto-translated, and cached**.
- **Chinese is two languages:** Hong Kong uses **Traditional (zh-Hant)**, Singapore uses **Simplified (zh-Hans)**.

**Supported languages (BCP-47):** `en`, `es`, `fr`, `de`, `zh-Hant`, `zh-Hans`.

**Decomposition & sequence (Approach A — plumbing-first, content-last):**

| # | Sub-project | Delivers | Depends on |
|---|---|---|---|
| 0 | Gemini model lineup | Multilingual engine + GPT-5-mini premium | Gemini API key |
| **A** | **i18n foundation (THIS SPEC)** | i18n framework, full UI extraction, `language` preference, switcher | — |
| B | AI speaks the language | Selected language passed to Coach/quiz/tips/greetings + moderation | 0, A |
| C | Market model + per-market progress | `Market` first-class; content + progress scoped per market; migrate existing → UK market | — |
| D | Cross-market rewards | Achievements / bonus XP / "Global Investor" track | C |
| E | Content localization pipeline + waves | AI-assisted authoring + expert review per market; curated translations; auto-translate fallback | 0, C |

This spec covers **Sub-project A only.**

---

## Goal

Establish the localization infrastructure so every static UI string in the app is displayed through an i18n system and can be translated later, with a per-user, server-backed **language preference** and a Settings switcher. **English is the only populated catalog at the end of A** — no strings are translated yet. The acceptance proof is that *dropping in a new catalog file translates the entire UI with zero further code changes.*

## Non-goals (YAGNI)

- No real translations (no es/fr/de/zh catalogs) — those arrive with later sub-projects.
- No translation of AI/dynamic output (Sub-project B) or curriculum (Sub-project E).
- No currency / number / date localization (that is the market axis, Sub-project C).
- No RTL support — none of the six supported languages are right-to-left.
- No change to existing `country_code` / `currency_code` behavior.

---

## Architecture

### Unit 1 — Supported-languages registry (shared contract)

A single source of truth, mirrored front and back, listing each supported language:

- `code` — BCP-47 (`en`, `es`, `fr`, `de`, `zh-Hant`, `zh-Hans`)
- `endonym` — native display name (English, Español, Français, Deutsch, 繁體中文, 简体中文)
- `available` — whether a UI catalog exists yet (only `en` is `true` in A)

**Backend:** a Python module (e.g. `app/core/languages.py`) exporting the set + a validator. **Frontend:** a TS constant (e.g. `src/i18n/languages.ts`). The two lists must stay in lockstep; a test asserts the code sets match so they cannot silently drift.

**Interface:** `is_supported_language(code) -> bool` (backend); `SUPPORTED_LANGUAGES` + `AVAILABLE_LANGUAGES` (frontend).

### Unit 2 — Backend user language preference

- **Model:** new column `User.language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="en")`.
- **Migration:** hand-written, chained Alembic revision (verify `alembic heads` first); adds the column with `server_default="en"` so existing rows backfill to English. Down-migration drops the column.
- **Read:** `language` added to the `/me` (current-user) response schema.
- **Write:** a dedicated `PATCH /me/language` accepting `{ "language": "<code>" }`; validates against the registry and returns **422** on an unknown code. Updates `current_user.language`, commits, returns the updated profile. (Dedicated endpoint, not folded into a broader settings update, so the switcher has one small, well-tested surface.)
- **Auth/session:** `language` included in the login/refresh user payload so the client hydrates on sign-in.

**Tests (async, `loop_scope="session"`, `db_session`/`client`/`admin_client` fixtures):**
- Migration applies; new users default to `en`.
- `PATCH` with a supported code persists and is reflected in `/me`.
- `PATCH` with an unsupported code → 422, no change.
- `/me` includes `language`.

### Unit 3 — Frontend i18n runtime

- **Dependencies:** `i18next`, `react-i18next`, `i18next-browser-languagedetector` (pinned; lockfile updated).
- **Init module** (`src/i18n/index.ts`): configures `fallbackLng: 'en'`, namespaces, interpolation, and **lazy-loads** each language's catalog (dynamic `import()`) so future languages don't bloat the initial bundle. Exposes the configured `i18n` instance.
- **Provider:** `<I18nextProvider>` (or the hook-based init) wrapping the app root, before the router renders.
- **Key convention (documented in the module + a short `src/i18n/README.md`):** feature-namespaced dotted keys — `home.hero.title`, `nav.simulator`, `settings.language.label`, `auth.login.submit`. One JSON file per namespace under `src/locales/<lng>/<namespace>.json`.

### Unit 4 — Full English extraction

- Every user-facing hardcoded string across all ~273 components is moved into `src/locales/en/*.json` and replaced in JSX with `t('key')`, using:
  - **Interpolation** for embedded values (`t('xp.earned', { count })`).
  - **i18next plurals** for count-dependent text.
  - **`<Trans>`** for strings containing inline markup/links.
- **Execution:** parallelized across subagents, each owning a slice of screens, all following the shared key convention. A reviewer pass reconciles namespace boundaries and duplicate keys.
- **Completeness is proven, not assumed:**
  - A **pseudo-locale** (`en-XA`) generated from `en` that wraps and accents every value (e.g. `Home` → `[!!Ĥömé!!]`). Dev/test only; never shipped as a user option. Switching to it visually surfaces any un-extracted string (it stays plain English) and reveals truncation/concatenation bugs.
  - A **lint guard** (ESLint `react/jsx-no-literals` or a custom rule, scoped to user-facing JSX text) that fails CI on any remaining literal, with a small documented allowlist for genuinely non-translatable tokens (brand name, numerals-only, icons).

### Unit 5 — Preference wiring & switcher

- **Resolution order on boot:** (1) authenticated `user.language` from the server = source of truth; (2) `localStorage` cache for instant pre-hydration paint; (3) first-run/unauthenticated → device locale via Capacitor `Device.getLanguageCode()` (web: `navigator.language`), mapped to the nearest supported code, else `en`.
- **Language control in Settings** (available to **both** child and parent, since the preference is per-user). Lists only languages with `available === true` — in A that is English alone, so the control exists, persists, and **auto-grows** when catalogs land. Copy notes more languages are coming.
- **On change:** set i18n active language → write `localStorage` → `PATCH /me/language`. On API failure, keep the local change and surface a non-blocking retry (the server reconciles on next load).
- **Accessibility:** the control is a labelled, keyboard-operable, screen-reader-friendly control with ≥16px touch targets (no `maximum-scale`); covered by `vitest-axe`.

---

## Data flow

```
Boot → i18n.init(fallback=en)
     → resolve language: server user.language ?? localStorage ?? deviceLocale ?? en
     → lazy-load catalog(s) for active language (en in A)
Render → components call t('namespace.key') → string from active catalog (en)
User changes language in Settings
     → i18n.changeLanguage(code) → re-render
     → localStorage[lang] = code
     → PATCH /me/language → server persists (validated)
Next login on any device → /me returns language → hydrates active language
```

## Error handling

- Unknown language code on `PATCH` → 422, no state change.
- Missing catalog key at runtime → i18next falls back to `en`, then to the key string; a dev-mode `missingKeyHandler` logs it (and can fail tests).
- Catalog lazy-load failure → fall back to `en` catalog; log; never blank the UI.
- Front/back registry drift → caught by the cross-list equality test in CI.

## Testing strategy

- **Backend:** migration + default; `PATCH` validation (happy + 422); `/me` includes language. Run `ruff` + `pytest` (full suite in CI).
- **Frontend:** i18n init renders keys; `changeLanguage` swaps resources; switcher persists to backend (mocked `apiFetch`) + `localStorage`; device-locale mapping; registry-parity test; **pseudo-locale extraction test** (no plain-English leakage on `en-XA`); `vitest-axe` on the switcher. Run `tsc -b` + `lint` (incl. the literal-string guard) + `vitest` + `build`.
- **iOS:** `npm run build && npx cap sync ios`, then Xcode rebuild; verify the Settings switcher renders and persists in the WKWebView.

## Definition of done

1. Dropping a new catalog file (e.g. `src/locales/es/*.json`) makes Spanish selectable and **translates the entire UI with no other code change** — the foundation's core proof.
2. Language persists per user across sessions and devices (server-backed).
3. The pseudo-locale + lint guard demonstrate **100% static-string extraction**.
4. The Settings language control is accessible (WCAG 2.2 AA) and works in the iOS WebView.
5. All six CI jobs green; iOS synced.

## Rollout / safety

- Backend-only DB change is **additive** (`language` column with `server_default`) — no destructive migration. **Per the standing rule, confirm whether to snapshot the prod DB before applying this migration in production.**
- The change is behaviorally inert for existing users (everyone defaults to `en`, UI unchanged); the only new surface is the language control.
- Promote `testing → staging → main` on green CI per the standard flow.
