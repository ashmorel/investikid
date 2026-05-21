# Sub-project 6: Mobile-First Responsive Design

**Status:** Approved — 2026-05-20
**Depends on:** Sub-projects 1–5 (all DONE)

## Goal

Make Invest-Ed feel native on phones (360px+), tablets (768px+), and desktops (1024px+) equally. Beyond responsive CSS fixes, add mobile-native interactions (pull-to-refresh, swipe navigation, bottom sheets, haptic feedback) and PWA installability.

## Audience & Constraints

- Kids 8+, parent accounts. Mixed device usage — phone, tablet, laptop equally likely.
- Must preserve WCAG 2.2 AA conformance from sub-project 5 (a11y primitives, focus management, reduced-motion support, touch target sizes).
- AADC/COPPA compliance from sub-project 1 unaffected (no new data collection).
- No offline caching — the app requires live API data; PWA is install-only.

---

## 1. Responsive Foundation

### 1.1 Spacing System

Replace blanket `p-6` with `px-4 py-4 sm:px-6 sm:py-6` on all page containers. Affected pages: Home, Lessons, Module, Lesson, Simulator, Market, Stock, Stats, Login, Signup, ForgotPassword, ResetPassword, ParentDashboard, Privacy, VerifyEmail, PendingConsent.

The `mx-auto max-w-*` wrappers remain unchanged.

### 1.2 Viewport & Safe Areas

