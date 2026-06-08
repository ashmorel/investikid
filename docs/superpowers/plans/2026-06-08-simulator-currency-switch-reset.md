# Simulator Currency Conversion + Start-Fresh Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a practice-currency switch genuinely convert the simulator portfolio's cash (value-preserving, holdings/trades intact), and add an opt-in "start fresh" reset that clears the play account while preserving XP/badges.

**Architecture:** Extract a shared `fx.convert` helper from the simulator router; add `set_portfolio_currency` + `reset_portfolio` services + two `POST /simulator/portfolio/*` endpoints; point the existing `CurrencySelector` at the new currency endpoint and add a confirmation-gated "Start fresh" button in ProfileMenu. No DB migration.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + pydantic v2 (backend); React 18 + Vite + TS + TanStack Query + vitest/vitest-axe (frontend).

**Conventions (MANDATORY):**
- Branch `testing`. Explicit `git add <paths>` only — never `git add -A`. Leave the unrelated modified `.gitignore` untouched.
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Backend tools (from `backend/`): pytest `/Users/leeashmore/Local Repo/.venv/bin/pytest`, ruff `/Users/leeashmore/Local Repo/.venv/bin/ruff`.
- Async DB tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `db_session`/`client` fixtures.

---

### Task 1: Shared FX helper (`app/services/fx.py`)

**Files:**
- Create: `backend/app/services/fx.py`
- Modify: `backend/app/routers/simulator.py` (replace local `_APPROX_USD_RATES`)
- Test: `backend/tests/test_fx.py`

- [ ] **Step 1: Write the failing test** `backend/tests/test_fx.py`

```python
from decimal import Decimal

from app.services import fx


def test_identity_returns_same_amount():
    assert fx.convert(Decimal("1000.00"), "USD", "USD") == Decimal("1000.00")


def test_usd_to_gbp_and_back_roundtrips_close():
    gbp = fx.convert(Decimal("1000.00"), "USD", "GBP")
    # 1 USD = 1/1.27 GBP -> ~787.40
    assert gbp == Decimal("787.40")
    back = fx.convert(gbp, "GBP", "USD")
    assert abs(back - Decimal("1000.00")) <= Decimal("0.01")


def test_usd_to_hkd():
    # 1 USD / 0.128 = ~7812.50 HKD
    assert fx.convert(Decimal("1000.00"), "USD", "HKD") == Decimal("7812.50")


def test_unknown_currency_treated_as_usd_parity():
    assert fx.convert(Decimal("100.00"), "ZZZ", "USD") == Decimal("100.00")
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_fx.py -v`
Expected: FAIL (`ModuleNotFoundError: app.services.fx`).

- [ ] **Step 3: Create `backend/app/services/fx.py`**

```python
"""Approximate play-money FX for the simulator. Not real rates — preserves the
relative VALUE of the child's virtual cash when their practice currency changes."""
from decimal import Decimal

# USD value of one unit of each currency (moved verbatim from the simulator router).
APPROX_USD_RATES: dict[str, float] = {
    "USD": 1.0,
    "GBP": 1.27,
    "HKD": 0.128,
    "EUR": 1.08,
    "JPY": 0.0067,
    "CAD": 0.73,
    "AUD": 0.65,
}

_CENTS = Decimal("0.01")


def convert(amount: Decimal, from_ccy: str, to_ccy: str) -> Decimal:
    if from_ccy == to_ccy:
        return amount.quantize(_CENTS)
    from_rate = Decimal(str(APPROX_USD_RATES.get(from_ccy, 1.0)))
    to_rate = Decimal(str(APPROX_USD_RATES.get(to_ccy, 1.0)))
    usd = amount * from_rate
    return (usd / to_rate).quantize(_CENTS)
```

- [ ] **Step 4: Repoint the router to the shared rates.** In `backend/app/routers/simulator.py`, DELETE the local `_APPROX_USD_RATES = { ... }` block (~line 418) and add to the imports near the other `from app.services...` imports:

