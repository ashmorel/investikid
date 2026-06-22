# Figma Handoff

Design-foundation reference (tokens/components, not full screens). Last verified: 2026-06-03 — treat as historical design context, not a per-release gate.

## Source Design

- Name: Funky investiKid app designs - Yasmin's choice Copy
- Figma Make URL: https://www.figma.com/make/avB9FCFMn26vUVlm04J58F/Funky-investiKid-app-designs---Yasmin-s-choice--Copy-?t=ArHKBNjOTWJpo8OM-6
- Figma file key: `avB9FCFMn26vUVlm04J58F`
- Figma Make root node: `0:1`

The Figma connector can read this file through `get_design_context`. The Make file exposes React/Tailwind source files including:

- `src/app/App.tsx`
- `src/app/components/Dashboard.tsx`
- `src/app/components/Layout.tsx`
- `src/app/components/BottomNav.tsx`
- `src/app/components/LearnPage.tsx`
- `src/app/components/ExplorePage.tsx`
- `src/app/components/PortfolioPage.tsx`
- `src/app/components/TradingFlow.tsx`
- `src/styles/theme.css`
- `src/styles/globals.css`

Treat the Figma Make code as reference material, not a direct drop-in replacement. The production app already has routing, auth, data fetching, accessibility fixes, Capacitor/iOS handling, and deployment wiring that must be preserved.

## App Repository

- GitHub repository: `ashmorel/investikid`
- App root: `invest-ed/`
- Frontend: `invest-ed/frontend/`
- Backend: `invest-ed/backend/`
- Default branch: `main`

## Deploy Path

UI changes should flow through GitHub:

1. Read the Figma Make context from file key `avB9FCFMn26vUVlm04J58F`, node `0:1`.
2. Create a focused implementation spec in `docs/superpowers/specs/`.
3. Create a task-by-task plan in `docs/superpowers/plans/`.
4. Implement changes in the React/Tailwind app, reusing existing production data hooks and components.
5. Verify frontend checks from `invest-ed/frontend/`:
   - `npx tsc -b`
   - `npm run lint`
   - `npm test`
   - `npm run build`
6. For native UI changes, run `npx cap sync ios` after the frontend build and verify an Xcode simulator build.
7. Commit and push to GitHub.
8. Confirm GitHub CI is green.
9. Vercel auto-deploys frontend changes from GitHub. Railway deploys backend changes after green CI.

## Implementation Rules

- Preserve existing app behavior and API calls. Restyle before rewriting.
- Use existing CSS variables and Tailwind tokens from `frontend/src/index.css` and `frontend/tailwind.config.js`.
- Keep mobile safe-area behavior and iOS text inputs at least 16px.
- Keep WCAG 2.2 AA coverage for new or changed UI.
- Do not copy generated Figma Make shadcn files wholesale unless the production app needs that exact component and tests cover it.
- Do not read or modify `.env` files.

## Fast Start Prompt

Use this when starting a new Figma-driven UI change:

> Use the Figma Make design at `https://www.figma.com/make/avB9FCFMn26vUVlm04J58F/Funky-investiKid-app-designs---Yasmin-s-choice--Copy-?t=ArHKBNjOTWJpo8OM-6` as the visual source. Implement the requested screen in `invest-ed/frontend`, preserving existing routes, API hooks, auth behavior, mobile safe-area handling, and accessibility. Create/update the relevant spec and plan first, then verify with frontend checks and an iOS build if native UI is affected.
