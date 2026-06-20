import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { isNativeApp } from '@/lib/platform';
import { REMINDER } from '@/lib/reminderConfig';
import { requestReminderPermission, syncStreakReminder } from '@/lib/streakReminder';
import { useProgress } from '@/hooks/useProgress';

const NUDGE_SEEN_KEY = 'notif_streak_nudge_seen';

/** One-time native nudge to enable the daily streak reminder. Shown to a child
 *  with a live streak who hasn't enabled it or dismissed the nudge. Web: null. */
export default function StreakReminderNudge() {
  const { t } = useTranslation('home');
  const { data: progress } = useProgress();
  const streakCount = progress?.streak_count ?? 0;
  const lastActivity = progress?.last_activity_date ?? null;

  const alreadyEnabled = localStorage.getItem(REMINDER.storageKey) === '1';
  const alreadySeen = localStorage.getItem(NUDGE_SEEN_KEY) === '1';
  const [dismissed, setDismissed] = useState(false);

  if (!isNativeApp() || streakCount <= 0 || alreadyEnabled || alreadySeen || dismissed) {
    return null;
  }

  function dismiss() {
    localStorage.setItem(NUDGE_SEEN_KEY, '1');
    setDismissed(true);
  }

  async function enable() {
    localStorage.setItem(NUDGE_SEEN_KEY, '1');
    const granted = await requestReminderPermission();
    if (granted) {
      localStorage.setItem(REMINDER.storageKey, '1');
      await syncStreakReminder({ lastActivity, streakCount });
    }
    setDismissed(true);
  }

  return (
    <section
      aria-label={t('streakNudge.title')}
      className="mb-4 rounded-2xl border border-line bg-card px-4 py-3"
    >
      <p className="text-sm font-semibold text-ink">{t('streakNudge.title')}</p>
      <p className="mb-3 text-sm text-muted-foreground">{t('streakNudge.body')}</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => void enable()}
          className="min-h-[44px] rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {t('streakNudge.enable')}
        </button>
        <button
          type="button"
          onClick={dismiss}
          className="min-h-[44px] rounded-md border border-line px-4 py-2 text-sm text-ink hover:bg-brand-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {t('streakNudge.dismiss')}
        </button>
      </div>
    </section>
  );
}
