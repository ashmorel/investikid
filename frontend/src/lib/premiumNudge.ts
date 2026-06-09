export const DISMISS_DAYS = 7;
const KEY_PREFIX = 'ik.premiumNudge.';

export function isNudgeDismissed(key: string): boolean {
  try {
    const raw = localStorage.getItem(KEY_PREFIX + key);
    if (!raw) return false;
    const ts = Number(raw);
    if (!Number.isFinite(ts)) return false;
    return Date.now() - ts < DISMISS_DAYS * 24 * 60 * 60 * 1000;
  } catch {
    return false;
  }
}

export function dismissNudge(key: string): void {
  try {
    localStorage.setItem(KEY_PREFIX + key, String(Date.now()));
  } catch {
    /* storage unavailable — nudge will simply re-show; acceptable */
  }
}
