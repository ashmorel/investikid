import { useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { billingApi, type Plan, type PlanOut, type SubscriptionStatus } from '@/api/billing';
import { Button } from '@/components/ui/button';
import { isAndroid, isNativeApp } from '@/lib/platform';
import { StoreKit } from '@/lib/storekit';
import { PlayBilling } from '@/lib/playBilling';
import { runNativePurchase } from '@/lib/nativePurchase';

const APPLE_MANAGE_URL = 'https://apps.apple.com/account/subscriptions';
const PLAY_MANAGE_URL = 'https://play.google.com/store/account/subscriptions';
const STATUS_QUERY_KEY = ['subscription-status'] as const;

function daysUntil(dateStr: string): number {
  const diff = new Date(dateStr).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

function isUserCancelled(err: unknown): boolean {
  return (
    typeof err === 'object' &&
    err !== null &&
    'code' in err &&
    (err as { code?: string }).code === 'USER_CANCELLED'
  );
}

function PlanPicker({
  plans,
  value,
  onChange,
}: {
  plans: PlanOut[] | undefined;
  value: Plan;
  onChange: (p: Plan) => void;
}) {
  const { t } = useTranslation('parent');
  if (!plans || plans.length === 0) return null;
  return (
    <fieldset className="mt-3">
      <legend className="sr-only">{t('subscription.choosePlanLegend')}</legend>
      <div role="radiogroup" aria-label={t('subscription.choosePlanAriaLabel')} className="flex flex-col gap-2">
        {plans.map((p) => {
          const checked = p.plan === value;
          const per = p.interval === 'year' ? '/yr' : '/mo';
          return (
            <label
              key={p.plan}
              className={`flex min-h-[44px] cursor-pointer items-center justify-between rounded-lg border-2 px-3 py-2.5 ${
                checked ? 'border-brand-600 bg-white' : 'border-brand-200 bg-white/60'
              }`}
            >
              <span className="flex items-center gap-2">
                <input
                  type="radio"
                  name="plan"
                  value={p.plan}
                  checked={checked}
                  onChange={() => onChange(p.plan)}
                  className="h-4 w-4 accent-brand-600"
                />
                <span className="text-sm font-bold capitalize text-brand-900">{p.plan}</span>
                {p.savings_pct != null && (
                  <span className="rounded-full bg-success-100 px-2 py-0.5 text-[11px] font-bold text-success-700">
                    {t('subscription.savePercent', { pct: p.savings_pct })}
                  </span>
                )}
              </span>
              <span className="text-sm font-extrabold text-brand-900">
                {p.display_price}
                <span className="font-medium text-gray-500">{per}</span>
              </span>
            </label>
          );
        })}
      </div>
      <p className="mt-2 text-xs font-medium text-brand-800">
        {t('subscription.oneSubscriptionNote')}
      </p>
    </fieldset>
  );
}

export function SubscriptionCard() {
  const { t } = useTranslation('parent');
  const qc = useQueryClient();
  const [note, setNote] = useState<string | null>(null);
  const [plan, setPlan] = useState<Plan>('annual');

  const { data: plansData } = useQuery({
    queryKey: ['billing-plans'],
    queryFn: billingApi.getPlans,
    staleTime: 5 * 60_000,
  });
  const selected = plansData?.plans.find((p) => p.plan === plan);
  const appleProductId = selected?.apple_product_id ?? 'premium_monthly';
  const playProductId = selected?.google_product_id ?? 'premium_monthly';

  const { data: sub, isLoading } = useQuery<SubscriptionStatus | null>({
    queryKey: STATUS_QUERY_KEY,
    queryFn: billingApi.getStatus,
  });

  // --- Web (Stripe) ---
  const checkout = useMutation({
    mutationFn: () => billingApi.createCheckout(plan),
    onSuccess: (data) => {
      if (data?.url) window.location.href = data.url;
    },
  });

  const portal = useMutation({
    mutationFn: billingApi.createPortal,
    onSuccess: (data) => {
      if (data?.url) window.location.href = data.url;
    },
  });

  // --- Native (StoreKit) ---
  const refreshStatus = () => qc.invalidateQueries({ queryKey: STATUS_QUERY_KEY });

  const subscribe = useMutation({
    mutationFn: () =>
      runNativePurchase({
        platform: 'ios',
        productId: appleProductId,
        getAppleToken: async () => {
          const account = await billingApi.appleAccountToken();
          if (!account) throw new Error('Could not start purchase.');
          return account.token;
        },
        verifyApple: (jws) => billingApi.appleVerify(jws).then(() => undefined),
      }),
    onMutate: () => setNote(null),
    onSuccess: async (res) => {
      if (res.status === 'active') {
        await refreshStatus();
      } else if (res.status === 'pending') {
        setNote(t('subscription.note.purchasePending'));
      }
    },
    onError: (err) => {
      if (isUserCancelled(err)) return;
      setNote(t('subscription.note.error'));
    },
  });

  const restore = useMutation({
    mutationFn: async () => {
      const { jws } = await StoreKit.restore();
      for (const token of jws) {
        await billingApi.appleVerify(token);
      }
      return { count: jws.length };
    },
    onMutate: () => setNote(null),
    onSuccess: async (res) => {
      if (res.count > 0) {
        await refreshStatus();
      } else {
        setNote(t('subscription.note.nothingToRestoreApple'));
      }
    },
    onError: (err) => {
      if (isUserCancelled(err)) return;
      setNote(t('subscription.note.error'));
    },
  });

  // --- Native (Play Billing / Android) ---
  const subscribeAndroid = useMutation({
    mutationFn: () =>
      runNativePurchase({
        platform: 'android',
        productId: playProductId,
        getGoogleToken: async () => {
          const account = await billingApi.accountToken();
          if (!account) throw new Error('Could not start purchase.');
          return account.token;
        },
        verifyGoogle: (purchaseToken, productId) =>
          billingApi.googleVerify({ purchaseToken, productId }).then(() => undefined),
      }),
    onMutate: () => setNote(null),
    onSuccess: async (res) => {
      if (res.status === 'active') {
        await refreshStatus();
      } else if (res.status === 'pending') {
        setNote(t('subscription.note.purchasePending'));
      }
    },
    onError: (err) => {
      if (isUserCancelled(err)) return;
      setNote(t('subscription.note.error'));
    },
  });

  const restoreAndroid = useMutation({
    mutationFn: async () => {
      const { purchaseTokens } = await PlayBilling.restore();
      for (const token of purchaseTokens) {
        await billingApi.googleVerify({
          purchaseToken: token,
          productId: playProductId,
        });
      }
      return { count: purchaseTokens.length };
    },
    onMutate: () => setNote(null),
    onSuccess: async (res) => {
      if (res.count > 0) {
        await refreshStatus();
      } else {
        setNote(t('subscription.note.nothingToRestoreGoogle'));
      }
    },
    onError: (err) => {
      if (isUserCancelled(err)) return;
      setNote(t('subscription.note.error'));
    },
  });

  if (isLoading || !sub) return null;

  const native = isNativeApp();
  const isActive = sub.has_subscription && sub.status !== 'canceled';

  // Active-state presentation: a status detail line + a status badge + a
  // tonal medallion. (Detail strings stay English here, matching the rest
  // of this card; the badge/title are translated.)
  let detail: string;
  let badgeText = t('subscription.badge.active');
  let medallionCls = 'bg-success-50 text-success-700';
  let badgeCls = 'bg-success-50 text-success-700';
  if (sub.status === 'trialing' && sub.trial_ends_at) {
    const days = daysUntil(sub.trial_ends_at);
    detail = `Trial — ${days} day${days !== 1 ? 's' : ''} remaining`;
    badgeText = t('subscription.badge.trial');
    medallionCls = 'bg-brand-100 text-brand-700';
    badgeCls = 'bg-brand-100 text-brand-700';
  } else if (sub.cancel_at_period_end && sub.current_period_end) {
    detail = `Cancels ${formatDate(sub.current_period_end)}`;
    badgeText = t('subscription.badge.ending');
    medallionCls = 'bg-accent-100 text-accent-700';
    badgeCls = 'bg-accent-100 text-accent-700';
  } else if (sub.status === 'past_due') {
    detail = 'Payment issue — retrying';
    badgeText = t('subscription.badge.paymentDue');
    medallionCls = 'bg-danger-100 text-danger-700';
    badgeCls = 'bg-danger-100 text-danger-700';
  } else if (sub.current_period_end) {
    detail = `Renews ${formatDate(sub.current_period_end)}`;
  } else {
    detail = 'Active';
  }

  // Shared active-subscription card: medallion + title + status detail + a
  // tonal badge, a divider, then the platform's manage action.
  const renderActive = (onManage: () => void, label: string, loading: boolean, errorEl: ReactNode) => (
    <section
      className="rounded-2xl border border-brand-200 bg-card p-4 sm:p-6"
      aria-label={t('subscription.sectionAriaLabel')}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {/* eslint-disable-next-line i18next/no-literal-string -- decorative check glyph */}
          <span aria-hidden="true" className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-lg font-extrabold ${medallionCls}`}>✓</span>
          <div>
            <p className="text-base font-extrabold text-ink">{t('subscription.activeTitle')}</p>
            <p className="text-sm text-muted-foreground">{detail}</p>
          </div>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-bold ${badgeCls}`}>{badgeText}</span>
      </div>
      <div className="my-4 h-px bg-brand-100" />
      <Button variant="outline" className="w-full" onClick={onManage} disabled={loading}>
        {label}
      </Button>
      {errorEl}
      {note && (
        <p className="mt-3 text-sm text-brand-700" role="status">{note}</p>
      )}
    </section>
  );

  // Native: in-app purchase Subscribe / Restore / Manage — no Stripe UI.
  // Android uses Play Billing; iOS uses StoreKit.
  if (native) {
    const android = isAndroid();
    const subscribeMutation = android ? subscribeAndroid : subscribe;
    const restoreMutation = android ? restoreAndroid : restore;
    const manageUrl = android ? PLAY_MANAGE_URL : APPLE_MANAGE_URL;
    if (isActive) {
      return renderActive(
        () => window.open(manageUrl, '_blank', 'noopener,noreferrer'),
        t('subscription.manageSubscription'),
        false,
        null,
      );
    }
    return (
      <section
        className="rounded-2xl border border-brand-200 bg-brand-50 p-4 sm:p-6"
        aria-label={t('subscription.sectionAriaLabel')}
      >
        <p className="text-sm font-medium text-brand-900">{t('subscription.freeUpgrade')}</p>
        <PlanPicker plans={plansData?.plans} value={plan} onChange={setPlan} />
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            className="bg-brand-600 text-white hover:bg-brand-700"
            onClick={() => subscribeMutation.mutate()}
            disabled={subscribeMutation.isPending}
          >
            {subscribeMutation.isPending ? t('subscription.subscribing') : t('subscription.subscribe')}
          </Button>
          <Button
            variant="outline"
            onClick={() => restoreMutation.mutate()}
            disabled={restoreMutation.isPending}
          >
            {restoreMutation.isPending ? t('subscription.restoring') : t('subscription.restorePurchases')}
          </Button>
        </div>
        {note && (
          <p className="mt-3 text-sm text-brand-700" role="status">{note}</p>
        )}
      </section>
    );
  }

  // Web: existing Stripe flow (unchanged behavior).
  if (!isActive) {
    return (
      <section
        className="rounded-2xl border border-brand-200 bg-brand-50 p-4 sm:p-6"
        aria-label={t('subscription.sectionAriaLabel')}
      >
        <p className="text-sm font-medium text-brand-900">
          {t('subscription.freeUpgrade')}
        </p>
        <PlanPicker plans={plansData?.plans} value={plan} onChange={setPlan} />
        <Button
          className="mt-3 bg-brand-600 text-white hover:bg-brand-700"
          onClick={() => checkout.mutate()}
          disabled={checkout.isPending}
        >
          {checkout.isPending ? t('subscription.redirecting') : t('subscription.subscribeToPremium')}
        </Button>
        {checkout.isError && (
          <p className="mt-2 text-sm text-danger-500" role="alert">
            {t('subscription.checkoutError')}
          </p>
        )}
      </section>
    );
  }

  return renderActive(
    () => portal.mutate(),
    portal.isPending ? t('subscription.redirecting') : t('subscription.manageBilling'),
    portal.isPending,
    portal.isError ? (
      <p className="mt-2 text-sm text-danger-500" role="alert">{t('subscription.portalError')}</p>
    ) : null,
  );
}
