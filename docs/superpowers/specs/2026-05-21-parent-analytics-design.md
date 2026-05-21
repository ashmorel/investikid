# Parent Analytics Dashboard — Design Spec

## Goal

Add inline learning analytics to each child card on the parent dashboard, giving parents a quick view of their child's progress without leaving the page.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Analytics purpose | Learning progress | Parents want to see how their child is doing with lessons, not safety monitoring |
| Location | Inline on child cards | No separate page — keeps everything in one view |
| Layout | Expandable detail section | Compact summary always visible; "Show progress" toggle reveals full detail |
| Time scope | Recent activity | Last 5 completed lessons; current streak/level/XP. Actionable, not overwhelming |
| Simulator data | Excluded | Simulator has its own page; keep analytics focused on learning |
| Data fetching | Extend existing endpoint | Add `analytics` to `GET /parent/children` response. One request, no waterfall |

## Backend

### Extended Response Schema

Extend the existing `GET /parent/children` endpoint. Each child in the response gains an `analytics` object:

```
ChildOut {
  user_id, username, email, country, status, is_premium,  // existing
  analytics: {
    level: int
    xp: int
    xp_to_next_level: int
    streak_count: int
    lessons_completed: int
    lessons_total: int
    recent_lessons: [
      { title: str, type: "card"|"quiz", score: float|null, completed_at: datetime }
    ]  // last 5 completed, ordered by completed_at desc
    badges: [
      { name: str, icon: str, earned_at: datetime }
    ]  // all earned badges
  }
}
```

### Data Sources

All data already exists — no new tables or migrations:

| Field | Source |
|-------|--------|
| `level`, `xp`, `streak_count` | `UserProgress` (one row per user) |
| `xp_to_next_level` | Computed from level thresholds (existing `LEVEL_THRESHOLDS` in backend) |
| `lessons_completed` | `COUNT(LessonCompletion)` for this user |
| `lessons_total` | `COUNT(Lesson)` filtered by child's country/region |
| `recent_lessons` | `LessonCompletion` JOIN `Lesson` — last 5 by `completed_at` desc |
| `badges` | `UserBadge` JOIN `Badge` — all earned |

### Query Strategy

Single query per child using SQLAlchemy eager loading. The parent endpoint already iterates children, so add the analytics fetch inside that loop. For N children this is N small queries (badges + recent lessons + progress), which is acceptable for the typical 1-3 children per parent. No need for complex aggregation queries.

## Frontend

### New Files

| File | Responsibility |
|------|---------------|
| `src/components/ChildAnalytics.tsx` | Expandable analytics section. Receives `analytics` prop. Renders summary line, expand toggle, progress bar, recent lessons, badges. |
| `src/components/ProgressBar.tsx` | Reusable animated progress bar with label. Takes `value`, `max`, `label` props. |

### Modified Files

| File | Change |
|------|--------|
| `src/components/ChildCard.tsx` | Import and render `<ChildAnalytics>` below existing card content |
| `src/api/parent.ts` | Update `ChildOut` TypeScript type to include `analytics` field |
| `backend/app/routers/parent.py` | Extend children query to include analytics data |
| `backend/app/schemas/parent.py` | Add `AnalyticsOut` and `RecentLessonOut` Pydantic schemas |

### UI Specification

**Compact summary line** (always visible, below child name/status):
- Format: `Lvl {level} · {xp} XP · {streak_count}-day streak` (with fire emoji if streak > 0)
- Font: 13px, muted colour (`text-gray-500`)
- Shows even when detail section is collapsed

**Expand toggle:**
- Text: "Show progress" / "Hide progress"
- Colour: amber-600 (brand colour)
- Uses `aria-expanded` for accessibility

**Expanded section** (Framer Motion animated height transition):

1. **Progress bar**: "{lessons_completed} of {lessons_total} lessons completed"
   - Gradient fill: amber-500 to orange-500
   - Height: 8px, rounded corners
   - `role="progressbar"` with `aria-valuenow` and `aria-valuemax`

2. **Recent lessons list**: Last 5 completed
   - Each row: lesson title, type badge (Card/Quiz), score
   - Quiz scores shown as percentage; card completions shown as checkmark
   - Subtle bottom borders between rows

3. **Badges row**: All earned badges
   - Format: emoji + badge name, separated by middots
   - Wraps if many badges

**Zero state** (child has no activity yet):
- Summary line: "No activity yet"
- Expanded section: "Your child hasn't started any lessons yet. Encourage them to begin!"

## Testing

### Unit Tests — `ChildAnalytics.test.tsx`

- Renders summary line with correct level, XP, streak
- Collapsed by default (expanded section not visible)
- Clicking toggle reveals expanded content
- Progress bar shows correct fraction
- Recent lessons render with correct titles, types, scores
- Badges render with names and icons
- Zero state shows appropriate message when analytics has no lessons

### Unit Tests — `ProgressBar.test.tsx`

- Renders with correct width percentage
- Displays label text
- Has correct ARIA attributes (`role`, `aria-valuenow`, `aria-valuemax`)
- Handles zero/full values

### Accessibility Tests — `child-analytics.a11y.test.tsx`

- Axe scan passes on collapsed state
- Axe scan passes on expanded state
- Toggle has `aria-expanded`
- Progress bar has `role="progressbar"` with value attributes
- Keyboard navigation works (Enter/Space toggles expand)

### Backend Tests

- `GET /parent/children` response includes `analytics` object with correct schema
- Analytics reflects actual lesson completions and badge awards
- `recent_lessons` ordered by `completed_at` desc, limited to 5
- `lessons_total` count is correct for child's region
- Zero-activity child returns empty arrays and zero counts

### E2E

No new e2e specs. The existing parent dashboard e2e tests cover page load and child card rendering. This feature is purely additive UI on an already-tested page.

## Scope Boundaries

**In scope:**
- Analytics data on `GET /parent/children`
- `ChildAnalytics` and `ProgressBar` components
- Unit, a11y, and backend tests

**Out of scope:**
- Separate analytics page or route
- Simulator/trading data in analytics
- Historical trends or charts
- Notification system for parent alerts
- Configurable time ranges
- Export/download of analytics data
