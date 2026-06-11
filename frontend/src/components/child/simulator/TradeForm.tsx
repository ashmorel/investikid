import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { EduTooltip } from './EduTooltip';
import { formatCurrency } from '@/lib/currency';
import { simulatorApi, type TradeRequest, type TradeType } from '@/api/simulator';
import { Button } from '@/components/ui/button';
import { BottomSheet } from '@/components/mobile/BottomSheet';
import { OfflineNotice } from '@/components/child/OfflineNotice';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { useHaptic } from '@/hooks/useHaptic';
import { useOnline } from '@/hooks/useOnline';

type TradeFormProps = {
  ticker: string;
  exchange: string;
  price: string;
  currency: string;
  availableCash: string;
  ownedShares: string;
  avgBuyPrice?: string | null;
  onSubmit: (req: TradeRequest) => Promise<void>;
  isSubmitting: boolean;
  submitError: string | null;
};

type Step = 'input' | 'review' | 'reflection';

const REFLECTION_REASONS = [
  {
    id: 'story',
    label: "The company's story has changed",
    response: 'A real reason to rethink — stories matter more than prices.',
  },
  {
    id: 'cash',
    label: 'I need the cash for something else',
    response: 'Fair — needing money is a real reason.',
  },
  {
    id: 'fear',
    label: 'The price is falling and it scares me',
    response:
      "That's the one to watch: falling prices alone are often the worst reason to sell. Markets wobble; selling locks in the loss.",
  },
] as const;

