import { useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Lightbulb } from 'lucide-react';
import { simulatorApi, type InvestingTip, type PricePoint } from '@/api/simulator';

function MiniChart({ exchange, ticker }: { exchange: string; ticker: string }) {
  const { data } = useQuery<PricePoint[] | null>({
    queryKey: ['stock-history', exchange, ticker, '5y'],
    queryFn: () => simulatorApi.getStockHistory(exchange, ticker, '5y'),
    staleTime: 30 * 60 * 1000,
  });

  const points = data ?? [];
  if (points.length < 2) {
    return (
      <div className="flex h-12 items-center justify-center rounded-md bg-brand-100 text-xs text-brand-700">
        Loading chart…
      </div>
    );
  }

  const isPositive = points[points.length - 1].close >= points[0].close;
  const color = isPositive ? '#16a34a' : '#dc2626';

  return (
    <ResponsiveContainer width="100%" height={48}>
      <AreaChart data={points}>
        <defs>
          <linearGradient id={`tipGrad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="close"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#tipGrad-${ticker})`}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

type Props = {
  contextTicker?: string;
  contextExchange?: string;
};

export function InvestingTips({ contextTicker, contextExchange }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  const { data: tips } = useQuery<InvestingTip[] | null>({
    queryKey: ['investing-tips'],
    queryFn: () => simulatorApi.getInvestingTips(),
    staleTime: 30 * 60 * 1000,
  });

  if (!tips) {
    return (
      <div className="rounded-2xl border border-brand-100 bg-card shadow-sm p-4">
        <div className="mb-3 flex items-center gap-2">
          <div className="h-5 w-5 animate-pulse rounded bg-brand-200" />
          <div className="h-4 w-28 animate-pulse rounded bg-brand-100" />
        </div>
        <div className="flex gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="min-w-[220px] rounded-xl border border-brand-200 bg-brand-50 p-3">
              <div className="mb-2 h-3 w-24 animate-pulse rounded bg-brand-200" />
              <div className="mb-1 h-2 w-full animate-pulse rounded bg-brand-100" />
              <div className="mb-2 h-2 w-3/4 animate-pulse rounded bg-brand-100" />
              <div className="h-12 animate-pulse rounded-md bg-brand-100" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (tips.length === 0) return null;

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollLeft, clientWidth } = scrollRef.current;
    const idx = Math.round(scrollLeft / (clientWidth * 0.65));
    setActiveIndex(Math.min(idx, tips.length - 1));
  };

  return (
    <div className="rounded-2xl border-2 border-brand-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <Lightbulb className="h-5 w-5 text-brand-700" />
        <h3 className="text-base font-semibold text-gray-800">Investing Tips</h3>
      </div>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex gap-3 overflow-x-auto scroll-smooth pb-2"
        style={{ scrollSnapType: 'x mandatory' }}
      >
        {tips.map((tip) => {
          const chartTicker = contextTicker ?? tip.example_ticker;
          const chartExchange = contextExchange ?? tip.example_exchange;
          return (
            <div
              key={tip.id}
              className="min-w-[220px] max-w-[260px] flex-shrink-0 rounded-xl border border-brand-200 bg-brand-50 p-3"
              style={{ scrollSnapAlign: 'start' }}
            >
              <h4 className="mb-1.5 text-xs font-bold text-brand-800">{tip.title}</h4>
              <p className="mb-2 text-xs leading-relaxed text-gray-700">{tip.description}</p>
              <div className="overflow-hidden rounded-md">
                <MiniChart exchange={chartExchange} ticker={chartTicker} />
              </div>
              <p className="mt-1 text-center text-[10px] text-gray-400">
                {chartTicker} · 5yr
              </p>
            </div>
          );
        })}
      </div>

      <div className="mt-2 flex justify-center gap-1">
        {tips.map((_, i) => (
          <span
            key={i}
            className={`inline-block h-1.5 w-1.5 rounded-full ${
              i === activeIndex ? 'bg-brand-500' : 'bg-gray-200'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
