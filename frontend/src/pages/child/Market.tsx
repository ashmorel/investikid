import { useState, useCallback, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Search } from 'lucide-react';
import { simulatorApi, type QuoteOut, type MarketSnapshot } from '@/api/simulator';
import { authApi, type Me } from '@/api/auth';
import { REGION_EXCHANGES, toRegionCode, type RegionCode } from '@/lib/region';
import { RegionSelector } from '@/components/child/simulator/RegionSelector';
import { MarketMovers } from '@/components/child/simulator/MarketMovers';
import { MarketNews } from '@/components/child/simulator/MarketNews';
import { InvestingTips } from '@/components/child/simulator/InvestingTips';
import { BackButton } from '@/components/child/BackButton';
import { OfflineNotice } from '@/components/child/OfflineNotice';
import { SectionCard } from '@/components/child/simulator/SectionCard';
import { formatCurrency } from '@/lib/currency';
import { useOnline } from '@/hooks/useOnline';

const EXCHANGE_BADGE_COLORS: Record<string, string> = {
  NASDAQ: 'bg-info-100 text-info-600',
  NYSE: 'bg-brand-100 text-brand-700',
  LSE: 'bg-brand-100 text-brand-700',
  HKEX: 'bg-brand-200 text-brand-800',
  TSE: 'bg-brand-100 text-brand-700',
  XETRA: 'bg-brand-100 text-brand-700',
  TSX: 'bg-success-100 text-success-700',
  ASX: 'bg-success-100 text-success-700',
};

const EXCHANGE_GROUP_LABELS: Record<string, string> = {
  NASDAQ: 'US Stocks',
  NYSE: 'US Stocks',
  LSE: 'UK Stocks',
  HKEX: 'Hong Kong Stocks',
};

export function groupByExchange(stocks: QuoteOut[], priority: string[] = []) {
  const groups: Record<string, QuoteOut[]> = {};
  for (const s of stocks) {
    (groups[s.exchange] ??= []).push(s);
  }
  const rank = (ex: string) => {
    const i = priority.indexOf(ex);
    return i === -1 ? priority.length : i;
  };
  return Object.entries(groups).sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b));
}

/** Merge exchange-keyed groups that share a country label (e.g. NASDAQ + NYSE
 *  → "US Stocks") into one group, preserving the incoming priority order. */
function mergeByLabel(groups: [string, QuoteOut[]][]): [string, QuoteOut[]][] {
  const order: string[] = [];
  const byLabel: Record<string, QuoteOut[]> = {};
  for (const [exchange, stocks] of groups) {
    const label = EXCHANGE_GROUP_LABELS[exchange] ?? exchange;
    if (!(label in byLabel)) {
      byLabel[label] = [];
      order.push(label);
    }
    byLabel[label].push(...stocks);
  }
  return order.map((label) => [label, byLabel[label]]);
}

