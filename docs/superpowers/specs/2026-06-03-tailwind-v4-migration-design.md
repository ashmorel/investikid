# Tailwind v4 Migration + iOS 17 Floor — Design

**Status:** Draft for review.
**Date:** 2026-06-03
**Programme:** "Yasmin's Choice" rebrand — **SP-0 of 6** (SP-0 v4 migration → SP-A foundation/rebrand → SP-B child core → SP-C simulator → SP-D auth/account → SP-E parent/admin).

## Goal

Upgrade the InvestiKid frontend from Tailwind CSS v3.4 to v4, and raise the iOS deployment target to 17.0, **with zero intended visual or behavioural change.** This is pure infrastructure: it unblocks authoring the new "Yasmin's Choice" design tokens in v4's CSS-first `@theme` form (SP-A) — matching the source prototype — instead of translating them into a v3 JS config twice.

## Why now / why first

- The Figma Make source ("Yasmin's choice") is authored in Tailwind v4 (`@import "tailwindcss"`, `@theme`, `oklch()` colours). Doing v4 first lets SP-A lift those tokens almost verbatim.
- Tailwind v4's baseline is **Safari/iOS 16.4+** (it relies on cascade layers, `@property`, `color-mix()`, `oklch()`). The app currently targets **iOS 15.0** in a Capacitor WKWebView, so v4 would break on iOS 15 devices. Decision (approved): raise the floor to **iOS 17.0**.
- Keeping the migration in its own behaviour-preserving sub-project means any visual regression is attributable to the upgrade alone, not tangled with the rebrand.

## Current state (verified)

- `tailwindcss@^3.4.16`, `vite@6.4.2`, PostCSS pipeline = `{ tailwindcss, autoprefixer }`.
- `tailwind.config.js`: `darkMode: ['class']`, `content` globs, `theme.extend.colors` mapped to `hsl(var(--token))`, `borderRadius` mapped to `var(--radius)`, single plugin `tailwindcss-animate`.
- `src/index.css`: v3 directives `@tailwind base/components/utilities`; `@layer base` defining HSL design tokens (`--background`, `--primary`, …), safe-area vars (`--safe-*`), the iOS ≥16px coarse-pointer input rule, and `:focus-visible` scroll-margins; only two `@apply` (`* { @apply border-border }`, `body { @apply bg-background text-foreground }`); no `theme()` function usage.
- Single shadcn-style `button.tsx` (the known fast-refresh lint warning).
- `IPHONEOS_DEPLOYMENT_TARGET = 15.0` (4 occurrences in `ios/App/App.xcodeproj/project.pbxproj`).

## Approach

CSS-first migration (the v4-native target), not the `@config` shim, because SP-A will author tokens in `@theme` anyway.

1. **Dependencies:** add `tailwindcss@^4` + `@tailwindcss/vite`; add `@tailwindcss/postcss` only if any non-Vite CSS path needs it (Vite plugin is preferred). Remove the PostCSS `tailwindcss`/`autoprefixer` entries (v4 bundles autoprefixing). Replace `tailwindcss-animate` with `tw-animate-css` (its v4 successor, used by the prototype). Run `npx @tailwindcss/upgrade` as a starting point, then hand-reconcile.
2. **Vite:** add `@tailwindcss/vite` to `vite.config.ts` plugins; drop `postcss.config.js` (or empty it) once Tailwind is out of the PostCSS chain.
3. **Entry CSS (`index.css`):** replace the three `@tailwind` directives with `@import "tailwindcss";` + `@import "tw-animate-css";`. Move the JS-config tokens into a CSS `@theme` block (colours, radii), keeping the **exact same HSL values** so output is identical. Preserve `@layer base` for `--safe-*`, the iOS coarse-pointer rule, and `:focus-visible` margins verbatim. Map dark mode via `@custom-variant dark (&:is(.dark *))`.
4. **Config:** reduce/remove `tailwind.config.js` (content auto-detection in v4 removes the `content` array; `darkMode` handled by the custom variant). Keep a minimal config only if a plugin or override still needs it.
5. **Known v4 default changes to neutralise (so nothing shifts visually):**
   - Default border colour changed `gray-200`→`currentColor`: our `* { @apply border-border }` already pins it, but verify no bare `border` usages relied on the old grey; add an explicit base border-colour if needed.
   - Default `ring` width changed `3px`→`1px` and ring colour default changed: audit `ring`/`focus:ring` usages (focus-visible styling is accessibility-critical) and pin width/colour to preserve current focus rings.
   - Preflight tweaks (placeholder colour, button cursor, dialog margins): spot-check forms/inputs.
6. **iOS:** set `IPHONEOS_DEPLOYMENT_TARGET = 17.0` in all four `project.pbxproj` build configs; bump the Capacitor `ios` platform/Podfile if a `platform :ios` line is added later. Update any docs/specs that state "iOS 15".
7. **Docs:** note v4 + iOS 17 in `AGENTS.md` / `.cursor/rules/frontend.mdc` / `CLAUDE.md` where the stack is described.

## Out of scope

- **No visual redesign** — that is SP-A onward. No colour/brand changes here; tokens keep their current amber values.
- No mascot/rebrand work. No new components. No backend changes.
- No Tailwind plugin additions beyond the animate replacement.

## Risks & mitigations

- **Subtle visual drift from v4 defaults** (borders, rings, preflight) → the neutralisation step above + a screenshot parity pass (see Testing) + the CI `responsive` and `a11y` Playwright jobs (chromium + webkit) as the safety net.
- **WKWebView parity** → Safari 17 fully supports v4's CSS; the `webkit` Playwright project approximates this and must stay green. Final confirmation is the manual Xcode/device rebuild at programme end.
- **iOS 17 floor drops old devices** → accepted product decision; pre-launch beta.
- **`@tailwindcss/upgrade` over-reaching** → treat its output as a draft; review every changed file in the diff, keep changes minimal.

## Testing / success criteria

Success = **the app looks and behaves identically**, on a modern engine, with the toolchain on v4.

- `npx tsc -b` clean; `npm run lint` clean (only the pre-existing `button.tsx` fast-refresh warning); `npm test` (full vitest + vitest-axe) green; `npm run build` succeeds.
- CI all 5 jobs green (frontend, backend, security, a11y, responsive) — the a11y (jsx-a11y + vitest-axe + playwright-axe chromium+webkit) and responsive (playwright viewport chromium+webkit) jobs are the automated visual/behavioural guard.
- **Visual parity pass:** before/after screenshots of Home + a lesson + the simulator on mobile viewport (reuse the mocked-API Playwright approach) — diffs should be nil beyond anti-aliasing.
- `npx cap sync ios` succeeds; deployment target reads 17.0. (Native device rebuild verified by the user at programme end, not per-sub-project.)

## Decisions captured

- Mascot → **Penny the pig** (SP-A); palette → **full sky-blue/indigo** (SP-A); coverage → **all screens**; iOS floor → **17.0**; Tailwind → **v4 (CSS-first)**. Name stays **"InvestiKid"**. IA/routes preserved (tab bar restyled, not screens dropped).
