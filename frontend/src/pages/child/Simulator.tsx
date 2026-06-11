import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useTrades } from '@/hooks/useTrades';
import { usePortfolioHistory } from '@/hooks/usePortfolioHistory';
import { useActiveMissions } from '@/hooks/useActiveMissions';
import { CashCard } from '@/components/child/simulator/CashCard';
import { HoldingsTable } from '@/components/child/simulator/HoldingsTable';
import { TradeHistoryTab } from '@/components/child/simulator/TradeHistoryTab';
import { PortfolioHero } from '@/components/child/simulator/PortfolioHero';
import { MissionBanner } from '@/components/child/simulator/MissionBanner';
import { DiversificationCard } from '@/components/child/simulator/DiversificationCard';
import { GrowthProjectionCard } from '@/components/child/simulator/GrowthProjectionCard';
import { formatCurrency } from '@/lib/currency';
import { cn } from '@/lib/utils';

type Tab = 'holdings' | 'history';

export default function Simulator() {
  const { data: portfolio, isLoading: portfolioLoading } = usePortfolio();
  const { data: trades } = useTrades();
  const { data: history } = usePortfolioHistory();
  const { data: missions } = useActiveMissions();
  const [params] = useSearchParams();
  const [activeTab, setActiveTab] = useState<Tab>('holdings');

  const missionId = params.get('mission');
  const activeMission = missions?.find((m) => m.id === missionId) ?? missions?.[0] ?? undefined;

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

  const weekChange = history && history.length >= 2
    ? (() => {
        const d = history[history.length - 1].value - history[0].value;
        return { value: `${d >= 0 ? '+' : '−'}${formatCurrency(Math.abs(d), portfolio.currency_code)}`, up: d >= 0 };
      })()
    : null;

  return (
    <div className="mx-auto max-w-4xl px-4 py-4 sm:px-6 sm:py-6">
      <MissionBanner mission={activeMission} />
      {history && history.length >= 2 ? (
        <PortfolioHero totalValue={portfolio.total_value} currencyCode={portfolio.currency_code} history={history} />
      ) : (
        <div className="rounded-3xl bg-brand-gradient p-5 text-white shadow-lg shadow-brand-600/30">
          <p className="text-xs font-bold uppercase tracking-wider text-white/90">Practice Portfolio <span className="font-medium normal-case opacity-80">· play money</span></p>
          <p className="mt-1 text-4xl font-extrabold">{formatCurrency(portfolio.total_value, portfolio.currency_code)}</p>
        </div>
      )}

      <div className="mt-4">
        <CashCard
          virtualCash={portfolio.virtual_cash}
          currencyCode={portfolio.currency_code}
          hasMultiCurrency={hasMultiCurrency}
          weekChange={weekChange}
        />
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <DiversificationCard
          holdingsCount={new Set(holdings.map((h) => `${h.exchange}:${h.ticker}`)).size}
        />
        <GrowthProjectionCard
          totalValue={portfolio.total_value}
          currencyCode={portfolio.currency_code}
        />
      </div>

      <div className="mt-6">
        <div role="tablist" className="mb-3 flex gap-1 rounded-lg bg-brand-50 p-1">
          <button
            role="tab"
            aria-selected={activeTab === 'holdings'}
            onClick={() => setActiveTab('holdings')}
            className={cn(
              'flex-1 rounded-md px-3 py-2 text-sm font-semibold transition-colors',
              activeTab === 'holdings' ? 'bg-white text-brand-700 shadow-sm' : 'text-gray-500 hover:text-gray-700',
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
              activeTab === 'history' ? 'bg-white text-brand-700 shadow-sm' : 'text-gray-500 hover:text-gray-700',
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
