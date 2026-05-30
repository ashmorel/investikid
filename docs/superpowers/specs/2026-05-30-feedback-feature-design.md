# User Feedback Feature — Design Spec

## Goal

Allow both parent and child users to submit bug reports, feature requests, and general feedback from within the app. Store submissions in PostgreSQL, send email notifications via Resend, and provide a read-only admin view.

## Architecture

Three layers:

1. **Backend:** New `Feedback` SQLAlchemy model, `feedback.py` router (`POST /api/feedback`), admin endpoint (`GET /api/admin/feedback`), email notification via existing `email.py` service.
2. **Frontend (user-facing):** `FeedbackDialog` component opened from profile menus. BottomSheet on mobile, Dialog on desktop (matching existing `ProfileMenu` pattern).
3. **Frontend (admin):** `FeedbackList` component at `/admin/feedback` with type filtering and pagination.

## Data Model

### Feedback Table

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, server-default |
| `user_id` | UUID | FK → users.id, NOT NULL |
| `feedback_type` | VARCHAR(20) | NOT NULL, one of: "bug", "feature", "general" |
| `message` | TEXT | NOT NULL, max 2000 chars (validated in schema) |
| `page_url` | VARCHAR(500) | Nullable — auto-captured current route |
| `created_at` | TIMESTAMP | Server-default UTC now |

Alembic migration adds the table. No relationships beyond the user FK.

### New Model File

`app/models/feedback.py` — single `Feedback` class inheriting from `Base`. Register in `app/models/__init__.py`.

## Backend API

### POST /api/feedback

- **Auth:** Requires authenticated user (child or parent).
- **Rate limit:** `5/hour` per user via slowapi.
- **Request body:**
  ```json
  {
    "feedback_type": "bug",
    "message": "The quiz timer doesn't stop when I switch tabs",
    "page_url": "/lessons/123/quiz"
  }
  ```
- **Validation:** `feedback_type` must be one of `bug`, `feature`, `general`. `message` must be 1–2000 characters. `page_url` is optional, max 500 chars.
- **Response:** 201 with `{ "id": "<uuid>" }`.
- **Side effect:** After persisting, send notification email (fire-and-forget, failure does not fail the request).

### GET /api/admin/feedback

- **Auth:** Admin token (same pattern as existing admin endpoints).
- **Query params:** `type` (optional filter), `page` (default 1), `per_page` (default 20, max 100).
- **Response:**
  ```json
  {
    "items": [
      {
        "id": "...",
        "username": "alex123",
        "user_role": "child",
        "feedback_type": "bug",
        "message": "...",
        "page_url": "/simulator",
        "created_at": "2026-05-30T10:00:00Z"
      }
    ],
    "total": 42,
    "page": 1,
    "per_page": 20
  }
  ```
- Items sorted newest-first. Username and role joined from user table.

### Router File

`app/routers/feedback.py` — new router, registered in `app/main.py`.

### Schemas

`app/schemas/feedback.py`:
- `FeedbackCreate` — request body validation (type, message, page_url).
- `FeedbackOut` — response for the admin list endpoint.

## Email Notification

### Approach

Add a `feedback_notification` template to the existing `email.py` service. On feedback submission, send an email to a configurable address.

### Config

Add `feedback_notify_email: str = ""` to `Settings` in `config.py`. When non-empty, sends notification emails. When empty, skips notification (useful for dev/test).

### Email Content

- **Subject:** `[Invest-Ed] Bug Report from alex123` (or "Feature Request" / "Feedback" based on type).
- **Body:** Username, role (child/parent), type, message, page URL, timestamp.
- **Template:** Plain text + HTML, following the existing email template pattern in `email.py`. No CTA button needed — purely informational.

### Fire-and-Forget

Email sending runs in a background task (or try/except with logging) so that email failures do not fail the feedback submission. The feedback row is the source of truth.

## Frontend — FeedbackDialog

### Component

