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
| `country_code` immutability hardening | ✅ shipped | `PATCH /users/me` no longer lets a user change `country_code` (drives COPPA/UK-GDPR consent regime); dropped from `UpdatePreferencesRequest` + router write; regression-tested. Spec was a spawned follow-up. |
| Next-quest resolver | ✅ shipped | Fixed false "You've finished everything" on Home. New backend `next_lesson_service.resolve_next_lesson` + `GET /next-lesson` walk all accessible modules (reusing `derive_level_states`) → true next lesson, or null only when genuinely caught up. `useNextLesson` collapsed to one call; retired client-side `pickTarget*` helpers. Spec/plan `docs/superpowers/{specs,plans}/2026-06-04-next-quest-and-back-nav*`. |
| Consistent Back navigation | ✅ shipped | New reusable accessible `BackButton` (≥44px, focus-visible, `aria-label`) on all child drill-down pages (Module/Level/Lesson/Stock + **Market**, which had no back affordance), replacing the subtle text links; deterministic up-one-level targets. |
| iOS YouTube **error 153** fix | ✅ shipped (code) — **needs device re-check** | Root cause: iOS WKWebView (`capacitor://` scheme) strips the HTTP Referer on the cross-origin YouTube request (WebKit bug 169846) → YouTube rejects with 153. Fix: native builds load the player via a static `public/yt.html` proxy served from the real https web origin (`VITE_WEB_ORIGIN`, default `https://lee-local-code-repo.vercel.app`), giving YouTube a valid Referer. Web build unchanged. No WebView-scheme/auth change. Spec `docs/superpowers/specs/2026-06-04-ios-youtube-153-fix-design.md`. **USER: after the Vercel deploy lands, `npm run build && npx cap sync ios` (done) → Xcode rebuild → confirm a lesson video plays inline with no 153.** |
| Dead compound-interest video | ✅ shipped | Seeded video `MqZmwQoHmAA` was deleted on YouTube → "Video unavailable". Data migration `c9d0e1f2a3b4` repoints it to a live Khan Academy video (`Rm6UdfRs3gw`) before the deploy-time re-seed; seed updated; guard test rejects the dead id. Auto-fixes the live DB on deploy. |
| Video link health + admin visibility | ✅ shipped | `video_health` table + oEmbed checker (`video_health_service`, 200→ok / 401·404→dead / transient→unknown) + admin `GET/POST /admin/video-health` + an admin **"Video health"** page (status badges, last-checked, Edit, "Check now") + a `python -m app.video_health.run` cron that emails `admin_alert_email` (reusing `admin_llm_alert`) **only when dead**. Spec/plan `docs/superpowers/{specs,plans}/2026-06-05-video-link-health*`. **USER: add a Railway cron service running `python -m app.video_health.run` (e.g. daily `0 6 * * *`) to enable the periodic check** (on-demand "Check now" works without it). Self-hosted curated video remains a separate, deferred sub-project. |

> **Also added by Codex during SP-D2 (beyond the plan):** a new CI job **"iOS (Capacitor sync · simulator build)"** (macOS — `npx cap sync ios` → resolve packages → `xcodebuild` simulator build), and YouTube-embed fixes for the Capacitor WebView. CI is now **6 jobs**; all green on HEAD.
>
> **Note on local "no such module 'Capacitor'":** the iOS CI job proves the SPM build is sound. If a *local* Xcode build hits this, it's a stale package graph: quit Xcode → `npm run build && npx cap sync ios` from `invest-ed/frontend` → reopen `ios/App/App.xcodeproj` (Capacitor 8 = SPM project, no workspace/Podfile) → File ▸ Packages ▸ Reset Package Caches + Resolve → Clean Build Folder → Build. (Capacitor's `capacitor-swift-pm` is a remote SPM dep Xcode must fetch.)

## ▶ Resume here: rebrand programme COMPLETE — only standing USER-only items remain
The "Yasmin's Choice" rebrand programme is fully shipped (SP-0/A/B/C/D1/D2/F + Country/Region switcher + `country_code`-immutability hardening + SP-E). No further code work is queued. The remaining items are all **USER-only** (see "Pending USER actions" below):
- **iOS Xcode device rebuild** to see the rebrand on a physical device (Vercel web already reflects everything).
- **SP-D1 OAuth credential setup** before real social sign-in works.
- **App Store Connect display name** → "InvestiKid".
- **Verify inline iOS video on the simulator:** confirm the inline lesson video plays *inline* (not forced fullscreen). If it forces fullscreen, add the Capacitor iOS WebView media setting (confirm the exact key first) — the only remaining SP-F follow-up.

## Pending USER actions (not code)
- **SP-D1 OAuth setup** before real social sign-in works: see `invest-ed/docs/parent-social-login-setup.md` (Google Cloud web+iOS client IDs; Apple Developer Sign-in-with-Apple + Services ID; Xcode capability + Google URL scheme; set the 4 backend env ids + `VITE_` frontend ids). Until set, the OAuth endpoints return `503 not_configured` — expected.
- **iOS Xcode clean rebuild** to see the rebrand on a physical device (deferred to programme end; Vercel web already reflects everything).
- Set the **App Store Connect display name** to "InvestiKid"; rename the Figma file.

## Key decisions (don't re-litigate)
Sky-blue/indigo brand + amber demoted to `accent-*` · **Penny pig** mascot (retired robot Eddie; persona renamed in backend LLM prompts) · Tailwind **v4** (CSS-first `@theme`, no `tailwind.config.js`) · iOS floor **17.0** · full **semantic colour tokens** (next reskin = `@theme` edits) · keep IA/routes · name stays **"InvestiKid"** · social login is **parents-only** (children keep parent-managed username login; ID-token-only verification, no client secrets) · SP-D2 Coach panel = slide-over, `/coach` route kept.
