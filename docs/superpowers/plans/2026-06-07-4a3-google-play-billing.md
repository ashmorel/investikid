# 4A·A3 — Google Play Billing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Android Google Play Billing subscriptions, validated server-side via the Google Play Developer API, feeding the existing source-agnostic entitlement core (a Google feeder mirroring A2's Apple side).

**Architecture:** New `google_billing_service` validates a Play purchase token via the Android Publisher API, binds it to the household via `obfuscatedAccountId = household_token(parent_email)`, acknowledges it, and upserts a `provider="google"` `subscriptions` row → `recompute_household_premium` (unchanged). RTDN (Pub/Sub) keeps state fresh. A custom Kotlin Play Billing plugin drives the Android purchase; `SubscriptionCard` splits native by `isAndroid()`.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 async · pydantic v2 · `google-api-python-client` + `google-auth` · Capacitor 8 (custom Kotlin Play Billing v7 plugin) · React 18 + Vite + TS · pytest · Vitest.

**Constraints:** venv `/Users/leeashmore/Local Repo/.venv` (pytest/ruff). Branch `testing` (never main); explicit `git add` paths (an unrelated root `.gitignore` change is present). **No DB migration** (the `provider` column already exists). **No Android toolchain here** — backend is fully pytest-tested; frontend verified by `tsc`/lint/`test`/build + `cap sync android`; the **Kotlin plugin + Gradle cannot be compiled here** (first compile = on-demand checkpoint `run_android` / Android Studio; device purchase test + Play Console + Google Cloud service account + Pub/Sub RTDN are operator-side). No iOS/Stripe/entitlement-core behaviour changes.

**Reuse (do NOT reimplement):** `household_token(parent_email)` and the provider-agnostic patterns live in `app/services/apple_billing_service.py`; `recompute_household_premium` in `app/services/entitlements.py`; the `Subscription` model has `provider`/`external_id`; the parent-auth test mechanism (real magic-link `_setup_parent`) is in `tests/routers/test_apple_billing.py`.

---

## File Structure

- `backend/app/core/config.py` — add `google_play_package_name`, `google_play_service_account_json`, `google_play_product_id`.
- `backend/.env.example` — Google Play block.
- `backend/requirements.txt` — `google-api-python-client`, `google-auth` (pinned).
- `backend/app/services/google_billing_service.py` (new) — validation/ack/recompute/RTDN.
- `backend/app/schemas/google_billing.py` (new) — request/response models.
- `backend/app/routers/billing.py` — google endpoints + generalized account-token.
- `backend/app/core/csrf.py` — exempt `/billing/google/notifications`.
- Tests: `backend/tests/core/test_google_config.py`, `tests/services/test_google_billing_service.py`, `tests/routers/test_google_billing.py`.
- `frontend/android/app/src/main/java/leeashmore/investikid/ai/app/PlayBillingPlugin.kt` (new) + registration; `frontend/android/app/build.gradle` (Play Billing dep).
- `frontend/src/lib/playBilling.ts` (new) — TS bridge.
- `frontend/src/api/billing.ts` — `googleVerify`, `accountToken`.
- `frontend/src/components/SubscriptionCard.tsx` — Android branch.
- `docs/2026-06-07-android-operator-runbook.md` — A3 operator section.

---

## Task 1: Google Play config + deps

**Files:** `backend/app/core/config.py`, `backend/.env.example`, `backend/requirements.txt`; Test `backend/tests/core/test_google_config.py`

- [ ] **Step 1: Failing test** `backend/tests/core/test_google_config.py`
```python
from app.core.config import settings

def test_google_play_settings_exist():
    for attr in ("google_play_package_name", "google_play_service_account_json", "google_play_product_id"):
        assert hasattr(settings, attr)
```

- [ ] **Step 2: Run → FAIL**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/core/test_google_config.py -v` (from `backend/`). Expected: AttributeError.

- [ ] **Step 3: Add settings** (in the Settings class, near the `apple_iap_*` block):
```python
    google_play_package_name: str = ""
    google_play_service_account_json: str = ""  # service-account JSON key contents
    google_play_product_id: str = ""
