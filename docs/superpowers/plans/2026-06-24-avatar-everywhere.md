# Avatar Everywhere Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the child's Penny avatar (equipped skin + accessories) in the top-left nav of every page and on every leaderboard row.

**Architecture:** No DB change — avatars derive from the existing `UserCosmetic`/`CosmeticItem` tables. The leaderboard service gains one batched query that attaches each row's equipped cosmetics; the frontend renders the existing `Penny` component in the nav and in leaderboard rows.

**Tech Stack:** FastAPI + async SQLAlchemy (no migration); React + TS + React Query + react-i18next + Tailwind; pytest (`pytest.mark.asyncio(loop_scope="session")` + `client`/`db_session` fixtures); vitest + vitest-axe.

## Global Constraints

- **No migration** — the avatar is read from `UserCosmetic` (equipped) joined to `CosmeticItem` (slug, type). Do not add columns.
- **Avatar = Penny only** (skin + accessories). Backgrounds are NOT shown in the nav or leaderboard.
- **Privacy unchanged:** public (market/global) leaderboard scopes still include only `leaderboard_consent AND NOT leaderboard_hidden` users; the avatar adds no PII and is `aria-hidden` (the name/handle carries the accessible label).
- **Identity per scope unchanged:** friends → `username`; market/global → `display_handle`.
- Async tests: `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`db_session` fixtures (never a raw AsyncClient). Test schema is built from models via `create_all`.
- Commit to `main`; end messages with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`. Backend deploys on green CI; web is a manual two-step Vercel deploy.
- GOTCHA: the local test Postgres can hang after a killed pytest run (~90s+ = environmental → rely on CI). The frontend has ~68 pre-existing local vitest failures from a baked `VITE_API_BASE_URL` (they pass in CI) — ignore them; run only the affected tests + tsc + lint + build.

---

### Task 1: Leaderboard rows carry equipped cosmetics

**Files:**
- Modify: `backend/app/services/leaderboard_service.py`
- Modify: `backend/app/schemas/gamification.py` (add `AvatarOut`, extend `LeaderboardRowOut`)
- Modify: `backend/app/routers/gamification.py` (map `avatar` in the `/leaderboard` response)
- Test: `backend/tests/test_leaderboard_avatar.py`

**Interfaces:**
- Consumes: `UserCosmetic`, `CosmeticItem` (`app/models/cosmetics.py`); existing `leaderboard()` row-building.
- Produces:
  - `AvatarData(skin: str | None, accessories: list[str])` dataclass on `LeaderboardRow.avatar`.
  - `AvatarOut { skin: str | None, accessories: list[str] }`; `LeaderboardRowOut.avatar: AvatarOut`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_leaderboard_avatar.py
import uuid
from datetime import UTC, datetime
import pytest
from sqlalchemy import select
from app.models.user import User
from app.models.content import Lesson, LessonCompletion
from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.services.leaderboard_service import leaderboard
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def _mk(client, db_session, email, *, market="GB"):
    await _register_and_login(client, email=email, username=email.split("@")[0])
    u = await db_session.scalar(select(User).where(User.email == email))
    u.active_market_code = market
    u.country_code = "GB"
    u.leaderboard_consent = True
    u.leaderboard_hidden = False
    u.display_handle = f"H{email.split('@')[0]}"
    await db_session.commit()
    return u

async def _equip(db_session, user, slug, ctype):
    item = await db_session.scalar(select(CosmeticItem).where(CosmeticItem.slug == slug))
    if item is None:
        item = CosmeticItem(slug=slug, name=slug, emoji="🎩", type=ctype, coin_cost=0, is_premium=False)
        db_session.add(item)
        await db_session.flush()
    db_session.add(UserCosmetic(user_id=user.id, item_id=item.id, equipped=True, unlocked_at=datetime.now(UTC)))
    await db_session.commit()

