import { useState } from 'react';
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from '@/components/ui/sheet';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { Penny } from '@/components/child/ui/Penny';
import { ParentalGate } from '@/components/child/ParentalGate';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { premiumApi } from '@/api/premium';
import { billingApi } from '@/api/billing';
import { runNativePurchase } from '@/lib/nativePurchase';
import { isNativeApp, isAndroid } from '@/lib/platform';
import { PAYWALL_CTA, PAYWALL_REQUEST_DECLINED, PAYWALL_TITLE, PREMIUM_BENEFITS } from '@/lib/premiumConfig';
import type { PaywallContext } from '@/hooks/usePremiumPaywall';

type Mode = 'idle' | 'gate' | 'working';

export function PremiumPaywall({ context, onClose }: { context: PaywallContext | null; onClose: () => void }) {
  const { t } = useTranslation('child');
  const isDesktop = useMediaQuery('(min-width: 640px)');
  const native = isNativeApp();
  const qc = useQueryClient();
  const [sentStatus, setSentStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<Mode>('idle');
  const [result, setResult] = useState<'active' | 'pending' | null>(null);
  const [error, setError] = useState(false);
  const open = context !== null;

  function reset() {
    setSentStatus(null);
    setMode('idle');
    setResult(null);
    setError(false);
  }

  async function ask() {
    if (!context) return;
    setBusy(true);
    try {
      const res = await premiumApi.requestUnlock({ kind: context.kind, label: context.label });
      setSentStatus(res?.status ?? 'sent');
    } finally {
      setBusy(false);
    }
  }

  async function startPurchase() {
    setMode('working');
    setError(false);
    try {
      const plans = await billingApi.childPlans();
      const plan = plans?.plans?.[0];
      if (!plan) {
        setError(true);
        setMode('idle');
        return;
      }
      const res = isAndroid()
        ? await runNativePurchase({
            platform: 'android',
            productId: plan.google_product_id,
            getGoogleToken: async () => (await billingApi.childGoogleAccountToken())!.token,
            verifyGoogle: (purchaseToken, productId) =>
              billingApi.childGoogleVerify({ purchaseToken, productId }).then(() => undefined),
          })
        : await runNativePurchase({
            platform: 'ios',
            productId: plan.apple_product_id,
            getAppleToken: async () => (await billingApi.childAppleAccountToken())!.token,
            verifyApple: (jws) => billingApi.childAppleVerify(jws).then(() => undefined),
          });
      if (res.status === 'active') {
        await qc.invalidateQueries({ queryKey: ['me'] });
        setResult('active');
        setMode('idle');
      } else if (res.status === 'pending') {
        setResult('pending');
        setMode('idle');
      } else {
        setMode('idle');
      }
    } catch {
      setError(true);
      setMode('idle');
    }
  }

  return (
    <Sheet open={open} onOpenChange={(o) => { if (!o) { onClose(); reset(); } }}>
      <SheetContent
        side={isDesktop ? 'right' : 'bottom'}
        className={
          isDesktop
            ? 'flex h-full w-full max-w-md flex-col gap-0 border-brand-100 bg-white p-0 sm:max-w-md'
            : 'flex max-h-[85svh] flex-col gap-0 rounded-t-2xl border-brand-100 bg-white p-0'
        }
      >
        <SheetHeader className="flex-row items-center gap-2 border-b border-brand-100 px-4 py-3 text-left">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100" aria-hidden="true">
            <Penny size={28} mood="happy" />
          </span>
          <div>
            <SheetTitle>{PAYWALL_TITLE}</SheetTitle>
            <SheetDescription>
              {context ? t('paywall.premiumTreat', { label: context.label }) : t('paywall.premiumUnlocks')}
            </SheetDescription>
          </div>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-auto px-4 py-3 pb-[calc(0.75rem+var(--safe-bottom))]">
          {result ? (
            <p role="status" className="py-6 text-center text-base font-semibold text-ink">
              {result === 'active' ? t('paywall.unlocked') : t('paywall.askedGrownup')}
            </p>
          ) : sentStatus ? (
            <p role="status" className="py-6 text-center text-base font-semibold text-ink">
              {sentStatus === 'no_parent'
                ? t('paywall.noParent')
                : sentStatus === 'declined'
                  ? PAYWALL_REQUEST_DECLINED
                  : sentStatus === 'already_sent'
                    ? t('paywall.alreadySent')
                    : t('paywall.sent')}
            </p>
          ) : mode === 'gate' ? (
            <ParentalGate onPass={startPurchase} onCancel={() => setMode('idle')} />
          ) : (
            <>
              <ul className="space-y-2">
                {PREMIUM_BENEFITS.map((b) => (
                  <li key={b} className="flex items-start gap-2 text-sm text-ink">
                    <span aria-hidden="true">✨</span><span>{b}</span>
                  </li>
                ))}
              </ul>
              {error && (
                <p role="alert" className="mt-3 text-center text-sm font-semibold text-red-600">
                  {t('paywall.purchaseError')}
                </p>
              )}
              {native ? (
                <>
                  <button
                    type="button"
                    onClick={() => { setError(false); setMode('gate'); }}
                    disabled={mode === 'working'}
                    className="mt-4 w-full rounded-full bg-brand-gradient px-5 py-3 text-sm font-bold text-white shadow disabled:opacity-60"
                  >
                    {mode === 'working' ? t('paywall.working') : t('paywall.getPremium')}
                  </button>
                  <button
                    type="button"
                    onClick={ask}
                    disabled={busy || mode === 'working'}
                    className="mt-2 w-full rounded-full px-5 py-2 text-sm font-semibold text-brand-600 disabled:opacity-60"
                  >
                    {busy ? t('paywall.sendingRequest') : t('paywall.askGrownupLink')}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={ask}
                  disabled={busy}
                  className="mt-4 w-full rounded-full bg-brand-gradient px-5 py-3 text-sm font-bold text-white shadow disabled:opacity-60"
                >
                  {busy ? t('paywall.sendingRequest') : PAYWALL_CTA}
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                className="mt-2 w-full rounded-full px-5 py-2 text-sm font-semibold text-muted-foreground"
              >
                {t('paywall.mayBeLater')}
              </button>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
