import { LocalNotifications } from '@capacitor/local-notifications';
import { isNativeApp } from './platform';
import { REMINDER } from './reminderConfig';

export type ReminderDecision = { action: 'cancel' } | { action: 'schedule'; at: Date };

/** Local YYYY-MM-DD (matches the backend's local-date streak handling). */
export function ymdLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function decideStreakReminder(args: {
  enabled: boolean;
  practicedToday: boolean;
  streakCount: number;
  now: Date;
}): ReminderDecision {
  const { enabled, practicedToday, streakCount, now } = args;
  if (!enabled || streakCount <= 0 || practicedToday) return { action: 'cancel' };
  const hour = now.getHours();
  let targetHour: number;
  if (hour < REMINDER.primaryHour) targetHour = REMINDER.primaryHour;
  else if (hour < REMINDER.fallbackHour) targetHour = REMINDER.fallbackHour;
  else return { action: 'cancel' };
  const at = new Date(now);
  at.setHours(targetHour, 0, 0, 0);
  return { action: 'schedule', at };
}

/** Read the current preference, decide, and apply. Native only; web no-op. */
export async function syncStreakReminder(args: {
  lastActivity: string | null;
  streakCount: number;
}): Promise<void> {
  if (!isNativeApp()) return;
  const enabled = localStorage.getItem(REMINDER.storageKey) === '1';
  const now = new Date();
  const practicedToday = args.lastActivity === ymdLocal(now);
  const decision = decideStreakReminder({
    enabled,
    practicedToday,
    streakCount: args.streakCount,
    now,
  });
  await applyStreakReminder(decision, args.streakCount);
}

/** Ask for notification permission. Returns true if granted. Native only. */
export async function requestReminderPermission(): Promise<boolean> {
  if (!isNativeApp()) return false;
  const res = await LocalNotifications.requestPermissions();
  return res.display === 'granted';
}

/** Apply a decision via the OS scheduler. No-op on web. */
export async function applyStreakReminder(
  decision: ReminderDecision,
  streakCount: number,
): Promise<void> {
  if (!isNativeApp()) return;
  // Always clear the existing one first so we never stack duplicates.
  await LocalNotifications.cancel({ notifications: [{ id: REMINDER.notificationId }] });
  if (decision.action === 'cancel') return;
  await LocalNotifications.schedule({
    notifications: [
      {
        id: REMINDER.notificationId,
        title: REMINDER.title(streakCount),
        body: REMINDER.body,
        schedule: { at: decision.at },
      },
    ],
  });
}
