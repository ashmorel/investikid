import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import type { PortfolioSnapshot } from '@/api/simulator';

type Props = {
  history: PortfolioSnapshot[];
};

export function PortfolioChart({ history }: Props) {
  if (history.length < 2) return null;

  return (
    <div className="mt-4 rounded-2xl border-2 border-amber-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Portfolio Value</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={history}>
          <defs>
            <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
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
    </div>
  );
}
