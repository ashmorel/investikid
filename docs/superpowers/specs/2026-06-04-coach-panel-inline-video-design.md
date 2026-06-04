# Coach Panel Float + Inline iOS Video (SP-F) — Design

**Status:** Draft for review.
**Date:** 2026-06-04
**Programme:** "Yasmin's Choice" rebrand — **SP-F** (post-beta UX fixes, bundled). Small, frontend-only. SP-0/A/B/C/D1/D2 shipped.

## Goal

Two user-reported fixes:
1. **Coach Penny panel reads as a full screen on phones** — it's already a `Sheet` slide-over (opens from the FAB, no navigation), but `SheetContent` uses `w-full max-w-md`, so on a ≤448px phone it's full-bleed. Make it visibly **float**: a **bottom sheet on mobile** (rounded top, ~85% height, dimmed page behind) and a **right-side panel on desktop**.
2. **iOS lesson video** — switch the native `VideoLesson` branch back to an **inline in-app player (B1)** instead of the thumbnail-that-opens-YouTube hand-off.

No route/data/validation/behaviour change beyond these.

## Change 1 — Responsive Coach panel

`src/components/child/CoachPanel.tsx`: pick the sheet side by viewport using the existing `useMediaQuery` hook.
- Desktop (`min-width: 640px`): `side="right"`, `className="… w-full max-w-md sm:max-w-md …"` (current behaviour — already floats on wide screens).
- Mobile (`< 640px`): `side="bottom"`, `className="h-[85svh] rounded-t-2xl …"` — a rounded card rising from the bottom; the dimmed page + the top ~15% stay visible → clearly a floating window.
- Keep the `SheetHeader` (Penny + "Coach Penny"), `CoachChat onNavigate={close} showHeader={false}`, the safe-area bottom padding, and the Radix focus-trap/ESC/overlay-close. The inner content stays `min-h-0 flex-1 overflow-hidden` so the chat scrolls within the sheet.

Implementation: `const isDesktop = useMediaQuery('(min-width: 640px)');` then `side={isDesktop ? 'right' : 'bottom'}` with the matching className. (`useMediaQuery` is SSR-safe.)

## Change 2 — Inline iOS video (B1)

`src/components/child/lesson/VideoLesson.tsx`: render the **inline YouTube `<iframe>` on native too**, dropping the `nativeApp ? thumbnail : iframe` split. Keep everything else (caption, "Captions available", transcript disclosure, "I watched this", "Mark complete", and the "Open video on YouTube" link as a fallback).
- Keep using `buildYouTubeUrls(...).embed` — `videoEmbed.ts` already platform-tunes the embed URL: **native** uses `https://www.youtube.com/embed/<id>?origin=…&widget_referrer=…&playsinline=1`, **web** uses `youtube-nocookie.com`. `playsinline=1` is the key flag that lets iOS WKWebView play **inline** (not forced-fullscreen).
- The `<iframe>` keeps `allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"`, `allowFullScreen`, `referrerPolicy="strict-origin-when-cross-origin"`, and a `title`.
- `isNativeApp()` is no longer needed in `VideoLesson` (remove the import/branch if unused).
- **WKWebView inline-media note:** Capacitor's iOS WebView enables `allowsInlineMediaPlayback` by default, so `playsinline=1` + a user tap should play inline. **Contingency (not applied pre-emptively):** if the simulator shows it still forcing fullscreen or not loading, the fix is a Capacitor iOS webview/`Info.plist` media setting — we add that only if the device check shows it's needed (avoid guessing a config key blind).

**Trade-off (acknowledged with the user):** B1 keeps YouTube's ads + end-screen "related videos" + WKWebView fragility. The long-term safer option for a kids' app (self-hosted curated videos, "B2") remains a separate backlog item.

## Accessibility / constraints

- Coach sheet: Radix Dialog keeps focus-trap, ESC, overlay-close, focus-return to the FAB; bottom-sheet variant still has an accessible title/description.
- Video: `<iframe title="Lesson video">`; transcript disclosure + caption text unchanged; the fallback YouTube link stays. iOS form controls ≥16px (unchanged). No `maximum-scale`.

## Testing

- `CoachPanel`: a test that it renders the chat + title when `open`; (mock `useMediaQuery` both ways to assert `side` switches — or at least that it renders without error in each). Mock `useCoachGreeting`/`aiApi` as the existing CoachChat tests do.
- `VideoLesson`: update the existing tests — the **native test must change** (it currently asserts *no iframe* + a thumbnail; the new behaviour is an iframe on native too). Keep/adjust the web tests; assert the iframe renders + uses the embed URL + the "Open on YouTube" fallback link still present.
- `tsc -b`, lint, test, build. Backend untouched. All 6 CI jobs green (incl. the iOS Capacitor compile job — note: that job *builds* the app, it doesn't verify inline video playback; that's a manual simulator check).

## Plan shape
T1 responsive `CoachPanel` + test → T2 inline `VideoLesson` (B1) + update tests → T3 regression + push (+ note: verify inline iOS playback on the simulator; apply the WKWebView contingency only if needed). Each green-CI.

## Decisions captured
Coach panel = bottom sheet on mobile / right panel on desktop · iOS video = inline B1 (reuse `videoEmbed` native URL + `playsinline`; keep YouTube-link fallback) · WKWebView media config added only if the simulator shows it's needed · self-hosted video (B2) deferred to backlog · country switcher is the next, separate feature.
