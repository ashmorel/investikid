// First-party product analytics (M4). Fire-and-forget: analytics must never
// break or slow the app — failures are swallowed, offline events are dropped,
// and nothing here blocks rendering.
// Spec: docs/superpowers/specs/2026-06-12-product-analytics-design.md
import { apiFetch } from '@/api/client';

export type ClientEventName = 'home_view' | 'home_cta_tap' | 'quicklink_tap' | 'paywall_view';

type ClientEvent = { event_name: ClientEventName; props?: Record<string, string | boolean> };

const FLUSH_DELAY_MS = 5_000;
const MAX_BATCH = 20;

let queue: ClientEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
let sessionFired = new Set<ClientEventName>();

async function flush(): Promise<void> {
  timer = null;
  if (queue.length === 0) return;
  if (typeof navigator !== 'undefined' && navigator.onLine === false) {
    queue = []; // by design: no offline persistence for analytics
    return;
  }
  const batch = queue.slice(0, MAX_BATCH);
  queue = queue.slice(MAX_BATCH);
  try {
    await apiFetch('/analytics/events', {
      method: 'POST',
      body: JSON.stringify({ events: batch }),
      keepalive: true,
    });
  } catch {
    // Silent: never surface analytics errors.
  }
  if (queue.length > 0) schedule();
}

function schedule(): void {
  if (timer === null) timer = setTimeout(() => void flush(), FLUSH_DELAY_MS);
}

export function track(name: ClientEventName, props?: Record<string, string | boolean>): void {
  queue.push(props ? { event_name: name, props } : { event_name: name });
  schedule();
}

/** Fire an event at most once per app session (e.g. home_view). */
export function trackOncePerSession(
  name: ClientEventName,
  props?: Record<string, string | boolean>,
): void {
  if (sessionFired.has(name)) return;
  sessionFired.add(name);
  track(name, props);
}

// Flush pending events when the tab goes to background (best-effort).
if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') void flush();
  });
}

/** Test hook: clear queue, timer and the once-per-session registry. */
export function resetForTests(): void {
  queue = [];
  sessionFired = new Set();
  if (timer !== null) {
    clearTimeout(timer);
    timer = null;
  }
}
