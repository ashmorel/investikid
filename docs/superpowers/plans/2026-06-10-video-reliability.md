# W2 — Video Reliability & Kid-Safety — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]` checkboxes.

**Goal:** Close the real video gaps — detect embedding-disabled videos in the health cron, end lesson videos into our own UI (not YouTube recommendations), fail gracefully, and disclose the embed — without rebuilding the already-working embed mechanics.

**Architecture:** Backend adds an env-gated YouTube Data API embeddability probe → new `blocked` health status (no migration; `status` is free-text `String(16)`). Frontend swaps the bare `<iframe>` for the YouTube **IFrame Player API**, driven by a testable message/event layer, with a graceful-failure fallback. iOS keeps the `/yt.html` proxy, now emitting `postMessage` on end/error.

**Spec:** `docs/superpowers/specs/2026-06-10-video-reliability-design.md`. **Decisions:** A1 (YouTube API key, env-gated) · build in parallel with device-testing build 2.

**Verify:** backend `/Users/leeashmore/Local Repo/.venv/bin/ruff check .` + `pytest`; frontend `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build` (+ vitest-axe for any UI). Branch `testing`; explicit `git add` of named paths only (never `-A`; leave `.gitignore` + iOS build files alone); commit messages end `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. No promotion.

---

### Task 1: Config + embeddability-aware health check (backend)

**Files:**
- Modify: `backend/app/core/config.py` (add `youtube_api_key: str = ""`)
- Modify: `backend/app/services/video_health_service.py`
- Modify: `backend/.env.example` (document `YOUTUBE_API_KEY`)
- Test: `backend/tests/test_video_health_service.py`

Design: after the existing oembed probe returns `ok` for a YouTube video, if `settings.youtube_api_key` is set, call Data API v3 `GET https://www.googleapis.com/youtube/v3/videos?part=status&id={id}&key={key}`. If the item's `status.embeddable is False` → return status `"blocked"`. If the key is empty, behaviour is unchanged (no regression). Add `"blocked"` to the summary init dict (`{"ok":0,"dead":0,"unknown":0,"blocked":0,"dead_items":[],"blocked_items":[]}`) and collect `blocked_items` like `dead_items`. Hosted videos are unaffected.

- [ ] **Step 1: Failing tests** in `test_video_health_service.py`:
```python
# embeddable=false → blocked (key set, mocked transport)
# embeddable=true  → ok
# no key set       → ok (oembed-only path, unchanged)
# dead/unknown oembed paths unchanged
```
Use `httpx.MockTransport` to stub both the oembed and googleapis responses; set the key via monkeypatch on `settings`.

- [ ] **Step 2:** Run, confirm fail (`blocked` not yet produced).
Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_health_service.py -q`

- [ ] **Step 3:** Implement. Add `youtube_api_key` to `Settings`. In `video_health_service.py` add `async def _embeddable(client, youtube_id) -> bool` (Data API call; on any HTTPError or missing item → treat as embeddable=True, i.e. don't false-alarm on a transient API failure). In `_probe`, after `classify` yields `"ok"` and a key exists, set status `"blocked"` when `not await _embeddable(...)`. Thread `blocked` into the summary + `blocked_items` (same shape as dead_items).

- [ ] **Step 4:** Run tests → pass. Then `ruff check .`.

- [ ] **Step 5: Commit**
```bash
cd /Users/leeashmore/investikid
git add backend/app/core/config.py backend/app/services/video_health_service.py backend/.env.example backend/tests/test_video_health_service.py
git commit -m "feat(video-health): detect embedding-disabled videos via YouTube Data API (blocked status)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Cron alerts on blocked videos (backend)

**Files:**
- Modify: `backend/app/video_health/run.py`
- Test: `backend/tests/test_video_health_cron.py`

- [ ] **Step 1: Failing test** — when `check_all_videos` returns `blocked > 0`, `run()` sends an admin alert whose detail lists the blocked items (mock `send_video_alert`/sender; assert called with blocked lines). Existing dead-alert test unchanged.

- [ ] **Step 2:** Run → fail.

- [ ] **Step 3:** Implement. In `run()`, after the dead block, add a blocked block: if `summary["blocked"]`, send an alert headlined `"{n} lesson video(s) can't be embedded"` listing `blocked_items` (same formatting). Update `main()`'s print to include blocked count.

- [ ] **Step 4:** Run tests → pass; `ruff check .`.

