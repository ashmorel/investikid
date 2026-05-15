import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
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
import { useToast } from '@/hooks/use-toast';

export default function Stock() {
  const { exchange, ticker } = useParams<{ exchange: string; ticker: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [chartPeriod, setChartPeriod] = useState('1mo');
  const [showCoachEddie, setShowCoachEddie] = useState(false);

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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      toast({ title: 'Trade executed!', description: `Your ${ticker} trade was successful.` });
      navigate('/simulator');
    },
    onError: (err: unknown) => {
      const msg = err instanceof ApiError ? err.detail : 'Trade failed. Try again.';
      setSubmitError(msg);
    },
  });

  if (quoteQ.isLoading || portfolioQ.isLoading) {
    return <div className="mx-auto max-w-3xl p-6"><p className="text-sm text-muted-foreground">Loading…</p></div>;
  }

  if (quoteQ.error?.status === 404) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-sm">Stock not found.</p>
        <Link to="/simulator/market" className="text-sm text-primary hover:underline">← Back to market</Link>
      </div>
    );
  }

  if (quoteQ.error?.status === 403) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-sm">This stock isn't available in practice mode.</p>
        <Link to="/simulator/market" className="text-sm text-primary hover:underline">← Back to market</Link>
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
    <div className="mx-auto max-w-3xl p-6">
      <Link to="/simulator/market" className="mb-4 inline-block text-sm text-primary hover:underline">
        ← Back to market
      </Link>

      <StockHeader
        name={quote.name}
        ticker={quote.ticker}
        exchange={quote.exchange}
        price={quote.price}
        currency={quote.currency}
        existingShares={existingHolding?.shares ?? null}
        existingAvgPrice={existingHolding?.avg_buy_price ?? null}
      />

      <div className="my-4">
        <StockChart
          exchange={quote.exchange}
          ticker={quote.ticker}
          currency={quote.currency}
          onPeriodChange={setChartPeriod}
        />
      </div>

      <div className="mb-4">
        <ChartGuide exchange={quote.exchange} ticker={quote.ticker} period={chartPeriod} onAskEddie={() => setShowCoachEddie(true)} />
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

      <TradeForm
        ticker={quote.ticker}
        exchange={quote.exchange}
        price={quote.price}
        currency={quote.currency}
        availableCash={portfolio.virtual_cash}
        ownedShares={existingHolding?.shares ?? '0'}
        onSubmit={async (req) => { setSubmitError(null); await tradeMutation.mutateAsync(req); }}
        isSubmitting={tradeMutation.isPending}
        submitError={submitError}
      />

      <div className="mt-6">
        <StockNewsSection exchange={quote.exchange} ticker={quote.ticker} />
      </div>

      {showCoachEddie && (
        <ChartCoachPanel
          ticker={quote.ticker}
          exchange={quote.exchange}
          period={chartPeriod}
          onClose={() => setShowCoachEddie(false)}
        />
      )}
    </div>
  );
}
