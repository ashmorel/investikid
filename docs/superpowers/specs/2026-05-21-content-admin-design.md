# Content Management Admin Panel — Design Spec

**Sub-project:** 10 of Invest-Ed hardening programme
**Date:** 2026-05-21
**Status:** Approved

## Goal

Replace seed-file-based content management with a web-based admin panel that lets administrators create, edit, reorder, and soft-delete modules, lessons, badges, and challenges without touching code.

## Scope

- Full CRUD for modules (with nested lessons), badges, and challenges
- Admin-only `/admin` route inside the existing React app
- Bearer-token authentication (shared secret from `.env`)
- Structured, type-specific lesson editors (card, quiz, scenario)
- Arrow-button reordering for modules and lessons
- Country targeting via multi-select of existing user countries

**Out of scope:** Rich text editing, media/image uploads, role-based admin users, audit logging, content versioning/drafts.

## Architecture

### Authentication

- New env var `ADMIN_TOKEN` — a random string set in `.env`
- Backend: `get_current_admin` FastAPI dependency checks `Authorization: Bearer <token>` against `settings.ADMIN_TOKEN`. Returns 401 on mismatch.
- Frontend: `/admin` route shows a token-entry screen. Token stored in `sessionStorage`. All admin API calls include `Authorization: Bearer <token>` header. On 401, redirect back to token entry.

### Frontend Structure

Admin pages live under `/admin` route in the existing React app, behind a token gate.

**Layout:**
- Persistent sidebar navigation (dark theme, matches app aesthetic)
- Four sections: Dashboard, Modules, Badges, Challenges
- "Back to App" link in sidebar footer

**Pages:**

1. **AdminLogin** — token entry form, stores in sessionStorage
2. **AdminLayout** — sidebar + outlet wrapper, 401 interceptor
3. **AdminDashboard** — read-only stats cards (module count, lesson count, badge count, challenge count)
4. **ModuleList** — sortable list with ↑↓ arrows, "+ New Module" button, each row shows icon/title/topic/lesson count/premium badge/country info
5. **ModuleForm** — create/edit form with fields: topic (text), title (text), icon (emoji text input), is_premium (checkbox), country_codes (multi-select chips from `/admin/countries`)
6. **LessonList** — inline within ModuleForm, showing lessons for the current module with ↑↓ arrows, type badges, title preview, XP
7. **LessonForm** — modal or inline form with type selector (pill tabs: card/quiz/scenario). Fields switch based on type:
   - **Card:** title (text), body (textarea)
   - **Quiz:** question (text), choices (dynamic list with add/remove), correct answer (radio), explanation (text)
   - **Scenario:** prompt (text), choices (dynamic list, each with label + outcome text), correct answer (radio)
   - All types: xp_reward (number, type-appropriate defaults: card=10, quiz=25, scenario=20)
8. **BadgeList** — list with name, icon, condition summary
9. **BadgeForm** — name (text), description (textarea), icon_url (text), condition_type (dropdown: lesson_count, streak_days, module_complete, xp_total), condition_value (number)
10. **ChallengeList** — list sorted by starts_at desc, with active/expired status badge
11. **ChallengeForm** — title (text), description (textarea), type (dropdown: lessons_completed, xp_earned, streak), target_value (number), xp_reward (number), badge_id (optional dropdown of existing badges), starts_at (date), ends_at (date), is_premium (checkbox)

**Shared components:**
- `AdminSidebar` — nav links with active state
- `AdminTokenGate` — wraps admin routes, checks sessionStorage for token
- `OrderArrows` — reusable ↑↓ button pair for reordering
- `ConfirmDialog` — confirmation modal for deletes

### Backend API

New router at `/admin` prefix. All endpoints require `get_current_admin` dependency.

#### Dashboard
| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/admin/stats` | `{ modules: int, lessons: int, badges: int, challenges: int }` |

#### Modules
| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| GET | `/admin/modules` | — | `Module[]` with lesson_count |
| POST | `/admin/modules` | `ModuleCreate` | `Module` |
| PUT | `/admin/modules/{id}` | `ModuleUpdate` | `Module` |
| DELETE | `/admin/modules/{id}` | — | `{ status: "ok" }` |
| PATCH | `/admin/modules/reorder` | `{ order: [{id, order_index}] }` | `{ status: "ok" }` |

#### Lessons
| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| GET | `/admin/modules/{id}/lessons` | — | `Lesson[]` |
| POST | `/admin/modules/{id}/lessons` | `LessonCreate` | `Lesson` |
| PUT | `/admin/lessons/{id}` | `LessonUpdate` | `Lesson` |
| DELETE | `/admin/lessons/{id}` | — | `{ status: "ok" }` |
| PATCH | `/admin/modules/{id}/lessons/reorder` | `{ order: [{id, order_index}] }` | `{ status: "ok" }` |

#### Badges
| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| GET | `/admin/badges` | — | `Badge[]` |
| POST | `/admin/badges` | `BadgeCreate` | `Badge` |
| PUT | `/admin/badges/{id}` | `BadgeUpdate` | `Badge` |
| DELETE | `/admin/badges/{id}` | — | `{ status: "ok" }` |

#### Challenges
| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| GET | `/admin/challenges` | — | `Challenge[]` |
| POST | `/admin/challenges` | `ChallengeCreate` | `Challenge` |
| PUT | `/admin/challenges/{id}` | `ChallengeUpdate` | `Challenge` |
| DELETE | `/admin/challenges/{id}` | — | `{ status: "ok" }` |

#### Utility
| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/admin/countries` | `string[]` — distinct country codes from User table |

