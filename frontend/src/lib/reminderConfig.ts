// Single source of truth for the streak-reminder local notification.
// Changing these needs an app release (native bundle); structured so a future
// server-config endpoint could hydrate it without touching callers.
export const REMINDER = {
  notificationId: 1001,
  primaryHour: 18, // first-choice fire time (local 24h)
  fallbackHour: 20, // used if it's already past primaryHour
  storageKey: 'notif_streak_reminder',
  title: (streak: number) => `🔥 Keep your ${streak}-day streak alive!`,
  body: 'A quick lesson before bed keeps your streak going.',
} as const;
