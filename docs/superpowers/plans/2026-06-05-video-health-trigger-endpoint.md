# Video-Health Trigger Endpoint + Scheduled Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fragile separate Railway cron service with a secret-guarded `POST /internal/video-health/run` endpoint on the existing backend, triggered by a scheduled GitHub Actions workflow.

**Architecture:** A new CSRF-exempt internal router authenticates via a shared `X-Cron-Secret` header and runs the existing, tested `app.video_health.run.run(session)` (check + dead-alert email + commit). A daily GitHub Actions workflow `curl`s it with secrets; a non-2xx response fails the workflow.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async (backend); GitHub Actions (scheduler).

---

## Reference facts (verified — read before starting)

- **Spec:** `invest-ed/docs/superpowers/specs/2026-06-05-video-health-trigger-endpoint-design.md`.
- **CSRF exempt list:** `app/core/csrf.py` — `_DEFAULT_EXEMPT_PATHS = frozenset({ ... "/billing/webhook", "/parent/auth/oauth/google", "/parent/auth/oauth/apple" })` (line ~26). Add the exact path `/internal/video-health/run`.
- **Router registration:** `app/main.py` imports `from app.routers import X as X_router` (lines 15-26) and calls `application.include_router(X_router.router)` (lines 159-172). Add an `internal_router` the same way.
- **Reuse:** `app/video_health/run.py::run(session: AsyncSession) -> dict` already does check_all_videos + emails `get_alert_emails` recipients only when dead + commits, returning `{"ok","dead","unknown","dead_items"}`. The endpoint calls it and returns the summary (drop `dead_items` from the response to keep it small).
- **Config:** `app/core/config.py` `Settings` — flat fields with `""` defaults for optional secrets (e.g. `stripe_secret_key: str = ""`). Add `cron_secret: str = ""`. Document in `backend/.env.example`.
- **not_configured / secret-compare patterns:** SP-D1 OAuth returns `503 {"detail":"not_configured"}`; use `secrets.compare_digest` for the header check (constant time).
- **Tests:** async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`db_session` fixtures. Monkeypatch the router's `run` so the endpoint test makes no network/DB-heavy call. The `client` fixture sends requests without a CSRF token by default — use it to prove CSRF-exemption. Ruff rejects semicolons in tests.
- **GitHub workflows** live in `.github/workflows/` (the CI workflow is there). New file: `.github/workflows/video-health-cron.yml`.

## Commands

- Backend (from `invest-ed/backend`): test `/Users/leeashmore/Local Repo/.venv/bin/pytest`; lint `/Users/leeashmore/Local Repo/.venv/bin/ruff check .`.
- Git from repo root `/Users/leeashmore/Local Repo`; commit to `main`; end commit messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. NEVER read/modify any `.env`. CI's 6 jobs gate the Railway deploy.

---

## Task 1: `cron_secret` config + CSRF exemption + the internal endpoint

**Files:**
- Modify: `invest-ed/backend/app/core/config.py` (add `cron_secret`)
- Modify: `invest-ed/backend/.env.example` (document it)
- Modify: `invest-ed/backend/app/core/csrf.py` (exempt the path)
- Create: `invest-ed/backend/app/routers/internal.py`
- Modify: `invest-ed/backend/app/main.py` (register the router)
- Test: `invest-ed/backend/tests/test_internal_video_health.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_internal_video_health.py`:

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/internal/video-health/run"


async def test_503_when_secret_unset(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "")
    r = await client.post(_PATH, headers={"X-Cron-Secret": "whatever"})
    assert r.status_code == 503
    assert r.json()["detail"] == "not_configured"