```python
from app.services.fx import APPROX_USD_RATES
```

Then update the one usage site (~line 452) from `_APPROX_USD_RATES.get(currency, 1.0)` to `APPROX_USD_RATES.get(currency, 1.0)`. Grep to be sure none remain: `grep -n "_APPROX_USD_RATES" app/routers/simulator.py` should return nothing.

- [ ] **Step 5: Run tests + ruff + a simulator sanity check**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_fx.py tests/test_simulator.py -q` → expect PASS (fx + no simulator regression).
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/fx.py app/routers/simulator.py tests/test_fx.py` → clean.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/fx.py backend/app/routers/simulator.py backend/tests/test_fx.py
git commit -m "refactor(simulator): extract shared fx.convert helper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Portfolio currency-convert + reset services

**Files:**
- Modify: `backend/app/services/simulator_service.py`
- Test: `backend/tests/test_portfolio_currency_reset.py`

Context — `simulator_service.py` already imports `Holding, Portfolio, Trade` from `app.models.simulator`, `select` from sqlalchemy, and has `get_or_create_portfolio(session, user)` using `get_starting_cash(session)`. `UserProgress` is on `app.models.user` and is independent of the portfolio.

- [ ] **Step 1: Read the existing simulator test seeding.** Open `backend/tests/test_simulator.py` and note how it: creates a user, gets/creates a portfolio, places trades (creating `Holding`/`Trade` rows). Reuse that exact setup in the new test (don't invent a new path). Also check how a `UserProgress` row is created for a user (it's created at registration; in tests you may need to add one explicitly).

- [ ] **Step 2: Write the failing tests** `backend/tests/test_portfolio_currency_reset.py`

```python
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.simulator import Holding, Portfolio, Trade
from app.models.user import User, UserProgress
from app.services.simulator_service import reset_portfolio, set_portfolio_currency

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_user_with_portfolio(db_session, currency="USD"):
    user = User(
        username=f"sim_{currency.lower()}", password_hash="x",
        dob=__import__("datetime").date(2014, 1, 1),
        country_code="US", currency_code=currency, parent_email="p@example.com",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    portfolio = Portfolio(user_id=user.id, virtual_cash=Decimal("1000.00"), currency_code=currency)
    db_session.add(portfolio)
    await db_session.flush()
    return user, portfolio


async def test_set_currency_converts_cash_and_preserves_holdings(db_session):
    user, portfolio = await _make_user_with_portfolio(db_session, "USD")
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="AAPL", exchange="NASDAQ",
                           shares=Decimal("2"), avg_buy_price=Decimal("100.00")))
    db_session.add(Trade(portfolio_id=portfolio.id, ticker="AAPL", exchange="NASDAQ",
                         trade_type="buy", shares=Decimal("2"), price=Decimal("100.00")))
    await db_session.flush()

    result = await set_portfolio_currency(db_session, user, "GBP")
    assert result is not None
    assert user.currency_code == "GBP"
    assert result.currency_code == "GBP"
    assert result.virtual_cash == Decimal("787.40")  # 1000 USD -> GBP at 1.27
    holdings = (await db_session.scalars(select(Holding).where(Holding.portfolio_id == portfolio.id))).all()
    trades = (await db_session.scalars(select(Trade).where(Trade.portfolio_id == portfolio.id))).all()
    assert len(holdings) == 1 and len(trades) == 1  # untouched


async def test_set_currency_same_currency_is_noop_value(db_session):
    user, portfolio = await _make_user_with_portfolio(db_session, "USD")
    result = await set_portfolio_currency(db_session, user, "USD")
    assert result.virtual_cash == Decimal("1000.00")
    assert result.currency_code == "USD"


async def test_set_currency_no_portfolio_returns_none_but_sets_pref(db_session):
    user = User(username="nopf", password_hash="x", dob=__import__("datetime").date(2014, 1, 1),
                country_code="US", currency_code="USD", parent_email="p@example.com", is_active=True)
    db_session.add(user)
    await db_session.flush()
    result = await set_portfolio_currency(db_session, user, "GBP")
    assert result is None
    assert user.currency_code == "GBP"


async def test_reset_clears_holdings_trades_resets_cash_preserves_progress(db_session):
    user, portfolio = await _make_user_with_portfolio(db_session, "GBP")
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="VOD", exchange="LSE",
                           shares=Decimal("3"), avg_buy_price=Decimal("1.00")))
    db_session.add(Trade(portfolio_id=portfolio.id, ticker="VOD", exchange="LSE",
                         trade_type="buy", shares=Decimal("3"), price=Decimal("1.00")))
    progress = UserProgress(user_id=user.id, xp=500, level=3, virtual_coins=42)
    db_session.add(progress)
    portfolio.virtual_cash = Decimal("10.00")
    await db_session.flush()

    result = await reset_portfolio(db_session, user)
    assert result.currency_code == "GBP"
    assert result.virtual_cash > Decimal("10.00")  # reset to starting cash for GBP
    holdings = (await db_session.scalars(select(Holding).where(Holding.portfolio_id == portfolio.id))).all()
    trades = (await db_session.scalars(select(Trade).where(Trade.portfolio_id == portfolio.id))).all()
    assert holdings == [] and trades == []
    refreshed = await db_session.get(UserProgress, progress.user_id)
    assert refreshed.xp == 500 and refreshed.virtual_coins == 42  # progress untouched
```

