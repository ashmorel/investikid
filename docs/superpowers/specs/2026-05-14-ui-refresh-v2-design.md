# UI Refresh v2 — Mobile, Animations & Simulator Polish

## Goal

Make Invest-Ed feel like a native mobile app for kids: responsive bottom-tab navigation on phones, playful reward animations throughout, a visually polished Simulator with a portfolio chart, and minor copy fixes.

## Scope

- **Mobile responsiveness**: Bottom tab bar on `< md` screens, responsive layout refinements
- **Playful animations**: Page transitions, XP counters, confetti, badge reveals, progress bar fills
- **Simulator visual refresh**: Warm header, styled tabs, portfolio value chart, better empty states
- **Copy fixes**: "Lessons" heading → "Quests", any other stale references

**Out of scope**: Parent dashboard, auth pages, backend API changes (except one new chart endpoint), dark mode.

## Design Decisions

### 1. Mobile Bottom Tab Bar

**What**: A fixed bottom navigation bar with four tabs (Home, Quests, Simulator, Stats), visible only on `< md` screens (below 768px). The existing TopNav hamburger menu is removed in favour of this pattern.

**Why bottom tabs over hamburger**: The target audience is kids on phones/tablets. Bottom tabs are thumb-friendly and match patterns they know from Duolingo, TikTok, and games. A hamburger menu hides navigation behind an extra tap — bad for discoverability with young users.

**Implementation**:
- New component: `src/components/child/BottomTabBar.tsx`
- Four icons from `lucide-react`: `Home`, `BookOpen` (Quests), `TrendingUp` (Simulator), `BarChart3` (Stats)
- Active tab uses amber fill + label; inactive uses gray outline only
- Fixed to bottom, `h-16`, `z-20`, with safe-area padding for notched phones (`pb-[env(safe-area-inset-bottom)]`)
- `Shell.tsx` renders `<BottomTabBar>` after `<main>` and adds `pb-16 md:pb-0` to main content on mobile
- TopNav: remove the `Sheet`/hamburger trigger entirely; the desktop nav (`hidden md:flex`) remains unchanged

**Layout at each breakpoint**:
- `< md`: Bottom tab bar visible, TopNav shows only logo + profile avatar (no nav links, no hamburger)
- `≥ md`: TopNav with full nav links, no bottom tab bar

### 2. Responsive Layout Refinements

Most grids already use `sm:`/`md:` breakpoints (Lessons grid, BadgeGrid, XpSummary, Market grid). Refinements needed:

- **Lessons grid**: Already `grid-cols-1 sm:grid-cols-2 md:grid-cols-3` ✅
- **Stats XpSummary**: Already `sm:grid-cols-3` ✅
- **Stats BadgeGrid**: Already `sm:grid-cols-2 lg:grid-cols-3` ✅
- **CashCard**: Already `sm:flex-row` ✅
- **Simulator tabs**: Touch targets need to be at least `h-11` on mobile (currently `py-2` — fine)
- **Home page quest card**: Ensure "Resume →" button doesn't get clipped on narrow screens — stack vertically on `< sm`
- **Module page header**: Ensure the illustration banner doesn't overflow on small screens

### 3. Animation Library: Framer Motion

**Why Framer Motion**: Tree-shakeable, React-idiomatic (component-based API), handles layout animations natively, great for page transitions via `AnimatePresence`. The only current animation dependency is `tailwindcss-animate` (CSS-only) — Framer Motion adds JS-driven animations for the playful effects that CSS can't do (counter animations, staggered reveals, physics-based springs).

**Bundle impact**: ~30KB gzipped for the features we use. Acceptable for a modern SPA.

### 4. Animation Inventory

