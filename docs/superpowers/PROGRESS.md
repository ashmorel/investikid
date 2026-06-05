# Yasmin's Choice rebrand — programme progress & resume guide

> **Cross-tool resume note.** This file is the single source of truth for where the
> "Yasmin's Choice" rebrand programme stands, so any agent (Claude Code, Codex,
> Cursor) can pick it up. Each sub-project follows: **design spec → implementation
> plan → execute task-by-task → green CI**. Specs live in `docs/superpowers/specs/`,
> plans in `docs/superpowers/plans/`. Commit to `main`; end commit messages with
> `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway deploys the
> backend **only on green CI** (5 jobs: frontend, backend, security, a11y, responsive).

## What this programme is
Reskin InvestiKid from amber → **sky-blue** with **Penny the pig** mascot, plus a few
features. Source design: a Figma Make export (cloned to `/tmp/yasminschoice`; re-clone
from GitHub `ashmorel/Investikidyasminschoice` if gone).

## Status

| Sub-project | State | Notes |
|---|---|---|
| **SP-0** Tailwind v4 + iOS 17 | ✅ shipped | CSS-first `@theme`; iOS deploy target 17.0 |
| **SP-A** Foundation & rebrand | ✅ shipped | semantic colour tokens, Penny mascot, Eddie→Penny (FE+BE persona), whole-app colour sweep |
| **SP-B** Child core layouts | ✅ shipped | gamified Home, learning-path progress, card Stats, Coach/Progress polish |
| **SP-C** Simulator suite | ✅ shipped | Practice Portfolio hero, quick-stats, Stock/Market polish |
| **SP-D1** Parent social login | ✅ shipped | Apple+Google (web+native) ID-token verification, `parent_identity` table; **needs user OAuth setup** |
| **SP-D2** Auth polish + Coach panel | ✅ shipped (in Codex) | branded `AuthPage`, polished + friendlier auth screens, `CoachChat` extracted, Coach slide-over panel; CI green |
| **SP-F** Coach panel float + inline iOS video | ✅ shipped | Coach panel = **bottom sheet on mobile** / right panel on desktop; `VideoLesson` plays **inline on iOS (B1)** instead of thumbnail hand-off; also un-tracked the Xcode-churned `Package.resolved` (gitignored) |
| **Country switcher** | ✅ shipped | **two independent settings** — `content_region` learning-region focus (US/GB/HK) gates content + currency, plus a **child-editable practice currency**; legal `country_code` untouched (consent regime intact); simulator features the chosen region's exchange first |
| **SP-E** Parent/admin polish | ✅ shipped | parent dashboard Penny header + polish; admin panel converted dark→light sky-blue across all 18 files; two WCAG AA contrast fixes (active nav + a card badge) |

> **🎉 The "Yasmin's Choice" rebrand programme is now COMPLETE.** All sub-projects shipped: SP-0, SP-A, SP-B, SP-C, SP-D1, SP-D2, SP-F, Country/Region switcher (+ `country_code`-immutability hardening), and SP-E. Only standing **USER-only** actions remain (see "Pending USER actions" below).

## Post-launch fixes (after programme completion)
| Fix | State | Notes |
|---|---|---|
| Parent session logout + revocation (audit H1) | ✅ shipped | Pre-beta security blocker. Parent sessions are now DB-backed + revocable: new `ParentSession` (`jti`+`revoked_at`, migration `f0a1b2c3d4e5`), `issue_parent_session` async + persists a row, `decode_parent_session`→`(email,jti)`, `revoke_parent_session`. `get_current_parent` 401s on missing/revoked/expired jti; `logout` revokes the row **and** clears the cookie with matching `samesite`/`secure`/`httponly`/`path` (the actual cookie-clear bug). Spec/plan `docs/superpowers/{specs,plans}/2026-06-05-parent-session-revocation*`. Full suite green (620), single head. **One-time effect: parents signed in pre-deploy must log in once.** |
| `country_code` immutability hardening | ✅ shipped | `PATCH /users/me` no longer lets a user change `country_code` (drives COPPA/UK-GDPR consent regime); dropped from `UpdatePreferencesRequest` + router write; regression-tested. Spec was a spawned follow-up. |
| Next-quest resolver | ✅ shipped | Fixed false "You've finished everything" on Home. New backend `next_lesson_service.resolve_next_lesson` + `GET /next-lesson` walk all accessible modules (reusing `derive_level_states`) → true next lesson, or null only when genuinely caught up. `useNextLesson` collapsed to one call; retired client-side `pickTarget*` helpers. Spec/plan `docs/superpowers/{specs,plans}/2026-06-04-next-quest-and-back-nav*`. |
| Consistent Back navigation | ✅ shipped | New reusable accessible `BackButton` (≥44px, focus-visible, `aria-label`) on all child drill-down pages (Module/Level/Lesson/Stock + **Market**, which had no back affordance), replacing the subtle text links; deterministic up-one-level targets. |
| iOS YouTube **error 153** fix | ✅ shipped — **device-verified** | Root cause: iOS WKWebView (`capacitor://` scheme) strips the HTTP Referer on the cross-origin YouTube request (WebKit bug 169846) → YouTube rejects with 153. Fix: native builds load the player via a static `public/yt.html` proxy served from the real https web origin (`VITE_WEB_ORIGIN`, default `https://lee-local-code-repo.vercel.app`), giving YouTube a valid Referer. Web build unchanged. No WebView-scheme/auth change. Spec `docs/superpowers/specs/2026-06-04-ios-youtube-153-fix-design.md`. **Confirmed on-device (2026-06-05): lesson videos + the repointed Compound Interest video play inline, no 153.** |
| Dead compound-interest video | ✅ shipped | Seeded video `MqZmwQoHmAA` was deleted on YouTube → "Video unavailable". Data migration `c9d0e1f2a3b4` repoints it to a live Khan Academy video (`Rm6UdfRs3gw`) before the deploy-time re-seed; seed updated; guard test rejects the dead id. Auto-fixes the live DB on deploy. |
| Self-hosted curated video (R2) | ✅ shipped (code) — **needs R2 setup** | Augments YouTube: a video lesson can be `video_source: youtube\|hosted`. Admins upload an MP4 in `LessonForm` via a **presigned PUT straight to Cloudflare R2** (`POST /admin/video-assets/presign`, `video_asset` table, mp4-only + 200 MB cap, `503 not_configured` when `R2_*` unset); children play it inline via HTML5 `<video playsinline>` (ad-free, no 153). Video-health also HEADs hosted URLs. Public-by-URL + MP4-only/no-transcode (accepted parity trade-offs). Spec/plan `docs/superpowers/{specs,plans}/2026-06-05-self-hosted-video*`. **USER: set up the R2 bucket + `R2_*` env per `docs/self-hosted-video-setup.md`** (until then, upload shows "not configured", YouTube unaffected). Signed URLs / transcoding deferred. |
| Video-health periodic trigger | ✅ shipped & **live** | Replaced the fragile separate Railway cron with a secret-guarded `POST /internal/video-health/run` (CSRF-exempt, `X-Cron-Secret` constant-time check, `503` when `CRON_SECRET` unset) that reuses `app.video_health.run.run`. A daily GitHub Actions workflow `.github/workflows/video-health-cron.yml` (06:00 UTC + manual run) curls it; backend URL hardcoded (public), only `CRON_SECRET` is a secret. Spec/plan `docs/superpowers/{specs,plans}/2026-06-05-video-health-trigger-endpoint*`. **Verified working 2026-06-05** (`CRON_SECRET` set on Railway + as a GitHub *repository* Actions secret — note: GitHub *environment* secrets are NOT visible to the job). Rotate the secret if needed; old separate Railway cron service can be deleted. |
| Video link health + admin visibility | ✅ shipped | `video_health` table + oEmbed checker (`video_health_service`, 200→ok / 401·404→dead / transient→unknown) + admin `GET/POST /admin/video-health` + an admin **"Video health"** page (status badges, last-checked, Edit, "Check now") + a `python -m app.video_health.run` cron that emails `admin_alert_email` (reusing `admin_llm_alert`) **only when dead**. Spec/plan `docs/superpowers/{specs,plans}/2026-06-05-video-link-health*`. **USER: add a Railway cron service running `python -m app.video_health.run` (e.g. daily `0 6 * * *`) to enable the periodic check** (on-demand "Check now" works without it). Self-hosted curated video remains a separate, deferred sub-project. |
| CI cost control + environments | ✅ implemented (local, pending commit/push) | Automatic `.github/workflows/ci.yml` is now Ubuntu-only for regular web/backend validation on `main`, `testing`, and PRs to `main`; jobs get GitHub environment labels (`production` for `main`, `testing` otherwise). The expensive macOS iOS simulator build was moved to manual-only `.github/workflows/ios-manual.yml` with a `testing`/`production` selector. Docs-only changes are path-filtered out; frontend browser suites run only on frontend/workflow changes. Spec/plan `docs/superpowers/{specs,plans}/2026-06-05-ci-environments-cost-control*`. Verified locally: YAML parses, `git diff --check` clean, `macos-latest` appears only in the manual iOS workflow. `actionlint` is not installed locally. |

