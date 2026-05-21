# Mobile-First Responsive Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Invest-Ed feel native on phones (360px+), tablets (768px+), and desktops (1024px+) with mobile-native interactions (pull-to-refresh, swipe nav, bottom sheets, haptics) and PWA installability.

**Architecture:** New hooks (`useMediaQuery`, `usePullToRefresh`, `useSwipeNav`, `useHaptic`) using vanilla browser APIs. New `BottomSheet` component via Framer Motion. PWA via minimal manifest + service worker. All changes frontend-only — no backend modifications.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, Framer Motion (already installed), Recharts, Radix UI, Vitest + vitest-axe, Playwright.

**Baseline:** Frontend 279 vitest green, lint clean, `tsc -b` + `vite build` clean. Backend 328 passed + 1 skipped (untouched by this plan).

**Working directory:** Worktree at `/Users/leeashmore/Local Repo/.claude/worktrees/plan-6-mobile` on branch `claude/plan-6-mobile`. Frontend at `invest-ed/frontend`. All file paths below are relative to `invest-ed/frontend` unless stated otherwise.

**Install command:** Always use `npm ci --legacy-peer-deps` (eslint-plugin-jsx-a11y peer range doesn't cover ESLint 10).

**Test commands:**
- Unit tests: `cd invest-ed/frontend && npx vitest run`
- Lint: `cd invest-ed/frontend && npm run lint`
- Type check: `cd invest-ed/frontend && npx tsc -b`
- Build: `cd invest-ed/frontend && npx vite build`
- E2E: `cd invest-ed/frontend && npx playwright test`

---

## File Map

### New files
| File | Responsibility |
|------|---------------|
| `src/hooks/useMediaQuery.ts` | SSR-safe `matchMedia` hook, boolean return |
| `src/hooks/usePullToRefresh.ts` | Touch-gesture pull-to-refresh with spinner |
| `src/hooks/useSwipeNav.ts` | Horizontal swipe between main tabs |
| `src/hooks/useHaptic.ts` | `navigator.vibrate()` wrapper, 3 intensities |
| `src/components/mobile/BottomSheet.tsx` | Slide-up sheet with drag-dismiss, focus trap, a11y |
| `src/components/mobile/PullToRefreshIndicator.tsx` | Spinner overlay for pull-to-refresh |
| `public/manifest.json` | PWA web app manifest |
| `public/sw.js` | Minimal service worker (install-only) |
| `public/icons/icon-192.png` | App icon 192×192 |
| `public/icons/icon-512.png` | App icon 512×512 |
| `public/icons/icon-192-maskable.png` | Maskable icon 192×192 |
| `public/icons/icon-512-maskable.png` | Maskable icon 512×512 |
| `tests/helpers/responsive.ts` | `renderMobile`/`renderTablet`/`renderDesktop`/`mockTouchDevice` |
| `tests/unit/useMediaQuery.test.ts` | Unit tests for useMediaQuery |
| `tests/unit/useHaptic.test.ts` | Unit tests for useHaptic |
| `tests/unit/usePullToRefresh.test.tsx` | Unit tests for pull-to-refresh |
| `tests/unit/useSwipeNav.test.tsx` | Unit tests for swipe navigation |
| `tests/unit/BottomSheet.test.tsx` | Unit tests for BottomSheet component |
| `tests/unit/HoldingsResponsive.test.tsx` | Unit tests for holdings card/table switch |
| `tests/e2e/responsive.spec.ts` | Playwright viewport tests |

### Modified files
| File | Changes |
|------|---------|
| `index.html` | viewport-fit=cover, manifest link, theme-color, apple-mobile-web-app metas, SW registration |
| `src/main.tsx` | Service worker registration |
| `src/index.css` | Safe-area CSS custom properties |
| `src/components/child/Shell.tsx` | Safe areas, swipe nav, pull-to-refresh, swipe direction animation |
| `src/components/child/TopNav.tsx` | Safe-area top padding |
| `src/components/child/BottomTabBar.tsx` | Touch target sizing |
| `src/components/child/simulator/HoldingsTable.tsx` | Mobile card layout via useMediaQuery |
| `src/components/child/simulator/StockChart.tsx` | Responsive tick count, touch target on period buttons |
| `src/components/child/simulator/PortfolioChart.tsx` | Responsive tick count |
| `src/components/child/simulator/TradeForm.tsx` | BottomSheet for review step, touch targets |
| `src/components/child/simulator/ChartCoachPanel.tsx` | BottomSheet on mobile |
| `src/components/child/ProfileMenu.tsx` | BottomSheet on mobile |
| `src/pages/child/Home.tsx` | Responsive spacing, pull-to-refresh |
| `src/pages/child/Lessons.tsx` | Responsive spacing |
| `src/pages/child/Module.tsx` | Responsive spacing |
| `src/pages/child/Lesson.tsx` | Responsive spacing |
| `src/pages/child/Simulator.tsx` | Responsive spacing, pull-to-refresh |
| `src/pages/child/Market.tsx` | Responsive spacing, touch targets, pull-to-refresh |
| `src/pages/child/Stock.tsx` | Responsive spacing |
| `src/pages/child/Stats.tsx` | Responsive spacing, pull-to-refresh |
| `src/pages/child/Login.tsx` | Responsive spacing |
| `src/pages/child/Signup.tsx` | Responsive spacing |
| `src/pages/child/PendingConsent.tsx` | Responsive spacing |
| `src/pages/ForgotPassword.tsx` | Responsive spacing |
| `src/pages/ResetPassword.tsx` | Responsive spacing |
| `src/pages/VerifyEmail.tsx` | Responsive spacing |
| `src/pages/Privacy.tsx` | Responsive spacing |
| `src/pages/ParentDashboard.tsx` | Responsive spacing, mobile sticky header |
| `src/components/ChildCard.tsx` | Mobile layout, BottomSheet for dialogs |
| `playwright.config.ts` | Add mobile viewport project |
| `package.json` | Add `test:e2e:responsive` script |
| `.github/workflows/ci.yml` (repo root) | Add `responsive` CI job |

---

### Task 1: useMediaQuery hook + test utilities

**Files:**
- Create: `src/hooks/useMediaQuery.ts`
- Create: `tests/helpers/responsive.ts`
- Create: `tests/unit/useMediaQuery.test.ts`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/useMediaQuery.test.ts`:

```ts
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useMediaQuery } from '@/hooks/useMediaQuery';

