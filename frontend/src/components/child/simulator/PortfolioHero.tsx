import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/currency';
import { PortfolioChart } from './PortfolioChart';
import type { PortfolioSnapshot } from '@/api/simulator';

export function PortfolioHero({
  totalValue,
  currencyCode,
  history,
}: {
  totalValue: string;
  currencyCode: string;
  history: PortfolioSnapshot[];
}) {
  const { t } = useTranslation('simulator');
  const showChange = Array.isArray(history) && history.length >= 2;
  let pill: React.ReactNode = null;
  if (showChange) {
    const first = history[0].value;
    const last = history[history.length - 1].value;
    const delta = last - first;
    const pct = first > 0 ? (delta / first) * 100 : 0;
    const up = delta >= 0;
    pill = (
      <div
        className={cn(
          'inline-flex items-center gap-1.5 rounded-lg border bg-white/15 px-2.5 py-1 text-sm font-bold text-white',
          up ? 'border-success-200/60' : 'border-danger-200/60',
        )}
      >
        <span aria-hidden="true">{up ? '▲' : '▼'}</span>
        {formatCurrency(Math.abs(delta), currencyCode)} · {Math.abs(pct).toFixed(1)}% {t('portfolioHero.thisWeek')}
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-3xl bg-brand-gradient p-5 text-white shadow-lg shadow-brand-600/30">
      <p className="text-xs font-bold uppercase tracking-wider text-white/90">
        {t('portfolioHero.practicePortfolio')} <span className="font-medium normal-case opacity-80">{t('portfolioHero.playMoney')}</span>
      </p>
      <p className="mt-1 text-4xl font-extrabold leading-tight">{formatCurrency(totalValue, currencyCode)}</p>
      {pill && <div className="mt-2">{pill}</div>}
      {showChange && (
        <div className="mt-4 -mx-1">
          <PortfolioChart history={history} variant="onGradient" />
        </div>
      )}
    </div>
  );
}