Verify `index.html` has:
```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

`viewport-fit=cover` enables `env(safe-area-inset-*)` vars. Extend safe-area handling beyond BottomTabBar:
- Shell's `<motion.main>`: add `pl-[env(safe-area-inset-left)] pr-[env(safe-area-inset-right)]` for landscape iPhones.
- TopNav: add `pt-[env(safe-area-inset-top)]` for notch devices in standalone PWA mode.

### 1.3 Touch Targets

Audit all interactive elements for 44×44px minimum (WCAG 2.5.8, already partially enforced in sub-project 5). Fix offenders via `min-h-[44px] min-w-[44px]` or padding. Likely targets:
- BottomTabBar links
- Trade form buttons (Buy/Sell radio, Max, Review)
- Market stock grid cards
- Quiz/Scenario option buttons
- Period selector buttons on StockChart

### 1.4 Breakpoint Strategy

Keep Tailwind defaults: `sm:640px`, `md:768px`, `lg:1024px`. Mobile-first means:
- Base styles → phone (360px+)
- `sm:` → tablet refinements
- `md:` → desktop layout (TopNav appears, BottomTabBar hides)
- `lg:` → wider grids where needed

---

## 2. Component Overhauls

### 2.1 HoldingsTable → Responsive Holdings

Single component, two render modes switched via `useMediaQuery('(min-width: 768px)')`:

**Mobile (< md):** Stacked cards. Each holding is a tappable `<Link>` card:
- Top row: ticker (bold) + exchange badge + P/L with trend icon (right-aligned)
- Bottom row: shares count + avg buy price + market value
- Card styling: `rounded-xl border-2 border-amber-200 bg-white p-3`
- Stack with `space-y-2`

**Desktop (>= md):** Keep existing 6-column `<table>` with horizontal scroll fallback.

### 2.2 Bottom Sheet Primitive

New `components/mobile/BottomSheet.tsx`:
- Slide-up panel from bottom of viewport
- Drag handle at top, drag-to-dismiss gesture (threshold ~100px downward)
- Backdrop overlay with tap-to-dismiss
- `env(safe-area-inset-bottom)` padding
- Framer Motion for enter/exit animation, respects `useReducedMotion`
- Focus trap + `aria-modal="true"` + `role="dialog"` (preserves a11y)

Adaptive rendering: detects viewport via `useMediaQuery`. Below `md:` → bottom sheet. At `md:` and above → delegates to existing Radix Dialog/DropdownMenu.

Wire into:
- **TradeForm** review step → bottom sheet on mobile
- **ChartCoachPanel** → bottom sheet on mobile
- **ProfileMenu** → bottom sheet on mobile (currently Radix DropdownMenu)

### 2.3 Market Stock Grid

Already responsive (`sm:grid-cols-2 lg:grid-cols-3`). Tighten mobile card padding: `p-2 sm:p-3`. Ensure stock link cards meet 44px touch target minimum.

### 2.4 Charts

Recharts `ResponsiveContainer` already handles width. Add:
- Reduced `XAxis`/`YAxis` tick count when container width < 400px (via Recharts `tick` prop or `interval` calculation)
- `ChartDescription` a11y table unchanged

---

## 3. Mobile-Native Interactions

### 3.1 Pull-to-Refresh

New `hooks/usePullToRefresh.ts`:
- Listens for `touchstart` / `touchmove` / `touchend` on the scroll container
- Triggers when pulled down > 60px while `scrollTop === 0`
- Shows a spinner indicator element at top of page (positioned above content, not pushing it down — translates into view)
- Calls React Query `queryClient.refetchQueries({ queryKey })` for relevant keys
- Only active on touch devices (`'ontouchstart' in window`)

Wire into pages:
| Page | Query keys refetched |
|------|---------------------|
| Home | `modules`, `recommendations`, `progress` |
| Market | `market-featured` |
| Simulator | `portfolio`, `trades`, `portfolio/history` |
| Stats | `progress`, `badges`, `challenges`, `leaderboard` |

### 3.2 Swipe Navigation

New `hooks/useSwipeNav.ts`:
- Detects horizontal swipe gestures: threshold ~50px distance, velocity > 0.3px/ms
- Navigates between tabs: Home ↔ Quests ↔ Simulator ↔ Stats
- Only active below `md:` breakpoint
- Page transition: Framer Motion slide-left / slide-right (replaces current fade), respects `useReducedMotion`
- Disabled on pages with their own horizontal scroll (charts, tables) — detect via `event.target` closest scrollable ancestor

Wire into Shell's `<motion.main>` wrapper. The swipe handler attaches to the main content area, not individual pages.

### 3.3 Haptic Feedback

New `hooks/useHaptic.ts`:
- Wraps `navigator.vibrate()` with graceful no-op fallback
- Three intensities:
  - `light` (10ms) — tab switch, option select
  - `medium` (25ms) — trade confirmed, pull-to-refresh complete
  - `heavy` (50ms) — badge earned, level up
- Respects `prefers-reduced-motion` — disable haptics when reduced motion preferred

Call sites:
- `useSwipeNav` → `light` on tab change
- TradeForm `onSuccess` → `medium`
- Pull-to-refresh completion → `medium`
- Badge earned notification → `heavy`
- Level up notification → `heavy`

---

## 4. PWA

### 4.1 Manifest

`public/manifest.json`:
```json
{
  "name": "Invest-Ed",
  "short_name": "Invest-Ed",
  "description": "Learn money skills with virtual investing",
  "display": "standalone",
  "start_url": "/home",
  "scope": "/",
  "theme_color": "#f59e0b",
  "background_color": "#fffbeb",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/icon-192-maskable.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
    { "src": "/icons/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

### 4.2 Icons

Generate via an inline Node script (`scripts/generate-icons.js`) using `<canvas>` (via the `canvas` npm package as a dev dependency, or a simple SVG-to-PNG pipeline). Reproduces the existing "IE" gradient circle (amber-400 → orange-500 linear gradient, white bold text):
- 192×192 and 512×512 regular (transparent background)
- 192×192 and 512×512 maskable (with safe-zone padding per Android spec, amber-50 `#fffbeb` background fill)
- Output to `public/icons/`
- The script runs once during development, not in CI. Icons are committed as static assets.

### 4.3 index.html Additions

```html
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#f59e0b">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="apple-touch-icon" href="/icons/icon-192.png">
```

### 4.4 Service Worker

Minimal `public/sw.js` — just enough to satisfy the browser install prompt:
```js
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
```

Register in `main.tsx`:
```ts
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
```

No caching. No fetch interception. Install-only.

---

## 5. Parent Dashboard Mobile

The parent dashboard (`ParentDashboard.tsx`) has no Shell. For mobile:

- Add a simple sticky header: "IE" logo + "Parent Dashboard" + logout button. Styled consistently with TopNav but without tab navigation.
- Tighten spacing: `px-4 sm:px-6`
- ChildCard action dialogs (premium toggle) use `BottomSheet` on mobile
- No bottom tab bar — single-page dashboard doesn't warrant tab navigation

---

## 6. Testing

### 6.1 Responsive Test Utilities

New `tests/helpers/responsive.ts`:
- `renderMobile(component)` — sets `window.innerWidth = 375`, mocks `matchMedia` to return `false` for `(min-width: 768px)` queries
- `renderTablet(component)` — 768px
- `renderDesktop(component)` — 1024px
- `mockTouchDevice()` — adds `ontouchstart` to window, returns cleanup function

### 6.2 Unit Tests

| Component/Hook | Assertions |
|---------------|------------|
| Holdings responsive | Cards on mobile, table on desktop |
| BottomSheet | Sheet on mobile, dialog on desktop |
| ProfileMenu | Bottom sheet on mobile, dropdown on desktop |
| usePullToRefresh | Fires callback after sufficient pull; no-ops on non-touch |
| useSwipeNav | Navigates on horizontal swipe; ignores vertical; disabled on desktop |
| useHaptic | Calls `navigator.vibrate` when available; no-ops when missing; respects reduced-motion |
| useMediaQuery | Returns correct boolean for given query |

### 6.3 Playwright Viewport Tests

New `tests/e2e/responsive.spec.ts`:
- Run key flows (login → home → market → stock → trade) at 375px, 768px, 1024px
- Assert no horizontal overflow: `scrollWidth <= innerWidth`
- Assert BottomTabBar visible at 375px, hidden at 1024px
- Assert TopNav desktop links hidden at 375px, visible at 1024px

### 6.4 CI

New `responsive` job in `.github/workflows/ci.yml` (or extend existing `a11y` job):
- `npm ci --legacy-peer-deps`
- `npx vitest run` (responsive-related tests)
- `npx playwright install --with-deps chromium`
- `npx playwright test responsive`

---

## Out of Scope

- Offline caching / sync
- Native app wrappers (Capacitor, React Native)
- Dark mode
- Stripe/payments (deferred to sub-project 7)
- OPEN-1 brand contrast fix (separate concern from sub-project 5)

## Dependencies

- `framer-motion` (already installed) — bottom sheet animations, swipe nav transitions
- No new npm dependencies anticipated. `useMediaQuery`, pull-to-refresh, swipe detection, haptics are all vanilla hooks using browser APIs.
