import { useTranslation } from 'react-i18next';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import type { PortfolioSnapshot } from '@/api/simulator';
import { ChartDescription } from '@/components/a11y/ChartDescription';

type Props = {
  history: PortfolioSnapshot[];
  variant?: 'card' | 'onGradient';
};

export function PortfolioChart({ history, variant = 'card' }: Props) {
  const { t } = useTranslation('simulator');
  if (!Array.isArray(history) || history.length < 2) return null;

  const onGrad = variant === 'onGradient';

  const start = history[0].value;
  const end = history[history.length - 1].value;
  const delta = end - start;
  const pct = start > 0 ? (delta / start) * 100 : 0;
  const dir = delta >= 0 ? 'rose' : 'fell';
  const summary = `Portfolio ${dir} from ${start.toFixed(2)} to ${end.toFixed(2)} (${pct.toFixed(1)}%) across ${history.length} points.`;

  const tickInterval =
    typeof window !== 'undefined' && window.innerWidth < 400
      ? Math.max(Math.floor(history.length / 3), 1)
      : undefined;

  const gradId = onGrad ? 'portfolioGradLight' : 'portfolioGrad';

  return (
    <div
      className={onGrad ? '' : 'mt-4 rounded-2xl border-2 border-brand-200 bg-white p-4'}
      role="img"
      aria-label={summary}
    >
      {!onGrad && (
        <h3 className="mb-3 text-sm font-semibold text-gray-700">{t('portfolioChart.heading')}</h3>
      )}
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={history}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              {onGrad ? (
                <>
                  <stop offset="0%" stopColor="#ffffff" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#ffffff" stopOpacity={0} />
                </>
              ) : (
                <>
                  <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0} />
                </>
              )}
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: onGrad ? 'rgba(255,255,255,0.85)' : undefined }}
            interval={tickInterval ?? 'preserveStartEnd'}
          />
          <YAxis hide />
          <Tooltip
            contentStyle={{
              borderRadius: '8px',
              border: '1px solid #bae6fd',
              fontSize: '13px',
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={onGrad ? '#ffffff' : '#0ea5e9'}
            strokeWidth={2}
            fill={`url(#${gradId})`}
          />
        </AreaChart>
      </ResponsiveContainer>
      <ChartDescription
        summary={summary}
        columns={['Date', 'Value']}
        rows={history.map((p) => [String(p.date), p.value.toFixed(2)])}
      />
    </div>
  );
}
