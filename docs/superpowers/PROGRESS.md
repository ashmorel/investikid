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
| **SP-E** Parent/admin polish | 📝 **next** | layout-only restyle of parent dashboard + admin panel |

> **Also added by Codex during SP-D2 (beyond the plan):** a new CI job **"iOS (Capacitor sync · simulator build)"** (macOS — `npx cap sync ios` → resolve packages → `xcodebuild` simulator build), and YouTube-embed fixes for the Capacitor WebView. CI is now **6 jobs**; all green on HEAD.
>
> **Note on local "no such module 'Capacitor'":** the iOS CI job proves the SPM build is sound. If a *local* Xcode build hits this, it's a stale package graph: quit Xcode → `npm run build && npx cap sync ios` from `invest-ed/frontend` → reopen `ios/App/App.xcodeproj` (Capacitor 8 = SPM project, no workspace/Podfile) → File ▸ Packages ▸ Reset Package Caches + Resolve → Clean Build Folder → Build. (Capacitor's `capacitor-swift-pm` is a remote SPM dep Xcode must fetch.)

## ▶ Resume here: SP-E (parent/admin polish)
Final layout sub-project. Brainstorm → spec → plan → execute as usual. Scope: sky-blue card/Penny polish of the **parent dashboard** (`src/pages/ParentDashboard.tsx` + `src/components/parent/*`) and the **admin panel** (`src/components/admin/*`, admin pages) — layout-only, no behaviour/route change. (Per the SP-B/C/D2 lesson: READ each screen first — some may already be fine post-SP-A, e.g. the parent `SignInMethods` card from SP-D1.)

## Pending USER actions (not code)
- **SP-D1 OAuth setup** before real social sign-in works: see `invest-ed/docs/parent-social-login-setup.md` (Google Cloud web+iOS client IDs; Apple Developer Sign-in-with-Apple + Services ID; Xcode capability + Google URL scheme; set the 4 backend env ids + `VITE_` frontend ids). Until set, the OAuth endpoints return `503 not_configured` — expected.
- **iOS Xcode clean rebuild** to see the rebrand on a physical device (deferred to programme end; Vercel web already reflects everything).
- Set the **App Store Connect display name** to "InvestiKid"; rename the Figma file.

## Key decisions (don't re-litigate)
Sky-blue/indigo brand + amber demoted to `accent-*` · **Penny pig** mascot (retired robot Eddie; persona renamed in backend LLM prompts) · Tailwind **v4** (CSS-first `@theme`, no `tailwind.config.js`) · iOS floor **17.0** · full **semantic colour tokens** (next reskin = `@theme` edits) · keep IA/routes · name stays **"InvestiKid"** · social login is **parents-only** (children keep parent-managed username login; ID-token-only verification, no client secrets) · SP-D2 Coach panel = slide-over, `/coach` route kept.
