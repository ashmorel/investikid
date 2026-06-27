import { Lock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { LevelOut } from '@/api/content';
import { PremiumBadge } from './PremiumBadge';
import { MasteredStamp } from './MasteredStamp';
import { OfflineBadge } from './OfflineBadge';

type Props = {
  level: LevelOut;
  onOpen: () => void;
  onLockedClick: () => void;
  isOfflineAvailable?: boolean;
};

export function LevelCard({ level, onOpen, onLockedClick, isOfflineAvailable }: Props) {
  const { t } = useTranslation('lessons');
  const locked = level.state === 'locked';
  const premium = level.locked_reason === 'premium';
  const handle = locked ? onLockedClick : onOpen;
  const ariaLabel = locked
    ? premium
      ? t('levelCard.ariaLabelPremium', { title: level.title })
      : t('levelCard.ariaLabelLocked', { title: level.title })
    : t('levelCard.ariaLabel', { title: level.title });
  return (
    <button
      type="button"
      onClick={handle}
      aria-label={ariaLabel}
      className="flex w-full flex-col items-start gap-1 rounded-2xl border border-brand-100 bg-white shadow-sm p-4 text-left"
    >
      <span className="text-2xl" aria-hidden="true">{level.icon}</span>
      <h2 className="text-sm font-bold text-gray-900">{level.title}</h2>
      {isOfflineAvailable && <OfflineBadge />}
      {level.mastered_at ? (
        <MasteredStamp masteredAt={level.mastered_at} />
      ) : level.state === 'completed' ? (
        <span className="text-xs font-medium text-success-600">{t('levelCard.completed')}</span>
      ) : null}
      {level.state === 'in_progress' && (
        <div className="w-full">
          <span className="text-xs text-gray-500">{t('levelCard.lessonsProgress', { completed: level.lessons_completed, total: level.lessons_total })}</span>
          <div
            className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-brand-100"
            role="progressbar"
            aria-valuenow={level.lessons_completed}
            aria-valuemin={0}
            aria-valuemax={level.lessons_total}
            aria-label={t('levelCard.progressAriaLabel', { title: level.title })}
          >
            <div className="h-full rounded-full bg-brand-gradient" style={{ width: `${level.lessons_total ? Math.round((level.lessons_completed / level.lessons_total) * 100) : 0}%` }} />
          </div>
        </div>
      )}
      {locked && premium && (
        <span className="flex flex-col items-start gap-1">
          <PremiumBadge />
          <span className="text-xs text-gray-400">{t('levelCard.unlockToContinue')}</span>
        </span>
      )}
      {locked && !premium && (
        <span className="inline-flex items-center gap-1 text-xs text-gray-400">
          <Lock className="h-3.5 w-3.5" aria-hidden="true" /> {t('levelCard.finishPrevious')}
        </span>
      )}
    </button>
  );
}
