import { useQuery } from '@tanstack/react-query';
import { GraduationCap, Sparkles } from 'lucide-react';
import { simulatorApi, type NewsSummary } from '@/api/simulator';

type Props = {
  exchange: string;
  ticker: string;
  period: string;
  onAskPenny?: () => void;
};

const CHART_TIPS = [
  {
    title: 'Reading the trend',
    tip: 'If the line goes up from left to right, the price has been rising. If it goes down, the price has been falling. The steeper the line, the faster the change.',
  },
  {
    title: 'Green vs Red',
    tip: 'A green chart means the price is higher now than at the start of the period — the stock gained value. Red means it lost value. Neither is permanently good or bad!',
  },
  {
    title: 'Time periods matter',
    tip: 'A stock might look bad on a 1-day chart but great on a 1-year chart. Always check multiple time periods before forming an opinion.',
  },
  {
    title: 'The shaded area',
    tip: 'The coloured area under the line helps you see the overall trend at a glance. A large shaded area that grows means steady gains over time.',
  },
];

export function ChartGuide({ exchange, ticker, period, onAskPenny }: Props) {
  const { data, isLoading } = useQuery<NewsSummary | null>({
    queryKey: ['chart-guide', exchange, ticker, period],
    queryFn: () => simulatorApi.getChartGuide(exchange, ticker, period),
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  const tipIndex = (ticker.charCodeAt(0) + period.length) % CHART_TIPS.length;
  const staticTip = CHART_TIPS[tipIndex];

  return (
    <div className="rounded-2xl border-2 border-blue-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <GraduationCap className="h-5 w-5 text-blue-600" />
        <h3 className="text-base font-semibold text-gray-800">Learn to Read Charts</h3>
      </div>

      {isLoading ? (
        <div className="mb-3 rounded-xl border border-purple-200 bg-gradient-to-r from-purple-50 to-blue-50 p-3">
          <div className="flex items-center gap-2 text-purple-700">
            <Sparkles className="h-4 w-4 animate-pulse" />
            <span className="text-sm font-medium">AI is analysing this chart for you…</span>
          </div>
        </div>
      ) : data?.summary ? (
        <div className="mb-3 rounded-xl border border-purple-200 bg-gradient-to-r from-purple-50 to-blue-50 p-3">
          <div className="mb-1.5 flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-purple-600" />
            <span className="text-xs font-semibold uppercase tracking-wide text-purple-700">AI Chart Insight</span>
          </div>
          <p className="text-sm leading-relaxed text-gray-700">{data.summary}</p>
        </div>
      ) : null}

      <div className="rounded-lg bg-blue-50 p-3">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-blue-700">{staticTip.title}</p>
        <p className="text-sm leading-relaxed text-gray-700">{staticTip.tip}</p>
      </div>
      {onAskPenny && (
        <button
          onClick={onAskPenny}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-full bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-amber-600"
        >
          <span>💡</span>
          Ask Coach Penny about this chart
        </button>
      )}
    </div>
  );
}