- [ ] **Step 5: Commit**
```bash
git add backend/app/video_health/run.py backend/tests/test_video_health_cron.py
git commit -m "feat(video-health): alert admins about embedding-blocked videos

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Surface `blocked` in admin Video Health list (frontend)

**Files:**
- Modify: `frontend/src/components/admin/VideoHealthList.tsx`
- Modify: the admin video-health API type (wherever `status` is typed: `ok|dead|unknown`) → add `blocked`
- Test: the existing VideoHealthList test (or add one)

- [ ] **Step 1: Failing test** — a row with `status: 'blocked'` renders an amber "Embedding disabled" badge distinct from the red "Unavailable"/dead badge.

- [ ] **Step 2:** Run → fail.

- [ ] **Step 3:** Implement — add the `blocked` branch to the status badge map + the type union.

- [ ] **Step 4:** `cd frontend && npx tsc -b && npm run test && npm run lint`.

- [ ] **Step 5: Commit**
```bash
git add frontend/src/components/admin/VideoHealthList.tsx frontend/src/api/<admin-video-health-types-file>.ts frontend/<test-file>
git commit -m "feat(admin): show embedding-blocked video status

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: IFrame Player API — end-screen control + graceful failure (frontend)

**Files:**
- Create: `frontend/src/components/child/lesson/useYouTubePlayer.ts` (testable hook/util)
- Modify: `frontend/src/components/child/lesson/VideoLesson.tsx`
- Modify: `frontend/public/yt.html` (iOS proxy: load IFrame API, postMessage `{type:'yt', event:'ended'|'error'}` to parent)
- Test: `frontend/src/components/child/lesson/__tests__/VideoLesson.test.tsx` (+ a unit test for the hook)

Design: keep the existing platform routing in `videoEmbed.ts`. Add a small layer that reacts to two events regardless of platform — **ended** and **error** — delivered via `window.postMessage` (iOS, from `yt.html`) or the IFrame API `onStateChange`/`onError` (web/Android). VideoLesson:
- On **ended**: hide the player, auto-tick "I watched this", show the "✓ Finished — Mark complete →" panel (NOT YouTube's end-screen).
- On **error** (or an ~8s ready-timeout): show the friendly fallback card — "This video is taking a break — read the lesson and continue." — always with Continue, plus the transcript if present.
Keep "Open on YouTube". Isolate the listener/parse logic into `useYouTubePlayer` so vitest can drive synthetic `message` events and assert state without a real player.

- [ ] **Step 1: Failing tests** (mock postMessage; no real YouTube):
```
- ended message → renders "Mark complete" panel, hides iframe, watched=true
- error message (code 153/150/101/100) → renders friendly fallback + Continue
- ready-timeout (fake timers, 8s, no ready) → friendly fallback
- malformed id path (buildYouTubeUrls null) → unchanged fallback
- vitest-axe: clean in player, ended, and fallback states
```

- [ ] **Step 2:** Run → fail.

- [ ] **Step 3:** Implement `useYouTubePlayer.ts` (origin-checked message handler: accept only messages from the embed origin / `VITE_WEB_ORIGIN`; parse `{type:'yt',event}`), wire it into `VideoLesson.tsx`, and update `yt.html` to run the IFrame API and postMessage ended/error to `parent` with the app origin as target. On web/Android, instantiate the API player in `VideoLesson` and forward its `onStateChange===ENDED`/`onError` through the same handler.

- [ ] **Step 4:** `cd frontend && npx tsc -b && npm run test && npm run lint && npm run build`.

- [ ] **Step 5: Commit**
```bash
git add frontend/src/components/child/lesson/useYouTubePlayer.ts frontend/src/components/child/lesson/VideoLesson.tsx frontend/public/yt.html frontend/src/components/child/lesson/__tests__/VideoLesson.test.tsx
git commit -m "feat(lesson): end videos into app UI + graceful failure (IFrame Player API)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Privacy-policy disclosure (doc)

**Files:**
- Modify: the privacy policy doc/route (locate via grep `privacy`); add the YouTube embed + Google-as-processor disclosure, note `youtube-nocookie` (no cookies until play), bump `privacy_notice_version` if the app tracks acceptance.

- [ ] **Step 1:** Locate the privacy notice (content + `privacy_notice_version` in config). Add a "Third-party content: YouTube" paragraph. If a version string gates re-consent, decide with care (bumping forces re-acceptance) — default: add the disclosure, and only bump the version if legal review wants re-consent. Note the decision in the commit.

- [ ] **Step 2: Commit**
```bash
git add <privacy-doc-path>
git commit -m "docs(privacy): disclose YouTube embed + Google processor

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Full regression + push

- [ ] Backend: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q`
- [ ] Frontend: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
- [ ] `git push origin testing`; report CI. (No `cap sync` needed for the cron/admin work; the IFrame change is web-bundle and ships via Vercel; a native rebuild folds into the next TestFlight.)

## Self-review
- Spec coverage: A (Task 1+2+3), B+C (Task 4), D (Task 5). Build-2 device verification is a W1 QA item, tracked separately.
- No migration (status is free-text). No premium/completion-logic change. Env-gated API key → no regression without it.
- Open detail for the implementer: confirm the admin video-health status type location and the privacy-notice file during Task 3/5.
