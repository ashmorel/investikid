# Module Archive + 30-Day Purge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move retired modules into an admin "Archived" section; "Delete" soft-archives (recoverable), and archived modules are auto-purged after 30 days.

**Architecture:** Add a nullable `modules.archived_at` timestamp (NULL = active). The admin delete endpoint sets it instead of hard-deleting (and refuses live modules); a restore endpoint clears it; curriculum republish auto-sets it on retired modules; a cron-gated `/internal` endpoint hard-deletes modules past the 30-day window (DB cascade cleans children). The admin Modules list splits active vs archived.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Postgres; React + TanStack Query + Vitest; GitHub Actions cron.

## Global Constraints
- Spec: `docs/superpowers/specs/2026-06-21-module-archive-purge-design.md`.
- Branch `main` (beta straight-to-main). End commits with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + the `db_session`/`admin_client` fixtures — never a raw `AsyncClient`.
- DB change = hand-written, chained Alembic migration; check `alembic heads` first (current head: `c3e5a7b9d1f2`).
- New `/internal/*` cron POST must be added to `_DEFAULT_EXEMPT_PATHS` in `backend/app/core/csrf.py` (else the Actions cron gets 403).
- Backend verify: `/Users/leeashmore/Local Repo/.venv/bin/pytest` + `ruff check .` (from `backend/`). Frontend verify: `npm run lint`, `npx tsc -b`, `npm test`, `npm run build` (from `frontend/`).

---

### Task 1: Schema — `archived_at` column, model field, retention setting

**Files:**
- Create: `backend/alembic/versions/<rev>_module_archived_at.py`
- Modify: `backend/app/models/content.py` (Module, ~line 45 after `published`)
- Modify: `backend/app/core/config.py` (after `data_retention_days`, ~line 45)
- Test: `backend/tests/test_module_archive.py`

**Interfaces:**
- Produces: `Module.archived_at: datetime | None`; `settings.archived_module_retention_days: int` (=30).

- [ ] **Step 1: Add the model field.** In `content.py`, `Module`, immediately after the `published` column:
```python
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
```
Confirm `datetime` and `DateTime` are imported at the top of the file (add to the existing `from datetime import datetime` / `from sqlalchemy import ... DateTime` imports if missing).

- [ ] **Step 2: Add the retention setting.** In `config.py`, after `data_retention_days: int = 30`:
```python
    archived_module_retention_days: int = 30  # archived modules hard-purged after this
```

- [ ] **Step 3: Find the current head.** Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` → expect `c3e5a7b9d1f2 (head)`.

- [ ] **Step 4: Write the migration.** Create the revision file with `down_revision = "c3e5a7b9d1f2"`:
```python
"""module archived_at + backfill retired modules

Revision ID: <rev>
Revises: c3e5a7b9d1f2
"""
from alembic import op
import sqlalchemy as sa