export function TradeForm({
  ticker, exchange, price, currency, availableCash, ownedShares, avgBuyPrice,
  onSubmit, isSubmitting, submitError,
}: TradeFormProps) {
  const isMobile = !useMediaQuery('(min-width: 768px)');
  const haptic = useHaptic();
  const online = useOnline();
  const [side, setSide] = useState<TradeType>('buy');
  const [shares, setShares] = useState('');
  const [step, setStep] = useState<Step>('input');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [reflectionReason, setReflectionReason] = useState<string | null>(null);
  const reflectionHeadingRef = useRef<HTMLParagraphElement>(null);

  const configQ = useQuery({
    queryKey: ['trade-config'],
    queryFn: () => simulatorApi.getTradeConfig(),
    staleTime: 30 * 60 * 1000,
  });
  const commissionPct = configQ.data ? parseFloat(configQ.data.commission_pct) : null;

  const priceNum = parseFloat(price);
  const sharesNum = parseInt(shares, 10) || 0;
  const totalCost = priceNum * sharesNum;
  const fee = commissionPct != null ? (totalCost * commissionPct) / 100 : null;
  const cashNum = parseFloat(availableCash);
  const ownedNum = parseInt(ownedShares, 10) || 0;
  const canSell = ownedNum > 0;
  const maxAffordable = priceNum > 0 ? Math.floor(cashNum / priceNum) : 0;
  const avgBuyNum = avgBuyPrice != null ? parseFloat(avgBuyPrice) : null;
  const isLossSale = side === 'sell' && avgBuyNum != null && priceNum < avgBuyNum;

  useEffect(() => {
    if (step === 'reflection') reflectionHeadingRef.current?.focus();
  }, [step]);

  function handleReview() {
    setValidationError(null);
    if (sharesNum < 1) {
      setValidationError('Enter at least 1 share');
      return;
    }
    if (side === 'buy' && totalCost + (fee ?? 0) > cashNum) {
      setValidationError('Insufficient cash for this trade');
      return;
    }
    if (side === 'sell' && sharesNum > ownedNum) {
      setValidationError('Insufficient shares');
      return;
    }
    setStep('review');
  }

  function handleBack() {
    setStep('input');
    setReflectionReason(null);
  }

  async function executeSubmit() {
    await onSubmit({ ticker, exchange, type: side, shares: sharesNum });
    haptic('medium');
  }

  async function handleConfirm() {
    if (isLossSale) {
      setReflectionReason(null);
      setStep('reflection');
      return;
    }
    await executeSubmit();
  }

  const feeLine = fee != null && sharesNum > 0 ? (
    <p className="text-muted-foreground">
      Fee ({commissionPct}%): <span className="font-medium text-foreground">{formatCurrency(fee.toFixed(2), currency)}</span>
      {' · '}
      {side === 'buy' ? (
        <>Total: <span className="font-medium text-foreground">{formatCurrency((totalCost + fee).toFixed(2), currency)}</span></>
      ) : (
        <>You&apos;ll receive ≈ <span className="font-medium text-foreground">{formatCurrency((totalCost - fee).toFixed(2), currency)}</span></>
      )}
    </p>
  ) : null;

  if (step === 'reflection') {
    const chosen = REFLECTION_REASONS.find((r) => r.id === reflectionReason);
    const reflectionContent = (
      <div className="rounded-lg border bg-muted/50 p-4">
        <p ref={reflectionHeadingRef} tabIndex={-1} className="font-medium">
          You&apos;d be selling at a loss. What&apos;s your reason?
        </p>
        <div role="radiogroup" aria-label="Reason for selling" className="mt-3 flex flex-col gap-2">
          {REFLECTION_REASONS.map((reason) => (
            <button
              key={reason.id}
              role="radio"
              aria-checked={reflectionReason === reason.id}
              onClick={() => setReflectionReason(reason.id)}
              className={`rounded-md border px-3 py-2 text-left text-sm font-medium ${reflectionReason === reason.id ? 'border-brand-500 bg-brand-50 text-brand-700' : 'bg-background'}`}
            >
              {reason.label}
            </button>
          ))}
        </div>
        <div aria-live="polite">
          {chosen && <p className="mt-3 text-sm text-muted-foreground">{chosen.response}</p>}
        </div>
        {submitError && (
          <p className="mt-2 text-sm text-danger-600">{submitError}</p>
        )}
        <div className="mt-4 flex gap-2">
          {chosen && (
            <Button onClick={executeSubmit} disabled={isSubmitting || !online}>
              {isSubmitting ? 'Submitting…' : 'Confirm sell'}
            </Button>
          )}
          <Button variant="outline" onClick={handleBack} disabled={isSubmitting}>Cancel</Button>
        </div>
      </div>
    );

    if (isMobile) {
      return (
        <BottomSheet
          open
          onOpenChange={(open) => { if (!open) handleBack(); }}
          title="Selling at a loss"
        >
          {reflectionContent}
        </BottomSheet>
      );
    }

    return <div>{reflectionContent}</div>;
  }

  if (step === 'review') {
    const cashAfter = side === 'buy' ? cashNum - totalCost - (fee ?? 0) : cashNum + totalCost - (fee ?? 0);
    const reviewContent = (
      <>
        <div className="rounded-lg border bg-muted/50 p-4">
          <p className="font-medium">{side === 'buy' ? 'Buy' : 'Sell'} {sharesNum} shares of {ticker}</p>
          <div className="mt-2 space-y-1 text-sm">
            <p>Price per share: {formatCurrency(price, currency)}</p>
            <p>Total {side === 'buy' ? 'cost' : 'proceeds'}: {formatCurrency(totalCost.toFixed(2), currency)}</p>
            {feeLine}
            <p>Cash after trade: {formatCurrency(cashAfter.toFixed(2), currency)}</p>
          </div>
          <div className="mt-2">
            <EduTooltip
              term="Review"
              explanation="Always review your trades before confirming. In real investing, you can't undo a trade!"
            />
          </div>
        </div>
        {submitError && (
          <p className="mt-2 text-sm text-danger-600">{submitError}</p>
        )}
        {!online && <OfflineNotice className="mt-2" />}
        <div className="mt-4 flex gap-2">
          <Button onClick={handleConfirm} disabled={isSubmitting || !online}>
            {isSubmitting ? 'Submitting…' : `Confirm ${side} of ${sharesNum} shares`}
          </Button>
          <Button variant="outline" onClick={handleBack} disabled={isSubmitting}>Go back</Button>
        </div>
      </>
    );

    if (isMobile) {
      return (
        <BottomSheet
          open
          onOpenChange={(open) => { if (!open) handleBack(); }}
          title="Review Trade"
        >
          {reviewContent}
        </BottomSheet>
      );
    }

    return (
      <div aria-live="assertive">
        {reviewContent}
      </div>
    );
  }

  return (
    <div>
      <div role="radiogroup" aria-label="Trade type" className="mb-4 flex gap-1">
        <button
          role="radio"
          aria-checked={side === 'buy'}
          aria-label="Buy"
          onClick={() => setSide('buy')}
          className={`rounded-md px-4 py-2 text-sm font-medium ${side === 'buy' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}
        >
          Buy
        </button>
        <button
          role="radio"
          aria-checked={side === 'sell'}
          aria-label="Sell"
          disabled={!canSell}
          onClick={() => canSell && setSide('sell')}
          className={`rounded-md px-4 py-2 text-sm font-medium ${side === 'sell' ? 'bg-primary text-primary-foreground' : 'bg-muted'} ${!canSell ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          Sell
        </button>
      </div>

      <div className="mb-4 rounded-lg border bg-muted/30 p-3 text-sm">
        {side === 'buy' ? (
          <div className="flex flex-col gap-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Available cash</span>
              <span className="font-medium">{formatCurrency(availableCash, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Price per share</span>
              <span className="font-medium">{formatCurrency(price, currency)}</span>
            </div>
            <div className="flex justify-between border-t pt-1">
              <span className="text-muted-foreground">You can afford</span>
              <span className="font-semibold text-success-700">{maxAffordable} {maxAffordable === 1 ? 'share' : 'shares'}</span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Shares owned</span>
              <span className="font-medium">{ownedNum}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Price per share</span>
              <span className="font-medium">{formatCurrency(price, currency)}</span>
            </div>
            <div className="flex justify-between border-t pt-1">
              <span className="text-muted-foreground">Value if sold</span>
              <span className="font-semibold text-success-700">{formatCurrency((ownedNum * priceNum).toFixed(2), currency)}</span>
            </div>
          </div>
        )}
      </div>

      <div className="mb-4">
        <label htmlFor="shares-input" className="mb-1 block text-sm font-medium">
          Number of shares
        </label>
        <div className="flex gap-2">
          <input
            id="shares-input"
            type="number"
            min={1}
            step={1}
            value={shares}
            onChange={(e) => setShares(e.target.value)}
            className="w-32 rounded-md border bg-background px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-ring"
          />
          {side === 'buy' && maxAffordable > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShares(String(maxAffordable))}
              aria-label="Max"
            >
              Max
            </Button>
          )}
          {side === 'sell' && canSell && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShares(String(ownedNum))}
              aria-label="Max"
            >
              Max
            </Button>
          )}
        </div>
      </div>

      {sharesNum > 0 && (
        <div className="mb-4 text-sm">
          <p className="text-muted-foreground">
            {sharesNum} {sharesNum === 1 ? 'share' : 'shares'} × {formatCurrency(price, currency)} = <span className="font-medium text-foreground">{formatCurrency(totalCost.toFixed(2), currency)}</span>
          </p>
          {feeLine}
          {side === 'buy' && (
            <p className="text-muted-foreground">
              Cash remaining: <span className={`font-medium ${cashNum - totalCost - (fee ?? 0) < 0 ? 'text-danger-600' : 'text-foreground'}`}>{formatCurrency((cashNum - totalCost - (fee ?? 0)).toFixed(2), currency)}</span>
            </p>
          )}
        </div>
      )}

      {validationError && (
        <p className="mb-2 text-sm text-danger-600">{validationError}</p>
      )}
      {submitError && (
        <p className="mb-2 text-sm text-danger-600">{submitError}</p>
      )}
      {!online && <OfflineNotice className="mb-2" />}

      <Button onClick={handleReview} disabled={!online}>Review trade</Button>
    </div>
  );
}
