import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Lightbulb, Pause, Play } from 'lucide-react';
import { simulatorApi, type InvestingTip, type PricePoint } from '@/api/simulator';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { SectionCard } from './SectionCard';

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

const ROTATE_MS = 7000;

export function InvestingTips({ contextTicker, contextExchange }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [paused, setPaused] = useState(false); // transient hover/focus pause
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');

  const { data: tips } = useQuery<InvestingTip[] | null>({
    queryKey: ['investing-tips'],
    queryFn: () => simulatorApi.getInvestingTips(),
    staleTime: 30 * 60 * 1000,
  });

  const count = tips?.length ?? 0;
  const autoRotate = isPlaying && !paused && !reducedMotion && count > 1;

  function scrollToIndex(i: number) {
    const el = scrollRef.current;
    if (el) el.scrollTo({ left: i * el.clientWidth * 0.65, behavior: 'smooth' });
  }

  function goToIndex(i: number) {
    setActiveIndex(i);
    scrollToIndex(i);
  }

  useEffect(() => {
    if (!autoRotate) return;
    const id = window.setInterval(() => {
      setActiveIndex((prev) => {
        const next = (prev + 1) % count;
        scrollToIndex(next);
        return next;
      });
    }, ROTATE_MS);
    return () => window.clearInterval(id);
  }, [autoRotate, count]);

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
    <SectionCard title="Investing Tips" icon={Lightbulb} collapsible defaultOpen headingLevel={3}>
      {!reducedMotion && count > 1 && (
        <div className="mb-2 flex justify-end">
          <button
            type="button"
            onClick={() => setIsPlaying((p) => !p)}
            aria-label={isPlaying ? 'Pause tips' : 'Play tips'}
            className="inline-flex h-7 w-7 items-center justify-center rounded-full text-brand-700 hover:bg-brand-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
        </div>
      )}

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        onFocus={() => setPaused(true)}
        onBlur={() => setPaused(false)}
        role="group"
        aria-label="Investing tips"
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
          <button
            key={i}
            type="button"
            onClick={() => goToIndex(i)}
            aria-label={`Go to tip ${i + 1}`}
            aria-current={i === activeIndex}
            className="inline-flex h-6 w-6 items-center justify-center rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
          >
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${
                i === activeIndex ? 'bg-brand-500' : 'bg-gray-200'
              }`}
            />
          </button>
        ))}
      </div>
    </SectionCard>
  );
}
