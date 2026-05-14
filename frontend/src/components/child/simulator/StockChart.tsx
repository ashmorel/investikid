import { useState } from 'react';
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
};

export function StockChart({ exchange, ticker, currency }: Props) {
  const [period, setPeriod] = useState('1mo');

  const { data, isLoading } = useQuery<PricePoint[] | null>({
    queryKey: ['stock-history', exchange, ticker, period],
    queryFn: () => simulatorApi.getStockHistory(exchange, ticker, period),
    staleTime: 5 * 60 * 1000,
  });

  const points = data ?? [];
  const hasData = points.length >= 2;

  const startPrice = hasData ? points[0].close : 0;
  const endPrice = hasData ? points[points.length - 1].close : 0;
  const change = endPrice - startPrice;
  const changePct = startPrice > 0 ? (change / startPrice) * 100 : 0;
  const isPositive = change >= 0;
  const color = isPositive ? '#16a34a' : '#dc2626';

  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">Price History</h3>
        {hasData && (
          <span className={`text-sm font-semibold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {isPositive ? '+' : ''}{change.toFixed(2)} ({isPositive ? '+' : ''}{changePct.toFixed(1)}%)
          </span>
        )}
      </div>

      <div className="mb-3 flex gap-1">
        {PERIODS.map((p) => (
          <button
            key={p.key}
            onClick={() => setPeriod(p.key)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              period === p.key
                ? 'bg-amber-500 text-white'
                : 'bg-amber-50 text-gray-600 hover:bg-amber-100'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
          Loading chart…
        </div>
      ) : !hasData ? (
        <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
          No price data available for this period
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
              interval="preserveStartEnd"
            />
            <YAxis
              hide
              domain={['dataMin', 'dataMax']}
            />
            <Tooltip
              contentStyle={{
                borderRadius: '8px',
                border: '1px solid #fde68a',
                fontSize: '13px',
              }}
              formatter={(value: number) => [`${currency === 'GBP' ? '£' : currency === 'HKD' ? 'HK$' : '$'}${value.toFixed(2)}`, 'Close']}
              labelFormatter={(d: string) => new Date(d).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
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
    </div>
  );
}
