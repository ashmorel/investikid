import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { GraduationCap, Sparkles } from 'lucide-react';
import { simulatorApi, type NewsSummary } from '@/api/simulator';

type Props = {
  exchange: string;
  ticker: string;
  period: string;
  onAskPenny?: () => void;
};

const CHART_TIP_KEYS = ['trend', 'colour', 'timePeriods', 'shadedArea'] as const;

export function ChartGuide({ exchange, ticker, period, onAskPenny }: Props) {
  const { t } = useTranslation('simulator');
  const { data, isLoading } = useQuery<NewsSummary | null>({
    queryKey: ['chart-guide', exchange, ticker, period],
    queryFn: () => simulatorApi.getChartGuide(exchange, ticker, period),
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  const tipKey = CHART_TIP_KEYS[(ticker.charCodeAt(0) + period.length) % CHART_TIP_KEYS.length];

  return (
    <div className="rounded-2xl border-2 border-info-100 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <GraduationCap className="h-5 w-5 text-info-600" />
        <h3 className="text-base font-semibold text-gray-800">{t('chartGuide.heading')}</h3>
      </div>

      {isLoading ? (
        <div className="mb-3 rounded-xl border border-purple-200 bg-gradient-to-r from-purple-50 to-blue-50 p-3">
          <div className="flex items-center gap-2 text-purple-700">
            <Sparkles className="h-4 w-4 animate-pulse" />
            <span className="text-sm font-medium">{t('chartGuide.aiAnalysing')}</span>
          </div>
        </div>
      ) : data?.summary ? (
        <div className="mb-3 rounded-xl border border-purple-200 bg-gradient-to-r from-purple-50 to-blue-50 p-3">
          <div className="mb-1.5 flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-purple-600" />
            <span className="text-xs font-semibold uppercase tracking-wide text-purple-700">{t('chartGuide.aiInsightLabel')}</span>
          </div>
          <p className="text-sm leading-relaxed text-gray-700">{data.summary}</p>
        </div>
      ) : null}

      <div className="rounded-lg bg-info-100 p-3">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-info-600">{t(`chartGuide.tips.${tipKey}.title`)}</p>
        <p className="text-sm leading-relaxed text-gray-700">{t(`chartGuide.tips.${tipKey}.tip`)}</p>
      </div>
      {onAskPenny && (
        <button
          onClick={onAskPenny}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-full bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
        >
          <span>💡</span>
          {t('chartGuide.askPenny')}
        </button>
      )}
    </div>
  );
}