NOTE: match `Holding`/`Trade`/`UserProgress` constructor fields to the real models — open `app/models/simulator.py` and `app/models/user.py` and adjust the kwargs above to the actual column names (e.g. `avg_buy_price`, `trade_type`, `shares`, `price`, `xp`, `virtual_coins`) before running. The test asserts behaviour, not exact column spelling.

- [ ] **Step 3: Run, expect FAIL**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_portfolio_currency_reset.py -v`
Expected: FAIL (`ImportError: cannot import name 'set_portfolio_currency'`).

- [ ] **Step 4: Implement the two services** in `backend/app/services/simulator_service.py`. Add the import `from app.services import fx` and `from sqlalchemy import delete` (alongside existing imports), then:

```python
async def set_portfolio_currency(session, user, new_currency: str) -> Portfolio | None:
    user.currency_code = new_currency
    portfolio = await session.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
    if portfolio is None:
        return None
    if portfolio.currency_code != new_currency:
        portfolio.virtual_cash = fx.convert(portfolio.virtual_cash, portfolio.currency_code, new_currency)
        portfolio.currency_code = new_currency
    await session.flush()
    return portfolio


async def reset_portfolio(session, user) -> Portfolio:
    from app.services.app_settings import get_starting_cash

    portfolio = await get_or_create_portfolio(session, user)
    await session.execute(delete(Holding).where(Holding.portfolio_id == portfolio.id))
    await session.execute(delete(Trade).where(Trade.portfolio_id == portfolio.id))
    cash_map = await get_starting_cash(session)
    portfolio.virtual_cash = cash_map.get(user.currency_code, Decimal("1000.00"))
    portfolio.currency_code = user.currency_code
    await session.flush()
    return portfolio
```

(`Decimal` and `select` are already imported in this module; if `Decimal` is not, add `from decimal import Decimal`.)

- [ ] **Step 5: Run tests + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_portfolio_currency_reset.py -v` → expect PASS (4).
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/simulator_service.py tests/test_portfolio_currency_reset.py` → clean.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/simulator_service.py backend/tests/test_portfolio_currency_reset.py
git commit -m "feat(simulator): set_portfolio_currency + reset_portfolio services

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Schemas + endpoints

**Files:**
- Modify: `backend/app/schemas/simulator.py` (add `SetCurrencyRequest`, `PortfolioSummaryOut`)
- Modify: `backend/app/routers/simulator.py` (two POST endpoints)
- Test: `backend/tests/test_portfolio_endpoints.py`

- [ ] **Step 1: Add schemas** to `backend/app/schemas/simulator.py`:

```python
from pydantic import field_validator

