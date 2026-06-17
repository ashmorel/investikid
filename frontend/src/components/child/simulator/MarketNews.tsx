import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Newspaper, Sparkles } from 'lucide-react';
import { simulatorApi, type StockNews, type NewsSummary } from '@/api/simulator';
import { SectionCard } from './SectionCard';

function timeAgo(dateStr: string): string {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function NewsCard({ item }: { item: StockNews }) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex gap-3 rounded-lg p-3 transition-colors hover:bg-brand-50"
    >
      {item.thumbnail && (
        <img
          src={item.thumbnail}
          alt=""
          className="h-16 w-24 flex-shrink-0 rounded-md object-cover"
        />
      )}
      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-sm font-medium leading-snug">{item.title}</p>
        {item.summary && (
          <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{item.summary}</p>
        )}
        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
          {item.publisher && <span>{item.publisher}</span>}
          {item.publisher && item.published && <span>·</span>}
          {item.published && <span>{timeAgo(item.published)}</span>}
          <span className="rounded bg-brand-100 px-1.5 py-0.5 text-xs font-medium text-brand-700">
            {item.related_ticker}
          </span>
        </div>
      </div>
    </a>
  );
}

function AiSummary() {
  const { t } = useTranslation('simulator');
  const { data, isLoading } = useQuery<NewsSummary | null>({
    queryKey: ['news-summary'],
    queryFn: () => simulatorApi.getNewsSummary(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="mb-4 rounded-xl border border-purple-200 bg-gradient-to-r from-purple-50 to-brand-50 p-4">
        <div className="flex items-center gap-2 text-purple-700">
          <Sparkles className="h-4 w-4 animate-pulse" />
          <span className="text-sm font-medium">{t('marketNews.aiReading')}</span>
        </div>
      </div>
    );
  }

  if (!data || !data.summary) return null;

  return (
    <div className="mb-4 rounded-xl border border-purple-200 bg-gradient-to-r from-purple-50 to-brand-50 p-4">
      <div className="mb-2 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-purple-600" />
        <span className="text-xs font-semibold uppercase tracking-wide text-purple-700">{t('marketNews.aiSummaryLabel')}</span>
      </div>
      <p className="text-sm leading-relaxed text-gray-700">{data.summary}</p>
      {data.tickers_mentioned.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {data.tickers_mentioned.map((ticker) => (
            <span key={ticker} className="rounded bg-purple-100 px-1.5 py-0.5 text-xs font-medium text-purple-700">
              {ticker}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function MarketNews() {
  const { t } = useTranslation('simulator');
  const { data, isLoading } = useQuery<StockNews[] | null>({
    queryKey: ['market-news'],
    queryFn: () => simulatorApi.getMarketNews(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-brand-100 bg-card shadow-sm p-4">
        <p className="text-sm text-muted-foreground">{t('marketNews.loading')}</p>
      </div>
    );
  }

  if (!data || data.length === 0) return null;

  return (
    <SectionCard title={t('marketNews.sectionTitle')} icon={Newspaper} collapsible defaultOpen={false}>
      <AiSummary />
      <div className="-mx-1 divide-y divide-gray-100">
        {data.map((item, i) => (
          <NewsCard key={`${item.related_ticker}-${i}`} item={item} />
        ))}
      </div>
    </SectionCard>
  );
}