| Location | Animation | Library | Trigger |
|----------|-----------|---------|---------|
| Page transitions | Fade + slight Y-slide | Framer Motion `AnimatePresence` | Route change |
| CompletionPanel | Confetti burst | `canvas-confetti` (3KB) | Quest completed |
| CompletionPanel | XP counter animates 0 → earned | Framer Motion `useSpring` | Mount |
| CompletionPanel | Trophy bounce-in | Framer Motion spring | Mount |
| Home page | Streak fire pulse | CSS `@keyframes` via tailwindcss-animate | Always |
| Home page | XP progress bar smooth fill | Framer Motion `animate` | Mount/update |
| Stats page | Badge unlock reveal | Framer Motion scale + opacity spring | Badge earned today |
| Stats page | Badge grid staggered entrance | Framer Motion `staggerChildren` | Mount |
| Module cards | Hover lift + shadow | CSS `transition` + `hover:` | Hover (desktop only) |
| Lesson options | Tap feedback scale | CSS `active:scale-95` | Tap/click |
| Progress bars | Smooth width transition | Framer Motion or CSS `transition-all` | Value change |

### 5. Page Transitions

Wrap the `<Outlet>` in `Shell.tsx` with Framer Motion's `AnimatePresence`:

```tsx
// Shell.tsx — simplified
<AnimatePresence mode="wait">
  <motion.div
    key={location.pathname}
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -8 }}
    transition={{ duration: 0.15 }}
  >
    <Outlet />
  </motion.div>
</AnimatePresence>
```

Short duration (150ms) so it feels snappy, not sluggish. The `mode="wait"` ensures old page exits before new page enters.

### 6. Confetti on Quest Completion

Use `canvas-confetti` — a tiny (3KB gzipped), zero-dependency library that fires confetti from a canvas overlay. No React wrapper needed; call the function imperatively:

```tsx
// In CompletionPanel, on mount when !already_completed:
import confetti from 'canvas-confetti';

useEffect(() => {
  if (!result.already_completed) {
    confetti({ particleCount: 80, spread: 60, origin: { y: 0.7 } });
  }
}, []);
```

The confetti canvas auto-cleans up. Colours default to party mix which matches our warm palette.

### 7. Animated XP Counter

When the CompletionPanel mounts, the XP number animates from 0 up to the earned amount over ~600ms:

```tsx
const spring = useSpring(0, { stiffness: 50, damping: 15 });
const display = useTransform(spring, (v) => `+${Math.round(v)}`);

useEffect(() => { spring.set(result.xp_awarded); }, []);

<motion.p className="text-3xl font-extrabold ...">
  <motion.span>{display}</motion.span> XP
</motion.p>
```

### 8. Simulator Visual Refresh

**Header treatment**: Add a warm gradient header matching module pages:

```tsx
<div className="rounded-t-2xl bg-gradient-to-b from-amber-100 to-amber-50 p-6 text-center">
  <span className="text-4xl">📊</span>
  <h1 className="mt-2 text-xl font-extrabold text-gray-900">Your Portfolio</h1>
  <p className="text-sm text-gray-500">Practice Mode — no real money</p>
</div>
```

**Styled tabs**: Replace plain `border-b` tabs with pill-style tabs matching the app's warm aesthetic:

```tsx
<div role="tablist" className="flex gap-1 rounded-lg bg-amber-50 p-1">
  <button className={cn(
    'flex-1 rounded-md px-3 py-2 text-sm font-semibold transition-colors',
    active ? 'bg-white text-amber-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
  )}>Holdings</button>
  ...
</div>
```

**Better empty states**: When holdings are empty, show an illustration + encouraging copy instead of just a text link:

```
📈 illustration (FallbackIllustration with topic="stocks")
"No stocks yet!"
"Start by browsing the market and making your first trade."
[Browse Market →] button (gradient amber)
```

### 9. Portfolio Value Chart

**Data source**: New backend endpoint `GET /simulator/portfolio/history` that returns daily portfolio snapshots. Computed from trade history — sum holdings × last known price at each trade date, plus remaining cash.

**Backend**:
- New endpoint in `app/routers/simulator.py`: `GET /portfolio/history`
- Returns `list[{ date: str, value: float }]` — one entry per day the user made a trade, plus today's value
- Logic: query all trades for the user ordered by `executed_at`. For each trade date, compute the portfolio value as `(virtual_cash at that point) + sum(shares_held × trade_price)`. Include today's value using current `portfolio.virtual_cash` + `portfolio.total_value`. If no trades exist, return an empty list.
- No new model needed — derived from existing `Trade` and `Portfolio` data

