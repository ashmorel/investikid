# Admin Settings Section (DB-backed, multi-email alerts) — Design Spec

## Goal
A general **Settings** section in the admin console, editable in-app (no redeploy), starting with **multiple alert email recipients**. Replaces managing `ADMIN_ALERT_EMAIL` only via a Railway env var (which the app cannot edit at runtime).

## Context
- Alerts (`app/services/alerting.py`) currently send to the single `settings.admin_alert_email` env var.
- Admin is account-based + CSRF-protected (`get_current_admin`); admin router `app/routers/admin.py` (router-level `Depends(get_current_admin)`), schemas in `app/schemas/admin.py`.
- Email send is single-recipient: `EmailSender.send(session, to: str, template, context, subject_id=None)` (`app/services/email.py`).
- Frontend admin uses session+CSRF via `adminFetch`→`apiFetch`; sidebar `AdminSidebar.tsx`; routes in `App.tsx`; nav items array.

## Design

### Backend
1. **`AppSetting` model** (`app/models/app_setting.py`): `key: str PK String(64)`, `value: str Text` (JSON-encoded for structured values), `updated_at: DateTime(tz)`. Register in `app/models/__init__.py`. One Alembic migration chaining from head `c3d4e5f6a7b8`.
2. **`app/services/app_settings.py`** — extensible KV seam:
   - `async def get_setting(session, key) -> str | None`, `async def set_setting(session, key, value: str) -> None` (upsert + updated_at).
   - `async def get_alert_emails(session) -> list[str]`: read key `"alert_emails"` (JSON list); if unset/empty, fall back to `[settings.admin_alert_email]` when the env var is non-empty, else `[]`.
   - `async def set_alert_emails(session, emails: list[str]) -> None`: store JSON list under `"alert_emails"`.
3. **Schemas** (`app/schemas/admin.py`): `AdminSettingsOut { alert_emails: list[str] }`, `AdminSettingsUpdate { alert_emails: list[EmailStr] }` (validator: strip, drop empties, dedupe case-insensitively, cap at a sane max e.g. 10).
4. **Endpoints** (`app/routers/admin.py`): `GET /admin/settings` → `AdminSettingsOut`; `PUT /admin/settings` (body `AdminSettingsUpdate`) → persists + returns `AdminSettingsOut`. Admin-gated (inherited), CSRF-protected (inherited).
5. **Alerting** (`app/services/alerting.py`): in `_send_alert`, resolve `recipients = await get_alert_emails(session)`; if empty → return; otherwise send one email per recipient (loop `get_email_sender().send(... to=addr ...)`), then commit. Throttle stays per alert-key (one tick fans out to all recipients).

### Frontend
6. **API** (`src/api/admin.ts`): `AdminSettings { alert_emails: string[] }`; `useAdminSettings()` (GET `['admin','settings']`), `useUpdateAdminSettings()` (PUT, invalidates the query).
7. **Settings page** (`src/components/admin/AdminSettings.tsx`): titled "Settings" with an **Alert emails** field — an editable list (text input + Add; each email shown as a removable row/chip), client-side email-format check, and a **Save** button (dark slate admin theme, labelled inputs for a11y). Show save success/error.
8. **Nav + route**: add `{ to: '/admin/settings', label: 'Settings', icon: '⚙️' }` to `AdminSidebar`; add `<Route path="settings" element={<AdminSettings />} />` under the admin route block in `App.tsx`.

## Testing
- Backend: GET returns env fallback when unset; PUT persists + validates (rejects bad emails, dedupes); `get_alert_emails` precedence (DB → env → empty); alerting fans out to all recipients (mock sender, assert N sends) and no-op when empty; admin-gated (non-admin 403). 
- Frontend: Settings page renders the email list, add/remove updates state, Save calls the hook; nav item present.
- CI 5 jobs green.

## Out of scope
- Other settings fields (the table/section is extensible; only `alert_emails` is wired now).
- Per-recipient throttling or per-alert-type recipient routing.
- Editing Railway env vars from the app (not possible; env var stays a fallback default).