`src/components/child/FeedbackDialog.tsx`:
- Renders as `BottomSheet` on mobile, `Dialog` on desktop (using existing `useMediaQuery` hook).
- Props: `open: boolean`, `onOpenChange: (open: boolean) => void`.

### Form Fields

1. **Type** — `<select>` with options: "Bug Report", "Feature Request", "General Feedback". Maps to `bug`, `feature`, `general`.
2. **Message** — `<textarea>` with dynamic placeholder based on selected type:
   - Bug: "Describe the bug you encountered..."
   - Feature: "What feature would you like to see?"
   - General: "Share your thoughts..."
3. Character counter showing `X / 2000`.

### Submission

- TanStack Query `useMutation` calling `POST /api/feedback`.
- Auto-captures `window.location.pathname` as `page_url`.
- On success: show success toast ("Thanks for your feedback!"), close dialog, reset form.
- On error: inline error banner.
- Submit button disabled while pending.

### Entry Points

1. **Child ProfileMenu** (`ProfileMenu.tsx`): Add "Send Feedback" `DropdownMenuItem` between "Profile" and "Log out", with a separator.
2. **Parent Dashboard** (`ParentDashboard.tsx`): Add "Send Feedback" button/link in the parent's account area.

### API Client

Add `feedbackApi.submit(data)` to a new file `src/api/feedback.ts`, using the existing `apiFetch` client.

## Frontend — Admin FeedbackList

### Component

`src/components/admin/FeedbackList.tsx`:
- Table with columns: Date, User, Type (colored badge), Message (truncated to 100 chars, expandable), Page URL.
- Type badges: red for bug, blue for feature, grey for general.
- Filter dropdown at top to filter by type (or "All").
- Pagination controls at bottom (Previous / Next / page indicator).

### Route & Nav

- Route: `/admin/feedback` added to admin routes.
- Add `{ to: '/admin/feedback', label: 'Feedback', icon: '💬', end: false }` to `AdminSidebar.tsx` NAV_ITEMS.

### API Client

Add `adminApi.listFeedback(params)` to the existing admin API client.

## Accessibility (WCAG 2.2 AA)

- All form fields have visible labels and proper `id`/`htmlFor` associations.
- Dialog/BottomSheet manages focus on open (auto-focus first field) and returns focus on close.
- Success/error states announced via `aria-live="polite"` region or toast (existing toast system).
- Type badges in admin list use text labels, not color alone.
- All interactive elements meet 44×44px minimum touch target on mobile.
- Character counter associated with textarea via `aria-describedby`.

## Testing

### Backend Tests

`tests/test_feedback.py`:
- Submit feedback (happy path, all three types).
- Validation: empty message, message too long, invalid type.
- Rate limiting (mock or skip in test).
- Admin list: pagination, type filtering, sorted newest-first.
- Unauthenticated access returns 401.

### Frontend Tests

- `FeedbackDialog` renders, submits, shows success toast.
- Character counter updates.
- Error state displayed on failure.
- Accessibility: labels, focus management.

## Files Summary

### New Files
- `backend/app/models/feedback.py`
- `backend/app/schemas/feedback.py`
- `backend/app/routers/feedback.py`
- `backend/alembic/versions/XXXX_add_feedback_table.py`
- `backend/tests/test_feedback.py`
- `frontend/src/api/feedback.ts`
- `frontend/src/components/child/FeedbackDialog.tsx`
- `frontend/src/components/admin/FeedbackList.tsx`

### Modified Files
- `backend/app/core/config.py` — add `feedback_notify_email` setting
- `backend/app/models/__init__.py` — register Feedback model
- `backend/app/main.py` — register feedback router
- `backend/app/services/email.py` — add `feedback_notification` template
- `frontend/src/components/child/ProfileMenu.tsx` — add "Send Feedback" menu item
- `frontend/src/pages/ParentDashboard.tsx` — add "Send Feedback" entry point
- `frontend/src/components/admin/AdminSidebar.tsx` — add Feedback nav item
- Admin routing file — add `/admin/feedback` route