**Frontend**:
- Use **Recharts** (`recharts`) — lightweight (40KB gzipped), React-native, excellent Tailwind compatibility
- Simple `AreaChart` with gradient amber fill under the line
- Responsive container that works on mobile
- Show only when user has at least 2 data points (otherwise the chart is meaningless)
- New component: `src/components/child/simulator/PortfolioChart.tsx`
- New hook: `src/hooks/usePortfolioHistory.ts`

**Chart styling**:
```tsx
<ResponsiveContainer width="100%" height={200}>
  <AreaChart data={history}>
    <defs>
      <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
        <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
      </linearGradient>
    </defs>
    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
    <YAxis hide />
    <Tooltip />
    <Area type="monotone" dataKey="value" stroke="#f59e0b" fill="url(#portfolioGrad)" />
  </AreaChart>
</ResponsiveContainer>
```

### 10. Copy Fixes

| File | Current | Fixed |
|------|---------|-------|
| `pages/child/Lessons.tsx:41` | `<h1>Lessons</h1>` | `<h1>Quests</h1>` |
| `pages/child/Lessons.tsx:42` | `{modules.length} modules` | `{modules.length} modules` (keep) |

Only one confirmed stale heading. The rest of the quest terminology is already applied.

## Architecture

### New Dependencies

| Package | Purpose | Size (gzipped) |
|---------|---------|----------------|
| `framer-motion` | Page transitions, spring animations, staggered reveals | ~30KB |
| `canvas-confetti` | Quest completion confetti burst | ~3KB |
| `recharts` | Portfolio value area chart | ~40KB |

### New Files

```
src/
  components/child/
    BottomTabBar.tsx              — Mobile bottom navigation (4 tabs)
    simulator/
      PortfolioChart.tsx          — Area chart for portfolio value over time
  hooks/
    usePortfolioHistory.ts        — React Query hook for portfolio history API

backend/
  app/routers/simulator.py        — Add GET /portfolio/history endpoint
```

### Modified Files

```
src/
  components/child/
    Shell.tsx                      — Add BottomTabBar, AnimatePresence page transitions, mobile padding
    TopNav.tsx                     — Remove hamburger/Sheet, simplify mobile to logo + profile only
    lesson/CompletionPanel.tsx     — Add confetti, animated XP counter, trophy bounce
    StatsBar.tsx                   — Add streak pulse animation
  components/child/stats/
    BadgeGrid.tsx                  — Add staggered entrance animation
  pages/child/
    Lessons.tsx                    — Fix "Lessons" → "Quests" heading
    Simulator.tsx                  — Warm header, styled tabs, empty state, chart
    Home.tsx                       — XP progress bar animation, streak pulse
```

### Backend Change

One new endpoint — no model changes, no migrations:

```python
@router.get("/portfolio/history", response_model=list[PortfolioSnapshot])
async def portfolio_history(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Return daily portfolio value snapshots derived from trade history."""
    ...
```

Schema:
```python
class PortfolioSnapshot(BaseModel):
    date: str       # ISO date string "2026-05-14"
    value: float    # Total portfolio value in user's currency
```

## What Does NOT Change

- Backend API endpoints (except adding one new GET endpoint)
- Database schema / migrations
- Auth pages (Login, Signup, PendingConsent)
- Parent dashboard
- Test infrastructure
- Lesson content or module data
- API response shapes for existing endpoints

## Testing Strategy

- **Visual**: Run `npm run dev`, test on desktop (≥ 768px) and mobile (< 768px) viewports
- **Bottom tab bar**: Verify it appears only on mobile, all 4 tabs navigate correctly, active state highlights
- **Animations**: Verify confetti fires on quest completion, XP counter animates, page transitions are smooth
- **Chart**: Complete at least 2 trades, verify portfolio chart renders with correct data
- **Build**: `npm run build` — no TypeScript or build errors
- **Backend**: `python -m pytest -v` — all existing tests pass + new test for portfolio history endpoint
- **Lint**: `npx eslint . && ruff check`
- **Responsive**: Chrome DevTools device toolbar at 375px, 768px, 1280px widths
