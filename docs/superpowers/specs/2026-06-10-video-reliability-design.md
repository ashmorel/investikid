# W2 — Video Reliability & Kid-Safety — Design Spec

**Date:** 2026-06-10
**Status:** Draft — awaiting user review
**Repo:** `ashmorel/investikid` · branch `testing`
**Roadmap:** Phase 0, workstream W2 (`docs/2026-06-10-best-in-class-roadmap.md`).
**Decision context:** curriculum video stays **curated-from-YouTube** (embedded, not re-hosted); App Store target **9+/12+** (not Kids Category); R2 self-hosting parked.

## Goal
Make curated YouTube lessons play reliably on real devices and be as kid-safe as embeds allow — by closing the *specific* gaps that remain, not rebuilding what already works.

## Current state (verified in code)
Already built and correct:
- `videoEmbed.ts` — `youtube-nocookie.com` embeds with `playsinline=1 · rel=0 · modestbranding=1`.
- **iOS error-153 fix** — `frontend/public/yt.html` proxy loaded from the real https origin (`VITE_WEB_ORIGIN`, default `https://app.investikid.ai`), because WKWebView strips the Referer on `capacitor://` (WebKit bug 169846). Present in the synced native bundle.
- `VideoLesson.tsx` — hosted/YouTube switch, caption line, transcript disclosure, "Open on YouTube" link, "I watched this" gate.
- `video_health_service.py` + daily cron (`video-health-cron.yml`) + admin `VideoHealthList` — probes each lesson video and emails admins about dead ones.

## The real remaining gaps
1. **The health cron can't detect the 153 cause.** `video_health_service.classify()` maps the YouTube **oembed** HTTP status: 200→ok, 401/404→dead. But oembed returns **200 for a public video whose owner has disabled embedding** — exactly the case that throws "error 153" in the player. So a lesson can be "ok" in admin yet broken for every child. *(This is the single highest-value fix.)*
2. **No end-screen control.** `rel=0` no longer removes related videos — it only restricts them to the same channel. At the end of a lesson video YouTube still shows an end-screen of other videos. For a kids' app we want the video to **end into our own "next lesson" UI**, which requires the YouTube **IFrame Player API** (listen for `onStateChange === ENDED`), not a bare `<iframe src>`.
3. **Graceful in-app failure is incomplete.** `VideoLesson` only shows its "Video unavailable" fallback when the id is *malformed*. If the embed itself fails to load (151/153/network), the child sees YouTube's raw error inside the frame, with no friendly recovery. There's no load-timeout → fallback path.
4. **Privacy disclosure.** `nocookie` is used, but the YouTube embed + Google-as-processor must be **disclosed in the privacy policy** (COPPA / UK Children's Code apply at 9+/12+ because under-13s hold accounts). Doc/legal task, not engineering.
5. **Verify the build-2 fix on device.** Build 1 may have shipped without a baked `VITE_WEB_ORIGIN`, making the `/yt.html` proxy URL wrong → 153. **Build 2 bakes `VITE_WEB_ORIGIN=https://app.investikid.ai`.** Confirm on a real iPhone before assuming any code change is needed. *(This is a W1 QA item; listed here because it may resolve the tester's report outright.)*

---

## Design

### A. Embeddability-aware health check (backend — highest value)
**Modify** `video_health_service.py`. oembed alone is insufficient; add an embeddability signal. Two options:

- **A1 (recommended): YouTube Data API v3 `videos.list?part=status`** → returns `status.embeddable` (bool) and `uploadStatus`. Needs a free API key (`YOUTUBE_API_KEY`, env-gated like R2). When the key is present, classify a non-embeddable public video as a new status **`blocked`** (distinct from `dead`); when absent, fall back to today's oembed behaviour (no regression). Quota is ample (1 unit/video/day vs 10k/day default).
- **A2 (no key): heuristic** — fetch the `nocookie` embed page server-side and detect the "Video unavailable / playback on other websites disabled" marker. Brittle (HTML can change); use only if we refuse an API key.

Add `blocked` to the `VideoHealth.status` set, the admin `VideoHealthList` surfacing, and the cron's admin email ("N videos can't be embedded"). **Recommendation: A1**, env-gated so nothing breaks without the key.

### B. End-screen → "next lesson" (frontend — kid-safety)
**Modify** `VideoLesson.tsx` (+ `yt.html`). Swap the bare iframe for the **IFrame Player API**: load `https://www.youtube.com/iframe_api`, instantiate the player on the same `nocookie` host, and on `onStateChange === YT.PlayerState.ENDED`, hide the player and show the app's "✓ Finished — Mark complete →" panel instead of YouTube's end-screen. The iOS path applies the same logic inside `yt.html` (post a `message` to the app on ENDED). Keep `playsinline`, keep the "Open on YouTube" link. Auto-tick "I watched this" on natural end.

### C. Graceful failure + load timeout (frontend)
**Modify** `VideoLesson.tsx`. Add an `onError`/load-timeout (~8s with no player-ready) → replace the frame with a friendly card: "This video is taking a break — you can read the lesson and continue." Always offer Continue, and surface the transcript if present. The IFrame API's `onError` event (codes 100/101/150/153) drives this directly.

### D. Privacy disclosure (doc)
Add the YouTube/Google-processor disclosure to the privacy policy and link it from the consent flow. Note `nocookie` + "no cookies set until play." No code.

## Out of scope
R2/self-hosting (parked); transcoding/HLS; any change to lesson completion logic, premium gating, or the simulator; changing the App Store category.

## Testing
- **Backend:** `video_health_service` unit tests — `blocked` classification when `status.embeddable=false` (A1, mocked API), oembed fallback unchanged when no key; cron email copy includes blocked count. (`ruff` + `pytest`.)
- **Frontend:** `videoEmbed`/`VideoLesson` vitest — ENDED → shows "Mark complete" panel not the iframe; `onError 153` → friendly fallback + Continue; malformed id path unchanged; vitest-axe clean. Web + native (`isNative`) branches both covered.
- **Device (W1 gate):** on a real iPhone + Android, an embeddable curated video plays, ends into the app panel, and a deliberately non-embeddable id shows the friendly fallback (not a raw YouTube error).

## Success criteria
1. The cron flags embedding-disabled videos as `blocked` before a child hits them (with `YOUTUBE_API_KEY` set).
2. A lesson video ends on InvestiKid's "next lesson" UI, not YouTube recommendations.
3. A failed/blocked video shows a friendly in-app fallback + Continue, never a raw YouTube error.
4. Privacy policy discloses the YouTube embed.
5. Build 2 confirmed to play curated video on a real iPhone (no 153).

## Open question for review
**A1 vs A2** — are you OK adding a free `YOUTUBE_API_KEY` (Google Cloud, no billing needed at this quota) for reliable embeddability detection? It's materially more robust than the HTML heuristic. *I'd set up the key myself only with your go-ahead, and you'd add it to the env (I never touch `.env`).*