### Schemas

**Module schemas:**
```python
class ModuleCreate(BaseModel):
    topic: str
    title: str
    icon: str
    is_premium: bool = False
    country_codes: list[str] = []
    order_index: int

class ModuleUpdate(BaseModel):
    topic: str | None = None
    title: str | None = None
    icon: str | None = None
    is_premium: bool | None = None
    country_codes: list[str] | None = None

class ModuleOut(BaseModel):
    id: uuid.UUID
    topic: str
    title: str
    icon: str
    is_premium: bool
    country_codes: list[str]
    order_index: int
    lesson_count: int

    model_config = ConfigDict(from_attributes=True)
```

**Lesson schemas:**
```python
class LessonCreate(BaseModel):
    type: Literal["card", "quiz", "scenario"]
    content_json: dict
    xp_reward: int
    order_index: int

    @field_validator("content_json")
    @classmethod
    def validate_content(cls, v, info):
        lesson_type = info.data.get("type")
        if lesson_type == "card":
            assert "title" in v and "body" in v, "Card requires title and body"
        elif lesson_type == "quiz":
            assert "question" in v and "choices" in v and "answer_index" in v and "explanation" in v
            assert len(v["choices"]) >= 2, "Quiz requires at least 2 choices"
            assert 0 <= v["answer_index"] < len(v["choices"]), "Invalid answer_index"
        elif lesson_type == "scenario":
            assert "prompt" in v and "choices" in v and "correct_index" in v
            assert len(v["choices"]) >= 2, "Scenario requires at least 2 choices"
            assert all("label" in c and "outcome" in c for c in v["choices"])
            assert 0 <= v["correct_index"] < len(v["choices"]), "Invalid correct_index"
        return v

class LessonUpdate(BaseModel):
    type: Literal["card", "quiz", "scenario"] | None = None
    content_json: dict | None = None
    xp_reward: int | None = None

class LessonOut(BaseModel):
    id: uuid.UUID
    module_id: uuid.UUID
    type: str
    content_json: dict
    xp_reward: int
    order_index: int

    model_config = ConfigDict(from_attributes=True)
```

**Content JSON validation rules:**
- **card**: `{ title: str (required), body: str (required) }`
- **quiz**: `{ question: str (required), choices: list[str] (min 2), answer_index: int (valid index), explanation: str (required) }`
- **scenario**: `{ prompt: str (required), choices: list[{label: str, outcome: str}] (min 2), correct_index: int (valid index) }`

**Badge schemas:**
```python
class BadgeCreate(BaseModel):
    name: str
    description: str
    icon_url: str
    condition_type: Literal["lesson_count", "streak_days", "module_complete", "xp_total"]
    condition_value: int

class BadgeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon_url: str | None = None
    condition_type: Literal["lesson_count", "streak_days", "module_complete", "xp_total"] | None = None
    condition_value: int | None = None

class BadgeOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    icon_url: str
    condition_type: str
    condition_value: int

    model_config = ConfigDict(from_attributes=True)
```

**Challenge schemas:**
```python
class ChallengeCreate(BaseModel):
    title: str
    description: str
    type: Literal["lessons_completed", "xp_earned", "streak"]
    target_value: int
    xp_reward: int
    badge_id: uuid.UUID | None = None
    starts_at: datetime
    ends_at: datetime
    is_premium: bool = False

class ChallengeUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    type: Literal["lessons_completed", "xp_earned", "streak"] | None = None
    target_value: int | None = None
    xp_reward: int | None = None
    badge_id: uuid.UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_premium: bool | None = None

class ChallengeOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    type: str
    target_value: int
    xp_reward: int
    badge_id: uuid.UUID | None
    starts_at: datetime
    ends_at: datetime
    is_premium: bool

    model_config = ConfigDict(from_attributes=True)
```

### Data Model Changes

No new database tables needed. Existing models (Module, Lesson, Badge, Challenge) already have all required fields.

**Additions to existing models:**
- None — current models support all CRUD operations

**New config:**
- `ADMIN_TOKEN: str` added to `Settings` in `app/core/config.py`

### Soft Delete Behavior

