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
};

export function PortfolioChart({ history }: Props) {
  if (!Array.isArray(history) || history.length < 2) return null;

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

  return (
    <div
      className="mt-4 rounded-2xl border-2 border-amber-200 bg-white p-4"
      role="img"
      aria-label={summary}
    >
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Portfolio Value</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={history}>
          <defs>
            <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={tickInterval ?? 'preserveStartEnd'} />
          <YAxis hide />
          <Tooltip
            contentStyle={{
              borderRadius: '8px',
              border: '1px solid #fde68a',
              fontSize: '13px',
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#f59e0b"
            strokeWidth={2}
            fill="url(#portfolioGrad)"
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