```

- [ ] **Step 4: `.env.example`** — add:
```bash
# Google Play Billing (item 4A·A3) — leave blank to disable Play billing
GOOGLE_PLAY_PACKAGE_NAME=
GOOGLE_PLAY_SERVICE_ACCOUNT_JSON=
GOOGLE_PLAY_PRODUCT_ID=
```

- [ ] **Step 5: requirements** — add to `backend/requirements.txt` (install + pin the resolved versions, matching the file's pin style):
```
google-api-python-client
google-auth
```
Run `/Users/leeashmore/Local\ Repo/.venv/bin/pip install google-api-python-client google-auth`, then pin both to the installed versions (check `pip show`).

- [ ] **Step 6: Run → PASS** + `ruff check app/core/config.py tests/core/test_google_config.py`.

- [ ] **Step 7: Commit**
```bash
git add app/core/config.py backend/.env.example backend/requirements.txt tests/core/test_google_config.py
git commit -m "feat(billing): Google Play config + deps"
```
(Adjust `.env.example`/`requirements.txt` paths to how git sees them from your cwd.)

---

## Task 2: `google_billing_service` — verify + acknowledge + recompute

**Files:** Create `backend/app/services/google_billing_service.py`; Test `backend/tests/services/test_google_billing_service.py`

- [ ] **Step 1: Failing test** (the Play API client, fetch, and acknowledge are module functions, so tests patch them)
```python
import pytest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace  # noqa: F401
from sqlalchemy import select
from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import is_premium
from app.services.apple_billing_service import household_token
from app.services import google_billing_service as gbs

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _child(db_session, email):
    u = User(username=f"kid-{email}", email=f"kid-{email}", parent_email=email,
             password_hash="x", dob=datetime(2014, 1, 1).date(), country_code="GB",
             currency_code="GBP", is_active=True)
    db_session.add(u); await db_session.flush(); return u


