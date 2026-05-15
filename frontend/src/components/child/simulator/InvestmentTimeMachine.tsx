import { useQuery } from '@tanstack/react-query';
import { Clock, BookOpen } from 'lucide-react';
import { simulatorApi, type TimeMachineData } from '@/api/simulator';
import { ApiError } from '@/api/client';

type Props = {
  exchange: string;
  ticker: string;
  currency: string;
};

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  GBP: '£',
  HKD: 'HK$',
  EUR: '€',
  JPY: '¥',
  CAD: 'C$',
  AUD: 'A$',
};

function formatValue(value: string, currency: string): string {
  const sym = CURRENCY_SYMBOLS[currency] ?? '$';
  const num = parseFloat(value);
  if (num >= 1000) {
    return `${sym}${num.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  }
  return `${sym}${num.toFixed(2)}`;
}

export function InvestmentTimeMachine({ exchange, ticker, currency }: Props) {
  const { data, isLoading } = useQuery<TimeMachineData | null, ApiError>({
    queryKey: ['time-machine', exchange, ticker],
    queryFn: () => simulatorApi.getTimeMachine(exchange, ticker),
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="rounded-2xl border-2 border-purple-200 bg-white p-4">
        <p className="text-sm text-muted-foreground">Calculating historical returns…</p>
      </div>
    );
  }

  if (!data || data.periods.length === 0) return null;

  return (
    <div className="rounded-2xl border-2 border-purple-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <Clock className="h-5 w-5 text-purple-600" />
        <h3 className="text-base font-semibold text-gray-800">Investment Time Machine</h3>
      </div>

      <p className="mb-3 text-sm text-gray-600">
        If you'd invested $5,000 in {ticker}…
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {data.periods.map((p) => (
          <div
            key={p.years_ago}
            className="rounded-xl bg-purple-50 p-3 text-center"
          >
            <div className="text-xs font-semibold text-purple-700">
              {p.years_ago} years ago
            </div>
            <div className="my-1 text-xl font-bold text-green-600">
              {formatValue(p.current_value, p.currency)}
            </div>
            <div className="text-xs text-gray-500">
              +{p.return_pct.toFixed(0)}%
            </div>
            {p.usd_equivalent && (
              <div className="mt-1 text-xs text-gray-400">
                {formatValue(p.current_value, p.currency)} · ${parseFloat(p.usd_equivalent).toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            )}
          </div>
        ))}
      </div>

      {data.fun_fact && (
        <div className="mt-3 rounded-lg bg-amber-50 p-3">
          <div className="flex items-start gap-2">
            <BookOpen className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
            <p className="text-sm text-amber-900">
              <span className="font-semibold">Did you know?</span> {data.fun_fact}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
