# iOS YouTube Error 153 Fix — https Proxy Page — Design

**Status:** Approved (approach); implementing.
**Date:** 2026-06-04
**Context:** Post-launch bug. In the iOS Capacitor app the inline YouTube player (SP-F's B1) fails with **error 153**. This is the long-standing SP-F follow-up.

## Root cause (confirmed)

YouTube's embedded player requires a valid HTTP `Referer` to authorise playback. The iOS app runs in a Capacitor **WKWebView** served from the default `capacitor://localhost` scheme (the Capacitor config sets only `androidScheme: 'https'` — **no `iosScheme`**). WKWebView strips the `Referer` on the cross-origin request to youtube.com (WebKit bug 169846), and a `capacitor://` origin is not a valid referer anyway → YouTube returns **error 153**. The existing `origin=`/`widget_referrer=` query params + `referrerPolicy` in `videoEmbed.ts` cannot restore the stripped referer, which is why the SP-F attempt did not fix it. Sources: corsproxy.io "Fix YouTube Error 150/153 in WebViews"; dev.to/davidvesely "Fixing YouTube Error 153 in iOS Capacitor Apps"; ionic-team/capacitor#8205.

## Fix — load the player through a real https origin (proxy page)

Route the native embed through a tiny static HTML page served from the app's **real https web origin** (Vercel). Because that page is an `https://…` document, the YouTube iframe inside it sends a valid https `Referer` → no 153. The auth/cookie scheme (CapacitorHttp/CapacitorCookies under `capacitor://`) is left untouched.

### Components
- **`frontend/public/yt.html`** (new, static) — deployed to Vercel + bundled in the app. Reads `?v=<id>` from its own query string, validates the id (`^[A-Za-z0-9_-]+$`), and renders a full-bleed `https://www.youtube-nocookie.com/embed/<id>?playsinline=1&rel=0&modestbranding=1` iframe (with `allow="autoplay; encrypted-media; picture-in-picture; fullscreen"`, `allowfullscreen`). Includes `<meta name="referrer" content="strict-origin-when-cross-origin">`. No framework, inline CSS, responsive 100%×100%. Shows a small "Video unavailable" message if `v` is missing/invalid.
- **`frontend/src/components/child/lesson/videoEmbed.ts`** — `buildYouTubeUrls(youtubeId, { isNative })`:
  - **Native** (`isNative === true`, default `isNativeApp()`): `embed = ${WEB_ORIGIN}/yt.html?v=<id>` where `WEB_ORIGIN = import.meta.env.VITE_WEB_ORIGIN || 'https://lee-local-code-repo.vercel.app'`.
  - **Web**: unchanged — direct `https://www.youtube-nocookie.com/embed/<id>?...` (the web build already works; no proxy needed).
  - `thumbnail`/`watch` unchanged. Invalid id → `null`.
  - Replace the brittle http-origin sniff with `@/lib/platform` `isNativeApp()` (Capacitor) for native detection; keep an injectable param for tests.
- **`VideoLesson.tsx`** — no structural change; it already renders `<iframe src={youtubeUrls.embed} …>`. Keep `referrerPolicy="strict-origin-when-cross-origin"`, `allow`, `allowFullScreen`. The "Open video on YouTube" fallback link stays.
- **Config docs** — note `VITE_WEB_ORIGIN` (optional; defaults to the Vercel origin) in `.env.example`.

## Out of scope
- Changing the iOS WebView scheme (`iosScheme`/hostname) — rejected (risks the Railway API cookie-auth setup).
- External-player handoff on native — rejected (reverts the SP-F inline B1 experience).
- Videos whose owner disabled embedding entirely (would be error 150, per-video) — no client fix possible; replace the video. Not the systemic 153 seen here.

## Testing
- **`videoEmbed.test.ts`** (new): native → `embed` is `<WEB_ORIGIN>/yt.html?v=<id>` and respects `VITE_WEB_ORIGIN`; web → nocookie embed URL; invalid id → null; thumbnail/watch correct.
- **`yt.html` guard test** (light, node/vitest reading the file): contains the `youtube-nocookie.com/embed/` reference, reads the `v` param, and has the referrer meta — so a regression that guts the proxy is caught.
- Manual (device, USER): rebuild iOS in Xcode after the Vercel deploy lands; confirm a lesson video plays inline with no 153. (Vercel auto-deploys `yt.html` on push; the native app references the remote URL.)
- `tsc -b` + lint + `npm test` + build; CI 6 jobs green.

## Decisions captured
- **https proxy page** on the deployed Vercel origin (`https://lee-local-code-repo.vercel.app`, overridable via `VITE_WEB_ORIGIN`) — keeps the inline player, no scheme/auth change. Native detection via Capacitor `isNativeApp()`. Requires `npm run build && npx cap sync ios` + an Xcode rebuild to take effect on device (iOS-visible change).
