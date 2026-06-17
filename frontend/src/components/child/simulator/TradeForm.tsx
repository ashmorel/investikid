import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
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

const REFLECTION_REASON_IDS = ['story', 'cash', 'fear'] as const;
type ReflectionReasonId = typeof REFLECTION_REASON_IDS[number];

export function TradeForm({
  ticker, exchange, price, currency, availableCash, ownedShares, avgBuyPrice,
  onSubmit, isSubmitting, submitError,
}: TradeFormProps) {
  const { t } = useTranslation('simulator');
  const isMobile = !useMediaQuery('(min-width: 768px)');
  const haptic = useHaptic();
  const online = useOnline();
  const [side, setSide] = useState<TradeType>('buy');
  const [shares, setShares] = useState('');
  const [step, setStep] = useState<Step>('input');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [reflectionReason, setReflectionReason] = useState<ReflectionReasonId | null>(null);
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
      setValidationError(t('tradeForm.validation.atLeastOneShare'));
      return;
    }
    if (side === 'buy' && totalCost + (fee ?? 0) > cashNum) {
      setValidationError(t('tradeForm.validation.insufficientCash'));
      return;
    }
    if (side === 'sell' && sharesNum > ownedNum) {
      setValidationError(t('tradeForm.validation.insufficientShares'));
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
      {t('tradeForm.feeLine', { pct: commissionPct, fee: formatCurrency(fee.toFixed(2), currency) })}
      {' · '}
      {side === 'buy' ? (
        <>{t('tradeForm.totalCost', { total: formatCurrency((totalCost + fee).toFixed(2), currency) })}</>
      ) : (
        <>{t('tradeForm.youReceive', { amount: formatCurrency((totalCost - fee).toFixed(2), currency) })}</>
      )}
    </p>
  ) : null;

  if (step === 'reflection') {
    const reflectionContent = (
      <div className="rounded-lg border bg-muted/50 p-4">
        <p ref={reflectionHeadingRef} tabIndex={-1} className="font-medium">
          {t('tradeForm.reflection.heading')}
        </p>
        <div role="radiogroup" aria-label={t('tradeForm.reflection.reasonGroupLabel')} className="mt-3 flex flex-col gap-2">
          {REFLECTION_REASON_IDS.map((reasonId) => (
            <button
              key={reasonId}
              role="radio"
              aria-checked={reflectionReason === reasonId}
              onClick={() => setReflectionReason(reasonId)}
              className={`rounded-md border px-3 py-2 text-left text-sm font-medium ${reflectionReason === reasonId ? 'border-brand-500 bg-brand-50 text-brand-700' : 'bg-background'}`}
            >
              {t(`tradeForm.reflection.reason.${reasonId}.label`)}
            </button>
          ))}
        </div>
        <div aria-live="polite">
          {reflectionReason && <p className="mt-3 text-sm text-muted-foreground">{t(`tradeForm.reflection.reason.${reflectionReason}.response`)}</p>}
        </div>
        {submitError && (
          <p className="mt-2 text-sm text-danger-600">{submitError}</p>
        )}
        <div className="mt-4 flex gap-2">
          {reflectionReason && (
            <Button onClick={executeSubmit} disabled={isSubmitting || !online}>
              {isSubmitting ? t('tradeForm.reflection.submitting') : t('tradeForm.reflection.confirmSell')}
            </Button>
          )}
          <Button variant="outline" onClick={handleBack} disabled={isSubmitting}>{t('tradeForm.reflection.cancel')}</Button>
        </div>
      </div>
    );

    if (isMobile) {
      return (
        <BottomSheet
          open
          onOpenChange={(open) => { if (!open) handleBack(); }}
          title={t('tradeForm.reflection.title')}
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
          <p className="font-medium">
            {t(side === 'buy' ? 'tradeForm.review.buyShares' : 'tradeForm.review.sellShares', { count: sharesNum, ticker })}
          </p>
          <div className="mt-2 space-y-1 text-sm">
            <p>{t('tradeForm.review.pricePerShare', { price: formatCurrency(price, currency) })}</p>
            <p>{t(side === 'buy' ? 'tradeForm.review.totalCost' : 'tradeForm.review.totalProceeds', { amount: formatCurrency(totalCost.toFixed(2), currency) })}</p>
            {feeLine}
            <p>{t('tradeForm.review.cashAfter', { amount: formatCurrency(cashAfter.toFixed(2), currency) })}</p>
          </div>
          <div className="mt-2">
            <EduTooltip
              term={t('tradeForm.review.tooltipTerm')}
              explanation={t('tradeForm.review.tooltipExplanation')}
            />
          </div>
        </div>
        {submitError && (
          <p className="mt-2 text-sm text-danger-600">{submitError}</p>
        )}
        {!online && <OfflineNotice className="mt-2" />}
        <div className="mt-4 flex gap-2">
          <Button onClick={handleConfirm} disabled={isSubmitting || !online}>
            {isSubmitting ? t('tradeForm.review.submitting') : t('tradeForm.review.confirm', { side, count: sharesNum })}
          </Button>
          <Button variant="outline" onClick={handleBack} disabled={isSubmitting}>{t('tradeForm.review.goBack')}</Button>
        </div>
      </>
    );

    if (isMobile) {
      return (
        <BottomSheet
          open
          onOpenChange={(open) => { if (!open) handleBack(); }}
          title={t('tradeForm.review.title')}
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
      <div role="radiogroup" aria-label={t('tradeForm.tradeTypeLabel')} className="mb-4 flex gap-1">
        <button
          role="radio"
          aria-checked={side === 'buy'}
          aria-label={t('tradeForm.buy')}
          onClick={() => setSide('buy')}
          className={`rounded-md px-4 py-2 text-sm font-medium ${side === 'buy' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}
        >
          {t('tradeForm.buy')}
        </button>
        <button
          role="radio"
          aria-checked={side === 'sell'}
          aria-label={t('tradeForm.sell')}
          disabled={!canSell}
          onClick={() => canSell && setSide('sell')}
          className={`rounded-md px-4 py-2 text-sm font-medium ${side === 'sell' ? 'bg-primary text-primary-foreground' : 'bg-muted'} ${!canSell ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {t('tradeForm.sell')}
        </button>
      </div>

      <div className="mb-4 rounded-lg border bg-muted/30 p-3 text-sm">
        {side === 'buy' ? (
          <div className="flex flex-col gap-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t('tradeForm.availableCash')}</span>
              <span className="font-medium">{formatCurrency(availableCash, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t('tradeForm.pricePerShare')}</span>
              <span className="font-medium">{formatCurrency(price, currency)}</span>
            </div>
            <div className="flex justify-between border-t pt-1">
              <span className="text-muted-foreground">{t('tradeForm.youCanAfford')}</span>
              <span className="font-semibold text-success-700">
                {t(maxAffordable === 1 ? 'tradeForm.sharesAffordable' : 'tradeForm.sharesAffordablePlural', { count: maxAffordable })}
              </span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t('tradeForm.sharesOwned')}</span>
              <span className="font-medium">{ownedNum}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t('tradeForm.pricePerShare')}</span>
              <span className="font-medium">{formatCurrency(price, currency)}</span>
            </div>
            <div className="flex justify-between border-t pt-1">
              <span className="text-muted-foreground">{t('tradeForm.valueIfSold')}</span>
              <span className="font-semibold text-success-700">{formatCurrency((ownedNum * priceNum).toFixed(2), currency)}</span>
            </div>
          </div>
        )}
      </div>

      <div className="mb-4">
        <label htmlFor="shares-input" className="mb-1 block text-sm font-medium">
          {t('tradeForm.numberOfShares')}
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
              aria-label={t('tradeForm.maxButton')}
            >
              {t('tradeForm.maxButton')}
            </Button>
          )}
          {side === 'sell' && canSell && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShares(String(ownedNum))}
              aria-label={t('tradeForm.maxButton')}
            >
              {t('tradeForm.maxButton')}
            </Button>
          )}
        </div>
      </div>

      {sharesNum > 0 && (
        <div className="mb-4 text-sm">
          <p className="text-muted-foreground">
            {sharesNum} {t(sharesNum === 1 ? 'tradeForm.share' : 'tradeForm.shares')} × {formatCurrency(price, currency)} = <span className="font-medium text-foreground">{formatCurrency(totalCost.toFixed(2), currency)}</span>
          </p>
          {feeLine}
          {side === 'buy' && (
            <p className="text-muted-foreground">
              {t('tradeForm.cashRemaining')} <span className={`font-medium ${cashNum - totalCost - (fee ?? 0) < 0 ? 'text-danger-600' : 'text-foreground'}`}>{formatCurrency((cashNum - totalCost - (fee ?? 0)).toFixed(2), currency)}</span>
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

      <Button onClick={handleReview} disabled={!online}>{t('tradeForm.reviewTrade')}</Button>
    </div>
  );
}
