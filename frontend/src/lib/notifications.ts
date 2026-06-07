import { LocalNotifications } from '@capacitor/local-notifications';
import { isAndroid } from './platform';

export const REMINDER_CHANNEL_ID = 'streak-reminders';

/** Create the Android notification channel for streak reminders. No-op off Android. */
export async function ensureAndroidChannel(): Promise<void> {
  if (!isAndroid()) return;
  try {
    await LocalNotifications.createChannel({
      id: REMINDER_CHANNEL_ID,
      name: 'Streak reminders',
      description: 'Gentle nudges to keep your learning streak going',
      importance: 3,
    });
  } catch {
    // createChannel is Android-only and can throw on older webviews; non-fatal.
  }
}