function BrowseGroup({
  title,
  stocks,
  headingLevel = 2,
}: {
  title: string;
  stocks: QuoteOut[];
  headingLevel?: 2 | 3;
}) {
  const Heading = headingLevel === 3 ? 'h3' : 'h2';
  return (
    <section>
      <Heading className="mb-2 flex items-center gap-2 text-sm font-extrabold uppercase tracking-wider text-muted-foreground">
        {title}
        <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700">
          {stocks.length}
        </span>
      </Heading>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {stocks.map((s) => (
          <Link
            key={`${s.exchange}-${s.ticker}`}
            to={`/simulator/stock/${s.exchange}/${s.ticker}`}
            className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm hover:border-brand-400 hover:shadow-md transition-all min-h-[44px]"
          >
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold">{s.ticker}</span>
              <span
                className={`rounded px-1.5 py-0.5 text-xs font-medium ${EXCHANGE_BADGE_COLORS[s.exchange] ?? 'bg-muted text-muted-foreground'}`}
              >
                {s.exchange}
              </span>
            </div>
            <p className="mt-1 truncate text-sm text-muted-foreground">{s.name}</p>
            <p className="mt-1 text-sm font-medium">{formatCurrency(s.price, s.currency)}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}

export default function Market() {
  const { t } = useTranslation('simulator');
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const queryClient = useQueryClient();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const online = useOnline();

  const { data: me } = useQuery<Me | null>({
    queryKey: ['me'],
    queryFn: () => authApi.me(),
    staleTime: 60_000,
  });
  const [selectedRegion, setSelectedRegion] = useState<RegionCode | null>(null);
  const region = selectedRegion ?? toRegionCode(me?.content_region ?? me?.country_code);
  const priorityExchanges = REGION_EXCHANGES[region] ?? [];

  useEffect(() => {
    clearTimeout(debounceRef.current);
    const trimmed = query.trim();
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(trimmed);
    }, trimmed.length === 0 ? 0 : 400);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  const { data: snapshot, isLoading: featuredLoading } = useQuery<MarketSnapshot | null>({
    queryKey: ['market-snapshot', region],
    queryFn: () => simulatorApi.getSnapshot(region),
    retry: false,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
  const featuredStocks = snapshot?.featured ?? null;

  const { data: searchResults, isFetching: searchFetching } = useQuery<QuoteOut[] | null>({
    queryKey: ['market-search', debouncedQuery],
    queryFn: () => simulatorApi.searchMarket(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    retry: false,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    placeholderData: (prev) => prev,
  });

  const isSearching = debouncedQuery.length >= 2;
  const stocks = isSearching ? (searchResults ?? []) : (featuredStocks ?? []);
  const isLoading = !isSearching && featuredLoading;

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await queryClient.invalidateQueries({ queryKey: ['market-snapshot', region] });
    } finally {
      setRefreshing(false);
    }
  }, [queryClient, region]);

  if (isLoading && stocks.length === 0) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-4 sm:px-6 sm:py-6">
        <BackButton to="/simulator" label={t('market.backLabel')} />
        {online ? (
          <p className="mt-2 text-sm text-muted-foreground">{t('market.loading')}</p>
        ) : (
          <OfflineNotice className="mt-3" />
        )}
      </div>
    );
  }

  // Group by exchange (priority-ordered), then merge same-country exchanges
  // (e.g. NASDAQ + NYSE → one "US Stocks" section).
  const groups = mergeByLabel(groupByExchange(stocks, priorityExchanges));
  const selectedLabels = new Set(
    priorityExchanges.map((ex) => EXCHANGE_GROUP_LABELS[ex] ?? ex),
  );
  const selectedGroups = isSearching ? groups : groups.filter(([label]) => selectedLabels.has(label));
  const otherGroups = isSearching ? [] : groups.filter(([label]) => !selectedLabels.has(label));
  const otherCount = otherGroups.reduce((n, [, s]) => n + s.length, 0);
  // Curated featured lists read as "Popular …"; search results keep the plain label.
  const browseTitle = (label: string) => (isSearching ? label : `${t('market.popularPrefix')}${label}`);

  return (
    <div className="mx-auto max-w-4xl px-4 py-4 sm:px-6 sm:py-6">
      <BackButton to="/simulator" label={t('market.backLabel')} />
      {!online && <OfflineNotice className="mt-3" />}
      <div className="mb-1 mt-2 flex items-center gap-2">
        <h1 className="text-2xl font-semibold">{t('market.heading')}</h1>
        <RegionSelector value={region} onChange={setSelectedRegion} />
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="ml-auto flex items-center gap-1.5 rounded-lg bg-brand-100 px-3 py-1.5 text-sm font-medium text-brand-700 transition-colors hover:bg-brand-200 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? t('market.refreshing') : t('market.refreshPrices')}
        </button>
      </div>
      <p className="mb-4 text-sm text-muted-foreground">
        {isSearching
          ? t(stocks.length !== 1 ? 'market.searchResultsPlural' : 'market.searchResults', { count: stocks.length, query: debouncedQuery })
          : query.trim().length === 1
            ? t('market.searchTypeMore')
            : t('market.featuredSummary', { count: stocks.length })}
      </p>

      <div className="relative mb-2">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          role="searchbox"
          aria-label={t('market.searchLabel')}
          placeholder={t('market.searchPlaceholder')}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full rounded-lg border bg-white py-2.5 pl-10 pr-4 text-base placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand-300"
        />
        {searchFetching && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <RefreshCw className="h-4 w-4 animate-spin text-brand-600" />
          </div>
        )}
      </div>

      <div aria-live="polite" className="sr-only">
        {t('market.stocksAvailable', { count: stocks.length })}
      </div>

      {!isSearching && (
        <div className="mt-4">
          <MarketMovers region={region} />
        </div>
      )}

      {stocks.length === 0 && isSearching && searchFetching ? (
        <p role="status" className="mt-6 text-center text-sm text-muted-foreground">
          {t('market.searching')}
        </p>
      ) : stocks.length === 0 ? (
        <p className="mt-6 text-center text-sm text-muted-foreground">
          {isSearching
            ? t('market.noResultsSearch', { query: debouncedQuery })
            : t('market.noStocks')}
        </p>
      ) : (
        <div className="mt-4 space-y-6">
          {selectedGroups.map(([label, groupStocks]) => (
            <BrowseGroup key={label} title={browseTitle(label)} stocks={groupStocks} />
          ))}
          {otherGroups.length > 0 && (
            <SectionCard title={t('market.moreMarkets')} count={otherCount} collapsible defaultOpen={false}>
              <div className="space-y-6">
                {otherGroups.map(([label, groupStocks]) => (
                  <BrowseGroup key={label} title={browseTitle(label)} stocks={groupStocks} headingLevel={3} />
                ))}
              </div>
            </SectionCard>
          )}
        </div>
      )}

      {!isSearching && (
        <div className="mt-4 space-y-4">
          <InvestingTips />
          <MarketNews />
        </div>
      )}
    </div>
  );
}
