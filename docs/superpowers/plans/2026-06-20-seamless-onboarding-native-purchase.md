# Seamless Onboarding + Native Child-Initiated Purchase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a child on native start a subscription themselves — behind a parental gate, mediated by Apple Ask-to-Buy / Google Play family approval — while keeping signup free of unnecessary parent-email collection and the web flow unchanged.

**Architecture:** Reuse the existing native StoreKit/Play purchase plugins (which already surface a `pending` flag for Ask-to-Buy) and the existing transaction-verification services; add **child-authed** billing endpoints scoped to a generalized household key (parent_email, or the teen's own email); add a reusable native parental gate; branch the child paywall to a native purchase path while web keeps the email request.

**Tech Stack:** FastAPI + SQLAlchemy async + pytest (backend); React 18 + Vite + TS + vitest + Capacitor (frontend).

**Spec:** `docs/superpowers/specs/2026-06-20-seamless-onboarding-native-purchase-design.md`
**Branch:** `testing`.

---

## Verified seams
- `backend/app/services/apple_billing_service.py`: `household_token(parent_email) -> str` (uuid5 of any string), `verify_transaction(session, *, parent_email, jws)`.
- `backend/app/services/google_billing_service.py`: `verify_purchase(session, *, parent_email, purchase_token, product_id)`; reuses `household_token`.
- `backend/app/services/entitlements.py`: `recompute_household_premium(session, parent_email)` matches children via `User.parent_email == parent_email`.
- `backend/app/routers/billing.py`: parent endpoints `GET /apple/account-token`, `GET /account-token`, `POST /apple/verify`, `POST /google/verify`, `GET /plans` — all `Depends(get_current_parent)`. Schemas: `AppleAccountTokenResponse`, `AccountTokenResponse`, `AppleVerifyRequest/Response`, `GoogleVerifyRequest/Response`, `PlansResponse`.
- `backend/app/routers/users.py:27`: `get_current_user` (child auth dependency).
- `frontend/src/lib/storekit.ts`: `StoreKit.purchase({productId, appAccountToken}) -> {jws?, pending?}`.
- `frontend/src/lib/playBilling.ts`: `PlayBilling.purchase({productId, obfuscatedAccountId}) -> {purchaseToken?, productId?, pending?}`.
- `frontend/src/components/SubscriptionCard.tsx`: the existing parent native purchase handlers (StoreKit/Play + account-token + verify) to extract.
- `frontend/src/components/child/PremiumPaywall.tsx`: child paywall, today always `premiumApi.requestUnlock` (email). `frontend/src/lib/premiumConfig.ts`: `PAYWALL_CTA`, `PAYWALL_TITLE`. `frontend/src/lib/platform.ts`: `isNativeApp`, `isAndroid`.

---

### Task 1: Onboarding verify + polish

**Files:** Test `backend/tests/test_register_consent_conditional.py` (create); Modify `frontend/src/pages/child/Signup.tsx` (copy only) + its locale.

- [ ] **Step 1: Lock the conditional with a backend regression test** — `backend/tests/test_register_consent_conditional.py`:

```python
from datetime import date

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _dob_for_age(age: int) -> str:
    today = date.today()
    return date(today.year - age, today.month, today.day).isoformat()


async def test_over_threshold_teen_registers_without_parent_email(client):
    # GB consent age is 13; a 15yo is self-managed and needs only their own email.
    resp = await client.post("/auth/register", json={
        "email": "teen-selfmanaged@example.com", "username": "teenself",
        "password": "SecurePass123!", "dob": _dob_for_age(15),
        "country_code": "GB", "currency_code": "GBP",
    })
    assert resp.status_code == 200, resp.text


async def test_under_threshold_child_requires_parent_email(client):
    # GB consent age is 13; a 9yo MUST have a parent email.
    resp = await client.post("/auth/register", json={
        "username": "younglearner", "password": "SecurePass123!",
        "dob": _dob_for_age(9), "country_code": "GB", "currency_code": "GBP",
    })
    assert resp.status_code == 400


async def test_under_threshold_child_succeeds_with_parent_email(client):
    resp = await client.post("/auth/register", json={
        "username": "younglearner2", "password": "SecurePass123!",
        "dob": _dob_for_age(9), "country_code": "GB", "currency_code": "GBP",
        "parent_email": "guardian@example.com",
    })
    assert resp.status_code == 200, resp.text
```

Run from `backend/`: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_register_consent_conditional.py -v`. These should PASS against the EXISTING logic (this is a regression lock, not new behavior). If any fails, the conditional is not behaving as the spec claims — STOP and report (do not change registration logic without escalating). If DB hangs ~90s+, note it and rely on CI.

- [ ] **Step 2: Copy polish (no logic change)** — in `frontend/src/pages/child/Signup.tsx`, on the consent path (where the parent-email field shows), ensure the helper copy explains *why* a grown-up's email is needed (one friendly line), and that over-threshold users see no parent-email prompt. Make only copy/className changes; route every string through the existing `t()` and add any new keys to the Signup namespace's locale file (grep `useTranslation(` in Signup.tsx for the namespace). Do NOT restructure the steps. Keep `no-literal-string` clean.

- [ ] **Step 3: Verify + commit** — `cd frontend && npx tsc -b && npm run lint`; backend test green. Commit:
```bash
cd /Users/leeashmore/investikid && git add backend/tests/test_register_consent_conditional.py frontend/src/pages/child/Signup.tsx frontend/src/locales && git commit -m "feat(onboarding): lock conditional parent-email + friendlier consent copy

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Household key + teen-aware entitlement

**Files:** Modify `backend/app/services/entitlements.py`; Test `backend/tests/test_household_key.py` (create).

A self-managed teen has no `parent_email`, so they form a single-member household keyed on their own email. Add a `household_key(user)` helper and generalize `recompute_household_premium` so a teen's self-keyed subscription grants them premium — without affecting normal parent households.

- [ ] **Step 1: Failing test** — `backend/tests/test_household_key.py`:

```python
from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import household_key, recompute_household_premium

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_household_key_prefers_parent_email():
    u = User(username="k1", password_hash="x", dob=date(2014, 1, 1),
             country_code="GB", currency_code="GBP",
             parent_email="P@Example.com", email="kid@example.com")
    assert household_key(u) == "p@example.com"  # lowercased parent email


def test_household_key_falls_back_to_own_email_for_teen():
    teen = User(username="k2", password_hash="x", dob=date(2009, 1, 1),
                country_code="GB", currency_code="GBP",
                parent_email=None, email="Teen@Example.com")
    assert household_key(teen) == "teen@example.com"


async def test_recompute_grants_teen_their_self_household(db_session):
    teen = User(username="teenbuyer", password_hash="x", dob=date(2009, 1, 1),
                country_code="GB", currency_code="GBP",
                parent_email=None, email="teenbuyer@example.com")
    db_session.add(teen)
    key = "teenbuyer@example.com"
    db_session.add(Subscription(
        parent_email=key, provider="apple", external_id="otid_teen",
        status="active", current_period_end=datetime.now(UTC) + timedelta(days=30),
    ))
    await db_session.flush()
    await recompute_household_premium(db_session, key)
    assert teen.is_premium is True
```

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_household_key.py -v` → FAIL (`household_key` missing; teen recompute fails).

- [ ] **Step 2: Implement** — in `backend/app/services/entitlements.py`:
  - Add the helper:
```python
def household_key(user: User) -> str:
    """The billing household scope for a user: the parent email when present,
    else the user's own email (a self-managed teen is their own household).
    Lowercased to match household_token's normalization."""
    raw = user.parent_email or user.email or ""
    return raw.strip().lower()
```
  - Generalize the children query in `recompute_household_premium`. Add `from sqlalchemy import and_, or_, select` (extend the existing import), and replace the children select with:
```python
    children = (await session.scalars(
        select(User).where(
            or_(
                User.parent_email == parent_email,
                and_(User.parent_email.is_(None), User.email == parent_email),
            )
        )
    )).all()
```
  (For a normal parent household, the second clause matches only a user whose `parent_email` is null AND whose own email equals the key — i.e. essentially never, so existing behavior is unchanged.)

- [ ] **Step 3: Verify + commit** — `pytest tests/test_household_key.py -v` PASS; run the entitlement/billing suite (`pytest tests/ -k "entitle or household or billing or webhook or reconcile" -q`) green; `ruff check .` clean. Commit:
```bash
cd /Users/leeashmore/investikid && git add backend/app/services/entitlements.py backend/tests/test_household_key.py && git commit -m "feat(billing): household_key + teen self-household entitlement

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Child-scoped billing endpoints

**Files:** Modify `backend/app/routers/billing.py`; Test `backend/tests/test_billing_child.py` (create).

Add child-authed (`get_current_user`) endpoints mirroring the parent ones, scoped via `household_key(current_user)`. Reuse the existing services unchanged.

- [ ] **Step 1: Failing test** — `backend/tests/test_billing_child.py`. Register + log in a child (copy the child-login helper from an existing test, e.g. how `test_ai.py`/`test_content.py` authenticate a child via `client`), then:
  - `GET /billing/child/apple/account-token` → 200, `token` == `apple_billing_service.household_token(household_key(child))`.
  - `GET /billing/child/account-token` → 200 (Google token, same value).
  - `GET /billing/child/plans` → 200 with the plan list shape.
  - `POST /billing/child/apple/verify` with a JWS, patching `apple_billing_service.verify_transaction` (AsyncMock) → asserts it's called with `parent_email == household_key(child)`.
  - Unauthenticated → 401.
  Mirror the patching style in the existing `test_billing.py`. Run → FAIL.

- [ ] **Step 2: Implement** — in `backend/app/routers/billing.py`:
  - Import `from app.routers.users import get_current_user` and `from app.services.entitlements import household_key`. `get_current_user` yields a `User`.
  - Add the endpoints (mirror the parent ones, swapping the dep + scope source):
```python
@router.get("/child/apple/account-token", response_model=AppleAccountTokenResponse)
async def child_apple_account_token(user: User = Depends(get_current_user)):
    return AppleAccountTokenResponse(token=apple_billing_service.household_token(household_key(user)))


@router.get("/child/account-token", response_model=AccountTokenResponse)
async def child_account_token(user: User = Depends(get_current_user)):
    return AccountTokenResponse(token=apple_billing_service.household_token(household_key(user)))


@router.get("/child/plans", response_model=PlansResponse)
async def child_list_plans(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await _build_plans_response(session)  # extract the parent /plans body into a shared helper


@router.post("/child/apple/verify", response_model=AppleVerifyResponse)
async def child_apple_verify(
    payload: AppleVerifyRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        await apple_billing_service.verify_transaction(
            session, parent_email=household_key(user), jws=payload.jws
        )
    except apple_billing_service.AppleBillingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return AppleVerifyResponse()


@router.post("/child/google/verify", response_model=GoogleVerifyResponse)
async def child_google_verify(
    payload: GoogleVerifyRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        await google_billing_service.verify_purchase(
            session, parent_email=household_key(user),
            purchase_token=payload.purchaseToken, product_id=payload.productId,
        )
    except google_billing_service.GoogleBillingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return GoogleVerifyResponse()
```
  - For `child/plans`, extract the existing parent `list_plans` body into a `_build_plans_response(session)` helper and call it from both (DRY). If `list_plans` needs the parent email for display currency, pass `household_key(user)` / the child's currency instead — check the existing `list_plans` body and adapt (the child has a `currency_code`). Keep the parent endpoint behavior identical.
  - `User` is already imported in the router (or import it from `app.models.user`).

- [ ] **Step 3: Verify + commit** — `pytest tests/test_billing_child.py tests/test_billing.py -v` green (parent endpoints unchanged); `ruff check .` clean. Commit:
```bash
cd /Users/leeashmore/investikid && git add backend/app/routers/billing.py backend/tests/test_billing_child.py && git commit -m "feat(billing): child-scoped account-token/verify/plans endpoints

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Parental gate component

**Files:** Create `frontend/src/lib/parentalGate.ts`, `frontend/src/components/child/ParentalGate.tsx`; Test `frontend/src/lib/__tests__/parentalGate.test.ts`, `frontend/src/components/child/__tests__/ParentalGate.test.tsx`; Modify a child locale file.

- [ ] **Step 1: Failing test (pure logic)** — `frontend/src/lib/__tests__/parentalGate.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { makeChallenge, checkAnswer } from '../parentalGate';

describe('parentalGate logic', () => {
  it('produces a multiplication challenge with a numeric answer', () => {
    const c = makeChallenge(() => 0.5); // deterministic rng
    expect(c.prompt).toMatch(/\d+\s*×\s*\d+/);
    expect(typeof c.answer).toBe('number');
  });
  it('accepts the exact answer and rejects others', () => {
    const c = makeChallenge(() => 0.5);
    expect(checkAnswer(c, String(c.answer))).toBe(true);
    expect(checkAnswer(c, String(c.answer + 1))).toBe(false);
    expect(checkAnswer(c, '')).toBe(false);
  });
});
```

- [ ] **Step 2: Implement the logic** — `frontend/src/lib/parentalGate.ts`:

```ts
export type GateChallenge = { a: number; b: number; prompt: string; answer: number };

/** A small "ask a grown-up" arithmetic challenge. Friction, NOT authentication —
 *  the real spend authorization is the OS purchase sheet + Ask-to-Buy. */
export function makeChallenge(rng: () => number = Math.random): GateChallenge {
  const a = 3 + Math.floor(rng() * 7); // 3..9
  const b = 3 + Math.floor(rng() * 7); // 3..9
  return { a, b, prompt: `${a} × ${b}`, answer: a * b };
}

export function checkAnswer(c: GateChallenge, input: string): boolean {
  const n = Number(input.trim());
  return Number.isInteger(n) && n === c.answer;
}
```

- [ ] **Step 3: Failing test (component)** — `frontend/src/components/child/__tests__/ParentalGate.test.tsx`: render `<ParentalGate onPass={fn} onCancel={fn} />`; entering the correct product calls `onPass`; a wrong answer shows an error and does NOT call `onPass`; cancel calls `onCancel`. Mock `react-i18next` `t` to echo keys. (Force determinism by stubbing `Math.random` or accepting an injectable rng prop.)

- [ ] **Step 4: Implement the component** — `frontend/src/components/child/ParentalGate.tsx`: a small modal/section showing `t('parentalGate.title')` ("Ask a grown-up"), the challenge prompt, a numeric input, Continue + Cancel buttons (min 44px, focus rings). On Continue, `checkAnswer` → `onPass()` or show `t('parentalGate.tryAgain')`. Props `{ onPass: () => void; onCancel: () => void; rng?: () => number }`. All strings i18n'd; add `parentalGate.*` keys to the child locale (`src/locales/en/child.json` — confirm the namespace the paywall/child uses).

- [ ] **Step 5: Verify + commit** — `npx vitest run src/lib/__tests__/parentalGate.test.ts src/components/child/__tests__/ParentalGate.test.tsx` PASS; `npx tsc -b && npm run lint` clean. Commit:
```bash
cd /Users/leeashmore/investikid && git add frontend/src/lib/parentalGate.ts frontend/src/components/child/ParentalGate.tsx frontend/src/lib/__tests__/parentalGate.test.ts frontend/src/components/child/__tests__/ParentalGate.test.tsx frontend/src/locales && git commit -m "feat(billing): lightweight parental gate before native purchase

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Shared native-purchase helper

**Files:** Create `frontend/src/lib/nativePurchase.ts`; Modify `frontend/src/components/SubscriptionCard.tsx`; Test `frontend/src/lib/__tests__/nativePurchase.test.ts`.

Extract the StoreKit/Play purchase-then-verify flow into one platform-aware helper that takes the account-token fetcher + verify caller, so both the parent card and the child paywall use one implementation. The helper surfaces the `pending` (Ask-to-Buy) case.

- [ ] **Step 1: Failing test** — `frontend/src/lib/__tests__/nativePurchase.test.ts`: mock `@/lib/storekit` + `@/lib/playBilling`. Assert:
  - iOS success: `StoreKit.purchase` returns `{ jws }` → helper calls the injected `verifyApple(jws)` and resolves `{ status: 'active' }`.
  - iOS pending: returns `{ pending: true }` (no jws) → resolves `{ status: 'pending' }`, verify NOT called.
  - Android success: `PlayBilling.purchase` returns `{ purchaseToken, productId }` → calls `verifyGoogle(...)` → `{ status: 'active' }`.
  - cancel/no-result: returns `{}` → `{ status: 'cancelled' }`.

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

const skPurchase = vi.fn();
const pbPurchase = vi.fn();
vi.mock('@/lib/storekit', () => ({ StoreKit: { purchase: (o: unknown) => skPurchase(o) } }));
vi.mock('@/lib/playBilling', () => ({ PlayBilling: { purchase: (o: unknown) => pbPurchase(o) } }));

import { runNativePurchase } from '../nativePurchase';

const deps = {
  productId: 'premium_monthly',
  getAppleToken: vi.fn(async () => 'apple-tok'),
  getGoogleToken: vi.fn(async () => 'google-tok'),
  verifyApple: vi.fn(async () => {}),
  verifyGoogle: vi.fn(async () => {}),
};

beforeEach(() => { skPurchase.mockReset(); pbPurchase.mockReset(); deps.verifyApple.mockClear(); deps.verifyGoogle.mockClear(); });

describe('runNativePurchase', () => {
  it('ios success verifies and returns active', async () => {
    skPurchase.mockResolvedValue({ jws: 'JWS' });
    const r = await runNativePurchase('ios', deps);
    expect(deps.verifyApple).toHaveBeenCalledWith('JWS');
    expect(r.status).toBe('active');
  });
  it('ios pending returns pending without verifying', async () => {
    skPurchase.mockResolvedValue({ pending: true });
    const r = await runNativePurchase('ios', deps);
    expect(deps.verifyApple).not.toHaveBeenCalled();
    expect(r.status).toBe('pending');
  });
  it('android success verifies and returns active', async () => {
    pbPurchase.mockResolvedValue({ purchaseToken: 'PT', productId: 'premium_monthly' });
    const r = await runNativePurchase('android', deps);
    expect(deps.verifyGoogle).toHaveBeenCalledWith('PT', 'premium_monthly');
    expect(r.status).toBe('active');
  });
  it('no token returned is cancelled', async () => {
    skPurchase.mockResolvedValue({});
    const r = await runNativePurchase('ios', deps);
    expect(r.status).toBe('cancelled');
  });
});
```

- [ ] **Step 2: Implement** — `frontend/src/lib/nativePurchase.ts`:

```ts
import { StoreKit } from '@/lib/storekit';
import { PlayBilling } from '@/lib/playBilling';

export type PurchaseStatus = 'active' | 'pending' | 'cancelled';
export type PurchaseResult = { status: PurchaseStatus };

export type NativePurchaseDeps = {
  productId: string;
  getAppleToken: () => Promise<string>;
  getGoogleToken: () => Promise<string>;
  verifyApple: (jws: string) => Promise<void>;
  verifyGoogle: (purchaseToken: string, productId: string) => Promise<void>;
};

/** Run a native subscription purchase and verify it. `pending` means the OS is
 *  awaiting parental approval (Ask-to-Buy) — entitlement flips later via webhook
 *  + reconcile, so we do NOT verify/unlock here. */
export async function runNativePurchase(
  platform: 'ios' | 'android',
  deps: NativePurchaseDeps,
): Promise<PurchaseResult> {
  if (platform === 'android') {
    const token = await deps.getGoogleToken();
    const res = await PlayBilling.purchase({ productId: deps.productId, obfuscatedAccountId: token });
    if (res.pending) return { status: 'pending' };
    if (!res.purchaseToken) return { status: 'cancelled' };
    await deps.verifyGoogle(res.purchaseToken, res.productId ?? deps.productId);
    return { status: 'active' };
  }
  const token = await deps.getAppleToken();
  const res = await StoreKit.purchase({ productId: deps.productId, appAccountToken: token });
  if (res.pending) return { status: 'pending' };
  if (!res.jws) return { status: 'cancelled' };
  await deps.verifyApple(res.jws);
  return { status: 'active' };
}
```

- [ ] **Step 3: Refactor `SubscriptionCard.tsx` onto the helper** — replace the inline iOS/Android purchase handlers' core (purchase → verify) with a `runNativePurchase('ios'|'android', { ...parent deps })` call, where the parent deps fetch the PARENT account-tokens (`billingApi.appleAccountToken()` / `accountToken()`) and call the PARENT verify (`billingApi.appleVerify` / `googleVerify`). Keep the surrounding UI/loading/restore logic. The existing `SubscriptionCard` tests are the regression guard — they MUST stay green. If the refactor risks behavior change beyond the extract, keep it minimal (extract only the purchase→verify core) and report a concern rather than over-refactoring.

- [ ] **Step 4: Verify + commit** — `npx vitest run src/lib/__tests__/nativePurchase.test.ts` + the SubscriptionCard tests green; `npx tsc -b && npm run lint` clean. Commit:
```bash
cd /Users/leeashmore/investikid && git add frontend/src/lib/nativePurchase.ts frontend/src/lib/__tests__/nativePurchase.test.ts frontend/src/components/SubscriptionCard.tsx && git commit -m "refactor(billing): shared runNativePurchase helper (pending-aware)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Native purchase path on the child paywall

**Files:** Modify `frontend/src/api/premium.ts` (or `frontend/src/api/billing.ts`), `frontend/src/components/child/PremiumPaywall.tsx`, a child locale; Test `frontend/src/components/child/__tests__/PremiumPaywall.test.tsx` (create/extend).

- [ ] **Step 1: Child billing API** — add child billing calls (in `frontend/src/api/billing.ts`, or extend `premium.ts`): `childAppleAccountToken()`, `childGoogleAccountToken()`, `childPlans()`, `childAppleVerify(jws)`, `childGoogleVerify(purchaseToken, productId)` → hitting the `/billing/child/*` endpoints via `apiFetch`.

- [ ] **Step 2: Failing test** — `frontend/src/components/child/__tests__/PremiumPaywall.test.tsx`: with `isNativeApp()` mocked true, the paywall shows a "Get premium" CTA → clicking opens the `ParentalGate` → passing the gate calls `runNativePurchase` (mock the helper) → on `{status:'active'}` shows unlocked; on `{status:'pending'}` shows the "asked your grown-up" message and does NOT show unlocked; cancel returns to the paywall. With `isNativeApp()` false (web), clicking the CTA calls `premiumApi.requestUnlock` (email) as today — and no gate/native purchase. Mock `@/lib/nativePurchase`, `@/lib/platform`, `@/api/*`, `react-i18next`.

- [ ] **Step 3: Implement** — extend `PremiumPaywall.tsx`:
  - `const native = isNativeApp();`
  - **Web** (`!native`): unchanged — the existing `ask()` (email `requestUnlock`) is the CTA.
  - **Native**: primary CTA `t('paywall.getPremium')` → show `<ParentalGate onPass={startPurchase} onCancel={...} />`. `startPurchase`:
    1. `const plan = (await billingApi.childPlans()).plans[0]` (or the lead plan id);
    2. `const res = await runNativePurchase(isAndroid() ? 'android' : 'ios', { productId: plan.productId, getAppleToken: billingApi.childAppleAccountToken→token, getGoogleToken: childGoogleAccountToken→token, verifyApple: billingApi.childAppleVerify, verifyGoogle: billingApi.childGoogleVerify })`;
    3. `active` → invalidate the `['me']`/entitlement queries + show `t('paywall.unlocked')`; `pending` → show `t('paywall.askedGrownup')`; `cancelled` → back to paywall.
  - Keep a secondary "or ask a grown-up" link on native that runs the existing email `ask()` (covers non-purchasable cases).
  - Add the new `paywall.*` keys to the child locale. All strings via `t()`.

- [ ] **Step 4: Verify + commit** — `npx vitest run src/components/child/__tests__/PremiumPaywall.test.tsx` PASS; `npx tsc -b && npm run lint && npx vitest run src/components/child` green. Commit:
```bash
cd /Users/leeashmore/investikid && git add frontend/src/api frontend/src/components/child/PremiumPaywall.tsx frontend/src/locales frontend/src/components/child/__tests__/PremiumPaywall.test.tsx && git commit -m "feat(billing): native child-initiated purchase on the paywall (Ask-to-Buy aware)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Full verification + promote

- [ ] **Step 1: Backend** — `cd backend && ruff check . && pytest tests/test_register_consent_conditional.py tests/test_household_key.py tests/test_billing_child.py tests/test_billing.py -q`; spot-run `pytest tests/ -k "entitle or billing or household or reconcile or webhook" -q`. All green; parent billing unchanged.
- [ ] **Step 2: Frontend** — `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build` green; `no-literal-string` clean; a11y (vitest-axe) on the gate + paywall.
- [ ] **Step 3: iOS sync** — `cd frontend && npm run build && npx cap sync ios`.
- [ ] **Step 4: Push + green CI** — `git push origin testing`; all 5 jobs green.
- [ ] **Step 5: Promote** — confirm whether any migration was introduced (expected: NONE — `household_key` is derived, no column). If none → no snapshot question. Merge `testing → staging → main` on green CI; manual Vercel prod for web; verify `/health` 200 and that `GET /billing/child/apple/account-token` returns **401** unauth (gated, deployed) not 404.
- [ ] **Step 6: Update trackers** (standing rule) — move this into "Live in prod" in `docs/MASTER-BACKLOG.md` and note it in the roadmap. Flag the **operator/App-Store items**: kids-category parental-gate review, and that Ask-to-Buy only mediates on Family-Sharing child devices (otherwise the OS sheet's own auth applies).

---

## Self-Review

**Spec coverage:**
- Unit 1 onboarding verify + polish → Task 1. ✓
- Unit 2 child-scoped billing endpoints (household key incl. teen fallback) → Tasks 2 + 3. ✓
- Unit 3 parental gate → Task 4. ✓
- Unit 4 native paywall purchase path (success/pending/cancel; web unchanged; native fallback link) → Tasks 5 + 6. ✓
- Unit 5 verify + promote → Task 7. ✓
- Non-goals respected: no onboarding rebuild, web email flow unchanged, no new SKUs, verification reused, consent matrix untouched.

**Placeholder scan:** full code for the household key, the helper, the gate logic, and the endpoint bodies. The two read-then-adapt spots are flagged with concrete checks: (a) `_build_plans_response` extraction must preserve parent `/plans` behavior; (b) the SubscriptionCard refactor must keep its existing tests green (extract only the purchase→verify core).

**Type/name consistency:** `household_key` (Task 2) used by every `/billing/child/*` endpoint (Task 3) and matches the teen test. `runNativePurchase(platform, deps)` + `PurchaseStatus` (Task 5) consumed by the paywall (Task 6) and the helper test. `ParentalGate {onPass,onCancel,rng?}` (Task 4) used in Task 6. `childApple/GoogleVerify` + `child*AccountToken` + `childPlans` (Task 6 api) match the endpoints in Task 3. `pending` flows from the plugin shapes (`{jws?,pending?}` / `{purchaseToken?,pending?}`) → `runNativePurchase` → paywall "asked your grown-up". No migration.
