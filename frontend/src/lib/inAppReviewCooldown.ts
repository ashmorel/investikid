// B5 — in-app-review cooldown + first-session guard (localStorage, best-effort).
// We pick the *moment* to ask for a rating; the OS also throttles independently.

const LAST_ASKED = 'ik:iar:lastAsked'; // epoch ms of the last time we asked
const BOOTS = 'ik:iar:boots'; // app-open counter — used to skip the very first session

/** 60 days — ask at most once per this window. */
export const COOLDOWN_MS = 60 * 24 * 60 * 60 * 1000;

/** Call once per app boot. Increments the session counter (best-effort). */
export function markSessionSeen(): void {
  try {
    const n = parseInt(localStorage.getItem(BOOTS) ?? '0', 10) || 0;
    localStorage.setItem(BOOTS, String(n + 1));
  } catch {
    /* private mode — best effort */
  }
}

function bootCount(): number {
  try {
    return parseInt(localStorage.getItem(BOOTS) ?? '0', 10) || 0;
  } catch {
    return 0;
  }
}

/**
 * True when it's an appropriate moment to ask for a review:
 * - not the user's first session (boot count ≥ 2), and
 * - never asked, or the 60-day cooldown has elapsed.
 * `now` is injectable for testing.
 */
export function shouldAskForReview(now: number = Date.now()): boolean {
  if (bootCount() < 2) return false;
  let raw: string | null;
  try {
    raw = localStorage.getItem(LAST_ASKED);
  } catch {
    return false;
  }
  if (!raw) return true; // never asked
  const last = parseInt(raw, 10);
  if (Number.isNaN(last)) return true;
  return now - last >= COOLDOWN_MS;
}

/** Record that we just asked, starting the cooldown. `now` is injectable for testing. */
export function recordReviewAsked(now: number = Date.now()): void {
  try {
    localStorage.setItem(LAST_ASKED, String(now));
  } catch {
    /* private mode — best effort */
  }
}
