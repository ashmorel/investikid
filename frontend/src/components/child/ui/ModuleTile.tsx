import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { PremiumBadge } from '@/components/child/PremiumBadge';

type Props = { emoji: string; title: string; subtitle: string; accent: string; tint: string; to?: string; locked?: boolean; recommended?: boolean; onLockedClick?: () => void };

export function ModuleTile({ emoji, title, subtitle, accent, tint, to, locked, recommended, onLockedClick }: Props) {
  const { t } = useTranslation('child');
  const inner = (
    <>
      {/* eslint-disable-next-line i18next/no-literal-string */}
      {recommended && <span className="absolute right-3 top-3 rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-extrabold text-brand-700"><span aria-hidden="true">★ </span>{t('moduleTile.next')}</span>}
      <span className="flex h-10 w-10 items-center justify-center rounded-xl text-xl" style={{ backgroundColor: accent }} aria-hidden="true">{emoji}</span>
      <span className="mt-2 block text-[15px] font-extrabold text-gray-900">{title}</span>
      <span className="text-[11px] font-bold text-gray-500">{subtitle}</span>
      {locked && <PremiumBadge className="mt-1.5" />}
    </>
  );
  const cls = cn('relative block rounded-2xl p-3.5', locked && 'opacity-60', 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500');
  if (to && !locked) return <Link to={to} className={cls} style={{ backgroundColor: tint }}>{inner}</Link>;
  if (locked && onLockedClick) {
    return (
      <button
        type="button"
        onClick={onLockedClick}
        aria-label={t('moduleTile.premiumAriaLabel', { title })}
        className={cn(cls, 'w-full text-left')}
        style={{ backgroundColor: tint }}
      >
        {inner}
      </button>
    );
  }
  return <div className={cls} style={{ backgroundColor: tint }} aria-disabled={locked || undefined}>{inner}</div>;
}
