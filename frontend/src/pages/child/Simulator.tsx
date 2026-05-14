import { useState } from 'react';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useTrades } from '@/hooks/useTrades';
import { CashCard } from '@/components/child/simulator/CashCard';
import { HoldingsTable } from '@/components/child/simulator/HoldingsTable';
import { TradeHistoryTab } from '@/components/child/simulator/TradeHistoryTab';

type Tab = 'holdings' | 'history';

export default function Simulator() {
  const { data: portfolio, isLoading: portfolioLoading } = usePortfolio();
  const { data: trades } = useTrades();
  const [activeTab, setActiveTab] = useState<Tab>('holdings');

  if (portfolioLoading || !portfolio) {
    return <div className="mx-auto max-w-4xl p-6"><p className="text-sm text-muted-foreground">Loading portfolio…</p></div>;
  }

  const holdings = portfolio.holdings ?? [];
  const hasMultiCurrency = holdings.some(
    (h) => {
      const hCurrency = h.exchange === 'LSE' ? 'GBP' : h.exchange === 'HKEX' ? 'HKD' : 'USD';
      return hCurrency !== portfolio.currency_code;
    }
  );

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-4 inline-flex items-center gap-2 rounded-full border bg-muted/50 px-3 py-1 text-xs text-muted-foreground">
        🎮 Practice Mode — no real money
      </div>

      <CashCard
        virtualCash={portfolio.virtual_cash}
        totalValue={portfolio.total_value}
        currencyCode={portfolio.currency_code}
        hasMultiCurrency={hasMultiCurrency}
        showTotalValue={holdings.length > 0}
      />

      <div className="mt-6">
        <div role="tablist" className="mb-3 flex gap-1 border-b">
          <button
            role="tab"
            aria-selected={activeTab === 'holdings'}
            onClick={() => setActiveTab('holdings')}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
              activeTab === 'holdings' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Holdings
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'history'}
            onClick={() => setActiveTab('history')}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
              activeTab === 'history' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
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