> **CI cost note:** the iOS simulator build was originally added to automatic CI during SP-D2, but it consumed GitHub Actions minutes quickly because `macos-latest` bills at a much higher rate than Ubuntu. As of the local CI cost-control work above, regular CI is back to Ubuntu-only and iOS validation is manual.
>
> **Note on local "no such module 'Capacitor'":** the manual iOS workflow can prove the SPM build is sound when run. If a *local* Xcode build hits this, it's a stale package graph: quit Xcode → `npm run build && npx cap sync ios` from `invest-ed/frontend` → reopen `ios/App/App.xcodeproj` (Capacitor 8 = SPM project, no workspace/Podfile) → File ▸ Packages ▸ Reset Package Caches + Resolve → Clean Build Folder → Build. (Capacitor's `capacitor-swift-pm` is a remote SPM dep Xcode must fetch.)

## ▶ Resume here (updated 2026-06-05)
The rebrand programme + all post-launch fixes are shipped. Most standing items are now **done**; the only remaining setup blocker is **R2**.

**Done since last update:**
- ✅ **CI cost-control split (local, pending commit/push)** — regular CI now covers web/backend on `main`, `testing`, and PRs using Ubuntu only; iOS simulator validation is manual via `iOS manual check` when explicitly requested.
- ✅ **iOS rebuild + 153/video** — device-verified (videos play inline, no 153; InvestiKid name + Apple entitlement in the build).
- ✅ **Video-health periodic trigger** — live (`/internal/video-health/run` + GitHub Actions; `CRON_SECRET` set).
- ✅ **OAuth credentials** — Google + Apple client IDs created; backend `GOOGLE_*`/`APPLE_*` on Railway + `VITE_*` on Vercel; Google web verified to token-exchange (a 404 for a non-matching email confirms it works). Google web client needs **Authorised redirect URI** `https://lee-local-code-repo.vercel.app/parent/login` (added). Xcode: Sign in with Apple capability + Google URL scheme committed.
- ✅ **On-device app name** = InvestiKid (`CFBundleDisplayName` + `CFBundleName`).

