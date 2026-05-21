import { useState } from 'react';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useTrades } from '@/hooks/useTrades';
import { usePortfolioHistory } from '@/hooks/usePortfolioHistory';
import { CashCard } from '@/components/child/simulator/CashCard';
import { HoldingsTable } from '@/components/child/simulator/HoldingsTable';
import { TradeHistoryTab } from '@/components/child/simulator/TradeHistoryTab';
import { PortfolioChart } from '@/components/child/simulator/PortfolioChart';
import { cn } from '@/lib/utils';

type Tab = 'holdings' | 'history';

export default function Simulator() {
  const { data: portfolio, isLoading: portfolioLoading } = usePortfolio();
  const { data: trades } = useTrades();
  const { data: history } = usePortfolioHistory();
  const [activeTab, setActiveTab] = useState<Tab>('holdings');

  if (portfolioLoading || !portfolio) {
    return <div className="mx-auto max-w-4xl px-4 py-4 sm:px-6 sm:py-6"><p className="text-sm text-muted-foreground">Loading portfolio…</p></div>;
  }

  const holdings = portfolio.holdings ?? [];
  const hasMultiCurrency = holdings.some(
    (h) => {
      const hCurrency = h.exchange === 'LSE' ? 'GBP' : h.exchange === 'HKEX' ? 'HKD' : 'USD';
      return hCurrency !== portfolio.currency_code;
    }
  );

  return (
    <div className="mx-auto max-w-4xl px-4 py-4 sm:px-6 sm:py-6">
      <div className="rounded-2xl border-2 border-amber-200 bg-gradient-to-b from-amber-100 to-amber-50 p-6 text-center">
        <span className="text-4xl" aria-hidden="true">📊</span>
        <h1 className="mt-2 text-xl font-extrabold text-gray-900">Your Portfolio</h1>
        <p className="text-sm text-gray-500">Practice Mode — no real money</p>
      </div>

      <div className="mt-4">
        <CashCard
          virtualCash={portfolio.virtual_cash}
          totalValue={portfolio.total_value}
          currencyCode={portfolio.currency_code}
          hasMultiCurrency={hasMultiCurrency}
          showTotalValue={holdings.length > 0}
        />
      </div>

      {history && <PortfolioChart history={history} />}

      <div className="mt-6">
        <div role="tablist" className="mb-3 flex gap-1 rounded-lg bg-amber-50 p-1">
          <button
            role="tab"
            aria-selected={activeTab === 'holdings'}
            onClick={() => setActiveTab('holdings')}
            className={cn(
              'flex-1 rounded-md px-3 py-2 text-sm font-semibold transition-colors',
              activeTab === 'holdings' ? 'bg-white text-amber-700 shadow-sm' : 'text-gray-500 hover:text-gray-700',
            )}
          >
            Holdings
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'history'}
            onClick={() => setActiveTab('history')}
            className={cn(
              'flex-1 rounded-md px-3 py-2 text-sm font-semibold transition-colors',
              activeTab === 'history' ? 'bg-white text-amber-700 shadow-sm' : 'text-gray-500 hover:text-gray-700',
            )}
          >
            Trade History
          </button>
        </div>

        <div role="tabpanel">
          {activeTab === 'holdings' ? (
            <HoldingsTable holdings={holdings} />
          ) : (
            <TradeHistoryTab trades={trades ?? []} />
          )}
        </div>
      </div>
    </div>
  );
}
