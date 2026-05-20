import { useState, useCallback, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Search } from 'lucide-react';
import { simulatorApi, type QuoteOut } from '@/api/simulator';
import { EduTooltip } from '@/components/child/simulator/EduTooltip';
import { MarketMovers } from '@/components/child/simulator/MarketMovers';
import { MarketNews } from '@/components/child/simulator/MarketNews';
import { InvestingTips } from '@/components/child/simulator/InvestingTips';
import { formatCurrency } from '@/lib/currency';

const EXCHANGE_BADGE_COLORS: Record<string, string> = {
  NASDAQ: 'bg-blue-100 text-blue-800',
  NYSE: 'bg-indigo-100 text-indigo-800',
  LSE: 'bg-purple-100 text-purple-800',
  HKEX: 'bg-orange-100 text-orange-800',
  TSE: 'bg-pink-100 text-pink-800',
  XETRA: 'bg-teal-100 text-teal-800',
  TSX: 'bg-red-100 text-red-800',
  ASX: 'bg-emerald-100 text-emerald-800',
};

const EXCHANGE_GROUP_LABELS: Record<string, string> = {
  NASDAQ: 'US Stocks',
  NYSE: 'US Stocks',
  LSE: 'UK Stocks',
  HKEX: 'Hong Kong Stocks',
};

function groupByExchange(stocks: QuoteOut[]) {
  const groups: Record<string, QuoteOut[]> = {};
  for (const s of stocks) {
    (groups[s.exchange] ??= []).push(s);
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
}

export default function Market() {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const queryClient = useQueryClient();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    clearTimeout(debounceRef.current);
    const trimmed = query.trim();
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(trimmed);
    }, trimmed.length === 0 ? 0 : 400);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  const { data: featuredStocks, isLoading: featuredLoading } = useQuery<QuoteOut[] | null>({
    queryKey: ['market-featured'],
    queryFn: () => simulatorApi.searchMarket(''),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const { data: searchResults, isFetching: searchFetching } = useQuery<QuoteOut[] | null>({
    queryKey: ['market-search', debouncedQuery],
    queryFn: () => simulatorApi.searchMarket(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    retry: false,
    staleTime: 60 * 1000,
    placeholderData: (prev) => prev,
  });

  const isSearching = debouncedQuery.length >= 2;
  const stocks = isSearching ? (searchResults ?? []) : (featuredStocks ?? []);
  const isLoading = !isSearching && featuredLoading;

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const fresh = await simulatorApi.searchMarket('', true);
      queryClient.setQueryData(['market-featured'], fresh);
    } finally {
      setRefreshing(false);
    }
  }, [queryClient]);

  if (isLoading && stocks.length === 0) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-4 sm:px-6 sm:py-6">
        <p className="text-sm text-muted-foreground">Loading stocks…</p>
      </div>
    );
  }

  const groups = groupByExchange(stocks);

  return (
    <div className="mx-auto max-w-4xl px-4 py-4 sm:px-6 sm:py-6">
      <div className="mb-1 flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Browse Stocks</h1>
        <EduTooltip
          term="Exchange"
          explanation="A stock exchange is a marketplace where stocks are bought and sold. Different countries have different exchanges."
        />
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="ml-auto flex items-center gap-1.5 rounded-lg bg-amber-100 px-3 py-1.5 text-sm font-medium text-amber-700 transition-colors hover:bg-amber-200 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Updating…' : 'Refresh prices'}
        </button>
      </div>
      <p className="mb-4 text-sm text-muted-foreground">
        {isSearching
          ? `${stocks.length} result${stocks.length !== 1 ? 's' : ''} for "${debouncedQuery}"`
          : query.trim().length === 1
            ? 'Type one more character to search…'
            : `${stocks.length} featured stocks — search to find any stock worldwide`}
      </p>

      <div className="relative mb-2">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          role="searchbox"
          aria-label="Search stocks"
          placeholder="Search any stock or company (e.g. Apple, Toyota, Samsung)…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full rounded-lg border bg-white py-2.5 pl-10 pr-4 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-300"
        />
        {searchFetching && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <RefreshCw className="h-4 w-4 animate-spin text-amber-500" />
          </div>
        )}
      </div>

      <div aria-live="polite" className="sr-only">
        {stocks.length} stocks available
      </div>

      {!isSearching && (
        <div className="mt-4 space-y-4">
          <MarketMovers />
          <InvestingTips />
          <MarketNews />
        </div>
      )}

      {stocks.length === 0 ? (
        <p className="mt-6 text-center text-sm text-muted-foreground">
          {isSearching
            ? `No stocks found for "${debouncedQuery}". Try a different name or ticker.`
            : 'No stocks available.'}
        </p>
      ) : (
        <div className="mt-4 space-y-6">
          {groups.map(([exchange, groupStocks]) => (
            <section key={exchange}>
              <h2 className="mb-2 text-sm font-medium text-muted-foreground">
                {EXCHANGE_GROUP_LABELS[exchange] ?? exchange}
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {groupStocks.map((s) => (
                  <Link
                    key={`${s.exchange}-${s.ticker}`}
                    to={`/simulator/stock/${s.exchange}/${s.ticker}`}
                    className="rounded-lg border bg-card p-2 sm:p-3 min-h-[44px] transition-shadow hover:shadow-md"
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
                    <p className="mt-1 text-sm font-medium">
                      {formatCurrency(s.price, s.currency)}
                    </p>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