async def _add_xp(db_session, user, amount):
    from app.models.content import Module
    mod = Module(title="M", market_code="GB"); db_session.add(mod); await db_session.flush()
    lesson = Lesson(module_id=mod.id, title="L", xp_reward=amount, order_index=0); db_session.add(lesson); await db_session.flush()
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, completed_at=datetime.now(UTC)))
    await db_session.commit()

async def test_rows_include_equipped_avatar(client, db_session):
    me = await _mk(client, db_session, "av_me@example.com")
    await _equip(db_session, me, "skin_sky", "skin")
    await _equip(db_session, me, "party_hat", "accessory")
    await _equip(db_session, me, "sunglasses", "accessory")
    await _add_xp(db_session, me, 30)

    rows = await leaderboard(db_session, viewer=me, scope="market", metric="xp")
    mine = next(r for r in rows if r.is_me)
    assert mine.avatar.skin == "skin_sky"
    assert set(mine.avatar.accessories) == {"party_hat", "sunglasses"}

async def test_row_with_no_cosmetics_has_empty_avatar(client, db_session):
    me = await _mk(client, db_session, "av_bare@example.com")
    await _add_xp(db_session, me, 10)
    rows = await leaderboard(db_session, viewer=me, scope="global", metric="xp")
    mine = next(r for r in rows if r.is_me)
    assert mine.avatar.skin is None
    assert mine.avatar.accessories == []
```

(If your repo's `Module`/`Lesson` constructors require other non-default fields, read `backend/app/models/content.py` and pass them — match the existing `test_leaderboard_service.py` helper style, which solved the same setup.)

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: 'LeaderboardRow' object has no attribute 'avatar'`)

Run: `cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m pytest tests/test_leaderboard_avatar.py -q`

- [ ] **Step 3: Implement in `leaderboard_service.py`**

Add the import and dataclass near the top (after the existing imports / `LeaderboardRow`):

```python
from app.models.cosmetics import CosmeticItem, UserCosmetic

@dataclass
class AvatarData:
    skin: str | None
    accessories: list[str]
```

Add `avatar` to `LeaderboardRow`:

```python
@dataclass
class LeaderboardRow:
    rank: int
    name: str
    country_code: str | None
    points: int
    is_me: bool
    avatar: AvatarData
```

Add the batched helper:

```python
async def _avatars_for(session, user_ids: list) -> dict:
    """Map user_id -> AvatarData(equipped skin + accessory slugs). One query."""
    if not user_ids:
        return {}
    stmt = (
        select(UserCosmetic.user_id, CosmeticItem.type, CosmeticItem.slug)
        .join(CosmeticItem, CosmeticItem.id == UserCosmetic.item_id)
        .where(UserCosmetic.equipped.is_(True), UserCosmetic.user_id.in_(user_ids))
        .order_by(UserCosmetic.user_id, CosmeticItem.slug)
    )
    out: dict = {}
    for uid, ctype, slug in (await session.execute(stmt)).all():
        a = out.setdefault(uid, AvatarData(skin=None, accessories=[]))
        if ctype == "skin":
            a.skin = slug
        elif ctype == "accessory":
            a.accessories.append(slug)
    return out
```

In `leaderboard()` (public path) — after fetching `rows`, attach avatars:

```python
    rows = (await session.execute(base.add_columns(total.label("pts")))).all()
    avatars = await _avatars_for(session, [uid for (uid, *_rest) in rows])
    out = [
        LeaderboardRow(rank=i + 1, name=handle or "—", country_code=cc,
                       points=int(pts), is_me=(uid == viewer.id),
                       avatar=avatars.get(uid, AvatarData(None, [])))
        for i, (uid, handle, cc, pts) in enumerate(rows)
    ]
    if not any(r.is_me for r in out):
        out.append(await _own_row(session, viewer=viewer, scope=scope, metric=metric, since=since))
    return out
```

In `_own_row()` — set the viewer's avatar before returning:

