import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Clock, BookOpen } from 'lucide-react';
import { simulatorApi, type TimeMachineData } from '@/api/simulator';
import { ApiError } from '@/api/client';

type Props = {
  exchange: string;
  ticker: string;
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

export function InvestmentTimeMachine({ exchange, ticker }: Props) {
  const { t } = useTranslation('simulator');
  const { data, isLoading } = useQuery<TimeMachineData | null, ApiError>({
    queryKey: ['time-machine', exchange, ticker],
    queryFn: () => simulatorApi.getTimeMachine(exchange, ticker),
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="rounded-2xl border-2 border-brand-200 bg-card p-4">
        <div className="mb-3 flex items-center gap-2">
          <div className="h-5 w-5 animate-pulse rounded bg-brand-200" />
          <div className="h-4 w-40 animate-pulse rounded bg-brand-100" />
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="rounded-xl bg-brand-50 p-3 text-center">
              <div className="mx-auto h-3 w-16 animate-pulse rounded bg-brand-200" />
              <div className="mx-auto my-2 h-6 w-20 animate-pulse rounded bg-brand-200" />
              <div className="mx-auto h-3 w-10 animate-pulse rounded bg-brand-100" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!data || data.periods.length === 0) return null;

  return (
    <div className="rounded-2xl border-2 border-brand-200 bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <Clock className="h-5 w-5 text-brand-600" />
        <h3 className="text-base font-semibold text-ink">{t('timeMachine.heading')}</h3>
      </div>

      <p className="mb-3 text-sm text-muted-foreground">
        {t('timeMachine.hypothetical', { ticker })}
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {data.periods.map((p) => (
          <div
            key={p.years_ago}
            className="rounded-xl bg-brand-50 p-3 text-center"
          >
            <div className="text-xs font-semibold text-brand-700">
              {t('timeMachine.yearsAgo', { n: p.years_ago })}
            </div>
            <div className="my-1 text-xl font-bold text-success-600">
              {formatValue(p.current_value, p.currency)}
            </div>
            <div className="text-xs text-muted-foreground">
              +{p.return_pct.toFixed(0)}%
            </div>
            {p.usd_equivalent && (
              <div className="mt-1 text-xs text-muted-foreground">
                {t('timeMachine.usdEquivalent', { local: formatValue(p.current_value, p.currency), usd: parseFloat(p.usd_equivalent).toLocaleString(undefined, { maximumFractionDigits: 0 }) })}
              </div>
            )}
          </div>
        ))}
      </div>

      {data.fun_fact && (
        <div className="mt-3 rounded-lg bg-brand-50 p-3">
          <div className="flex items-start gap-2">
            <BookOpen className="mt-0.5 h-4 w-4 flex-shrink-0 text-brand-700" />
            <p className="text-sm text-brand-900">
              <span className="font-semibold">{t('timeMachine.didYouKnow')}</span> {data.fun_fact}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
