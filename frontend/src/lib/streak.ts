/**
 * A streak is "active" if the user logged a completion today or yesterday (UTC).
 * Two-day grace window matches the backend's `streak_after_activity` semantics.
 */
export function isStreakActive(lastActivityDate: string | null, today: Date): boolean {
  if (!lastActivityDate) return false;
  const last = new Date(`${lastActivityDate}T00:00:00Z`);
  const todayUtc = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  const diffDays = Math.floor((todayUtc - last.getTime()) / 86_400_000);
  return diffDays >= 0 && diffDays <= 1;
}