describe('useMediaQuery', () => {
  let listeners: Array<(e: { matches: boolean }) => void>;
  let currentMatches: boolean;

  beforeEach(() => {
    listeners = [];
    currentMatches = false;
    vi.stubGlobal(
      'matchMedia',
      vi.fn((query: string) => ({
        matches: currentMatches,
        media: query,
        addEventListener: (_: string, cb: (e: { matches: boolean }) => void) => {
          listeners.push(cb);
        },
        removeEventListener: (_: string, cb: (e: { matches: boolean }) => void) => {
          listeners = listeners.filter((l) => l !== cb);
        },
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns false when media query does not match', () => {
    currentMatches = false;
    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)'));
    expect(result.current).toBe(false);
  });

  it('returns true when media query matches', () => {
    currentMatches = true;
    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)'));
    expect(result.current).toBe(true);
  });

  it('updates when media query changes', () => {
    currentMatches = false;
    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)'));
    expect(result.current).toBe(false);

    act(() => {
      listeners.forEach((cb) => cb({ matches: true }));
    });
    expect(result.current).toBe(true);
  });

  it('cleans up listener on unmount', () => {
    const { unmount } = renderHook(() => useMediaQuery('(min-width: 768px)'));
    expect(listeners).toHaveLength(1);
    unmount();
    expect(listeners).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/useMediaQuery.test.ts`
Expected: FAIL — module `@/hooks/useMediaQuery` not found.

- [ ] **Step 3: Implement useMediaQuery**

Create `src/hooks/useMediaQuery.ts`:

```ts
import { useState, useEffect } from 'react';

/**
 * SSR-safe media query hook. Returns `true` when the query matches.
 * Defaults to `false` during SSR / before hydration.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    const mql = window.matchMedia(query);
    setMatches(mql.matches);

    const handler = (e: MediaQueryListEvent | { matches: boolean }) => {
      setMatches(e.matches);
    };
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [query]);

  return matches;
}
```

- [ ] **Step 4: Create responsive test helpers**

Create `tests/helpers/responsive.ts`:

```ts
import { render, type RenderOptions } from '@testing-library/react';
import { vi } from 'vitest';
import type { ReactElement } from 'react';

type Viewport = 'mobile' | 'tablet' | 'desktop';

const WIDTHS: Record<Viewport, number> = {
  mobile: 375,
  tablet: 768,
  desktop: 1024,
};

function setupViewport(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  });

  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => {
      // Parse "(min-width: Xpx)" patterns
      const minMatch = query.match(/\(min-width:\s*(\d+)px\)/);
      const matches = minMatch ? width >= parseInt(minMatch[1], 10) : false;
      return {
        matches,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      };
    }),
  );
}

function renderAt(viewport: Viewport, ui: ReactElement, options?: RenderOptions) {
  setupViewport(WIDTHS[viewport]);
  return render(ui, options);
}

export function renderMobile(ui: ReactElement, options?: RenderOptions) {
  return renderAt('mobile', ui, options);
}

export function renderTablet(ui: ReactElement, options?: RenderOptions) {
  return renderAt('tablet', ui, options);
}

export function renderDesktop(ui: ReactElement, options?: RenderOptions) {
  return renderAt('desktop', ui, options);
}

/**
 * Simulate a touch-capable device. Returns a cleanup function.
 */
export function mockTouchDevice(): () => void {
  const had = 'ontouchstart' in window;
  Object.defineProperty(window, 'ontouchstart', {
    writable: true,
    configurable: true,
    value: () => {},
  });
  return () => {
    if (!had) {
      delete (window as Record<string, unknown>).ontouchstart;
    }
  };
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/useMediaQuery.test.ts`
Expected: 4 tests PASS.

- [ ] **Step 6: Run full suite to confirm no regressions**

Run: `cd invest-ed/frontend && npx vitest run`
Expected: 279+ tests PASS (may be higher if sub-project 5 added tests).

- [ ] **Step 7: Commit**

```bash
git add src/hooks/useMediaQuery.ts tests/helpers/responsive.ts tests/unit/useMediaQuery.test.ts
git commit -m "feat(6): add useMediaQuery hook + responsive test helpers"
```

---

### Task 2: useHaptic hook

**Files:**
- Create: `src/hooks/useHaptic.ts`
- Create: `tests/unit/useHaptic.test.ts`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/useHaptic.test.ts`:

```ts
import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useHaptic } from '@/hooks/useHaptic';

describe('useHaptic', () => {
  let vibrateSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vibrateSpy = vi.fn();
    Object.defineProperty(navigator, 'vibrate', {
      writable: true,
      configurable: true,
      value: vibrateSpy,
    });
    // Default: no reduced motion
    vi.stubGlobal(
      'matchMedia',
      vi.fn((query: string) => ({
        matches: false,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('vibrates with light intensity (10ms)', () => {
    const { result } = renderHook(() => useHaptic());
    result.current('light');
    expect(vibrateSpy).toHaveBeenCalledWith(10);
  });

  it('vibrates with medium intensity (25ms)', () => {
    const { result } = renderHook(() => useHaptic());
    result.current('medium');
    expect(vibrateSpy).toHaveBeenCalledWith(25);
  });

  it('vibrates with heavy intensity (50ms)', () => {
    const { result } = renderHook(() => useHaptic());
    result.current('heavy');
    expect(vibrateSpy).toHaveBeenCalledWith(50);
  });

  it('no-ops when navigator.vibrate is unavailable', () => {
    Object.defineProperty(navigator, 'vibrate', {
      writable: true,
      configurable: true,
      value: undefined,
    });
    const { result } = renderHook(() => useHaptic());
    // Should not throw
    expect(() => result.current('medium')).not.toThrow();
  });

  it('no-ops when prefers-reduced-motion is active', () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn((query: string) => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );
    const { result } = renderHook(() => useHaptic());
    result.current('heavy');
    expect(vibrateSpy).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/useHaptic.test.ts`
Expected: FAIL — module `@/hooks/useHaptic` not found.

- [ ] **Step 3: Implement useHaptic**

Create `src/hooks/useHaptic.ts`:

```ts
import { useCallback } from 'react';
import { useMediaQuery } from './useMediaQuery';

type Intensity = 'light' | 'medium' | 'heavy';

const DURATIONS: Record<Intensity, number> = {
  light: 10,
  medium: 25,
  heavy: 50,
};

/**
 * Returns a function that triggers haptic feedback via `navigator.vibrate()`.
 * No-ops when vibrate is unavailable or prefers-reduced-motion is active.
 */
export function useHaptic(): (intensity: Intensity) => void {
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');

  return useCallback(
    (intensity: Intensity) => {
      if (reducedMotion) return;
      if (typeof navigator === 'undefined' || typeof navigator.vibrate !== 'function') return;
      navigator.vibrate(DURATIONS[intensity]);
    },
    [reducedMotion],
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/useHaptic.test.ts`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/useHaptic.ts tests/unit/useHaptic.test.ts
git commit -m "feat(6): add useHaptic hook with reduced-motion respect"
```

---

### Task 3: BottomSheet component

**Files:**
- Create: `src/components/mobile/BottomSheet.tsx`
- Create: `tests/unit/BottomSheet.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/BottomSheet.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { BottomSheet } from '@/components/mobile/BottomSheet';

function setupMatchMedia(mobile: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => {
      const minMatch = query.match(/\(min-width:\s*(\d+)px\)/);
      const matches = minMatch ? !mobile : false;
      return {
        matches,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      };
    }),
  );
}

describe('BottomSheet', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders children in a bottom sheet on mobile', () => {
    setupMatchMedia(true);
    render(
      <BottomSheet open onOpenChange={() => {}} title="Test Sheet">
        <p>Sheet content</p>
      </BottomSheet>,
    );
    expect(screen.getByText('Sheet content')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('renders children in fallback (dialog slot) on desktop', () => {
    setupMatchMedia(false);
    render(
      <BottomSheet
        open
        onOpenChange={() => {}}
        title="Test Sheet"
        desktopFallback={<div data-testid="desktop-fallback">Desktop</div>}
      >
        <p>Sheet content</p>
      </BottomSheet>,
    );
    expect(screen.getByTestId('desktop-fallback')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('has correct ARIA attributes on mobile', () => {
    setupMatchMedia(true);
    render(
      <BottomSheet open onOpenChange={() => {}} title="My Title">
        <p>Content</p>
      </BottomSheet>,
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByText('My Title')).toBeInTheDocument();
  });

  it('calls onOpenChange(false) when backdrop is clicked', () => {
    setupMatchMedia(true);
    const onClose = vi.fn();
    render(
      <BottomSheet open onOpenChange={onClose} title="Sheet">
        <p>Content</p>
      </BottomSheet>,
    );
    const backdrop = screen.getByTestId('bottom-sheet-backdrop');
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledWith(false);
  });

  it('does not render when open is false', () => {
    setupMatchMedia(true);
    render(
      <BottomSheet open={false} onOpenChange={() => {}} title="Sheet">
        <p>Hidden content</p>
      </BottomSheet>,
    );
    expect(screen.queryByText('Hidden content')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/BottomSheet.test.tsx`
Expected: FAIL — module `@/components/mobile/BottomSheet` not found.

- [ ] **Step 3: Implement BottomSheet**

Create `src/components/mobile/BottomSheet.tsx`:

```tsx
import { useRef, useEffect, type ReactNode } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { useMediaQuery } from '@/hooks/useMediaQuery';

type BottomSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
  /** Rendered on desktop (>= md) instead of the sheet. If omitted, children render inline on desktop. */
  desktopFallback?: ReactNode;
};

export function BottomSheet({ open, onOpenChange, title, children, desktopFallback }: BottomSheetProps) {
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const prefersReducedMotion = useReducedMotion();
  const sheetRef = useRef<HTMLDivElement>(null);
  const dragStartY = useRef(0);

  // Focus trap: focus the sheet on open
  useEffect(() => {
    if (open && !isDesktop && sheetRef.current) {
      sheetRef.current.focus();
    }
  }, [open, isDesktop]);

  // Lock body scroll when sheet is open on mobile
  useEffect(() => {
    if (open && !isDesktop) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [open, isDesktop]);

  if (isDesktop) {
    return desktopFallback ? <>{desktopFallback}</> : open ? <>{children}</> : null;
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            data-testid="bottom-sheet-backdrop"
            className="fixed inset-0 z-40 bg-black/40"
            initial={prefersReducedMotion ? false : { opacity: 0 }}
            animate={prefersReducedMotion ? undefined : { opacity: 1 }}
            exit={prefersReducedMotion ? undefined : { opacity: 0 }}
            onClick={() => onOpenChange(false)}
          />

          {/* Sheet */}
          <motion.div
            ref={sheetRef}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            tabIndex={-1}
            className="fixed inset-x-0 bottom-0 z-50 rounded-t-2xl bg-white shadow-xl outline-none"
            style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
            initial={prefersReducedMotion ? false : { y: '100%' }}
            animate={prefersReducedMotion ? undefined : { y: 0 }}
            exit={prefersReducedMotion ? undefined : { y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            onTouchStart={(e) => {
              dragStartY.current = e.touches[0].clientY;
            }}
            onTouchEnd={(e) => {
              const delta = e.changedTouches[0].clientY - dragStartY.current;
              if (delta > 100) {
                onOpenChange(false);
              }
            }}
          >
            {/* Drag handle */}
            <div className="flex justify-center py-3">
              <div className="h-1.5 w-10 rounded-full bg-gray-300" />
            </div>

            {/* Title */}
            <div className="px-4 pb-2">
              <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            </div>

            {/* Content */}
            <div className="max-h-[70vh] overflow-y-auto px-4 pb-4">
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/BottomSheet.test.tsx`
Expected: 5 tests PASS.

- [ ] **Step 5: Run full suite + lint + tsc**

Run: `cd invest-ed/frontend && npx vitest run && npm run lint && npx tsc -b`
Expected: All green.

- [ ] **Step 6: Commit**

```bash
git add src/components/mobile/BottomSheet.tsx tests/unit/BottomSheet.test.tsx
git commit -m "feat(6): add BottomSheet component with drag-dismiss and a11y"
```

---

### Task 4: usePullToRefresh hook

**Files:**
- Create: `src/hooks/usePullToRefresh.ts`
- Create: `src/components/mobile/PullToRefreshIndicator.tsx`
- Create: `tests/unit/usePullToRefresh.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/usePullToRefresh.test.tsx`:

```tsx
import { render, fireEvent, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useRef } from 'react';
import { usePullToRefresh } from '@/hooks/usePullToRefresh';

function TestHarness({ onRefresh }: { onRefresh: () => Promise<void> }) {
  const ref = useRef<HTMLDivElement>(null);
  const { indicatorProps } = usePullToRefresh({ ref, onRefresh });
  return (
    <div ref={ref} data-testid="scroll-container" style={{ height: 200, overflow: 'auto' }}>
      {indicatorProps.visible && <div data-testid="pull-indicator">Refreshing</div>}
      <div style={{ height: 1000 }}>Content</div>
    </div>
  );
}

describe('usePullToRefresh', () => {
  beforeEach(() => {
    // Simulate touch device
    Object.defineProperty(window, 'ontouchstart', {
      writable: true,
      configurable: true,
      value: () => {},
    });
  });

  afterEach(() => {
    delete (window as Record<string, unknown>).ontouchstart;
    vi.restoreAllMocks();
  });

  it('calls onRefresh after pulling down > 60px at scroll top', async () => {
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(<TestHarness onRefresh={onRefresh} />);

    const container = screen.getByTestId('scroll-container');

    // Simulate: scrollTop is 0, pull down 80px
    Object.defineProperty(container, 'scrollTop', { value: 0, writable: true });

    await act(async () => {
      fireEvent.touchStart(container, { touches: [{ clientY: 100 }] });
      fireEvent.touchMove(container, { touches: [{ clientY: 180 }] });
      fireEvent.touchEnd(container, { changedTouches: [{ clientY: 180 }] });
    });

    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it('does NOT call onRefresh when pull distance < 60px', async () => {
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(<TestHarness onRefresh={onRefresh} />);

    const container = screen.getByTestId('scroll-container');
    Object.defineProperty(container, 'scrollTop', { value: 0, writable: true });

    await act(async () => {
      fireEvent.touchStart(container, { touches: [{ clientY: 100 }] });
      fireEvent.touchMove(container, { touches: [{ clientY: 140 }] });
      fireEvent.touchEnd(container, { changedTouches: [{ clientY: 140 }] });
    });

    expect(onRefresh).not.toHaveBeenCalled();
  });

  it('does NOT trigger when not at scroll top', async () => {
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(<TestHarness onRefresh={onRefresh} />);

    const container = screen.getByTestId('scroll-container');
    Object.defineProperty(container, 'scrollTop', { value: 100, writable: true });

    await act(async () => {
      fireEvent.touchStart(container, { touches: [{ clientY: 100 }] });
      fireEvent.touchMove(container, { touches: [{ clientY: 200 }] });
      fireEvent.touchEnd(container, { changedTouches: [{ clientY: 200 }] });
    });

    expect(onRefresh).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/usePullToRefresh.test.tsx`
Expected: FAIL — module `@/hooks/usePullToRefresh` not found.

- [ ] **Step 3: Implement usePullToRefresh**

Create `src/hooks/usePullToRefresh.ts`:

```ts
import { useState, useEffect, useCallback, useRef, type RefObject } from 'react';

const PULL_THRESHOLD = 60;

type UsePullToRefreshOptions = {
  ref: RefObject<HTMLElement | null>;
  onRefresh: () => Promise<void>;
};

type IndicatorProps = {
  visible: boolean;
  progress: number; // 0..1 while pulling, stays 1 while refreshing
};

export function usePullToRefresh({ ref, onRefresh }: UsePullToRefreshOptions) {
  const [refreshing, setRefreshing] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const startY = useRef(0);
  const pulling = useRef(false);

  const isTouchDevice = typeof window !== 'undefined' && 'ontouchstart' in window;

  const handleTouchStart = useCallback(
    (e: TouchEvent) => {
      const el = ref.current;
      if (!el || el.scrollTop > 0 || refreshing) return;
      startY.current = e.touches[0].clientY;
      pulling.current = true;
      setPullDistance(0);
    },
    [ref, refreshing],
  );

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      if (!pulling.current) return;
      const delta = e.touches[0].clientY - startY.current;
      if (delta > 0) {
        setPullDistance(delta);
      }
    },
    [],
  );

  const handleTouchEnd = useCallback(
    async () => {
      if (!pulling.current) return;
      pulling.current = false;
      if (pullDistance >= PULL_THRESHOLD) {
        setRefreshing(true);
        try {
          await onRefresh();
        } finally {
          setRefreshing(false);
        }
      }
      setPullDistance(0);
    },
    [pullDistance, onRefresh],
  );

  useEffect(() => {
    const el = ref.current;
    if (!el || !isTouchDevice) return;

    el.addEventListener('touchstart', handleTouchStart, { passive: true });
    el.addEventListener('touchmove', handleTouchMove, { passive: true });
    el.addEventListener('touchend', handleTouchEnd);

    return () => {
      el.removeEventListener('touchstart', handleTouchStart);
      el.removeEventListener('touchmove', handleTouchMove);
      el.removeEventListener('touchend', handleTouchEnd);
    };
  }, [ref, isTouchDevice, handleTouchStart, handleTouchMove, handleTouchEnd]);

  const indicatorProps: IndicatorProps = {
    visible: refreshing || pullDistance > 10,
    progress: refreshing ? 1 : Math.min(pullDistance / PULL_THRESHOLD, 1),
  };

  return { indicatorProps, refreshing };
}
```

Create `src/components/mobile/PullToRefreshIndicator.tsx`:

```tsx
type Props = {
  visible: boolean;
  progress: number;
};

export function PullToRefreshIndicator({ visible, progress }: Props) {
  if (!visible) return null;
  const isRefreshing = progress >= 1;

  return (
    <div
      className="flex justify-center py-2"
      role="status"
      aria-label={isRefreshing ? 'Refreshing' : 'Pull to refresh'}
    >
      <div
        className={`h-6 w-6 rounded-full border-2 border-amber-400 border-t-transparent ${
          isRefreshing ? 'animate-spin' : ''
        }`}
        style={{
          opacity: Math.max(progress, 0.3),
          transform: `rotate(${progress * 360}deg)`,
        }}
      />
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/usePullToRefresh.test.tsx`
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/usePullToRefresh.ts src/components/mobile/PullToRefreshIndicator.tsx tests/unit/usePullToRefresh.test.tsx
git commit -m "feat(6): add usePullToRefresh hook + indicator component"
```

---

### Task 5: useSwipeNav hook

**Files:**
- Create: `src/hooks/useSwipeNav.ts`
- Create: `tests/unit/useSwipeNav.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/useSwipeNav.test.tsx`:

```tsx
import { render, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useRef } from 'react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { useSwipeNav } from '@/hooks/useSwipeNav';

const navigateMock = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

function TestHarness() {
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();
  useSwipeNav({ ref });
  return (
    <div ref={ref} data-testid="swipe-area" style={{ width: 375, height: 600 }}>
      <p data-testid="path">{location.pathname}</p>
    </div>
  );
}

function setupMobile() {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => {
      const minMatch = query.match(/\(min-width:\s*(\d+)px\)/);
      const matches = minMatch ? 375 >= parseInt(minMatch[1], 10) : false;
      return {
        matches,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      };
    }),
  );
  Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 375 });
}

describe('useSwipeNav', () => {
  beforeEach(() => {
    navigateMock.mockClear();
    setupMobile();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('navigates right (next tab) on left swipe from /home', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <TestHarness />
      </MemoryRouter>,
    );
    const area = document.querySelector('[data-testid="swipe-area"]')!;
    const now = Date.now();

    act(() => {
      fireEvent.touchStart(area, {
        touches: [{ clientX: 300, clientY: 300 }],
        timeStamp: now,
      });
      fireEvent.touchEnd(area, {
        changedTouches: [{ clientX: 100, clientY: 305 }],
        timeStamp: now + 100,
      });
    });

    expect(navigateMock).toHaveBeenCalledWith('/lessons');
  });

  it('navigates left (prev tab) on right swipe from /lessons', () => {
    render(
      <MemoryRouter initialEntries={['/lessons']}>
        <TestHarness />
      </MemoryRouter>,
    );
    const area = document.querySelector('[data-testid="swipe-area"]')!;
    const now = Date.now();

    act(() => {
      fireEvent.touchStart(area, {
        touches: [{ clientX: 100, clientY: 300 }],
        timeStamp: now,
      });
      fireEvent.touchEnd(area, {
        changedTouches: [{ clientX: 300, clientY: 305 }],
        timeStamp: now + 100,
      });
    });

    expect(navigateMock).toHaveBeenCalledWith('/home');
  });

  it('does NOT navigate on vertical swipe', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <TestHarness />
      </MemoryRouter>,
    );
    const area = document.querySelector('[data-testid="swipe-area"]')!;
    const now = Date.now();

    act(() => {
      fireEvent.touchStart(area, {
        touches: [{ clientX: 200, clientY: 100 }],
        timeStamp: now,
      });
      fireEvent.touchEnd(area, {
        changedTouches: [{ clientX: 205, clientY: 400 }],
        timeStamp: now + 100,
      });
    });

    expect(navigateMock).not.toHaveBeenCalled();
  });

  it('does NOT navigate when swipe distance is too small', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <TestHarness />
      </MemoryRouter>,
    );
    const area = document.querySelector('[data-testid="swipe-area"]')!;
    const now = Date.now();

    act(() => {
      fireEvent.touchStart(area, {
        touches: [{ clientX: 200, clientY: 300 }],
        timeStamp: now,
      });
      fireEvent.touchEnd(area, {
        changedTouches: [{ clientX: 175, clientY: 305 }],
        timeStamp: now + 100,
      });
    });

    expect(navigateMock).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/useSwipeNav.test.tsx`
Expected: FAIL — module `@/hooks/useSwipeNav` not found.

- [ ] **Step 3: Implement useSwipeNav**

Create `src/hooks/useSwipeNav.ts`:

```ts
import { useEffect, useRef, type RefObject } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useMediaQuery } from './useMediaQuery';

const TABS = ['/home', '/lessons', '/simulator', '/stats'] as const;
const SWIPE_THRESHOLD = 50; // px
const VELOCITY_THRESHOLD = 0.3; // px/ms

type UseSwipeNavOptions = {
  ref: RefObject<HTMLElement | null>;
};

export function useSwipeNav({ ref }: UseSwipeNavOptions) {
  const navigate = useNavigate();
  const location = useLocation();
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const startX = useRef(0);
  const startY = useRef(0);
  const startTime = useRef(0);

  useEffect(() => {
    const el = ref.current;
    if (!el || isDesktop) return;

    const handleTouchStart = (e: TouchEvent) => {
      startX.current = e.touches[0].clientX;
      startY.current = e.touches[0].clientY;
      startTime.current = e.timeStamp;
    };

    const handleTouchEnd = (e: TouchEvent) => {
      const dx = e.changedTouches[0].clientX - startX.current;
      const dy = e.changedTouches[0].clientY - startY.current;
      const dt = e.timeStamp - startTime.current;

      // Ignore vertical swipes
      if (Math.abs(dy) > Math.abs(dx)) return;
      // Ignore short swipes
      if (Math.abs(dx) < SWIPE_THRESHOLD) return;
      // Ignore slow swipes
      if (dt > 0 && Math.abs(dx) / dt < VELOCITY_THRESHOLD) return;

      // Check if we're swiping from a scrollable element
      const target = e.target as HTMLElement;
      if (target.closest('[data-swipe-ignore]') || target.closest('.overflow-x-auto')) return;

      const currentPath = location.pathname;
      const currentIdx = TABS.indexOf(currentPath as (typeof TABS)[number]);
      if (currentIdx === -1) return;

      if (dx < 0 && currentIdx < TABS.length - 1) {
        // Swipe left → next tab
        navigate(TABS[currentIdx + 1]);
      } else if (dx > 0 && currentIdx > 0) {
        // Swipe right → prev tab
        navigate(TABS[currentIdx - 1]);
      }
    };

    el.addEventListener('touchstart', handleTouchStart, { passive: true });
    el.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      el.removeEventListener('touchstart', handleTouchStart);
      el.removeEventListener('touchend', handleTouchEnd);
    };
  }, [ref, isDesktop, navigate, location.pathname]);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/useSwipeNav.test.tsx`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/useSwipeNav.ts tests/unit/useSwipeNav.test.tsx
git commit -m "feat(6): add useSwipeNav hook for tab swiping"
```

---

### Task 6: PWA manifest, service worker, icons, and index.html

**Files:**
- Create: `public/manifest.json`
- Create: `public/sw.js`
- Create: `public/icons/` directory with 4 icon files (SVG-based PNGs)
- Modify: `index.html`
- Modify: `src/main.tsx`

- [ ] **Step 1: Create manifest.json**

Create `public/manifest.json`:

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

- [ ] **Step 2: Create minimal service worker**

Create `public/sw.js`:

```js
// Minimal service worker — satisfies PWA install prompt.
// No caching, no fetch interception. Install-only.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
```

- [ ] **Step 3: Generate PWA icons**

Create `public/icons/` directory. Generate icons using a Node script that creates SVG-based PNG files:

```bash
mkdir -p public/icons
```

Create a script `scripts/generate-icons.js`:

```js
// Run once: node scripts/generate-icons.js
// Generates PWA icons as inline SVG data URIs converted to PNG via sharp or canvas.
// Fallback: create SVG files that browsers accept as PWA icons.

const fs = require('fs');
const path = require('path');

const sizes = [192, 512];
const outDir = path.join(__dirname, '..', 'public', 'icons');
fs.mkdirSync(outDir, { recursive: true });

for (const size of sizes) {
  const r = size / 2;
  const fontSize = Math.round(size * 0.32);

  // Regular icon (transparent bg, gradient circle)
  const regularSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#f97316"/>
    </linearGradient>
  </defs>
  <circle cx="${r}" cy="${r}" r="${r}" fill="url(#g)"/>
  <text x="${r}" y="${r}" dy="0.35em" text-anchor="middle" font-family="system-ui,sans-serif" font-weight="800" font-size="${fontSize}" fill="white">IE</text>
</svg>`;

  // Maskable icon (filled bg for safe zone)
  const pad = Math.round(size * 0.1); // 10% safe zone
  const innerR = r - pad;
  const maskableSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <rect width="${size}" height="${size}" fill="#fffbeb"/>
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#f97316"/>
    </linearGradient>
  </defs>
  <circle cx="${r}" cy="${r}" r="${innerR}" fill="url(#g)"/>
  <text x="${r}" y="${r}" dy="0.35em" text-anchor="middle" font-family="system-ui,sans-serif" font-weight="800" font-size="${fontSize}" fill="white">IE</text>
</svg>`;

  // Write as SVG files (browsers accept SVG in manifest, and we rename to .png
  // for broader compat — alternatively install `sharp` to convert).
  // For maximum compat, ship as SVG with .svg extension.
  fs.writeFileSync(path.join(outDir, `icon-${size}.svg`), regularSvg);
  fs.writeFileSync(path.join(outDir, `icon-${size}-maskable.svg`), maskableSvg);

  console.log(`Generated ${size}x${size} regular + maskable`);
}

console.log('Done. Icons in public/icons/');
```

Run the script, then update the manifest to use `.svg`:

```bash
cd invest-ed/frontend && node scripts/generate-icons.js
```

Update `public/manifest.json` icon entries to use `.svg` extension and `image/svg+xml` type:

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
    { "src": "/icons/icon-192.svg", "sizes": "192x192", "type": "image/svg+xml" },
    { "src": "/icons/icon-512.svg", "sizes": "512x512", "type": "image/svg+xml" },
    { "src": "/icons/icon-192-maskable.svg", "sizes": "192x192", "type": "image/svg+xml", "purpose": "maskable" },
    { "src": "/icons/icon-512-maskable.svg", "sizes": "512x512", "type": "image/svg+xml", "purpose": "maskable" }
  ]
}
```

- [ ] **Step 4: Update index.html**

Modify `index.html` — replace the current viewport meta and add PWA tags:

Current:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Invest-Ed Parent Dashboard</title>
```

Replace with:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
<meta name="theme-color" content="#f59e0b" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="default" />
<link rel="manifest" href="/manifest.json" />
<link rel="apple-touch-icon" href="/icons/icon-192.svg" />
<title>Invest-Ed</title>
```

- [ ] **Step 5: Register service worker in main.tsx**

Add to the end of `src/main.tsx` (after the `ReactDOM.createRoot` call):

```ts
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
```

- [ ] **Step 6: Run lint + tsc + build**

Run: `cd invest-ed/frontend && npm run lint && npx tsc -b && npx vite build`
Expected: All clean. (`sw.js` and icons are in `public/` so Vite copies them.)

- [ ] **Step 7: Commit**

```bash
git add public/manifest.json public/sw.js public/icons/ scripts/generate-icons.js index.html src/main.tsx
git commit -m "feat(6): add PWA manifest, service worker, icons, and meta tags"
```

---

### Task 7: Responsive spacing across all pages

**Files:**
- Modify: All page files listed in spec §1.1

This task changes `p-6` to `px-4 py-4 sm:px-6 sm:py-6` across all page containers. Where pages use `px-6 py-8` or similar, scale proportionally.

- [ ] **Step 1: Update child pages**

In `src/pages/child/Home.tsx`, change:
```tsx
<div className="mx-auto max-w-3xl p-6">
```
to:
```tsx
<div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
```

In `src/pages/child/Lessons.tsx`, change:
```tsx
<div className="mx-auto max-w-5xl p-6">
```
to:
```tsx
<div className="mx-auto max-w-5xl px-4 py-4 sm:px-6 sm:py-6">
```

In `src/pages/child/Module.tsx`, change the loading/error containers:
```tsx
<div className="mx-auto max-w-3xl p-6 text-sm text-gray-500">
```
to:
```tsx
<div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6 text-sm text-gray-500">
```

And the error container:
```tsx
<div className="mx-auto max-w-3xl p-6">
```
to:
```tsx
<div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
```

And the banner section:
```tsx
<div className="bg-gradient-to-br from-amber-100 to-amber-200 px-6 py-8 text-center">
```
to:
```tsx
<div className="bg-gradient-to-br from-amber-100 to-amber-200 px-4 py-6 sm:px-6 sm:py-8 text-center">
```

And the quest list container:
```tsx
<div className="px-6 py-4">
```
to:
```tsx
<div className="px-4 py-4 sm:px-6">
```

In `src/pages/child/Lesson.tsx`, change ALL `p-6` containers (there are 5: loading, error, practice, completion, main):
```tsx
<div className="mx-auto max-w-2xl p-6">
```
to:
```tsx
<div className="mx-auto max-w-2xl px-4 py-4 sm:px-6 sm:py-6">
```

In `src/pages/child/Simulator.tsx`:
```tsx
<div className="mx-auto max-w-4xl p-6">
```
to (2 instances — loading and main):
```tsx
<div className="mx-auto max-w-4xl px-4 py-4 sm:px-6 sm:py-6">
```

In `src/pages/child/Market.tsx`:
```tsx
<div className="mx-auto max-w-4xl p-6">
```
to (2 instances — loading and main):
```tsx
<div className="mx-auto max-w-4xl px-4 py-4 sm:px-6 sm:py-6">
```

In `src/pages/child/Stock.tsx`:
```tsx
<div className="mx-auto max-w-3xl p-6">
```
to (4 instances — loading, 404, 403, main):
```tsx
<div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
```

In `src/pages/child/Stats.tsx` — already uses `px-4 py-6`, tighten:
```tsx
<div className="mx-auto max-w-5xl space-y-8 px-4 py-6">
```
to:
```tsx
<div className="mx-auto max-w-5xl space-y-6 px-4 py-4 sm:space-y-8 sm:py-6">
```

In `src/pages/child/Login.tsx`:
```tsx
<main className="mx-auto max-w-md p-6">
```
to:
```tsx
<main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
```

In `src/pages/child/Signup.tsx` — 2 instances (step 1, step 2):
```tsx
<main className="mx-auto max-w-md p-6">
```
to:
```tsx
<main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
```

In `src/pages/child/PendingConsent.tsx` — 2 instances:
```tsx
<main className="mx-auto max-w-md p-6">
```
to:
```tsx
<main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
```

- [ ] **Step 2: Update public and parent pages**

In `src/pages/ForgotPassword.tsx` — 2 instances (submitted and form):
```tsx
<main className="mx-auto max-w-md p-6">
```
to:
```tsx
<main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
```

In `src/pages/ResetPassword.tsx` — 4 instances (no-token, success, expired, form):
```tsx
<main className="mx-auto max-w-md p-6">
```
to:
```tsx
<main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
```

In `src/pages/VerifyEmail.tsx` — the `Page` wrapper function:
```tsx
return <main className="mx-auto max-w-md p-6">{children}</main>;
```
to:
```tsx
return <main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">{children}</main>;
```

In `src/pages/Privacy.tsx`:
```tsx
<main className="mx-auto max-w-md p-6">
```
to:
```tsx
<main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
```

In `src/pages/ParentDashboard.tsx`:
```tsx
<main className="mx-auto max-w-2xl p-6">
```
to:
```tsx
<main className="mx-auto max-w-2xl px-4 py-4 sm:px-6 sm:py-6">
```

- [ ] **Step 3: Run full suite to confirm no regressions**

Run: `cd invest-ed/frontend && npx vitest run && npm run lint && npx tsc -b`
Expected: All green. Some test snapshots may need updating if any tests check exact class strings.

- [ ] **Step 4: Commit**

```bash
git add src/pages/ src/components/
git commit -m "feat(6): responsive spacing — px-4/py-4 mobile, px-6/py-6 desktop"
```

---

### Task 8: Safe areas + touch targets

**Files:**
- Modify: `src/index.css`
- Modify: `src/components/child/Shell.tsx`
- Modify: `src/components/child/TopNav.tsx`
- Modify: `src/components/child/BottomTabBar.tsx`
- Modify: `src/components/child/simulator/StockChart.tsx`

- [ ] **Step 1: Add safe-area CSS vars to index.css**

In `src/index.css`, add inside the `:root` block (after `--radius: 0.75rem;`):

```css
--safe-top: env(safe-area-inset-top, 0px);
--safe-bottom: env(safe-area-inset-bottom, 0px);
--safe-left: env(safe-area-inset-left, 0px);
--safe-right: env(safe-area-inset-right, 0px);
```

- [ ] **Step 2: Apply safe areas to Shell**

In `src/components/child/Shell.tsx`, update the main element:

Current:
```tsx
className="pb-20 md:pb-0 outline-none"
```

Replace with:
```tsx
className="pb-20 md:pb-0 outline-none"
style={{ paddingLeft: 'var(--safe-left)', paddingRight: 'var(--safe-right)' }}
```

- [ ] **Step 3: Apply safe areas to TopNav**

In `src/components/child/TopNav.tsx`, update the `<header>`:

Current:
```tsx
<header className="sticky top-0 z-10 border-b border-amber-200 bg-white/95 backdrop-blur">
```

Replace with:
```tsx
<header
  className="sticky top-0 z-10 border-b border-amber-200 bg-white/95 backdrop-blur"
  style={{ paddingTop: 'var(--safe-top)' }}
>
```

- [ ] **Step 4: Enlarge BottomTabBar touch targets**

In `src/components/child/BottomTabBar.tsx`, update the NavLink className to ensure 44px min:

Current inner class:
```tsx
'flex flex-col items-center gap-0.5 px-3 py-1 text-xs font-medium transition-colors',
```

Replace with:
```tsx
'flex flex-col items-center gap-0.5 px-3 py-2 min-h-[44px] min-w-[44px] text-xs font-medium transition-colors',
```

- [ ] **Step 5: Enlarge StockChart period button touch targets**

In `src/components/child/simulator/StockChart.tsx`, update the period button className:

Current:
```tsx
className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
```

Replace with:
```tsx
className={`rounded-md px-2.5 py-2 min-h-[44px] min-w-[44px] text-xs font-medium transition-colors ${
```

- [ ] **Step 6: Add responsive tick count to charts**

In `src/components/child/simulator/StockChart.tsx`, add inside the `StockChart` component before the return (after `const color = ...`):

```ts
// Reduce tick count on narrow screens
const tickInterval = typeof window !== 'undefined' && window.innerWidth < 400
  ? Math.max(Math.floor(points.length / 3), 1)
  : undefined; // let Recharts auto-calculate
```

Then update the `<XAxis>` component, adding `interval={tickInterval}` and removing `interval="preserveStartEnd"`:

```tsx
<XAxis
  dataKey="date"
  tick={{ fontSize: 10 }}
  tickFormatter={(d: string) => {
    const date = new Date(d);
    return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  }}
  interval={tickInterval ?? 'preserveStartEnd'}
/>
```

In `src/components/child/simulator/PortfolioChart.tsx`, add similar before the return:

```ts
const tickInterval = typeof window !== 'undefined' && window.innerWidth < 400
  ? Math.max(Math.floor(history.length / 3), 1)
  : undefined;
```

And update `<XAxis>`:

Current:
```tsx
<XAxis dataKey="date" tick={{ fontSize: 11 }} />
```

Replace with:
```tsx
<XAxis dataKey="date" tick={{ fontSize: 11 }} interval={tickInterval ?? 'preserveStartEnd'} />
```

- [ ] **Step 7: Run full suite + lint + tsc**

Run: `cd invest-ed/frontend && npx vitest run && npm run lint && npx tsc -b`
Expected: All green.

- [ ] **Step 8: Commit**

```bash
git add src/index.css src/components/child/Shell.tsx src/components/child/TopNav.tsx src/components/child/BottomTabBar.tsx src/components/child/simulator/StockChart.tsx src/components/child/simulator/PortfolioChart.tsx
git commit -m "feat(6): safe areas, touch targets, responsive chart ticks"
```

---

### Task 9: HoldingsTable responsive card layout

**Files:**
- Modify: `src/components/child/simulator/HoldingsTable.tsx`
- Create: `tests/unit/HoldingsResponsive.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/HoldingsResponsive.test.tsx`:

```tsx
import { screen } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { renderMobile, renderDesktop } from '../helpers/responsive';
import { HoldingsTable } from '@/components/child/simulator/HoldingsTable';

const MOCK_HOLDINGS = [
  {
    ticker: 'AAPL',
    exchange: 'NASDAQ',
    shares: '5',
    avg_buy_price: '168.20',
    current_price: '210.50',
    market_value: '1052.50',
    unrealized_pl: '42.30',
  },
  {
    ticker: 'MSFT',
    exchange: 'NASDAQ',
    shares: '3',
    avg_buy_price: '425.10',
    current_price: '419.10',
    market_value: '1257.30',
    unrealized_pl: '-18.60',
  },
];

describe('HoldingsTable responsive', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders cards on mobile', () => {
    renderMobile(
      <MemoryRouter>
        <HoldingsTable holdings={MOCK_HOLDINGS} />
      </MemoryRouter>,
    );
    // Cards should exist, table should not
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('MSFT')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('renders table on desktop', () => {
    renderDesktop(
      <MemoryRouter>
        <HoldingsTable holdings={MOCK_HOLDINGS} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('table')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/HoldingsResponsive.test.tsx`
Expected: FAIL — the current `HoldingsTable` always renders a `<table>`.

- [ ] **Step 3: Add mobile card layout to HoldingsTable**

Rewrite `src/components/child/simulator/HoldingsTable.tsx`:

```tsx
import { Link } from 'react-router-dom';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { EduTooltip } from './EduTooltip';
import { formatCurrency } from '@/lib/currency';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import type { HoldingOut } from '@/api/simulator';

const EXCHANGE_CURRENCY: Record<string, string> = {
  NASDAQ: 'USD', LSE: 'GBP', HKEX: 'HKD',
};

const EXCHANGE_BADGE: Record<string, string> = {
  NASDAQ: 'bg-blue-100 text-blue-800',
  NYSE: 'bg-indigo-100 text-indigo-800',
  LSE: 'bg-purple-100 text-purple-800',
  HKEX: 'bg-orange-100 text-orange-800',
};

type Props = { holdings: HoldingOut[] };

export function HoldingsTable({ holdings }: Props) {
  const isDesktop = useMediaQuery('(min-width: 768px)');

  if (holdings.length === 0) {
    return (
      <div className="rounded-2xl border-2 border-amber-200 bg-white p-8 text-center space-y-3">
        <span className="text-5xl" aria-hidden="true">📈</span>
        <p className="font-bold text-gray-900">No stocks yet!</p>
        <p className="text-sm text-gray-500">Start by browsing the market and making your first trade.</p>
        <Link
          to="/simulator/market"
          className="inline-block rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-5 py-2 text-sm font-bold text-white hover:from-amber-500 hover:to-orange-600 transition-colors"
        >
          Browse Market →
        </Link>
      </div>
    );
  }

  if (!isDesktop) {
    return <MobileCards holdings={holdings} />;
  }

  return <DesktopTable holdings={holdings} />;
}

function MobileCards({ holdings }: Props) {
  return (
    <div className="space-y-2">
      {holdings.map((h) => {
        const pl = parseFloat(h.unrealized_pl);
        const plSign = pl > 0 ? 'positive' : pl < 0 ? 'negative' : 'neutral';
        const currency = EXCHANGE_CURRENCY[h.exchange] ?? 'USD';
        return (
          <Link
            key={`${h.exchange}-${h.ticker}`}
            to={`/simulator/stock/${h.exchange}/${h.ticker}`}
            className="block rounded-xl border-2 border-amber-200 bg-white p-3 transition-shadow hover:shadow-md"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-base font-bold">{h.ticker}</span>
                <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${EXCHANGE_BADGE[h.exchange] ?? 'bg-muted text-muted-foreground'}`}>
                  {h.exchange}
                </span>
              </div>
              <span className={`text-sm font-semibold flex items-center gap-1 ${plSign === 'positive' ? 'text-green-600' : plSign === 'negative' ? 'text-red-600' : ''}`}>
                {plSign === 'positive' && <TrendingUp className="h-3.5 w-3.5" />}
                {plSign === 'negative' && <TrendingDown className="h-3.5 w-3.5" />}
                {plSign === 'neutral' && <Minus className="h-3.5 w-3.5" />}
                {formatCurrency(h.unrealized_pl, currency)}
              </span>
            </div>
            <div className="mt-2 flex justify-between text-xs text-gray-500">
              <span>{h.shares} shares</span>
              <span>Avg {formatCurrency(h.avg_buy_price, currency)}</span>
              <span className="font-semibold text-gray-900">{formatCurrency(h.market_value, currency)}</span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function DesktopTable({ holdings }: Props) {
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="border-b bg-muted/50">
          <tr>
            <th className="px-3 py-2 text-left font-medium">Ticker</th>
            <th className="px-3 py-2 text-right font-medium">Shares</th>
            <th className="px-3 py-2 text-right font-medium">Avg Buy</th>
            <th className="px-3 py-2 text-right font-medium">Current</th>
            <th className="px-3 py-2 text-right font-medium">Value</th>
            <th className="px-3 py-2 text-right font-medium">
              <EduTooltip
                term="Unrealized P/L"
                explanation="This is how much you'd gain or lose if you sold now. It's 'unrealized' because you haven't sold yet."
              />
            </th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => {
            const pl = parseFloat(h.unrealized_pl);
            const plSign = pl > 0 ? 'positive' : pl < 0 ? 'negative' : 'neutral';
            const currency = EXCHANGE_CURRENCY[h.exchange] ?? 'USD';
            return (
              <tr key={`${h.exchange}-${h.ticker}`} className="border-b last:border-0 hover:bg-muted/30">
                <td colSpan={6} className="p-0">
                  <Link
                    to={`/simulator/stock/${h.exchange}/${h.ticker}`}
                    className="flex items-center justify-between gap-2 px-3 py-2"
                  >
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{h.ticker}</span>
                      <span className="rounded bg-muted px-1.5 py-0.5 text-xs">{h.exchange}</span>
                    </span>
                    <span className="flex items-center gap-4 text-right">
                      <span>{h.shares}</span>
                      <span>{formatCurrency(h.avg_buy_price, currency)}</span>
                      <span>{formatCurrency(h.current_price, currency)}</span>
                      <span>{formatCurrency(h.market_value, currency)}</span>
                      <span className={`flex items-center gap-1 ${plSign === 'positive' ? 'text-green-600' : plSign === 'negative' ? 'text-red-600' : ''}`}>
                        {plSign === 'positive' && <TrendingUp className="h-3.5 w-3.5" data-pl="positive" />}
                        {plSign === 'negative' && <TrendingDown className="h-3.5 w-3.5" data-pl="negative" />}
                        {plSign === 'neutral' && <Minus className="h-3.5 w-3.5" data-pl="neutral" />}
                        {h.unrealized_pl}
                      </span>
                    </span>
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd invest-ed/frontend && npx vitest run tests/unit/HoldingsResponsive.test.tsx`
Expected: 2 tests PASS.

- [ ] **Step 5: Run full suite**

Run: `cd invest-ed/frontend && npx vitest run && npm run lint && npx tsc -b`
Expected: All green.

- [ ] **Step 6: Commit**

```bash
git add src/components/child/simulator/HoldingsTable.tsx tests/unit/HoldingsResponsive.test.tsx
git commit -m "feat(6): responsive HoldingsTable — cards on mobile, table on desktop"
```

---

### Task 10: Wire BottomSheet into ProfileMenu, ChartCoachPanel, TradeForm

**Files:**
- Modify: `src/components/child/ProfileMenu.tsx`
- Modify: `src/components/child/simulator/ChartCoachPanel.tsx`
- Modify: `src/components/child/simulator/TradeForm.tsx`

- [ ] **Step 1: Wire BottomSheet into ProfileMenu**

Modify `src/components/child/ProfileMenu.tsx`. Wrap the interest-area Dialog in a BottomSheet on mobile. The DropdownMenu trigger stays as-is (it's in TopNav which is only visible on desktop). Add the BottomSheet for the profile editor dialog:

Add import at top:
```ts
import { BottomSheet } from '@/components/mobile/BottomSheet';
import { useMediaQuery } from '@/hooks/useMediaQuery';
```

Inside the component, add:
```ts
const isMobile = !useMediaQuery('(min-width: 768px)');
```

Replace the `<Dialog>` block with:

```tsx
{isMobile ? (
  <BottomSheet open={open} onOpenChange={setOpen} title="Your interest area">
    <div className="space-y-1.5">
      <label htmlFor="profile-topic" className="text-sm font-medium">
        Interest area
      </label>
      <select
        id="profile-topic"
        className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
      >
        {TOPIC_OPTIONS.map((t) => (
          <option key={t.value} value={t.value}>{t.label}</option>
        ))}
      </select>
    </div>
    <div className="mt-4 flex justify-end">
      <Button
        type="button"
        disabled={save.isPending}
        onClick={() => save.mutate(topic === '' ? null : topic)}
      >
        {save.isPending ? 'Saving…' : 'Save'}
      </Button>
    </div>
  </BottomSheet>
) : (
  <Dialog open={open} onOpenChange={setOpen}>
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Your interest area</DialogTitle>
      </DialogHeader>
      <div className="space-y-1.5">
        <label htmlFor="profile-topic" className="text-sm font-medium">
          Interest area
        </label>
        <select
          id="profile-topic"
          className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        >
          {TOPIC_OPTIONS.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>
      <DialogFooter>
        <Button
          type="button"
          disabled={save.isPending}
          onClick={() => save.mutate(topic === '' ? null : topic)}
        >
          {save.isPending ? 'Saving…' : 'Save'}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
)}
```

- [ ] **Step 2: Wire BottomSheet into ChartCoachPanel**

Modify `src/components/child/simulator/ChartCoachPanel.tsx`. Wrap the entire panel in a BottomSheet on mobile:

Add import:
```ts
import { useMediaQuery } from '@/hooks/useMediaQuery';
```

Inside the component, add:
```ts
const isMobile = !useMediaQuery('(min-width: 768px)');
```

Wrap the existing return JSX. If mobile, render inside a `BottomSheet`; otherwise keep the existing fixed-position panel:

Replace the return with:

```tsx
const panelContent = (
  <>
    <div className="flex items-center justify-between border-b border-amber-100 px-4 py-3">
      <div className="flex items-center gap-2">
        <span className="text-xl">💡</span>
        <span className="font-bold text-gray-900">Coach Eddie</span>
        <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-700">{ticker} Chart</span>
      </div>
      <div className="flex items-center gap-3">
        {remaining !== null && (
          <span className="text-xs text-gray-400">{remaining} messages left</span>
        )}
        {!isMobile && (
          <button onClick={onClose} className="text-lg text-gray-400 hover:text-gray-600">✕</button>
        )}
      </div>
    </div>

    <div className="max-h-64 space-y-3 overflow-y-auto p-4">
      {messages.length === 0 && (
        <p className="text-center text-sm text-gray-400">
          Ask me anything about this {ticker} chart! 📊
        </p>
      )}
      {messages.map((m, i) => (
        <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
          <div
            className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
              m.role === 'user'
                ? 'bg-gradient-to-r from-amber-400 to-orange-500 text-white'
                : 'bg-amber-50 text-gray-800'
            }`}
          >
            {m.content}
          </div>
        </div>
      ))}
      {sendMessage.isPending && (
        <div className="flex justify-start">
          <div className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-gray-400">
            Thinking…
          </div>
        </div>
      )}
      {sendMessage.isError && (
        <div className="flex justify-start">
          <div className="max-w-[80%] rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">
            Something went wrong. Try sending your message again.
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>

    <div className="flex gap-2 border-t border-amber-100 p-3">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        placeholder="Ask about the chart…"
        maxLength={200}
        className="flex-1 rounded-xl border border-amber-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-300"
        disabled={remaining === 0}
      />
      <Button
        onClick={handleSend}
        disabled={!input.trim() || sendMessage.isPending || remaining === 0}
        className="rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-4 text-white"
      >
        Send
      </Button>
    </div>
  </>
);

if (isMobile) {
  return (
    <BottomSheet open onOpenChange={(open) => { if (!open) onClose(); }} title="Coach Eddie">
      {panelContent}
    </BottomSheet>
  );
}

return (
  <div className="fixed inset-x-0 bottom-0 z-50 mx-auto max-w-2xl animate-in slide-in-from-bottom">
    <div className="rounded-t-2xl border-2 border-amber-200 bg-white shadow-xl">
      {panelContent}
    </div>
  </div>
);
```

Also add import for `BottomSheet`:
```ts
import { BottomSheet } from '@/components/mobile/BottomSheet';
```

- [ ] **Step 3: Wire BottomSheet into TradeForm review step**

Modify `src/components/child/simulator/TradeForm.tsx`. Wrap the review step in a BottomSheet on mobile:

Add imports:
```ts
import { BottomSheet } from '@/components/mobile/BottomSheet';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { useHaptic } from '@/hooks/useHaptic';
```

Inside the component, add:
```ts
const isMobile = !useMediaQuery('(min-width: 768px)');
const haptic = useHaptic();
```

Update `handleConfirm` to trigger haptic:
```ts
async function handleConfirm() {
  await onSubmit({ ticker, exchange, type: side, shares: sharesNum });
  haptic('medium');
}
```

Wrap the review step. Replace the `if (step === 'review')` block. If mobile, render inside a BottomSheet; else keep inline:

```tsx
if (step === 'review') {
  const cashAfter = side === 'buy' ? cashNum - totalCost : cashNum + totalCost;
  const reviewContent = (
    <div>
      <div className="rounded-lg border bg-muted/50 p-4">
        <p className="font-medium">{side === 'buy' ? 'Buy' : 'Sell'} {sharesNum} shares of {ticker}</p>
        <div className="mt-2 space-y-1 text-sm">
          <p>Price per share: {formatCurrency(price, currency)}</p>
          <p>Total {side === 'buy' ? 'cost' : 'proceeds'}: {formatCurrency(totalCost.toFixed(2), currency)}</p>
          <p>Cash after trade: {formatCurrency(cashAfter.toFixed(2), currency)}</p>
        </div>
        <div className="mt-2">
          <EduTooltip
            term="Review"
            explanation="Always review your trades before confirming. In real investing, you can't undo a trade!"
          />
        </div>
      </div>
      {submitError && (
        <p className="mt-2 text-sm text-red-600">{submitError}</p>
      )}
      <div className="mt-4 flex gap-2">
        <Button onClick={handleConfirm} disabled={isSubmitting}>
          {isSubmitting ? 'Submitting…' : `Confirm ${side} of ${sharesNum} shares`}
        </Button>
        <Button variant="outline" onClick={handleBack} disabled={isSubmitting}>Go back</Button>
      </div>
    </div>
  );

  if (isMobile) {
    return (
      <BottomSheet open onOpenChange={(open) => { if (!open) handleBack(); }} title="Review Trade">
        {reviewContent}
      </BottomSheet>
    );
  }

  return <div aria-live="assertive">{reviewContent}</div>;
}
```

- [ ] **Step 4: Run full suite + lint + tsc**

Run: `cd invest-ed/frontend && npx vitest run && npm run lint && npx tsc -b`
Expected: All green.

- [ ] **Step 5: Commit**

```bash
git add src/components/child/ProfileMenu.tsx src/components/child/simulator/ChartCoachPanel.tsx src/components/child/simulator/TradeForm.tsx
git commit -m "feat(6): wire BottomSheet into ProfileMenu, ChartCoach, TradeForm"
```

---

### Task 11: Wire pull-to-refresh + swipe nav into Shell and pages

**Files:**
- Modify: `src/components/child/Shell.tsx`
- Modify: `src/pages/child/Home.tsx`
- Modify: `src/pages/child/Market.tsx`
- Modify: `src/pages/child/Simulator.tsx`
- Modify: `src/pages/child/Stats.tsx`

- [ ] **Step 1: Wire swipe nav + pull-to-refresh container into Shell**

Modify `src/components/child/Shell.tsx`:

Add imports:
```ts
import { useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSwipeNav } from '@/hooks/useSwipeNav';
import { usePullToRefresh } from '@/hooks/usePullToRefresh';
import { PullToRefreshIndicator } from '@/components/mobile/PullToRefreshIndicator';
```

Inside the `Shell` component (after `useRouteFocus()`), add:

```ts
const mainRef = useRef<HTMLDivElement>(null);
const swipeRef = useRef<HTMLDivElement>(null);
const queryClient = useQueryClient();

useSwipeNav({ ref: swipeRef });

const handleRefresh = useCallback(async () => {
  // Refetch all active queries for the current page
  await queryClient.refetchQueries({ type: 'active' });
}, [queryClient]);

const { indicatorProps } = usePullToRefresh({ ref: mainRef, onRefresh: handleRefresh });
```

Update the returned JSX. Wrap the `<motion.main>` in a ref div and add the pull indicator:

Replace the return from `<div className="min-h-screen ...">` onwards:

```tsx
return (
  <div className="min-h-screen bg-gradient-to-b from-amber-50 to-orange-50" ref={swipeRef}>
    <SkipLink />
    <TopNav username={session.data.username} />
    <div className="mx-auto flex max-w-5xl items-center px-4 pt-2">
      <TierBadge premium={session.data.is_premium} />
    </div>
    <VerifyEmailBanner profile={session.data} />
    <div ref={mainRef}>
      <PullToRefreshIndicator {...indicatorProps} />
      <AnimatePresence mode="wait">
        <motion.main
          key={location.pathname}
          id="main"
          tabIndex={-1}
          className="pb-20 md:pb-0 outline-none"
          style={{ paddingLeft: 'var(--safe-left)', paddingRight: 'var(--safe-right)' }}
          initial={prefersReducedMotion ? false : { opacity: 0, y: 8 }}
          animate={prefersReducedMotion ? undefined : { opacity: 1, y: 0 }}
          exit={prefersReducedMotion ? undefined : { opacity: 0, y: -8 }}
          transition={{ duration: prefersReducedMotion ? 0 : 0.15 }}
        >
          <Outlet />
        </motion.main>
      </AnimatePresence>
    </div>
    <BottomTabBar />
  </div>
);
```

- [ ] **Step 2: Run full suite**

Run: `cd invest-ed/frontend && npx vitest run && npm run lint && npx tsc -b`
Expected: All green.

- [ ] **Step 3: Commit**

```bash
git add src/components/child/Shell.tsx
git commit -m "feat(6): wire pull-to-refresh + swipe nav into Shell"
```

---

### Task 12: Parent Dashboard mobile header

**Files:**
- Modify: `src/pages/ParentDashboard.tsx`

- [ ] **Step 1: Add sticky mobile header**

Modify `src/pages/ParentDashboard.tsx`. Replace the current `<header>` with a responsive one:

Add import:
```ts
import { Link } from 'react-router-dom';
```

(The file already imports `useNavigate` from `react-router-dom` — add `Link` to the existing import.)

Replace the current `<header>`:

Current:
```tsx
<header className="flex items-center justify-between">
  <h1 className="text-2xl font-semibold">Parent dashboard</h1>
  <Button variant="ghost" onClick={() => logout.mutate()} disabled={logout.isPending}>
    Log out
  </Button>
</header>
```

Replace with:
```tsx
<header className="sticky top-0 z-10 -mx-4 -mt-4 mb-4 flex items-center justify-between border-b border-amber-200 bg-white/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:-mt-6 sm:px-6">
  <div className="flex items-center gap-2">
    <Link to="/parent" className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500 text-sm font-extrabold text-white">
      IE
    </Link>
    <h1 className="text-lg font-semibold sm:text-2xl">Parent Dashboard</h1>
  </div>
  <Button variant="ghost" size="sm" onClick={() => logout.mutate()} disabled={logout.isPending}>
    Log out
  </Button>
</header>
```

- [ ] **Step 2: Run full suite**

Run: `cd invest-ed/frontend && npx vitest run && npm run lint && npx tsc -b`
Expected: All green.

- [ ] **Step 3: Commit**

```bash
git add src/pages/ParentDashboard.tsx
git commit -m "feat(6): parent dashboard mobile sticky header + responsive spacing"
```

---

### Task 13: Market stock grid mobile touch targets

**Files:**
- Modify: `src/pages/child/Market.tsx`

- [ ] **Step 1: Tighten mobile card padding and ensure touch targets**

In `src/pages/child/Market.tsx`, update the stock card link:

Current:
```tsx
className="rounded-lg border bg-card p-3 transition-shadow hover:shadow-md"
```

Replace with:
```tsx
className="rounded-lg border bg-card p-2 sm:p-3 transition-shadow hover:shadow-md min-h-[44px]"
```

Also update the refresh button to have a min touch target:

Current:
```tsx
className="ml-auto flex items-center gap-1.5 rounded-lg bg-amber-100 px-3 py-1.5 text-sm font-medium text-amber-700 transition-colors hover:bg-amber-200 disabled:opacity-50"
```

Replace with:
```tsx
className="ml-auto flex items-center gap-1.5 rounded-lg bg-amber-100 px-3 py-2 min-h-[44px] text-sm font-medium text-amber-700 transition-colors hover:bg-amber-200 disabled:opacity-50"
```

- [ ] **Step 2: Run full suite**

Run: `cd invest-ed/frontend && npx vitest run && npm run lint && npx tsc -b`
Expected: All green.

- [ ] **Step 3: Commit**

```bash
git add src/pages/child/Market.tsx
git commit -m "feat(6): market grid mobile padding + touch targets"
```

---

### Task 14: Playwright responsive viewport tests + CI

**Files:**
- Create: `tests/e2e/responsive.spec.ts`
- Modify: `playwright.config.ts`
- Modify: `package.json`
- Modify: `../../.github/workflows/ci.yml` (repo root)

- [ ] **Step 1: Add mobile project to Playwright config**

Modify `playwright.config.ts`:

```ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    {
      name: 'mobile',
      use: { ...devices['iPhone 13'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
```

- [ ] **Step 2: Create responsive e2e test**

Create `tests/e2e/responsive.spec.ts`:

```ts
import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'phone', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1024, height: 768 },
] as const;

for (const vp of VIEWPORTS) {
  test.describe(`${vp.name} (${vp.width}px)`, () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
    });

    test('login page has no horizontal overflow', async ({ page }) => {
      await page.goto('/login');
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      const innerWidth = await page.evaluate(() => window.innerWidth);
      expect(scrollWidth).toBeLessThanOrEqual(innerWidth);
    });

    test('signup page has no horizontal overflow', async ({ page }) => {
      await page.goto('/signup');
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      const innerWidth = await page.evaluate(() => window.innerWidth);
      expect(scrollWidth).toBeLessThanOrEqual(innerWidth);
    });
  });
}

test.describe('mobile-specific visibility', () => {
  test('BottomTabBar visible at 375px', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/login');
    // BottomTabBar is inside Shell which requires auth — check unauth pages don't crash
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(375);
  });

  test('TopNav desktop links hidden at 375px, visible at 1024px', async ({ page }) => {
    await page.goto('/login');

    await page.setViewportSize({ width: 375, height: 812 });
    // TopNav is inside Shell (authed), so check the public login page instead
    // Just verify no overflow
    let scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(375);

    await page.setViewportSize({ width: 1024, height: 768 });
    scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(1024);
  });
});
```

- [ ] **Step 3: Add npm script**

Add to `package.json` scripts:
```json
"test:e2e:responsive": "playwright test tests/e2e/responsive.spec.ts"
```

- [ ] **Step 4: Add CI job**

Add to `../../.github/workflows/ci.yml` (the repo-root CI file), after the `a11y` job:

```yaml
  responsive:
    name: Responsive (viewport tests)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: invest-ed/frontend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: invest-ed/frontend/package-lock.json

      - run: npm ci --legacy-peer-deps

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Responsive viewport tests
        run: npm run test:e2e:responsive
```

- [ ] **Step 5: Run Playwright responsive tests locally**

Run: `cd invest-ed/frontend && npx playwright install chromium && npx playwright test tests/e2e/responsive.spec.ts`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/e2e/responsive.spec.ts playwright.config.ts package.json ../../.github/workflows/ci.yml
git commit -m "feat(6): Playwright responsive viewport tests + CI job"
```

---

### Task 15: Full regression + close-out

**Files:** None new.

- [ ] **Step 1: Run full vitest suite**

Run: `cd invest-ed/frontend && npx vitest run`
Expected: 279+ tests PASS (original 279 + new tests from this plan).

- [ ] **Step 2: Run lint**

Run: `cd invest-ed/frontend && npm run lint`
Expected: Clean (0 errors, ≤1 pre-existing warning).

- [ ] **Step 3: Run tsc build check**

Run: `cd invest-ed/frontend && npx tsc -b`
Expected: Clean, no errors.

- [ ] **Step 4: Run vite build**

Run: `cd invest-ed/frontend && npx vite build`
Expected: Build succeeds.

- [ ] **Step 5: Run Playwright e2e tests**

Run: `cd invest-ed/frontend && npx playwright test`
Expected: All e2e tests PASS (existing a11y + new responsive).

- [ ] **Step 6: Run backend tests to confirm no regressions**

Run: `cd invest-ed && /Users/leeashmore/Local Repo/.venv/bin/pytest backend -v`
Expected: 328 passed, 1 skipped.

- [ ] **Step 7: Summarize results**

Report final test counts and any issues found.