**Still outstanding (USER):**
- **R2 storage setup** — the last real blocker; self-hosted video upload until then shows "not configured" (YouTube unaffected). See `invest-ed/docs/self-hosted-video-setup.md`.
- **Native social login is PARKED by choice** — the local build had no `VITE_*` so the buttons are hidden in-app (correct). To enable later: add the 3 `VITE_*` to `invest-ed/frontend/.env` → `npm run build && npx cap sync ios` → rebuild.
- **Full social login test** needs a parent account whose email matches the social account (social login links to an *existing* parent; it never creates one). Apple **web** may prompt for domain verification on first use (host `apple-developer-domain-association.txt` at `/.well-known/`).
- **App Store Connect listing name** = "InvestiKid" — set when you **register the app** (not created yet); the on-device name is already correct.

## Key decisions (don't re-litigate)
Sky-blue/indigo brand + amber demoted to `accent-*` · **Penny pig** mascot (retired robot Eddie; persona renamed in backend LLM prompts) · Tailwind **v4** (CSS-first `@theme`, no `tailwind.config.js`) · iOS floor **17.0** · full **semantic colour tokens** (next reskin = `@theme` edits) · keep IA/routes · name stays **"InvestiKid"** · social login is **parents-only** (children keep parent-managed username login; ID-token-only verification, no client secrets) · SP-D2 Coach panel = slide-over, `/coach` route kept.
