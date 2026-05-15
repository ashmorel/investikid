import { useState } from 'react';
import { EduTooltip } from './EduTooltip';
import { formatCurrency } from '@/lib/currency';
import type { TradeRequest, TradeType } from '@/api/simulator';
import { Button } from '@/components/ui/button';

type TradeFormProps = {
  ticker: string;
  exchange: string;
  price: string;
  currency: string;
  availableCash: string;
  ownedShares: string;
  onSubmit: (req: TradeRequest) => Promise<void>;
  isSubmitting: boolean;
  submitError: string | null;
};

type Step = 'input' | 'review';

export function TradeForm({
  ticker, exchange, price, currency, availableCash, ownedShares,
  onSubmit, isSubmitting, submitError,
}: TradeFormProps) {
  const [side, setSide] = useState<TradeType>('buy');
  const [shares, setShares] = useState('');
  const [step, setStep] = useState<Step>('input');
  const [validationError, setValidationError] = useState<string | null>(null);

  const priceNum = parseFloat(price);
  const sharesNum = parseInt(shares, 10) || 0;
  const totalCost = priceNum * sharesNum;
  const cashNum = parseFloat(availableCash);
  const ownedNum = parseInt(ownedShares, 10) || 0;
  const canSell = ownedNum > 0;
  const maxAffordable = priceNum > 0 ? Math.floor(cashNum / priceNum) : 0;

  function handleReview() {
    setValidationError(null);
    if (sharesNum < 1) {
      setValidationError('Enter at least 1 share');
      return;
    }
    if (side === 'buy' && totalCost > cashNum) {
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
  }

  async function handleConfirm() {
    await onSubmit({ ticker, exchange, type: side, shares: sharesNum });
  }

  if (step === 'review') {
    const cashAfter = side === 'buy' ? cashNum - totalCost : cashNum + totalCost;
    return (
      <div aria-live="assertive">
        <div className="rounded-lg border bg-muted/50 p-4">
          <p className="font-medium">{side === 'buy' ? 'Buy' : 'Sell'} {sharesNum} shares of {ticker}</p>
          <div className="mt-2 space-y-1 text-sm">
            <p>Price per share: {formatCurrency(price, currency)}</p>
            <p>Total {side === 'buy' ? 'cost' : 'proceeds'}: {formatCurrency(totalCost.toFixed(2), currency)}</p>
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
          <p className="mt-2 text-sm text-red-600">{submitError}</p>
        )}
        <div className="mt-4 flex gap-2">
          <Button onClick={handleConfirm} disabled={isSubmitting}>
            {isSubmitting ? 'Submitting…' : `Confirm ${side} of ${sharesNum} shares`}
          </Button>
          <Button variant="outline" onClick={handleBack} disabled={isSubmitting}>Go back</Button>
        </div>
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
              <span className="font-semibold text-green-700">{maxAffordable} {maxAffordable === 1 ? 'share' : 'shares'}</span>
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
              <span className="font-semibold text-green-700">{formatCurrency((ownedNum * priceNum).toFixed(2), currency)}</span>
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
            className="w-32 rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
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
          {side === 'buy' && (
            <p className="text-muted-foreground">
              Cash remaining: <span className={`font-medium ${cashNum - totalCost < 0 ? 'text-red-600' : 'text-foreground'}`}>{formatCurrency((cashNum - totalCost).toFixed(2), currency)}</span>
            </p>
          )}
        </div>
      )}

      {validationError && (
        <p className="mb-2 text-sm text-red-600">{validationError}</p>
      )}
      {submitError && (
        <p className="mb-2 text-sm text-red-600">{submitError}</p>
      )}

      <Button onClick={handleReview}>Review trade</Button>
    </div>
  );
}
