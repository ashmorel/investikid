import { useTranslation } from 'react-i18next';
import { useMarketProgress, useMarkets } from '../../hooks/useMarkets';
import { flagFor } from '../../lib/marketFlags';

export function MarketXpBreakdown() {
  const { t } = useTranslation('markets');
  const { data: progress } = useMarketProgress();
  const { data: markets } = useMarkets();
  const rows = progress?.markets ?? [];
  if (rows.length === 0) return null;
  const nameFor = (code: string) => markets?.find((m) => m.code === code)?.name ?? code;
  return (
    <section aria-label={t('stats.byMarket')} className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
      <h3 className="mb-2 text-sm font-bold text-foreground">{t('stats.byMarket')}</h3>
      <ul className="space-y-1.5">
        {rows.map((r) => (
          <li key={r.market_code} className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              <span aria-hidden="true">{flagFor(r.market_code)}</span>
              <span className="font-medium text-foreground">{nameFor(r.market_code)}</span>
            </span>
            <span className="font-bold text-brand-700">{r.xp}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