```python
    av = (await _avatars_for(session, [viewer.id])).get(viewer.id, AvatarData(None, []))
    return LeaderboardRow(rank=ahead + 1, name=viewer.display_handle or "—",
                          country_code=viewer.country_code, points=points, is_me=True, avatar=av)
```

In `_friends()` — attach avatars the same way:

```python
    rows = (await session.execute(base.add_columns(total.label("pts")))).all()
    avatars = await _avatars_for(session, [uid for (uid, *_rest) in rows])
    return [
        LeaderboardRow(rank=i + 1, name=uname, country_code=cc,
                       points=int(pts), is_me=(uid == viewer.id),
                       avatar=avatars.get(uid, AvatarData(None, [])))
        for i, (uid, uname, cc, pts) in enumerate(rows)
    ]
```

- [ ] **Step 4: Schema + endpoint**

In `backend/app/schemas/gamification.py` add and extend:

```python
class AvatarOut(BaseModel):
    skin: str | None = None
    accessories: list[str] = []
```

Add `avatar: AvatarOut` to `LeaderboardRowOut`.

In `backend/app/routers/gamification.py`, the `/leaderboard` mapping becomes (import `AvatarOut`):

```python
    return [LeaderboardRowOut(rank=r.rank, name=r.name, country_code=r.country_code,
                              points=r.points, is_me=r.is_me,
                              avatar=AvatarOut(skin=r.avatar.skin, accessories=r.avatar.accessories))
            for r in rows]
```

- [ ] **Step 5: Run — expect PASS**

Run: `python -m pytest tests/test_leaderboard_avatar.py tests/test_leaderboard_service.py tests/test_leaderboard_api.py -q`

- [ ] **Step 6: Lint + commit**

```bash
cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m ruff check app/services/leaderboard_service.py app/schemas/gamification.py app/routers/gamification.py tests/test_leaderboard_avatar.py
git add backend/app/services/leaderboard_service.py backend/app/schemas/gamification.py backend/app/routers/gamification.py backend/tests/test_leaderboard_avatar.py
git commit -m "feat(leaderboard): rows carry the user's equipped avatar (skin + accessories)"
```

---

### Task 2: Penny avatar + name in the top-left nav

**Files:**
- Modify: `frontend/src/components/child/TopNav.tsx`
- Modify: `frontend/src/locales/en/child.json` (add `topNav.homeAria`)
- Test: `frontend/src/components/child/__tests__/TopNav.test.tsx`

**Interfaces:**
- Consumes: `useEquippedCosmetics()` (`@/api/cosmetics`) → `{ accessories: string[]; skin: string | null }`; `Penny` (`@/components/child/ui/Penny`); the `username` prop TopNav already receives.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/child/__tests__/TopNav.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';

vi.mock('@/api/cosmetics', () => ({
  useEquippedCosmetics: () => ({ accessories: ['party_hat'], skin: 'skin_sky', background: null }),
}));

import { TopNav } from '../TopNav';

function renderNav() {
  return render(<MemoryRouter><TopNav username="Sam" /></MemoryRouter>);
}

