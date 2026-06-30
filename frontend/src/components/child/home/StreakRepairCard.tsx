import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useProgress } from '@/hooks/useProgress';
import { useRepairStreak } from '@/api/streak';
import { useToast } from '@/hooks/use-toast';
import { ApiError } from '@/api/client';

/**
 * Non-blocking Home card offering a coin-funded streak repair when the backend
 * marks the streak as just-lapsed and repairable. Self-hiding on loading /
 * error / not-available; dismissible for the session via local state. On a
 * successful repair the progress refetch flips `streak_repair_available` to
 * false and the card self-hides.
 */
export default function StreakRepairCard() {
  const { t } = useTranslation('home');
  const { data, isLoading, isError } = useProgress();
  const { toast } = useToast();
  const repair = useRepairStreak();
  const [dismissed, setDismissed] = useState(false);

  if (isLoading || isError || !data?.streak_repair_available || dismissed) return null;

  const cost = data.streak_repair_cost;

  const onConfirm = () => {
    repair.mutate(undefined, {
      onSuccess: () => {
        toast({ title: t('streakRepair.successTitle'), description: t('streakRepair.successBody') });
      },
      onError: (err) => {
        const notEnough = err instanceof ApiError && err.code === 'not_enough_coins';
        toast({ description: notEnough ? t('streakRepair.notEnoughCoins') : t('streakRepair.error') });
      },
    });
  };

  return (
    <section
      aria-label={t('streakRepair.ariaLabel')}
      className="mb-4 rounded-2xl border border-brand-200 bg-brand-50 px-4 py-3"
    >
      <p className="text-sm font-semibold text-brand-800">{t('streakRepair.title')}</p>
      <p className="mb-3 text-sm text-brand-700">{t('streakRepair.body', { count: cost })}</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onConfirm}
          disabled={repair.isPending}
          className="min-h-[44px] rounded-xl bg-brand-gradient px-4 py-2 text-sm font-bold text-white hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 disabled:opacity-60"
        >
          {t('streakRepair.confirm')}
        </button>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          className="min-h-[44px] rounded-xl border border-brand-200 px-4 py-2 text-sm text-brand-700 hover:bg-brand-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
        >
          {t('streakRepair.dismiss')}
        </button>
      </div>
    </section>
  );
}
