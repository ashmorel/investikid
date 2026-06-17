import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { simulatorApi, type ExchangeMovers, type MarketMover } from '@/api/simulator';
import { type RegionCode } from '@/lib/region';
import { formatCurrency } from '@/lib/currency';
import { SectionCard } from './SectionCard';

function MoverRow({ mover, rank }: { mover: MarketMover; rank: number }) {
  const isPositive = mover.change_percent >= 0;
  return (
    <Link
      to={`/simulator/stock/${mover.exchange}/${mover.ticker}`}
      className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-brand-50"
    >
      <span className="w-5 text-center text-xs font-medium text-muted-foreground">{rank}</span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{mover.ticker}</p>
        <p className="truncate text-xs text-muted-foreground">{mover.name}</p>
      </div>
      <div className="text-right">
        <p className="text-sm font-medium">{formatCurrency(mover.price, mover.currency)}</p>
        <p className={`text-xs font-semibold ${isPositive ? 'text-success-600' : 'text-danger-600'}`}>
          {isPositive ? '+' : ''}{mover.change_percent.toFixed(2)}%
        </p>
      </div>
    </Link>
  );
}

function ExchangeSection({ exchange, data }: { exchange: string; data: ExchangeMovers }) {
  const { t } = useTranslation('simulator');
  if (!data.winners.length && !data.losers.length) return null;
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-muted-foreground">{exchange}</h3>
      <div className="grid gap-4 sm:grid-cols-2">
        {data.winners.length > 0 && (
          <div className="rounded-2xl border border-brand-100 bg-card shadow-sm p-3">
            <div className="mb-2 flex items-center gap-1.5 text-success-700">
              <TrendingUp className="h-4 w-4" />
              <span className="text-xs font-semibold uppercase tracking-wide">{t('marketMovers.topGainers')}</span>
            </div>
            <div className="-mx-1 divide-y divide-gray-100">
              {data.winners.map((m, i) => <MoverRow key={`${m.exchange}-${m.ticker}`} mover={m} rank={i + 1} />)}
            </div>
          </div>
        )}
        {data.losers.length > 0 && (
          <div className="rounded-2xl border border-brand-100 bg-card shadow-sm p-3">
            <div className="mb-2 flex items-center gap-1.5 text-danger-700">
              <TrendingDown className="h-4 w-4" />
              <span className="text-xs font-semibold uppercase tracking-wide">{t('marketMovers.topLosers')}</span>
            </div>
            <div className="-mx-1 divide-y divide-gray-100">
              {data.losers.map((m, i) => <MoverRow key={`${m.exchange}-${m.ticker}`} mover={m} rank={i + 1} />)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function MarketMovers({ region }: { region: RegionCode }) {
  const { t } = useTranslation('simulator');
  const { data, isLoading } = useQuery<Record<string, ExchangeMovers> | null>({
    queryKey: ['market-movers', region],
    queryFn: () => simulatorApi.getMarketMovers(region),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-brand-100 bg-card shadow-sm p-4">
        <p className="text-sm text-muted-foreground">{t('marketMovers.loading')}</p>
      </div>
    );
  }

  if (!data || Object.keys(data).length === 0) return null;

  const exchanges = Object.entries(data).sort(([a], [b]) => a.localeCompare(b));

  return (
    <SectionCard title={t('marketMovers.sectionTitle')} icon={TrendingUp}>
      <div className="space-y-5">
        {exchanges.map(([exchange, movers]) => (
          <ExchangeSection key={exchange} exchange={exchange} data={movers} />
        ))}
      </div>
    </SectionCard>
  );
}