_MAJOR_CURRENCIES = {"USD", "GBP", "HKD"}


class SetCurrencyRequest(BaseModel):
    currency_code: str

    @field_validator("currency_code")
    @classmethod
    def _supported(cls, v: str) -> str:
        v = v.upper()
        if v not in _MAJOR_CURRENCIES:
            raise ValueError("currency_code must be one of USD, GBP, HKD")
        return v


class PortfolioSummaryOut(BaseModel):
    id: uuid.UUID
    virtual_cash: Decimal
    currency_code: str
```

(`BaseModel` is already imported; ensure `uuid` and `Decimal` are imported in this module — they are used by `PortfolioOut`/`HoldingOut`; if not, add `import uuid` / `from decimal import Decimal`.)

- [ ] **Step 2: Write the failing endpoint tests** `backend/tests/test_portfolio_endpoints.py`

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_set_currency_rejects_unsupported(client, authed_child_headers):
    # authed_child_headers = however the existing simulator tests authenticate a child
    resp = await client.post("/simulator/portfolio/currency",
                             json={"currency_code": "EUR"}, headers=authed_child_headers)
    assert resp.status_code == 422


async def test_set_currency_happy_path(client, authed_child_headers):
    resp = await client.post("/simulator/portfolio/currency",
                             json={"currency_code": "GBP"}, headers=authed_child_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["currency_code"] == "GBP"
    assert "virtual_cash" in body and "id" in body


async def test_reset_requires_auth(client):
    resp = await client.post("/simulator/portfolio/reset")
    assert resp.status_code == 401


async def test_reset_happy_path(client, authed_child_headers):
    resp = await client.post("/simulator/portfolio/reset", headers=authed_child_headers)
    assert resp.status_code == 200
    assert "currency_code" in resp.json()
```

IMPORTANT: replace `authed_child_headers` with the EXACT auth mechanism the existing simulator endpoint tests use (read `tests/test_simulator.py` — it already calls authed simulator routes like `/portfolio` and `/trade`; copy that fixture/login + CSRF handling verbatim, including any CSRF header the existing POST `/trade` test sends).