def _sub_response(email, *, product="premium_monthly", state="SUBSCRIPTION_STATE_ACTIVE",
                  acknowledged=True):
    expiry = (datetime.now(UTC) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
    return {
        "subscriptionState": state,
        "acknowledgementState": ("ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED" if acknowledged
                                 else "ACKNOWLEDGEMENT_STATE_PENDING"),
        "externalAccountIdentifiers": {"obfuscatedExternalAccountId": household_token(email)},
        "lineItems": [{"productId": product, "expiryTime": expiry}],
    }


async def test_verify_records_and_grants(db_session, monkeypatch):
    email = "a@example.com"
    child = await _child(db_session, email)
    monkeypatch.setattr(gbs, "_require_google", lambda: None)
    monkeypatch.setattr(gbs, "_fetch_subscription", lambda token: _sub_response(email))
    acks = []
    monkeypatch.setattr(gbs, "_acknowledge", lambda product_id, token: acks.append(token))
    await gbs.verify_purchase(db_session, parent_email=email,
                              purchase_token="TOK-1", product_id="premium_monthly")
    row = await db_session.scalar(select(Subscription).where(
        Subscription.provider == "google", Subscription.external_id == "TOK-1"))
    assert row is not None and row.status == "active" and row.parent_email == email
    assert is_premium(child) is True
    assert acks == []  # already acknowledged → no ack call


async def test_verify_acknowledges_when_pending(db_session, monkeypatch):
    email = "b@example.com"
    await _child(db_session, email)
    monkeypatch.setattr(gbs, "_require_google", lambda: None)
    monkeypatch.setattr(gbs, "_fetch_subscription",
                        lambda token: _sub_response(email, acknowledged=False))
    acks = []
    monkeypatch.setattr(gbs, "_acknowledge", lambda product_id, token: acks.append((product_id, token)))
    await gbs.verify_purchase(db_session, parent_email=email,
                              purchase_token="TOK-2", product_id="premium_monthly")
    assert acks == [("premium_monthly", "TOK-2")]


async def test_verify_rejects_household_mismatch(db_session, monkeypatch):
    monkeypatch.setattr(gbs, "_require_google", lambda: None)
    resp = _sub_response("a@example.com")
    resp["externalAccountIdentifiers"]["obfuscatedExternalAccountId"] = "00000000-0000-0000-0000-000000000000"
    monkeypatch.setattr(gbs, "_fetch_subscription", lambda token: resp)
    monkeypatch.setattr(gbs, "_acknowledge", lambda *a: None)
    with pytest.raises(gbs.GoogleBillingError):
        await gbs.verify_purchase(db_session, parent_email="a@example.com",
                                  purchase_token="x", product_id="premium_monthly")


async def test_verify_rejects_wrong_product(db_session, monkeypatch):
    monkeypatch.setattr(gbs, "_require_google", lambda: None)
    monkeypatch.setattr(gbs, "_fetch_subscription", lambda token: _sub_response("a@example.com"))
    monkeypatch.setattr(gbs, "_acknowledge", lambda *a: None)
    monkeypatch.setattr(gbs.settings, "google_play_product_id", "premium_monthly")
    with pytest.raises(gbs.GoogleBillingError):
        await gbs.verify_purchase(db_session, parent_email="a@example.com",
                                  purchase_token="x", product_id="something_else")
```
Confirm the real `User` required fields against `app/models/user.py` (and `tests/services/test_apple_billing_service.py`'s `_child`); adjust if they differ. Run → FAIL (module missing).

- [ ] **Step 2: Implement** `backend/app/services/google_billing_service.py`
```python
from __future__ import annotations

import base64
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.subscription import Subscription
from app.services.apple_billing_service import household_token
from app.services.entitlements import recompute_household_premium

_SCOPE = "https://www.googleapis.com/auth/androidpublisher"

# Google Play subscriptionState → our entitlement status.
_STATE_MAP = {
    "SUBSCRIPTION_STATE_ACTIVE": "active",
    "SUBSCRIPTION_STATE_CANCELED": "active",        # access continues until expiry
    "SUBSCRIPTION_STATE_IN_GRACE_PERIOD": "in_grace_period",
    "SUBSCRIPTION_STATE_ON_HOLD": "expired",
    "SUBSCRIPTION_STATE_PAUSED": "expired",
    "SUBSCRIPTION_STATE_EXPIRED": "expired",
    "SUBSCRIPTION_STATE_PENDING": "expired",
}


class GoogleBillingError(Exception):
    """Raised when a Play purchase cannot be trusted/processed."""


def _require_google() -> None:
    if not (settings.google_play_package_name and settings.google_play_service_account_json):
        raise GoogleBillingError("Google Play billing is not configured")


def _play_client():
    """Android Publisher client from the service-account JSON. Patched in tests."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    info = json.loads(settings.google_play_service_account_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=[_SCOPE])
    return build("androidpublisher", "v3", credentials=creds, cache_discovery=False)


def _fetch_subscription(purchase_token: str) -> dict:
    """Authoritative subscription state from the Play Developer API. Patched in tests."""
    client = _play_client()
    return client.purchases().subscriptionsv2().get(
        packageName=settings.google_play_package_name, token=purchase_token).execute()


def _acknowledge(product_id: str, purchase_token: str) -> None:
    """Acknowledge a purchase (idempotent at the call site). Patched in tests."""
    client = _play_client()
    client.purchases().subscriptions().acknowledge(
        packageName=settings.google_play_package_name,
        subscriptionId=product_id, token=purchase_token, body={}).execute()


def _map_status(state: str | None) -> str:
    return _STATE_MAP.get(state or "", "expired")


def _line_item(resp: dict) -> dict:
    items = resp.get("lineItems") or [{}]
    return items[0]


def _expiry_dt(resp: dict) -> datetime | None:
    exp = _line_item(resp).get("expiryTime")
    if not exp:
        return None
    return datetime.fromisoformat(exp.replace("Z", "+00:00"))


async def _upsert_and_recompute(session: AsyncSession, *, parent_email: str,
                                purchase_token: str, status: str,
                                expiry: datetime | None) -> None:
    sub = await session.scalar(select(Subscription).where(
        Subscription.provider == "google", Subscription.external_id == purchase_token))
    now = datetime.now(UTC)
    if sub is None:
        sub = Subscription(parent_email=parent_email, provider="google",
                           external_id=purchase_token, created_at=now)
        session.add(sub)
    sub.status = status
    sub.parent_email = parent_email
    sub.current_period_end = expiry
    sub.updated_at = now
    await session.flush()
    await recompute_household_premium(session, sub.parent_email)


async def verify_purchase(session: AsyncSession, *, parent_email: str,
                          purchase_token: str, product_id: str) -> None:
    """Validate a Play purchase token, bind to the household, acknowledge, record + recompute."""
    _require_google()
    resp = _fetch_subscription(purchase_token)

    obfuscated = (resp.get("externalAccountIdentifiers") or {}).get("obfuscatedExternalAccountId")
    if obfuscated and obfuscated != household_token(parent_email):
        raise GoogleBillingError("obfuscatedAccountId does not match the authenticated parent")

    expected_product = settings.google_play_product_id
    line_product = _line_item(resp).get("productId") or product_id
    if expected_product and line_product != expected_product:
        raise GoogleBillingError("Purchase product does not match the configured subscription product")

    if resp.get("acknowledgementState") == "ACKNOWLEDGEMENT_STATE_PENDING":
        try:
            _acknowledge(line_product, purchase_token)
        except Exception:
            pass  # best-effort; already-acked or transient — entitlement still recorded

    await _upsert_and_recompute(session, parent_email=parent_email,
                                purchase_token=purchase_token,
                                status=_map_status(resp.get("subscriptionState")),
                                expiry=_expiry_dt(resp))
    await session.commit()
```
(Leave `handle_notification` for Task 3.)

- [ ] **Step 3: Run → PASS** (4 tests) + `ruff check`.

- [ ] **Step 4: Commit**
```bash
git add app/services/google_billing_service.py tests/services/test_google_billing_service.py
git commit -m "feat(billing): google_billing_service (Play API verify + acknowledge + recompute)"
```

---

## Task 3: RTDN `handle_notification`

**Files:** Modify `backend/app/services/google_billing_service.py`; extend `tests/services/test_google_billing_service.py`

- [ ] **Step 1: Failing tests** (add)
```python
import base64, json  # noqa: E401  (at top of test file if not present)


def _rtdn(purchase_token: str) -> str:
    payload = {"subscriptionNotification": {"notificationType": 4, "purchaseToken": purchase_token}}
    return base64.b64encode(json.dumps(payload).encode()).decode()


async def test_notification_updates_known_token(db_session, monkeypatch):
    email = "n@example.com"
    child = await _child(db_session, email)
    child.is_premium = True
    db_session.add(Subscription(parent_email=email, provider="google",
                   external_id="TOK-N", status="active"))
    await db_session.flush()
    monkeypatch.setattr(gbs, "_require_google", lambda: None)
    monkeypatch.setattr(gbs, "_fetch_subscription",
                        lambda token: _sub_response(email, state="SUBSCRIPTION_STATE_EXPIRED"))
    await gbs.handle_notification(db_session, {"message": {"data": _rtdn("TOK-N")}})
    assert is_premium(child) is False


async def test_notification_unknown_token_noop(db_session, monkeypatch):
    monkeypatch.setattr(gbs, "_require_google", lambda: None)
    called = {"n": 0}
    def _fetch(token): called["n"] += 1; return _sub_response("z@example.com")
    monkeypatch.setattr(gbs, "_fetch_subscription", _fetch)
    await gbs.handle_notification(db_session, {"message": {"data": _rtdn("UNKNOWN")}})
    assert called["n"] == 0  # never fetched for an unknown token
```
Run → FAIL.

- [ ] **Step 2: Implement** (append to `google_billing_service.py`)
```python
def _decode_rtdn(message: dict) -> str | None:
    """Extract the purchaseToken from a Pub/Sub RTDN push body. Returns None if absent."""
    data_b64 = (message.get("message") or {}).get("data")
    if not data_b64:
        return None
    payload = json.loads(base64.b64decode(data_b64).decode())
    return (payload.get("subscriptionNotification") or {}).get("purchaseToken")


async def handle_notification(session: AsyncSession, message: dict) -> None:
    """Process a Google RTDN (Pub/Sub push). Re-fetches authoritative state; no-op on unknown token."""
    _require_google()
    token = _decode_rtdn(message)
    if not token:
        return
    sub = await session.scalar(select(Subscription).where(
        Subscription.provider == "google", Subscription.external_id == token))
    if sub is None:
        return  # unknown purchase — never bound to a household; ignore
    resp = _fetch_subscription(token)
    await _upsert_and_recompute(session, parent_email=sub.parent_email,
                                purchase_token=token,
                                status=_map_status(resp.get("subscriptionState")),
                                expiry=_expiry_dt(resp))
    await session.commit()
```

- [ ] **Step 3: Run → PASS** (all 6) + `ruff check`.

- [ ] **Step 4: Commit**
```bash
git add app/services/google_billing_service.py tests/services/test_google_billing_service.py
git commit -m "feat(billing): Google RTDN handle_notification (re-fetch + recompute)"
```

---

## Task 4: Endpoints + schemas + CSRF + generalized account-token

**Files:** Create `backend/app/schemas/google_billing.py`; Modify `backend/app/routers/billing.py`, `backend/app/core/csrf.py`; Test `backend/tests/routers/test_google_billing.py`

- [ ] **Step 1: Schemas** `backend/app/schemas/google_billing.py`
```python
from __future__ import annotations
from pydantic import BaseModel


class GoogleVerifyRequest(BaseModel):
    purchaseToken: str
    productId: str


class GoogleVerifyResponse(BaseModel):
    status: str = "ok"


class AccountTokenResponse(BaseModel):
    token: str
```

- [ ] **Step 2: Failing tests** `backend/tests/routers/test_google_billing.py` — copy the `_setup_parent` magic-link auth pattern from `tests/routers/test_apple_billing.py` (read it). Cover:
```python
import pytest
from unittest.mock import AsyncMock, patch
pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_google_verify_requires_parent_auth(client):
    client.cookies.clear()
    r = await client.post("/billing/google/verify", json={"purchaseToken": "x", "productId": "p"})
    assert r.status_code in (401, 403)

async def test_google_notifications_csrf_exempt_and_dispatches(client):
    client.cookies.clear()
    with patch("app.routers.billing.google_billing_service.handle_notification", new=AsyncMock()) as m:
        r = await client.post("/billing/google/notifications", json={"message": {"data": "e30="}})
    assert r.status_code == 200
    m.assert_awaited_once()

async def test_account_token_returns_uuid(client):
    # authenticate as a parent via the shared _setup_parent helper, then:
    # r = await client.get("/billing/account-token", headers/csrf as needed)
    # assert r.status_code == 200 and uuid.UUID(r.json()["token"]) parses
    ...
```
Implement the authenticated `verify` + `account-token` cases using the same auth + `X-CSRF-Token` approach as `test_apple_billing.py` (patch `app.routers.billing.google_billing_service.verify_purchase` with AsyncMock for the verify success case). Run → FAIL.

- [ ] **Step 3: Implement endpoints** in `app/routers/billing.py`
```python
from app.schemas.google_billing import (
    AccountTokenResponse, GoogleVerifyRequest, GoogleVerifyResponse)
from app.services import google_billing_service
```
```python
@router.get("/account-token", response_model=AccountTokenResponse)
async def account_token(parent_email: str = Depends(get_current_parent)):
    return AccountTokenResponse(token=apple_billing_service.household_token(parent_email))


@router.post("/google/verify", response_model=GoogleVerifyResponse)
async def google_verify(
    payload: GoogleVerifyRequest,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    try:
        await google_billing_service.verify_purchase(
            session, parent_email=parent_email,
            purchase_token=payload.purchaseToken, product_id=payload.productId)
    except google_billing_service.GoogleBillingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return GoogleVerifyResponse()


@router.post("/google/notifications")
async def google_notifications(request: Request, session: AsyncSession = Depends(get_session)):
    body = await request.json()
    try:
        await google_billing_service.handle_notification(session, body)
    except google_billing_service.GoogleBillingError:
        return {"status": "ignored"}
    return {"status": "ok"}
```
Keep `GET /apple/account-token` as-is (alias). The new `/account-token` returns the same household token.

- [ ] **Step 4: CSRF exempt** — add `"/billing/google/notifications",` to `_DEFAULT_EXEMPT_PATHS` in `app/core/csrf.py`.

- [ ] **Step 5: Run** `pytest tests/routers/test_google_billing.py -v` → PASS; `pytest tests/ -k billing -q` → no regressions; `ruff check` changed files.

- [ ] **Step 6: Commit**
```bash
git add app/schemas/google_billing.py app/routers/billing.py app/core/csrf.py tests/routers/test_google_billing.py
git commit -m "feat(billing): google verify + notifications endpoints + generalized account-token"
```

---

## Task 5: Backend regression

- [ ] **Step 1:** `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q` → ruff clean; all green.
- [ ] **Step 2:** Commit only if fixes were needed.

---

## Task 6: Kotlin Play Billing plugin + TS bridge

**Files:** Create `frontend/android/app/src/main/java/leeashmore/investikid/ai/app/PlayBillingPlugin.kt`; Modify `frontend/android/app/src/main/java/.../MainActivity.java` (register) + `frontend/android/app/build.gradle` (dep); Create `frontend/src/lib/playBilling.ts`. (Cannot compile here — verify via `npx cap sync android` + tsc on the bridge.)

- [ ] **Step 1: Confirm the package path + MainActivity**

Run: `find frontend/android/app/src/main/java -name '*.java' -o -name '*.kt'` to get the real package dir (Capacitor generates `MainActivity.java` under a package derived from appId `leeashmore.investikid.ai.app`). Use that exact package in the Kotlin file's `package` line and place the file beside `MainActivity`.

- [ ] **Step 2: Play Billing Gradle dependency**

In `frontend/android/app/build.gradle`, inside `dependencies { ... }`, add:
```gradle
    implementation "com.android.billingclient:billing-ktx:7.1.1"
```
(If the project has a central version catalog, follow that style; otherwise the direct coordinate is fine.)

- [ ] **Step 3: Plugin** `PlayBillingPlugin.kt` (package line must match the discovered package)
```kotlin
package leeashmore.investikid.ai.app

import com.android.billingclient.api.*
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

@CapacitorPlugin(name = "PlayBilling")
class PlayBillingPlugin : Plugin() {

    private var billingClient: BillingClient? = null

    private fun client(onReady: (BillingClient) -> Unit, onError: (String) -> Unit) {
        val existing = billingClient
        if (existing != null && existing.isReady) { onReady(existing); return }
        val c = BillingClient.newBuilder(context)
            .enablePendingPurchases()
            .setListener { _, _ -> /* purchases delivered via the per-call listener below */ }
            .build()
        billingClient = c
        c.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(result: BillingResult) {
                if (result.responseCode == BillingClient.BillingResponseCode.OK) onReady(c)
                else onError("Billing setup failed: ${result.responseCode}")
            }
            override fun onBillingServiceDisconnected() { /* retried lazily on next call */ }
        })
    }

    @PluginMethod
    fun getProducts(call: PluginCall) {
        val ids = call.getArray("productIds") ?: run { call.reject("productIds required"); return }
        val productList = (0 until ids.length()).map {
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(ids.getString(it))
                .setProductType(BillingClient.ProductType.SUBS).build()
        }
        client({ c ->
            val params = QueryProductDetailsParams.newBuilder().setProductList(productList).build()
            c.queryProductDetailsAsync(params) { result, details ->
                if (result.responseCode != BillingClient.BillingResponseCode.OK) {
                    call.reject("getProducts failed: ${result.responseCode}"); return@queryProductDetailsAsync
                }
                val arr = JSArray()
                details.forEach { d ->
                    val offer = d.subscriptionOfferDetails?.firstOrNull()
                    val price = offer?.pricingPhases?.pricingPhaseList?.firstOrNull()?.formattedPrice ?: ""
                    arr.put(JSObject().put("id", d.productId).put("displayPrice", price).put("displayName", d.name))
                }
                call.resolve(JSObject().put("products", arr))
            }
        }, { call.reject(it) })
    }

    @PluginMethod
    fun purchase(call: PluginCall) {
        val productId = call.getString("productId") ?: run { call.reject("productId required"); return }
        val account = call.getString("obfuscatedAccountId") ?: run { call.reject("obfuscatedAccountId required"); return }
        client({ c ->
            val params = QueryProductDetailsParams.newBuilder().setProductList(listOf(
                QueryProductDetailsParams.Product.newBuilder()
                    .setProductId(productId).setProductType(BillingClient.ProductType.SUBS).build())).build()
            c.queryProductDetailsAsync(params) { r, details ->
                val d = details.firstOrNull()
                if (r.responseCode != BillingClient.BillingResponseCode.OK || d == null) {
                    call.reject("Unknown product"); return@queryProductDetailsAsync
                }
                val offerToken = d.subscriptionOfferDetails?.firstOrNull()?.offerToken
                if (offerToken == null) { call.reject("No subscription offer"); return@queryProductDetailsAsync }
                val flowParams = BillingFlowParams.newBuilder()
                    .setProductDetailsParamsList(listOf(
                        BillingFlowParams.ProductDetailsParams.newBuilder()
                            .setProductDetails(d).setOfferToken(offerToken).build()))
                    .setObfuscatedAccountId(account)
                    .build()
                // one-shot purchase listener
                pendingCall = call
                c.launchBillingFlow(activity, flowParams)
            }
        }, { call.reject(it) })
    }

    private var pendingCall: PluginCall? = null

    // BillingClient's global listener (set in client()) forwards here.
    private fun onPurchases(result: BillingResult, purchases: List<Purchase>?) {
        val call = pendingCall ?: return
        pendingCall = null
        when (result.responseCode) {
            BillingClient.BillingResponseCode.OK -> {
                val p = purchases?.firstOrNull()
                if (p == null) { call.resolve(JSObject().put("pending", true)); return }
                call.resolve(JSObject().put("purchaseToken", p.purchaseToken)
                    .put("productId", p.products.firstOrNull() ?: ""))
            }
            BillingClient.BillingResponseCode.USER_CANCELED -> call.reject("cancelled", "USER_CANCELLED")
            else -> call.reject("purchase failed: ${result.responseCode}")
        }
    }

    @PluginMethod
    fun restore(call: PluginCall) {
        client({ c ->
            c.queryPurchasesAsync(QueryPurchasesParams.newBuilder()
                .setProductType(BillingClient.ProductType.SUBS).build()) { r, purchases ->
                if (r.responseCode != BillingClient.BillingResponseCode.OK) {
                    call.reject("restore failed: ${r.responseCode}"); return@queryPurchasesAsync
                }
                val arr = JSArray(); purchases.forEach { arr.put(it.purchaseToken) }
                call.resolve(JSObject().put("purchaseTokens", arr))
            }
        }, { call.reject(it) })
    }
}
```
> Implementer note: wire the global `setListener` in `client()` to call `onPurchases(...)` (replace the inline comment with `{ result, purchases -> onPurchases(result, purchases) }`). The one-shot `pendingCall` pattern bridges `launchBillingFlow`'s async result back to the JS promise. If a cleaner per-call structure is obvious, use it — the contract is: `purchase` resolves `{purchaseToken, productId}` / `{pending:true}` or rejects `USER_CANCELLED`.

- [ ] **Step 4: Register the plugin**

In `MainActivity.java` (Capacitor 8 registers plugins via `registerPlugin` in `onCreate`, or auto-discovery). Add `registerPlugin(PlayBillingPlugin.class);` before `super.onCreate(...)` if the project uses explicit registration; otherwise confirm `@CapacitorPlugin` auto-discovery picks it up after `cap sync`. (Match how A1's scaffold handles MainActivity.)

- [ ] **Step 5: TS bridge** `frontend/src/lib/playBilling.ts`
```ts
import { registerPlugin } from '@capacitor/core';

export interface PlayProduct { id: string; displayPrice: string; displayName: string }
export interface PlayBillingPlugin {
  getProducts(o: { productIds: string[] }): Promise<{ products: PlayProduct[] }>;
  purchase(o: { productId: string; obfuscatedAccountId: string }): Promise<{ purchaseToken?: string; productId?: string; pending?: boolean }>;
  restore(): Promise<{ purchaseTokens: string[] }>;
}
export const PlayBilling = registerPlugin<PlayBillingPlugin>('PlayBilling');
```

- [ ] **Step 6: Verify** `npx tsc -b` (bridge typechecks) + `npx cap sync android` (ok). Cannot compile Kotlin here — note it.

- [ ] **Step 7: Commit**
```bash
git add frontend/android/app/src/main/java frontend/android/app/build.gradle frontend/src/lib/playBilling.ts
git commit -m "feat(android): custom Play Billing Kotlin plugin + TS bridge"
```

---

## Task 7: Frontend billing API client

**Files:** Modify `frontend/src/api/billing.ts`; Test `frontend/src/api/__tests__/billing.test.ts`

- [ ] **Step 1: Failing test** (extend the existing billing api test)
```ts
it('googleVerify POSTs purchaseToken + productId', async () => {
  const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ status: 'ok' } as never);
  await billingApi.googleVerify({ purchaseToken: 'TOK', productId: 'premium_monthly' });
  expect(spy).toHaveBeenCalledWith('/billing/google/verify',
    expect.objectContaining({ method: 'POST',
      body: JSON.stringify({ purchaseToken: 'TOK', productId: 'premium_monthly' }) }));
});
it('accountToken GETs /billing/account-token', async () => {
  const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ token: 'uuid' } as never);
  await billingApi.accountToken();
  expect(spy).toHaveBeenCalledWith('/billing/account-token');
});
```
(Match the file's existing mock style — it may use `vi.mock('@/api/client')` instead of `spyOn`; mirror Task-11-A2's approach.)

- [ ] **Step 2: Implement** in `src/api/billing.ts` (inside `billingApi`)
```ts
  googleVerify: (body: { purchaseToken: string; productId: string }) =>
    apiFetch<{ status: string }>('/billing/google/verify',
      { method: 'POST', body: JSON.stringify(body) }),
  accountToken: () => apiFetch<{ token: string }>('/billing/account-token'),
```
(Keep the existing `appleVerify` + `appleAccountToken`; `appleAccountToken` stays as the alias.)

- [ ] **Step 3: Run** `npx vitest run src/api/__tests__/billing.test.ts` → PASS; `npx tsc -b` → clean.

- [ ] **Step 4: Commit**
```bash
git add src/api/billing.ts src/api/__tests__/billing.test.ts
git commit -m "feat(fe): googleVerify + accountToken billing API"
```

---

## Task 8: SubscriptionCard Android branch

**Files:** Modify `frontend/src/components/SubscriptionCard.tsx`; Test `frontend/src/components/__tests__/SubscriptionCard.android.test.tsx`

- [ ] **Step 1: Failing test** `SubscriptionCard.android.test.tsx`
Mock `@/lib/platform` → `isNativeApp: () => true, isAndroid: () => true`. Mock `@/lib/playBilling` → `PlayBilling.getProducts/purchase(resolves {purchaseToken:'TOK', productId:'premium_monthly'})/restore(resolves {purchaseTokens:[]})`. Mock `@/api/billing` → `billingApi` with `accountToken` → `{token:'1111...'}`, `googleVerify` (spy) → `{status:'ok'}`, status method → no active sub. Render in the QueryClientProvider wrapper (mirror `SubscriptionCard.native.test.tsx`).
Assert: a **Subscribe** + **Restore** button render and NO Stripe checkout button; clicking Subscribe calls `accountToken` → `PlayBilling.purchase({productId:'premium_monthly', obfuscatedAccountId:'1111...'})` → `billingApi.googleVerify({purchaseToken:'TOK', productId:'premium_monthly'})`; `axe` has no violations.
Run → FAIL.

- [ ] **Step 2: Implement** — in `SubscriptionCard.tsx`, the native branch currently uses StoreKit. Split it with `isAndroid()` (from `@/lib/platform`):
  - **iOS** (native && !android): existing StoreKit flow unchanged.
  - **Android** (native && android): `const { token } = await billingApi.accountToken();` → `const r = await PlayBilling.purchase({ productId: PLAY_PRODUCT_ID, obfuscatedAccountId: token });` → `if (r.purchaseToken) await billingApi.googleVerify({ purchaseToken: r.purchaseToken, productId: PLAY_PRODUCT_ID });` → invalidate `['subscription-status']`. `{pending:true}` → gentle "purchase pending" note; reject code `USER_CANCELLED` swallowed.
  - **Restore (Android):** `const { purchaseTokens } = await PlayBilling.restore();` → for each, `await billingApi.googleVerify({ purchaseToken, productId: PLAY_PRODUCT_ID });` → invalidate; empty → "nothing to restore".
  - **Manage (Android):** `window.open('https://play.google.com/store/account/subscriptions', '_blank', 'noopener,noreferrer')`.
  - Add `const PLAY_PRODUCT_ID = 'premium_monthly';`. Keep `PREMIUM_PRODUCT_ID` (iOS). Web branch unchanged. Card stays parent-only.

- [ ] **Step 3: Run** `npx vitest run src/components/__tests__/SubscriptionCard.android.test.tsx` and the existing `SubscriptionCard.native.test.tsx` → both PASS; `npx tsc -b` → clean; `npm run lint` → clean for changed files.

- [ ] **Step 4: Commit**
```bash
git add src/components/SubscriptionCard.tsx src/components/__tests__/SubscriptionCard.android.test.tsx
git commit -m "feat(fe): SubscriptionCard Android Play Billing branch"
```

---

## Task 9: Regression + iOS/Android sync + runbook + close-out

- [ ] **Step 1: Frontend gates** (from `frontend/`): `npx tsc -b && npm run lint && npm run test && npm run build` → all green (pre-existing react-refresh warnings OK). Fix any A3-caused failures (e.g. a sibling test mocking `@/lib/platform` that now needs `isAndroid`/`isNativeApp`).
- [ ] **Step 2: Sync** `npx cap sync android` → ok; `npx cap ls` shows android plugins. If `cap sync` regenerated tracked android plugin-registration files (capacitor.plugins.json etc.) because of the new plugin, stage+commit them so android/ stays consistent. (Custom plugins registered via `@CapacitorPlugin` aren't in capacitor.plugins.json, so likely none — confirm with `git status --porcelain frontend/android`.)
- [ ] **Step 3: Runbook** — add an "A3 — Google Play Billing" section to `docs/2026-06-07-android-operator-runbook.md`: Play Console subscription product `premium_monthly` + base plan + 7-day free-trial offer; create a Google Cloud **service account**, grant it in Play Console → Users & permissions / API access (View financial data, Manage orders); set env `GOOGLE_PLAY_PACKAGE_NAME=leeashmore.investikid.ai.app`, `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` (key contents), `GOOGLE_PLAY_PRODUCT_ID=premium_monthly`; enable Pub/Sub, create the RTDN topic + a push subscription to `{backend}/billing/google/notifications`, set it as Play's Real-time developer notifications topic; add license-test accounts; device purchase test via internal testing.
- [ ] **Step 4: PROGRESS** — mark 4A·A3 implemented (in-repo) in `docs/superpowers/PROGRESS.md`; note Kotlin plugin first-compile = checkpoint `run_android`/Android Studio; device purchase test + Play/Cloud setup operator-side; 4A now feature-complete across web/iOS/Android.
- [ ] **Step 5: Commit**
```bash
git add docs/2026-06-07-android-operator-runbook.md docs/superpowers/PROGRESS.md
git commit -m "docs: 4A·A3 Play Billing operator steps + mark implemented"
```

---

## Self-Review (completed)

- **Spec coverage:** config/deps → T1; service verify+ack+recompute → T2; RTDN → T3; endpoints+schemas+CSRF+account-token → T4; backend regression → T5; Kotlin plugin+bridge+gradle → T6; FE api → T7; SubscriptionCard Android → T8; runbook+regression+sync → T9. No DB migration (provider exists) — correctly omitted.
- **Reuse:** `household_token` imported from `apple_billing_service`; `recompute_household_premium` reused; provider-agnostic `Subscription` reused; product-allowlist + household-binding guards mirrored from A2.
- **Type/name consistency:** `verify_purchase(session,*,parent_email,purchase_token,product_id)`, `handle_notification(session, message)`, `GoogleBillingError`, `_fetch_subscription`/`_acknowledge`/`_map_status`/`_upsert_and_recompute`, `GoogleVerifyRequest{purchaseToken,productId}`, `billingApi.googleVerify({purchaseToken,productId})`/`accountToken()`, `PlayBilling.purchase({productId,obfuscatedAccountId})` → `{purchaseToken,productId,pending}`, `PLAY_PRODUCT_ID='premium_monthly'` — consistent across backend + FE + Kotlin.
- **Constraints honored:** backend fully pytest-tested; Kotlin/gradle flagged as non-compilable here (checkpoint/operator); no iOS/Stripe/core changes; explicit `git add` paths.
- **Flagged for implementer:** confirm the real Android package dir for the Kotlin file/registration (T6 Step 1); wire the BillingClient global listener → `onPurchases` (T6 note); match the existing billing-api test mock style (T7).