async def test_401_when_secret_missing_or_wrong(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    assert (await client.post(_PATH)).status_code == 401
    r = await client.post(_PATH, headers={"X-Cron-Secret": "nope"})
    assert r.status_code == 401


async def test_200_runs_check_when_secret_matches(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")

    called = {}

    async def fake_run(session):
        called["yes"] = True
        return {"ok": 3, "dead": 0, "unknown": 1, "dead_items": []}

    monkeypatch.setattr(internal, "run", fake_run)
    r = await client.post(_PATH, headers={"X-Cron-Secret": "s3cr3t"})
    assert r.status_code == 200
    body = r.json()
    assert called.get("yes") is True
    assert body["ok"] == 3 and body["dead"] == 0 and body["unknown"] == 1
    assert "dead_items" not in body  # summary only
```

- [ ] **Step 2: Run it — expect FAIL (404, route missing)**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_internal_video_health.py -v`
Expected: FAIL — endpoint not found.

- [ ] **Step 3: Add the config field + .env.example**

In `app/core/config.py` add near the other optional secrets:
```python
    cron_secret: str = ""  # shared secret for POST /internal/video-health/run (machine trigger)
```
In `backend/.env.example` add: `CRON_SECRET=` with a one-line comment ("enables the scheduled video-health trigger endpoint; set the same value as the GitHub Actions CRON_SECRET secret").

- [ ] **Step 4: CSRF-exempt the path**

In `app/core/csrf.py`, add `"/internal/video-health/run",` to the `_DEFAULT_EXEMPT_PATHS` frozenset (alongside `/billing/webhook`).

- [ ] **Step 5: Create the internal router**

Create `app/routers/internal.py`:

```python
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.video_health.run import run

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/video-health/run")
async def trigger_video_health(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    summary = await run(session)
    return {"ok": summary["ok"], "dead": summary["dead"], "unknown": summary["unknown"]}
```

- [ ] **Step 6: Register the router**

In `app/main.py`, add the import with the others: `from app.routers import internal as internal_router`, and `application.include_router(internal_router.router)` alongside the other `include_router` calls.

- [ ] **Step 7: Run tests — expect PASS**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_internal_video_health.py -v`
Expected: 3 passed. (The CSRF middleware does not 403 the POST because the path is exempt; the secret is the auth.)

- [ ] **Step 8: Lint + commit**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/core/config.py invest-ed/backend/.env.example invest-ed/backend/app/core/csrf.py invest-ed/backend/app/routers/internal.py invest-ed/backend/app/main.py invest-ed/backend/tests/test_internal_video_health.py
git commit -m "feat(video-health): secret-guarded /internal/video-health/run trigger endpoint

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Scheduled GitHub Actions workflow + docs

**Files:**
- Create: `.github/workflows/video-health-cron.yml`
- Modify: `invest-ed/docs/superpowers/PROGRESS.md`, `invest-ed/AGENTS.md`

- [ ] **Step 1: Add the scheduled workflow**

Create `.github/workflows/video-health-cron.yml`:

```yaml
name: Video health cron

on:
  schedule:
    - cron: "0 6 * * *"   # daily 06:00 UTC
  workflow_dispatch: {}      # manual "Run workflow" button

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger video-health check
        run: |
          curl -fsS -X POST \
            -H "X-Cron-Secret: ${{ secrets.CRON_SECRET }}" \
            "${{ secrets.BACKEND_URL }}/internal/video-health/run"
```
(`-f` makes a non-2xx response a non-zero exit → the workflow run fails visibly. `secrets.BACKEND_URL` is the Railway backend base URL with no trailing slash, e.g. `https://<backend>.up.railway.app`.)

- [ ] **Step 2: Validate the workflow YAML**

Run: `cd "/Users/leeashmore/Local Repo" && python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/video-health-cron.yml')); print('yaml ok')"`
Expected: `yaml ok`. (Confirms it's well-formed; GitHub will pick it up on push.)

- [ ] **Step 3: Update docs**

- In `invest-ed/docs/superpowers/PROGRESS.md`, update the video-health row (or add a note): the periodic check now runs via `POST /internal/video-health/run` (secret-guarded) triggered by the `Video health cron` GitHub Actions workflow. **USER: set `CRON_SECRET` on the Railway backend + add GitHub repo secrets `CRON_SECRET` (same value) and `BACKEND_URL`; delete the old separate Railway cron service.** On-demand "Check now" in Admin → Video health still works regardless.
- Mirror a one-liner in `invest-ed/AGENTS.md`.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add .github/workflows/video-health-cron.yml invest-ed/docs/superpowers/PROGRESS.md invest-ed/AGENTS.md
git commit -m "feat(video-health): scheduled GitHub Actions trigger + docs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Regression + push

- [ ] **Step 1: Backend regression**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest`
Expected: ruff clean; tests pass (rely on CI if local Postgres hangs).

- [ ] **Step 2: Push + watch CI**

```bash
cd "/Users/leeashmore/Local Repo"
git push origin main
```
Confirm all 6 CI jobs green. (No frontend change; the new workflow does not run in PR CI — it's schedule/dispatch only.)

- [ ] **Step 3: Close-out note (report to user)**

The endpoint is live once deployed, but the schedule only works after the USER sets `CRON_SECRET` (Railway backend) + the two GitHub repo secrets (`CRON_SECRET`, `BACKEND_URL`). Then they can hit **Actions → Video health cron → Run workflow** to test immediately and see the JSON summary in the step log. The old Railway cron service can be deleted.

---

## Self-review notes

- **Spec coverage:** config `cron_secret` (T1), CSRF exemption (T1 Step 4), the secret-guarded endpoint reusing `run()` with 503/401/200 paths (T1), summary-only response (T1 test asserts no `dead_items`), GitHub Actions scheduler with the two secrets (T2), docs + setup (T2/T3), regression/push (T3).
- **Placeholder scan:** full code + tests in every step.
- **Type consistency:** `cron_secret` (config) ↔ `settings.cron_secret` (router) ↔ `CRON_SECRET` (env/.env.example/GH secret); `run(session) -> {ok,dead,unknown,dead_items}` reused; response is the 3-key summary. Header `X-Cron-Secret` consistent between endpoint, test, and workflow.
- **Security:** `secrets.compare_digest` constant-time compare; disabled by default (503 when unset); CSRF-exempt is intentional + safe (secret is the auth, idempotent, low blast radius).
