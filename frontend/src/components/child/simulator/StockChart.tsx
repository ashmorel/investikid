import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { simulatorApi, type PricePoint } from '@/api/simulator';
import { ChartDescription } from '@/components/a11y/ChartDescription';

const PERIODS = [
  { key: '1d', label: '1D' },
  { key: '5d', label: '5D' },
  { key: '1mo', label: '1M' },
  { key: '3mo', label: '3M' },
  { key: '6mo', label: '6M' },
  { key: '1y', label: '1Y' },
  { key: '5y', label: '5Y' },
] as const;

type Props = {
  exchange: string;
  ticker: string;
  currency: string;
  onPeriodChange?: (period: string) => void;
};

export function StockChart({ exchange, ticker, currency, onPeriodChange }: Props) {
  const { t } = useTranslation('simulator');
  const [period, setPeriod] = useState('1mo');

  const handlePeriodChange = (p: string) => {
    setPeriod(p);
    onPeriodChange?.(p);
  };

  const { data, isLoading } = useQuery<PricePoint[] | null>({
    queryKey: ['stock-history', exchange, ticker, period],
    queryFn: () => simulatorApi.getStockHistory(exchange, ticker, period),
    staleTime: 5 * 60 * 1000,
  });

  const points = (data ?? []).filter((p) => Number.isFinite(p.close));
  const hasData = points.length >= 2;

  const startPrice = hasData ? points[0].close : 0;
  const endPrice = hasData ? points[points.length - 1].close : 0;
  const change = endPrice - startPrice;
  const changePct = startPrice > 0 ? (change / startPrice) * 100 : 0;
  const isPositive = change >= 0;
  const color = isPositive ? '#16a34a' : '#dc2626';
  const dir = isPositive ? 'rose' : 'fell';
  const chartSummary = hasData
    ? `${ticker} price ${dir} from ${startPrice.toFixed(2)} to ${endPrice.toFixed(2)} (${changePct.toFixed(1)}%) over ${points.length} ${period} points.`
    : `${ticker} price history unavailable for ${period}.`;

  const tickInterval =
    typeof window !== 'undefined' && window.innerWidth < 400
      ? Math.max(Math.floor(points.length / 3), 1)
      : undefined;

  return (
    <div
      className="rounded-2xl border-2 border-brand-200 bg-card p-4"
      role="img"
      aria-label={chartSummary}
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-muted-foreground">{t('stockChart.priceHistory')}</h3>
        {hasData && (
          <span className={`text-sm font-semibold ${isPositive ? 'text-success-600' : 'text-danger-600'}`}>
            {isPositive ? '+' : ''}{change.toFixed(2)} ({isPositive ? '+' : ''}{changePct.toFixed(1)}%)
          </span>
        )}
      </div>

      <div className="mb-3 flex gap-1">
        {PERIODS.map((p) => (
          <button
            key={p.key}
            onClick={() => handlePeriodChange(p.key)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors min-h-[44px] min-w-[44px] ${
              period === p.key
                ? 'bg-brand-600 text-white'
                : 'bg-brand-50 text-muted-foreground hover:bg-brand-100'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
          {t('stockChart.loading')}
        </div>
      ) : !hasData ? (
        <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
          {t('stockChart.noData')}
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={points}>
            <defs>
              <linearGradient id={`stockGrad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.2} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10 }}
              tickFormatter={(d: string) => {
                const date = new Date(d);
                return period === '1d' || period === '5d'
                  ? date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
                  : date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
              }}
              interval={tickInterval ?? 'preserveStartEnd'}
            />
            <YAxis
              hide
              domain={['dataMin', 'dataMax']}
            />
            <Tooltip
              contentStyle={{
                borderRadius: '8px',
                border: '1px solid #bae6fd',
                fontSize: '13px',
              }}
              formatter={(value) => [`${currency === 'GBP' ? '£' : currency === 'HKD' ? 'HK$' : '$'}${Number(value).toFixed(2)}`, 'Close']}
              labelFormatter={(d) => new Date(String(d)).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
            />
            <Area
              type="monotone"
              dataKey="close"
              stroke={color}
              strokeWidth={2}
              fill={`url(#stockGrad-${ticker})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
      {hasData && (
        <ChartDescription
          summary={chartSummary}
          columns={['Date', 'Close']}
          rows={points.map((p) => [String(p.date), p.close.toFixed(2)])}
        />
      )}
    </div>
  );
}
