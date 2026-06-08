import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { simulatorApi, type TradeRequest, type QuoteOut, type PortfolioOut } from '@/api/simulator';
import { ApiError } from '@/api/client';
import { StockHeader } from '@/components/child/simulator/StockHeader';
import { StockChart } from '@/components/child/simulator/StockChart';
import { ChartGuide } from '@/components/child/simulator/ChartGuide';
import { StockNewsSection } from '@/components/child/simulator/StockNews';
import { TradeForm } from '@/components/child/simulator/TradeForm';
import { InvestmentTimeMachine } from '@/components/child/simulator/InvestmentTimeMachine';
import { InvestingTips } from '@/components/child/simulator/InvestingTips';
import { ChartCoachPanel } from '@/components/child/simulator/ChartCoachPanel';
import { BackButton } from '@/components/child/BackButton';
import { useToast } from '@/hooks/use-toast';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';

export default function Stock() {
  const { exchange, ticker } = useParams<{ exchange: string; ticker: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { open: openPaywall } = usePremiumPaywall();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [chartPeriod, setChartPeriod] = useState('1mo');
  const [showCoachPenny, setShowCoachPenny] = useState(false);

  const quoteQ = useQuery<QuoteOut | null, ApiError>({
    queryKey: ['quote', exchange, ticker],
    queryFn: () => simulatorApi.getQuote(exchange!, ticker!),
    retry: false,
    refetchOnWindowFocus: true,
  });

  const portfolioQ = useQuery<PortfolioOut | null>({
    queryKey: ['portfolio'],
    queryFn: () => simulatorApi.getPortfolio(),
    retry: false,
    refetchOnWindowFocus: true,
  });

  const tradeMutation = useMutation({
    mutationFn: (req: TradeRequest) => simulatorApi.placeTrade(req),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      queryClient.invalidateQueries({ queryKey: ['active-missions'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });

      const r = result?.rewards;
      const bits: string[] = [];
      if (r) {
        if (r.xp_awarded > 0) bits.push(`+${r.xp_awarded} XP`);
        if (r.streak_extended) bits.push('🔥 streak kept');
        if (Number(r.cash_granted) > 0) bits.push(`+${r.cash_granted} to invest`);
        if (r.missions_completed.length) bits.push(`Mission complete: ${r.missions_completed[0].title}`);
      }
      if (bits.length) {
        toast({ title: 'Nice trade!', description: bits.join(' · ') });
      } else {
        toast({ title: 'Trade executed!', description: `Your ${ticker} trade was successful.` });
      }
      navigate('/simulator');
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.code === 'premium_required') {
        const ctx = (err.context as { label?: string }) ?? {};
        openPaywall({ kind: 'ticker', label: ctx.label ?? 'this stock' });
        return;
      }
      const msg = err instanceof ApiError ? err.detail : 'Trade failed. Try again.';
      setSubmitError(msg);
    },
  });

  if (quoteQ.isLoading || portfolioQ.isLoading) {
    return <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6"><p className="text-sm text-muted-foreground">Loading…</p></div>;
  }

  if (quoteQ.error?.status === 404) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
        <BackButton to="/simulator/market" label="Market" />
        <p className="mt-2 text-sm">Stock not found.</p>
      </div>
    );
  }

  if (quoteQ.error?.status === 403) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
        <BackButton to="/simulator/market" label="Market" />
        <p className="mt-2 text-sm">This stock isn't available in practice mode.</p>
      </div>
    );
  }

  const quote = quoteQ.data;
  const portfolio = portfolioQ.data;
  if (!quote || !portfolio) return null;

  const existingHolding = portfolio.holdings.find(
    (h) => h.ticker === ticker && h.exchange === exchange,
  );

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <BackButton to="/simulator/market" label="Market" className="mb-4" />

      <StockHeader
        name={quote.name}
        ticker={quote.ticker}
        exchange={quote.exchange}
        price={quote.price}
        currency={quote.currency}
        existingShares={existingHolding?.shares ?? null}
        existingAvgPrice={existingHolding?.avg_buy_price ?? null}
      />

      <div className="my-4 rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
        <StockChart
          exchange={quote.exchange}
          ticker={quote.ticker}
          currency={quote.currency}
          onPeriodChange={setChartPeriod}
        />
        <ChartGuide exchange={quote.exchange} ticker={quote.ticker} period={chartPeriod} onAskPenny={() => setShowCoachPenny(true)} />
      </div>

      <div className="mb-4">
        <InvestmentTimeMachine
          exchange={quote.exchange}
          ticker={quote.ticker}
        />
      </div>

      <div className="mb-4">
        <InvestingTips
          contextTicker={quote.ticker}
          contextExchange={quote.exchange}
        />
      </div>

      <div className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
        <TradeForm
          ticker={quote.ticker}
          exchange={quote.exchange}
          price={quote.price}
          currency={quote.currency}
          availableCash={portfolio.virtual_cash}
          ownedShares={existingHolding?.shares ?? '0'}
          onSubmit={async (req) => {
            setSubmitError(null);
            // Errors are surfaced via the mutation's onError (toast or paywall);
            // swallow the rejection here so it isn't an unhandled promise.
            await tradeMutation.mutateAsync(req).catch(() => {});
          }}
          isSubmitting={tradeMutation.isPending}
          submitError={submitError}
        />
      </div>

      <div className="mt-6">
        <StockNewsSection exchange={quote.exchange} ticker={quote.ticker} />
      </div>

      {showCoachPenny && (
        <ChartCoachPanel
          ticker={quote.ticker}
          exchange={quote.exchange}
          period={chartPeriod}
          onClose={() => setShowCoachPenny(false)}
        />
      )}
    </div>
  );
}