- **Modules:** set `is_premium = False` and mark as inactive (no `deleted_at` column on Module). Or simply delete the row — modules have no user-facing history that needs preservation. Decision: hard delete with cascade to lessons (admin is intentionally removing content).
- **Lessons:** hard delete (cascade from module, or individual delete)
- **Badges:** hard delete — but warn if any UserBadge references exist. If users have earned this badge, block deletion and show a message.
- **Challenges:** hard delete — safe since challenge completions reference challenge_id but the admin should be aware.

### Reorder Mechanism

The `PATCH /admin/modules/reorder` and `PATCH /admin/modules/{id}/lessons/reorder` endpoints accept a list of `{ id, order_index }` pairs. The backend updates all items in a single transaction.

Frontend sends the full ordered list after each ↑↓ click:
```typescript
// After clicking ↑ on item at index 2:
// Swap order_index of items at index 1 and 2
// Send: [{ id: "...", order_index: 0 }, { id: "...", order_index: 1 }, ...]
```

### Frontend API Client

New `api/admin.ts` module with TanStack Query hooks:
- `useAdminStats()` — GET /admin/stats
- `useModules()` — GET /admin/modules
- `useCreateModule()`, `useUpdateModule()`, `useDeleteModule()`, `useReorderModules()`
- `useLessons(moduleId)` — GET /admin/modules/{id}/lessons
- `useCreateLesson()`, `useUpdateLesson()`, `useDeleteLesson()`, `useReorderLessons()`
- `useBadges()`, `useCreateBadge()`, `useUpdateBadge()`, `useDeleteBadge()`
- `useChallenges()`, `useCreateChallenge()`, `useUpdateChallenge()`, `useDeleteChallenge()`
- `useCountries()` — GET /admin/countries

All hooks include the admin token from sessionStorage in the Authorization header. On 401, clear sessionStorage and redirect to login.

### Testing Strategy

**Backend (pytest):**
- Admin auth middleware: valid token, invalid token, missing token
- Module CRUD: create, read, update, delete, reorder
- Lesson CRUD: create per type (card/quiz/scenario), update, delete, reorder
- Content JSON validation: valid and invalid payloads per type
- Badge CRUD: create, update, delete, delete-blocked-by-users
- Challenge CRUD: create, update, delete
- Countries endpoint: returns distinct codes

**Frontend (vitest):**
- AdminTokenGate: renders login when no token, renders children when token present, clears on 401
- ModuleList: renders modules, reorder arrows work, delete confirmation
- ModuleForm: create mode, edit mode, validation
- LessonForm: type switching, field validation per type, dynamic choice add/remove
- BadgeForm: field rendering, validation
- ChallengeForm: field rendering, date pickers, badge dropdown
- AdminSidebar: active link state, navigation

**Accessibility (vitest + axe):**
- Admin forms pass axe audit
- Type selector keyboard accessible
- Confirm dialog focus management
- Form error announcements via aria-live

### File Structure

**Backend:**
```
backend/app/
├── routers/
│   └── admin.py              # All admin endpoints
├── routers/
│   └── admin_auth.py          # get_current_admin dependency
├── schemas/
│   └── admin.py               # All admin request/response schemas
├── services/
│   └── admin_service.py       # CRUD business logic
└── core/
    └── config.py              # Add ADMIN_TOKEN to Settings
```

**Frontend:**
```
frontend/src/
├── api/
│   └── admin.ts               # API client + TanStack Query hooks
├── components/admin/
│   ├── AdminLayout.tsx         # Sidebar + outlet wrapper
│   ├── AdminLogin.tsx          # Token entry screen
│   ├── AdminDashboard.tsx      # Stats overview
│   ├── AdminSidebar.tsx        # Nav component
│   ├── ModuleList.tsx          # Module list with reorder
│   ├── ModuleForm.tsx          # Module create/edit form
│   ├── LessonList.tsx          # Lesson list within module
│   ├── LessonForm.tsx          # Type-specific lesson editor
│   ├── BadgeList.tsx           # Badge list
│   ├── BadgeForm.tsx           # Badge create/edit form
│   ├── ChallengeList.tsx       # Challenge list
│   ├── ChallengeForm.tsx       # Challenge create/edit form
│   ├── OrderArrows.tsx         # Reusable ↑↓ buttons
│   └── ConfirmDialog.tsx       # Delete confirmation modal
├── components/admin/
│   └── __tests__/              # All admin component tests
└── tests/a11y/
    └── admin.a11y.test.tsx     # Accessibility tests
```

**Tests:**
```
backend/tests/
└── test_admin.py               # All admin endpoint tests

frontend/src/components/admin/__tests__/
├── AdminLogin.test.tsx
├── ModuleList.test.tsx
├── ModuleForm.test.tsx
├── LessonForm.test.tsx
├── BadgeList.test.tsx
├── BadgeForm.test.tsx
├── ChallengeList.test.tsx
├── ChallengeForm.test.tsx
├── OrderArrows.test.tsx
└── ConfirmDialog.test.tsx
```