describe('TopNav', () => {
  it('shows the child name and a Penny avatar (svg), not the brand image', () => {
    const { container } = renderNav();
    expect(screen.getByText('Sam')).toBeInTheDocument();
    expect(container.querySelector('svg[viewBox="0 0 56 56"]')).toBeTruthy();   // Penny
    expect(container.querySelector('img[src="/icons/icon-192.png"]')).toBeNull();
  });

  it('the home link is accessible and points to /home', () => {
    renderNav();
    const link = screen.getByRole('link', { name: /home/i });
    expect(link).toHaveAttribute('href', '/home');
  });

  it('has no axe violations', async () => {
    expect(await axe(renderNav().container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run — expect FAIL** (`cd frontend && npx vitest run src/components/child/__tests__/TopNav.test.tsx`)

- [ ] **Step 3: Implement TopNav**

Replace the `<Link to="/home">…</Link>` block and add imports:

```tsx
import { Link, NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ProfileMenu } from './ProfileMenu';
import { Penny } from '@/components/child/ui/Penny';
import { useEquippedCosmetics } from '@/api/cosmetics';
import { cn } from '@/lib/utils';
```

```tsx
export function TopNav({ username }: { username: string }) {
  const { t } = useTranslation('child');
  const { accessories, skin } = useEquippedCosmetics();
  return (
    <header className="sticky top-0 z-10 border-b border-brand-200 bg-white/95 backdrop-blur" style={{ paddingTop: 'var(--safe-top)' }}>
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
        <Link to="/home" className="flex items-center gap-2" aria-label={t('topNav.homeAria', { name: username })}>
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100" aria-hidden="true">
            <Penny size={28} accessories={accessories} skin={skin} />
          </span>
          <span className="text-lg font-extrabold text-gray-900">{username}</span>
        </Link>
        {/* …unchanged nav + ProfileMenu… */}
```

Keep the rest of the file (the `<nav>` and `<ProfileMenu>`) unchanged.

Add to `frontend/src/locales/en/child.json` under `topNav`: `"homeAria": "Home — {{name}}"`. (Keep the existing `topNav.homeLink` key even if now unused by TopNav — other code/tests may reference it; removing it is out of scope.)

- [ ] **Step 4: Run — expect PASS** + tsc + lint

Run: `cd frontend && npx vitest run src/components/child/__tests__/TopNav.test.tsx && npx tsc --noEmit && npm run lint`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/child/TopNav.tsx frontend/src/locales/en/child.json frontend/src/components/child/__tests__/TopNav.test.tsx
git commit -m "feat(nav): show the child's Penny avatar + name in the top-left"
```

---

### Task 3: Penny avatar on each leaderboard row

**Files:**
- Modify: `frontend/src/api/gamification.ts` (`LeaderboardRow` gains `avatar`)
- Modify: `frontend/src/components/child/stats/LeaderboardTable.tsx` (leading avatar cell)
- Modify: `frontend/src/components/child/stats/__tests__/LeaderboardCard.test.tsx` (mock rows need `avatar`)
- Modify: `frontend/tests/unit/child-Stats.test.tsx` (mock row needs `avatar`)
- Test: assertions added to `LeaderboardCard.test.tsx`

**Interfaces:**
- Consumes: Task 1's `/leaderboard` response (`avatar: { skin, accessories }` per row); `Penny`.
- Produces: `LeaderboardRow.avatar: { skin: string | null; accessories: string[] }`.

- [ ] **Step 1: Write the failing test** (add to `LeaderboardCard.test.tsx`)

In the `beforeEach` mock rows, give each row an `avatar`, then add:

```tsx
  it('renders a Penny avatar on each row', async () => {
    const { container } = wrap(<LeaderboardCard currentName="You" />);
    await screen.findByText('CleverOtter42');
    // at least one Penny svg in the rendered rows
    expect(container.querySelectorAll('svg[viewBox="0 0 56 56"]').length).toBeGreaterThanOrEqual(1);
  });
```

And update the existing `getLeaderboard.mockResolvedValue([...])` rows to include `avatar`, e.g.:
```tsx
{ rank: 1, name: 'CleverOtter42', country_code: 'GB', points: 120, is_me: false, avatar: { skin: 'skin_sky', accessories: ['party_hat'] } },
{ rank: 2, name: 'You', country_code: 'GB', points: 90, is_me: true, avatar: { skin: null, accessories: [] } },
```

- [ ] **Step 2: Run — expect FAIL (type + assertion)**

Run: `cd frontend && npx vitest run src/components/child/stats/__tests__/LeaderboardCard.test.tsx`

- [ ] **Step 3: Implement**

In `frontend/src/api/gamification.ts`, extend the type:

```ts
export type LeaderboardRow = {
  rank: number; name: string; country_code: string | null; points: number; is_me: boolean;
  avatar: { skin: string | null; accessories: string[] };
};
```

In `frontend/src/components/child/stats/LeaderboardTable.tsx`, import `Penny` and add a leading column:

```tsx
import { Penny } from '@/components/child/ui/Penny';
```
Add a header cell before the name header:
```tsx
            <th className="px-2 py-3 sr-only">{t('leaderboard.colAvatar')}</th>
```
Add a body cell before the name cell:
```tsx
              <td className="px-2 py-3">
                <Penny size={28} accessories={r.avatar.accessories} skin={r.avatar.skin} />
              </td>
```

Add `leaderboard.colAvatar` to `frontend/src/locales/en/child.json` (e.g. `"colAvatar": "Avatar"`).

- [ ] **Step 4: Fix the other mock that renders the leaderboard**

In `frontend/tests/unit/child-Stats.test.tsx`, the `useLeaderboard` mock row must include `avatar`:
```tsx
{ rank: 1, name: 'You', country_code: 'GB', points: 100, is_me: true, avatar: { skin: null, accessories: [] } },
```

- [ ] **Step 5: Run — expect PASS** + tsc + lint + build

Run: `cd frontend && npx vitest run src/components/child/stats src/api/__tests__/leaderboard.test.ts tests/unit/child-Stats.test.tsx && npx tsc --noEmit && npm run lint && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/gamification.ts frontend/src/components/child/stats/LeaderboardTable.tsx frontend/src/components/child/stats/__tests__/LeaderboardCard.test.tsx frontend/tests/unit/child-Stats.test.tsx frontend/src/locales/en/child.json
git commit -m "feat(leaderboard): show a Penny avatar on each row"
```

---

### Task 4: Full verification + ship

**Files:** none.

- [ ] **Step 1: Backend gate**

Run: `cd backend && source "/Users/leeashmore/Local Repo/.venv/bin/activate" && python -m ruff check app tests && python -m pytest tests/test_leaderboard_avatar.py tests/test_leaderboard_service.py tests/test_leaderboard_api.py tests/test_cosmetics_api.py -q`
Expected: pass, ruff clean.

- [ ] **Step 2: Frontend gate**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run src/components/child/__tests__/TopNav.test.tsx src/components/child/stats src/api/__tests__/leaderboard.test.ts tests/unit/child-Stats.test.tsx && npm run build`
Expected: tsc 0, lint 0 errors, targeted tests pass, build clean. Then run the FULL suite once and confirm the failure count is the same ~68 env-only base-URL failures (no NEW failures) and ZERO unhandled errors: `npx vitest run 2>&1 | grep -iE "Tests |Unhandled"`.

- [ ] **Step 3: Push + watch CI**

```bash
git push origin main
gh run watch "$(gh run list --branch main --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
```
Expected: CI green (5 jobs). **No migration** in this feature → Railway just redeploys the backend; **no snapshot question needed.**

- [ ] **Step 4: Manual web deploy + alias**

```bash
cd frontend && vercel --prod --force --yes
vercel alias set <printed-hash>-investikid.vercel.app app.investikid.ai
```

- [ ] **Step 5: `cap sync ios`** (nav is a native-visible change)

Run: `cd frontend && npx cap sync ios`

- [ ] **Step 6: Verify live** in the user's Chrome: top-left shows their Penny + name on every page; `/stats` leaderboard rows each show a mini Penny.

- [ ] **Step 7: Update docs/memory** — MASTER-BACKLOG (Avatar Everywhere live; no migration) + the `project_leaderboard`/`project_arcade` memory note; record that **Feature B (limited-edition collectables) is the next spec**.

---

## Notes for the implementer

- **No migration.** If you find yourself writing one, stop — avatars come from existing `UserCosmetic`/`CosmeticItem`.
- The `Penny` component already handles unknown slugs (ignores unknown accessories; falls back to the mood gradient for an unknown skin) — no extra guarding needed.
- Keep avatars `aria-hidden` (they're inside an `aria-hidden` wrapper in the nav; in rows the row's name is the accessible content). The leaderboard avatar `<td>` Penny has no text, so it needs no label.