revision = "<rev>"
down_revision = "c3e5a7b9d1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("modules", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_modules_archived_at", "modules", ["archived_at"])
    # Backfill: archive genuinely-retired modules (published=false AND not referenced
    # by any active proposal). Staged in-progress modules (in an accepted proposal)
    # stay active.
    op.execute(
        """
        UPDATE modules SET archived_at = now()
        WHERE published = false
          AND NOT EXISTS (
            SELECT 1 FROM market_curriculum_proposal p,
                 jsonb_array_elements((p.proposal_json)::jsonb->'modules') m
            WHERE p.status IN ('proposed','accepted','published')
              AND (m->>'module_id')::uuid = modules.id
          )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_modules_archived_at", table_name="modules")
    op.drop_column("modules", "archived_at")
```

- [ ] **Step 5: Write the failing test** in `test_module_archive.py`:
```python
import uuid
import pytest
from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from app.models.content import Module
from app.models.market_curriculum import MarketCurriculumProposal

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _module(db_session, *, published, market="GB"):
    m = Module(topic="t", title="M", country_codes=[], market_code=market,
               is_premium=False, order_index=0, icon="📚", published=published)
    db_session.add(m)
    await db_session.flush()
    return m


async def test_module_has_archived_at_default_null(db_session):
    m = await _module(db_session, published=True)
    assert m.archived_at is None
```

- [ ] **Step 6: Run it.** `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_module_archive.py -v` → PASS (column exists via model; migration tested in CI's fresh DB).

- [ ] **Step 7: Apply + sanity-check migration.** `/Users/leeashmore/Local\ Repo/.venv/bin/alembic upgrade head` then `/Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` (one head). `ruff check .`.

- [ ] **Step 8: Commit.**
```bash
git add backend/app/models/content.py backend/app/core/config.py backend/alembic/versions/ backend/tests/test_module_archive.py
git commit -m "feat(modules): archived_at column + retention setting + retired-module backfill"
```

---

### Task 2: Soft-archive delete + block live + restore endpoint + schema

**Files:**
- Modify: `backend/app/routers/admin.py` (`delete_module` ~line 269; add restore endpoint after it)
- Modify: `backend/app/schemas/admin.py` (`AdminModule` ~line 48, `ModuleOut` ~line 80)
- Test: `backend/tests/test_module_archive.py`

**Interfaces:**
- Consumes: `Module.archived_at` (Task 1).
- Produces: `DELETE /admin/modules/{id}` soft-archives (409 if published); `POST /admin/modules/{id}/restore` clears `archived_at`; `AdminModule.archived_at: datetime | None`.

- [ ] **Step 1: Add `archived_at` to schemas.** In `admin.py` schemas, add to `AdminModule` and `ModuleOut`:
```python
    archived_at: datetime | None = None
```
Ensure `from datetime import datetime` is imported. Update every place an `AdminModule`/`ModuleOut` is constructed from a `Module` to pass `archived_at=m.archived_at` (search `ModuleOut(` / `AdminModule(` in `app/routers/admin.py`). If they're built with `from_attributes`/`model_validate(module)`, no change needed — verify which pattern is used and only add explicit kwargs where the code constructs them field-by-field.

- [ ] **Step 2: Write failing tests:**
```python
async def test_delete_archives_non_live_module(admin_client, db_session):
    m = await _module(db_session, published=False)
    await db_session.commit()
    r = await admin_client.delete(f"/admin/modules/{m.id}")
    assert r.status_code == 200, r.text
    await db_session.refresh(m)
    assert m.archived_at is not None


async def test_delete_live_module_blocked_409(admin_client, db_session):
    m = await _module(db_session, published=True)
    await db_session.commit()
    r = await admin_client.delete(f"/admin/modules/{m.id}")
    assert r.status_code == 409, r.text
    await db_session.refresh(m)
    assert m.archived_at is None


async def test_restore_clears_archived_at(admin_client, db_session):
    m = await _module(db_session, published=False)
    m.archived_at = datetime.now(UTC)
    await db_session.commit()
    r = await admin_client.post(f"/admin/modules/{m.id}/restore")
    assert r.status_code == 200, r.text
    await db_session.refresh(m)
    assert m.archived_at is None
```

- [ ] **Step 3: Run → fail.** `pytest tests/test_module_archive.py -v` (delete still hard-deletes; no restore route).

- [ ] **Step 4: Replace `delete_module` body** (`admin.py:269`):
```python
@router.delete("/modules/{module_id}")
async def delete_module(module_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if module.published:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Unpublish or replace this live module before archiving")
    module.archived_at = datetime.now(UTC)
    await session.commit()
    return {"status": "archived"}


@router.post("/modules/{module_id}/restore")
async def restore_module(module_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    module.archived_at = None
    await session.commit()
    return {"status": "restored"}
```
Ensure `datetime`/`UTC` imported in `admin.py` (`from datetime import UTC, datetime`).

- [ ] **Step 5: Run → pass.** `pytest tests/test_module_archive.py -v`. `ruff check .`.

- [ ] **Step 6: Commit.**
```bash
git add backend/app/routers/admin.py backend/app/schemas/admin.py backend/tests/test_module_archive.py
git commit -m "feat(modules): delete soft-archives (blocks live) + restore endpoint + archived_at in schema"
```

---

### Task 3: Republish auto-archives retired modules

**Files:**
- Modify: `backend/app/services/market_curriculum/curriculum_publish_service.py`
- Test: `backend/tests/test_curriculum_endpoints.py`

**Interfaces:**
- Consumes: `Module.archived_at`.
- Produces: `publish_market_curriculum` sets `archived_at=now()` on the modules it retires.

- [ ] **Step 1: Write failing test** (in `test_curriculum_endpoints.py`, follows existing seed helpers there):
```python
async def test_publish_archives_retired_modules(admin_client, db_session):
    from datetime import datetime
    from app.models.content import Module
    # A previously-live module that the new curriculum will replace.
    old = Module(topic="t", title="Old", country_codes=[], market_code="US",
                 is_premium=False, order_index=99, icon="📚", published=True)
    db_session.add(old)
    await db_session.flush()
    # Build + accept a fresh proposal, generate a lesson into each staged module,
    # then publish (reuse the helpers used by test_design_then_accept_flow).
    # ... seed verified brief, design (mock LLM), accept, add one Lesson per staged
    #     module so the publish guard passes ...
    # After publish:
    await db_session.refresh(old)
    assert old.archived_at is not None
```
(Model this on `test_design_then_accept_flow`'s mock + the publish guard "every staged module must have a lesson"; add a `Lesson` row per staged module before calling publish.)

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Update the retire `UPDATE`** in `curriculum_publish_service.py` (the statement that sets `published=False` on `Module.id.notin_(staged_ids)`):
```python
    from datetime import UTC, datetime
    retired = (await session.execute(
        update(Module)
        .where(Module.market_code == market_code, Module.published.is_(True),
               Module.id.notin_(staged_ids))
        .values(published=False, archived_at=datetime.now(UTC))
    )).rowcount or 0
```

- [ ] **Step 4: Run → pass.** `ruff check .`.

- [ ] **Step 5: Commit.**
```bash
git add backend/app/services/market_curriculum/curriculum_publish_service.py backend/tests/test_curriculum_endpoints.py
git commit -m "feat(curriculum): republish auto-archives the modules it retires"
```

---

### Task 4: Purge service + internal cron endpoint + CSRF + workflow step

**Files:**
- Create: `backend/app/services/module_purge_service.py`
- Modify: `backend/app/routers/internal.py` (new endpoint)
- Modify: `backend/app/core/csrf.py` (`_DEFAULT_EXEMPT_PATHS`, line 26 set)
- Modify: `.github/workflows/video-health-cron.yml`
- Test: `backend/tests/test_module_purge.py`

**Interfaces:**
- Consumes: `Module.archived_at`, `settings.archived_module_retention_days`.
- Produces: `module_purge_service.purge_archived_modules(session, *, now) -> int`; `POST /internal/purge-archived-modules` (X-Cron-Secret).

- [ ] **Step 1: Write the purge service** in `module_purge_service.py`:
```python
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.content import Lesson, Module


async def purge_archived_modules(session: AsyncSession, *, now: datetime) -> int:
    """Hard-delete modules archived longer than the retention window. DB-level
    ON DELETE CASCADE removes levels/lessons/progress; lessons are deleted
    explicitly first to match the existing delete_module path."""
    cutoff = now - timedelta(days=settings.archived_module_retention_days)
    ids = (await session.execute(
        select(Module.id).where(Module.archived_at.is_not(None),
                                Module.archived_at < cutoff)
    )).scalars().all()
    if not ids:
        return 0
    await session.execute(delete(Lesson).where(Lesson.module_id.in_(ids)))
    await session.execute(delete(Module).where(Module.id.in_(ids)))
    return len(ids)
```

- [ ] **Step 2: Write failing tests** in `test_module_purge.py`:
```python
import pytest
from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from app.models.content import Module
from app.services.module_purge_service import purge_archived_modules

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _m(db_session, archived_days_ago):
    m = Module(topic="t", title="M", country_codes=[], market_code="GB",
               is_premium=False, order_index=0, icon="📚", published=False)
    if archived_days_ago is not None:
        m.archived_at = datetime.now(UTC) - timedelta(days=archived_days_ago)
    db_session.add(m)
    await db_session.flush()
    return m


async def test_purges_only_past_window(db_session):
    old = await _m(db_session, 31)
    recent = await _m(db_session, 5)
    active = await _m(db_session, None)
    n = await purge_archived_modules(db_session, now=datetime.now(UTC))
    assert n == 1
    remaining = set((await db_session.execute(select(Module.id))).scalars().all())
    assert old.id not in remaining
    assert recent.id in remaining and active.id in remaining
```

- [ ] **Step 3: Run → fail, then pass** after Step 1 exists. `pytest tests/test_module_purge.py -v`.

- [ ] **Step 4: Add the endpoint** to `internal.py` (mirror the cron-secret pattern exactly):
```python
from app.services import module_purge_service  # add to the existing services import

@router.post("/purge-archived-modules")
async def trigger_purge_archived_modules(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    purged = await module_purge_service.purge_archived_modules(session, now=datetime.now(UTC))
    await session.commit()
    return {"purged": purged}
```

- [ ] **Step 5: Add to CSRF exempt set** in `csrf.py` `_DEFAULT_EXEMPT_PATHS`:
```python
    "/internal/purge-archived-modules",
```

- [ ] **Step 6: Test the endpoint gate** (append to `test_module_purge.py`):
```python
async def test_purge_endpoint_requires_secret(admin_client, monkeypatch):
    from app.core.config import settings as s
    monkeypatch.setattr(s, "cron_secret", "sekret")
    bad = await admin_client.post("/internal/purge-archived-modules")
    assert bad.status_code == 401
    ok = await admin_client.post("/internal/purge-archived-modules",
                                 headers={"X-Cron-Secret": "sekret"})
    assert ok.status_code == 200 and "purged" in ok.json()
```

- [ ] **Step 7: Add the cron step** to `.github/workflows/video-health-cron.yml` (a new independent `curl` step in the existing job, alongside the others, with `--retry 3`):
```yaml
      - name: Purge archived modules (>30d)
        env:
          CRON_SECRET: ${{ secrets.CRON_SECRET }}
        run: |
          set -uo pipefail
          curl -fsS --retry 3 --retry-all-errors -X POST \
            -H "X-Cron-Secret: ${CRON_SECRET}" \
            "${BACKEND_URL}/internal/purge-archived-modules" || echo "::warning::purge step failed"
```

- [ ] **Step 8: Run all + lint.** `pytest tests/test_module_purge.py -v && ruff check .`.

- [ ] **Step 9: Commit.**
```bash
git add backend/app/services/module_purge_service.py backend/app/routers/internal.py backend/app/core/csrf.py .github/workflows/video-health-cron.yml backend/tests/test_module_purge.py
git commit -m "feat(modules): 30-day purge service + cron-gated internal endpoint + workflow step"
```

---

### Task 5: Frontend — Archived section + Restore

**Files:**
- Modify: `frontend/src/api/admin.ts` (`AdminModule` type; add `useRestoreModule`)
- Modify: `frontend/src/components/admin/ModuleList.tsx`
- Modify: `frontend/src/locales/en/admin.json` (`moduleList` copy)
- Test: `frontend/src/components/admin/__tests__/ModuleList.test.tsx`

**Interfaces:**
- Consumes: `GET /admin/modules` now returns `archived_at`; `POST /admin/modules/{id}/restore`.

- [ ] **Step 1: Extend the type + hook** in `admin.ts`. Add to `AdminModule`:
```ts
  archived_at?: string | null;
```
Add a restore hook near `useDeleteModule`:
```ts
export function useRestoreModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/modules/${id}/restore`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'modules'] }),
  });
}
```

- [ ] **Step 2: Add copy** to `admin.json` under `moduleList`:
```json
      "archivedHeading": "Archived",
      "archivedHint": "Auto-deletes in {{days}} days",
      "restore": "Restore",
      "deleteMessage": "Archive this module? It moves to Archived and is permanently deleted after 30 days — you can restore it before then."
```
(Replace the existing `deleteMessage` value.)

- [ ] **Step 3: Write failing test** in `ModuleList.test.tsx` (mock `useModules`/`useRestoreModule` like the existing admin tests):
```tsx
it('renders archived modules in a separate section with restore', async () => {
  modulesData = [
    { id: 'a', topic: 't', title: 'Active Mod', market_code: 'GB', order_index: 0, archived_at: null },
    { id: 'z', topic: 't', title: 'Old Mod', market_code: 'GB', order_index: 1,
      archived_at: new Date(Date.now() - 5*864e5).toISOString() },
  ];
  render(<ModuleList />, { wrapper });
  const archivedHeading = await screen.findByText('Archived');
  expect(archivedHeading).toBeInTheDocument();
  // Active module is NOT under the archived section; old one shows a restore button
  expect(screen.getByRole('button', { name: /restore/i })).toBeInTheDocument();
  expect(screen.getByText(/Auto-deletes in 25 days/)).toBeInTheDocument();
});
```

- [ ] **Step 4: Run → fail.** `cd frontend && npx vitest run src/components/admin/__tests__/ModuleList.test.tsx`.

- [ ] **Step 5: Implement the split** in `ModuleList.tsx`:
  - Derive `const active = modules.filter(m => !m.archived_at)` and `const archived = modules.filter(m => !!m.archived_at)`.
  - Render the existing reorderable list from `active`.
  - Below it, if `archived.length`, render a section: heading `t('moduleList.archivedHeading')`; for each, the title, `t('moduleList.archivedHint', { days: daysLeft })` where `daysLeft = Math.max(0, 30 - Math.floor((Date.now() - Date.parse(m.archived_at)) / 864e5))`, and a Restore button calling `restore.mutate(m.id)` (`const restore = useRestoreModule()`).
  - Keep the delete confirm dialog; it now uses the new `deleteMessage` copy.

- [ ] **Step 6: Run → pass.** Then full frontend verify: `npm run lint && npx tsc -b && npm test && npm run build`.

- [ ] **Step 7: Commit.**
```bash
git add frontend/src/api/admin.ts frontend/src/components/admin/ModuleList.tsx frontend/src/locales/en/admin.json frontend/src/components/admin/__tests__/ModuleList.test.tsx
git commit -m "feat(admin): Archived modules section with restore + 30-day countdown"
```

---

### Final verification
- [ ] Backend: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q && ruff check .`
- [ ] Frontend: `cd frontend && npm run lint && npx tsc -b && npm test && npm run build`
- [ ] Push to `main` (beta flow); watch CI green; **ask the user about a prod DB snapshot before the migration runs on prod** (standing rule).
- [ ] After deploy: confirm the old GB modules now appear under Archived in the admin; deleting a non-live module archives it; Restore works; a manual `workflow_dispatch` of the cron returns `{"purged": ...}`.