- [ ] **Step 3: Run, expect FAIL**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_portfolio_endpoints.py -v`
Expected: FAIL (404 — routes don't exist yet).

- [ ] **Step 4: Add the endpoints** to `backend/app/routers/simulator.py`. Import the new schemas + services at the top (with the existing simulator schema/service imports):

```python
from app.schemas.simulator import SetCurrencyRequest, PortfolioSummaryOut
from app.services.simulator_service import set_portfolio_currency, reset_portfolio
```

Then add (mirror the auth + `session: AsyncSession = Depends(get_session)` style of `place_trade`; these do NOT need the price provider):

```python
@router.post("/portfolio/currency", response_model=PortfolioSummaryOut)
async def set_currency(
    payload: SetCurrencyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    portfolio = await set_portfolio_currency(session, current_user, payload.currency_code)
    await session.commit()
    if portfolio is None:
        # No portfolio yet — reflect the new preference with a zero-less summary by creating one.
        from app.services.simulator_service import get_or_create_portfolio
        portfolio = await get_or_create_portfolio(session, current_user)
        await session.commit()
    return PortfolioSummaryOut(
        id=portfolio.id, virtual_cash=portfolio.virtual_cash, currency_code=portfolio.currency_code,
    )


@router.post("/portfolio/reset", response_model=PortfolioSummaryOut)
async def reset_portfolio_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    portfolio = await reset_portfolio(session, current_user)
    await session.commit()
    return PortfolioSummaryOut(
        id=portfolio.id, virtual_cash=portfolio.virtual_cash, currency_code=portfolio.currency_code,
    )
```

(Confirm `get_session`/`AsyncSession`/`User` are already imported in the router — they are, used by the other endpoints.)

- [ ] **Step 5: Run tests + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_portfolio_endpoints.py -v` → expect PASS (4).
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/schemas/simulator.py app/routers/simulator.py tests/test_portfolio_endpoints.py` → clean.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/simulator.py backend/app/routers/simulator.py backend/tests/test_portfolio_endpoints.py
git commit -m "feat(simulator): POST portfolio/currency + portfolio/reset endpoints

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Frontend wiring + full regression

**Files:**
- Modify: `frontend/src/api/simulator.ts`
- Modify: `frontend/src/components/child/CurrencySelector.tsx`
- Modify: `frontend/src/components/child/ProfileMenu.tsx`
- Test: `frontend/src/components/child/__tests__/CurrencySelector.test.tsx` (create/extend), `frontend/src/components/child/__tests__/ProfileMenu.startfresh.test.tsx` (create)

- [ ] **Step 1: Add API client methods** to `frontend/src/api/simulator.ts`:

```typescript
export type PortfolioSummaryOut = {
  id: string;
  virtual_cash: string;
  currency_code: string;
};
```
and inside the `simulatorApi` object:
```typescript
  setCurrency: (currency_code: string) =>
    apiFetch<PortfolioSummaryOut>('/simulator/portfolio/currency',
      { method: 'POST', body: JSON.stringify({ currency_code }) }),
  resetPortfolio: () =>
    apiFetch<PortfolioSummaryOut>('/simulator/portfolio/reset', { method: 'POST' }),
```

- [ ] **Step 2: Point `CurrencySelector` at the new endpoint** (`frontend/src/components/child/CurrencySelector.tsx`). Change the import of `authApi` → `simulatorApi` and the mutation:

```typescript
import { simulatorApi } from '@/api/simulator';
// ...
  const save = useMutation({
    mutationFn: (currency_code: string) => simulatorApi.setCurrency(currency_code),
    onSuccess: () => {
      for (const key of [['me'], ['portfolio'], ['portfolio-history']]) {
        qc.invalidateQueries({ queryKey: key });
      }
    },
  });
```
(Leave the rest of the component — options, labels, select — unchanged.)

- [ ] **Step 3: Write the failing CurrencySelector test** `frontend/src/components/child/__tests__/CurrencySelector.test.tsx` (copy the render-with-`QueryClientProvider` helper from a sibling child test; mock `@/api/simulator`):

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('@/api/simulator', () => ({ simulatorApi: { setCurrency: vi.fn(() => Promise.resolve({ id: '1', virtual_cash: '787.40', currency_code: 'GBP' })) } }));
// import simulatorApi (mocked), CurrencySelector, renderWithProviders

describe('CurrencySelector', () => {
  beforeEach(() => vi.clearAllMocks());
  it('calls simulatorApi.setCurrency on change', async () => {
    renderWithProviders(<CurrencySelector currentCurrency="USD" />);
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /practice currency/i }), 'GBP');
    await waitFor(() => expect(simulatorApi.setCurrency).toHaveBeenCalledWith('GBP'));
  });
});
```

Run: `cd frontend && npm run test -- CurrencySelector` → expect FAIL first (still mocking old api), then PASS after Step 2. (If the component already had a test referencing `authApi`, update it.)

- [ ] **Step 4: Add the "Start fresh" control to `ProfileMenu`** (`frontend/src/components/child/ProfileMenu.tsx`). Import the dialog + api + state:

```tsx
import { useState } from 'react'; // (already imported — reuse)
import { ConfirmDialog } from '@/components/admin/ConfirmDialog';
import { simulatorApi } from '@/api/simulator';
```
Add near the other mutations:
```tsx
  const [confirmReset, setConfirmReset] = useState(false);
  const resetPf = useMutation({
    mutationFn: () => simulatorApi.resetPortfolio(),
    onSuccess: () => {
      for (const key of [['portfolio'], ['portfolio-history']]) qc.invalidateQueries({ queryKey: key });
      setConfirmReset(false);
    },
  });
```
In the Preferences section, AFTER `<CurrencySelector ... />`, add:
```tsx
        <button
          type="button"
          onClick={() => setConfirmReset(true)}
          className="min-h-[44px] w-full rounded-md border border-line px-3 text-sm font-medium text-brand-700 hover:bg-brand-50"
        >
          Start fresh
        </button>
        <ConfirmDialog
          open={confirmReset}
          title="Start fresh?"
          message={`Start your practice portfolio over in ${currentCurrency}? This clears your current play holdings and history. Your XP and badges are safe.`}
          confirmLabel="Start fresh"
          onConfirm={() => resetPf.mutate()}
          onCancel={() => setConfirmReset(false)}
        />
```
IMPORTANT: open `src/components/admin/ConfirmDialog.tsx` first and match its ACTUAL props (e.g. `open`/`isOpen`, `onConfirm`/`onConfirm`, `confirmLabel`/`confirmText`, `message`/`description`) — adjust the JSX above to the real prop names.

- [ ] **Step 5: Write the failing ProfileMenu start-fresh test** `frontend/src/components/child/__tests__/ProfileMenu.startfresh.test.tsx` (mock `@/api/simulator`; reuse the existing ProfileMenu test's provider/render + any `authApi.me` mock it uses):

```typescript
// mock simulatorApi.resetPortfolio = vi.fn(resolve summary)
it('opens ConfirmDialog and resets on confirm', async () => {
  renderProfileMenu();
  await userEvent.click(await screen.findByRole('button', { name: /start fresh/i }));
  await userEvent.click(screen.getByRole('button', { name: /start fresh/i, /* the dialog confirm */ }));
  await waitFor(() => expect(simulatorApi.resetPortfolio).toHaveBeenCalled());
});
it('does not reset on cancel', async () => {
  renderProfileMenu();
  await userEvent.click(await screen.findByRole('button', { name: /start fresh/i }));
  await userEvent.click(screen.getByRole('button', { name: /cancel/i }));
  expect(simulatorApi.resetPortfolio).not.toHaveBeenCalled();
});
```
Disambiguate the two "Start fresh" buttons (trigger vs dialog-confirm) using the dialog's role/container per how `ConfirmDialog` renders (e.g. `within(screen.getByRole('dialog'))`). Add an axe assertion on the open-dialog state. Look at `ConfirmDialog.test.tsx` for how it's queried.

Run: `npm run test -- ProfileMenu` → FAIL first, then PASS after Step 4.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/simulator.ts frontend/src/components/child/CurrencySelector.tsx frontend/src/components/child/ProfileMenu.tsx frontend/src/components/child/__tests__/CurrencySelector.test.tsx frontend/src/components/child/__tests__/ProfileMenu.startfresh.test.tsx
git commit -m "feat(simulator): currency switch converts portfolio + Start fresh reset (FE)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 7: Full regression**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q` → expect clean + green.
Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build` → expect all green.

- [ ] **Step 8: Push + confirm CI**

```bash
git push origin testing
```
Confirm the CI run for the new HEAD is green (frontend, backend, security, a11y, responsive). No `cap sync` needed (logic/UX only; no native-plugin change).

---

## Self-review notes
- Spec coverage: fx helper (Task 1), convert+reset services (Task 2), schemas+endpoints (Task 3), FE wiring + Start-fresh + regression (Task 4). All spec sections covered. No migration (matches spec).
- Type consistency: `set_portfolio_currency`/`reset_portfolio` names + `PortfolioSummaryOut{id,virtual_cash,currency_code}` + `simulatorApi.setCurrency`/`resetPortfolio` are consistent across BE and FE tasks. `fx.convert(amount, from, to)` signature identical in Tasks 1–2.
- Implementer notes: (a) match test constructor kwargs to the real `Holding`/`Trade`/`UserProgress` columns (Task 2 Step 2); (b) copy the existing simulator-test auth/CSRF fixture for the endpoint tests (Task 3 Step 2); (c) match the real `ConfirmDialog` prop names (Task 4 Step 4).
