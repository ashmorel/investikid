import { useEffect } from 'react';
import { useProgress } from './useProgress';
import { syncStreakReminder } from '@/lib/streakReminder';

/** Re-evaluates the streak reminder whenever progress changes. Native only; web no-op. */
export function useStreakReminder(): void {
  const { data: progress } = useProgress();
  const lastActivity = progress?.last_activity_date ?? null;
  const streakCount = progress?.streak_count ?? 0;

  useEffect(() => {
    void syncStreakReminder({ lastActivity, streakCount }).catch(() => {});
  }, [lastActivity, streakCount]);
}
