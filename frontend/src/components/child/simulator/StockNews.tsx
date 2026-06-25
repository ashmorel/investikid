import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Newspaper, Sparkles } from 'lucide-react';
import { simulatorApi, type StockNews as StockNewsType, type NewsSummary } from '@/api/simulator';

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

type Props = {
  exchange: string;
  ticker: string;
};

export function StockNewsSection({ exchange, ticker }: Props) {
  const { t } = useTranslation('simulator');
  const { data: news, isLoading: newsLoading } = useQuery<StockNewsType[] | null>({
    queryKey: ['stock-news', exchange, ticker],
    queryFn: () => simulatorApi.getStockNews(exchange, ticker),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const { data: summary, isLoading: summaryLoading } = useQuery<NewsSummary | null>({
    queryKey: ['stock-news-summary', exchange, ticker],
    queryFn: () => simulatorApi.getStockNewsSummary(exchange, ticker),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  if (newsLoading) {
    return (
      <div className="rounded-2xl border-2 border-brand-200 bg-card p-4">
        <p className="text-sm text-muted-foreground">{t('stockNews.loading')}</p>
      </div>
    );
  }

  if (!news || news.length === 0) return null;

  return (
    <div className="rounded-2xl border-2 border-brand-200 bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <Newspaper className="h-5 w-5 text-brand-700" />
        <h3 className="text-base font-semibold text-ink">{t('stockNews.heading', { ticker })}</h3>
      </div>

      {summaryLoading ? (
        <div className="mb-4 rounded-xl border border-brand-200 bg-gradient-to-r from-brand-50 to-brand-50 p-4">
          <div className="flex items-center gap-2 text-brand-700">
            <Sparkles className="h-4 w-4 animate-pulse" />
            <span className="text-sm font-medium">{t('stockNews.aiReading')}</span>
          </div>
        </div>
      ) : summary?.summary ? (
        <div className="mb-4 rounded-xl border border-brand-200 bg-gradient-to-r from-brand-50 to-brand-50 p-4">
          <div className="mb-2 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand-600" />
            <span className="text-xs font-semibold uppercase tracking-wide text-brand-700">{t('stockNews.aiSummaryLabel')}</span>
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">{summary.summary}</p>
        </div>
      ) : null}

      <div className="-mx-1 divide-y divide-brand-100">
        {news.slice(0, 5).map((item, i) => (
          <a
            key={`${item.related_ticker}-${i}`}
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex gap-3 rounded-lg p-3 transition-colors hover:bg-brand-50"
          >
            {item.thumbnail && (
              <img
                src={item.thumbnail}
                alt=""
                className="h-14 w-20 flex-shrink-0 rounded-md object-cover"
              />
            )}
            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 text-sm font-medium leading-snug">{item.title}</p>
              <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                {item.publisher && <span>{item.publisher}</span>}
                {item.publisher && item.published && <span>·</span>}
                {item.published && <span>{timeAgo(item.published)}</span>}
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
