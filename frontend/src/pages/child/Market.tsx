import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { simulatorApi, type QuoteOut } from '@/api/simulator';
import { MarketSearchBar } from '@/components/child/simulator/MarketSearchBar';
import { EduTooltip } from '@/components/child/simulator/EduTooltip';
import { formatCurrency } from '@/lib/currency';

const EXCHANGE_GROUPS = [
  { key: 'NASDAQ', label: 'US Stocks (NASDAQ)' },
  { key: 'LSE', label: 'UK Stocks (LSE)' },
  { key: 'HKEX', label: 'Hong Kong Stocks (HKEX)' },
] as const;

const EXCHANGE_BADGE_COLORS: Record<string, string> = {
  NASDAQ: 'bg-blue-100 text-blue-800',
  LSE: 'bg-purple-100 text-purple-800',
  HKEX: 'bg-orange-100 text-orange-800',
};

export default function Market() {
  const [query, setQuery] = useState('');

  const { data: allStocks, isLoading, isError } = useQuery<QuoteOut[] | null>({
    queryKey: ['market-search'],
    queryFn: () => simulatorApi.searchMarket(''),
    retry: false,
    staleTime: Infinity,
  });

  const stocks = allStocks ?? [];
  const filtered = query.trim()
    ? stocks.filter(
        (s) =>
          s.ticker.toLowerCase().includes(query.toLowerCase()) ||
          s.name.toLowerCase().includes(query.toLowerCase()),
      )
    : stocks;

  const resultCount = filtered.length;

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-muted-foreground">Loading stocks…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-red-600">Couldn't load stocks. Try again.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-1 flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Browse Stocks</h1>
        <EduTooltip
          term="Exchange"
          explanation="A stock exchange is a marketplace where stocks are bought and sold. Different countries have different exchanges."
        />
      </div>
      <p className="mb-4 text-sm text-muted-foreground">
        {stocks.length} stocks available in practice mode
      </p>

      <MarketSearchBar value={query} onChange={setQuery} />

      <div aria-live="polite" className="sr-only">
        {resultCount} stocks available
      </div>

      {resultCount === 0 ? (
        <p className="mt-6 text-center text-sm text-muted-foreground">
          No stocks match '{query}'. Try AAPL, VOD, or 0700.
        </p>
      ) : (
        <div className="mt-6 space-y-6">
          {EXCHANGE_GROUPS.map((group) => {
            const groupStocks = filtered.filter((s) => s.exchange === group.key);
            if (groupStocks.length === 0) return null;
            return (
              <section key={group.key}>
                <h2 className="mb-2 text-sm font-medium text-muted-foreground">{group.label}</h2>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {groupStocks.map((s) => (
                    <Link
                      key={`${s.exchange}-${s.ticker}`}
                      to={`/simulator/stock/${s.exchange}/${s.ticker}`}
                      className="rounded-lg border bg-card p-3 transition-shadow hover:shadow-md"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold">{s.ticker}</span>
                        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${EXCHANGE_BADGE_COLORS[s.exchange] ?? 'bg-muted'}`}>
                          {s.exchange}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{s.name}</p>
                      <p className="mt-1 text-sm font-medium">{formatCurrency(s.price, s.currency)}</p>
                    </Link>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
