import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { billingApi, type Plan, type PlanOut, type SubscriptionStatus } from '@/api/billing';
import { Button } from '@/components/ui/button';
import { isAndroid, isNativeApp } from '@/lib/platform';
import { StoreKit } from '@/lib/storekit';
import { PlayBilling } from '@/lib/playBilling';

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
    mutationFn: async () => {
      const account = await billingApi.appleAccountToken();
      if (!account) throw new Error('Could not start purchase.');
      const result = await StoreKit.purchase({
        productId: appleProductId,
        appAccountToken: account.token,
      });
      if (result.jws) {
        await billingApi.appleVerify(result.jws);
        return { verified: true as const };
      }
      return { pending: Boolean(result.pending) };
    },
    onMutate: () => setNote(null),
    onSuccess: async (res) => {
      if ('verified' in res && res.verified) {
        await refreshStatus();
      } else if ('pending' in res && res.pending) {
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
    mutationFn: async () => {
      const account = await billingApi.accountToken();
      if (!account) throw new Error('Could not start purchase.');
      const result = await PlayBilling.purchase({
        productId: playProductId,
        obfuscatedAccountId: account.token,
      });
      if (result.purchaseToken) {
        await billingApi.googleVerify({
          purchaseToken: result.purchaseToken,
          productId: playProductId,
        });
        return { verified: true as const };
      }
      return { pending: Boolean(result.pending) };
    },
    onMutate: () => setNote(null),
    onSuccess: async (res) => {
      if ('verified' in res && res.verified) {
        await refreshStatus();
      } else if ('pending' in res && res.pending) {
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

  // Active subscription states (every branch below assigns statusText)
  let statusText: string;
  if (sub.status === 'trialing' && sub.trial_ends_at) {
    const days = daysUntil(sub.trial_ends_at);
    statusText = `Premium trial — ${days} day${days !== 1 ? 's' : ''} remaining`;
  } else if (sub.cancel_at_period_end && sub.current_period_end) {
    statusText = `Premium — cancels ${formatDate(sub.current_period_end)}`;
  } else if (sub.status === 'past_due') {
    statusText = 'Premium — payment issue, retrying';
  } else if (sub.current_period_end) {
    statusText = `Premium — renews ${formatDate(sub.current_period_end)}`;
  } else {
    statusText = 'Premium — active';
  }

  // Native: in-app purchase Subscribe / Restore / Manage — no Stripe UI.
  // Android uses Play Billing; iOS uses StoreKit.
  if (native) {
    const android = isAndroid();
    const subscribeMutation = android ? subscribeAndroid : subscribe;
    const restoreMutation = android ? restoreAndroid : restore;
    const manageUrl = android ? PLAY_MANAGE_URL : APPLE_MANAGE_URL;
    return (
      <section
        className="rounded-lg border-2 border-brand-200 bg-brand-50 px-4 py-4 sm:px-6 sm:py-6"
        aria-label={t('subscription.sectionAriaLabel')}
      >
        <p className="text-sm font-medium text-brand-900">
          {isActive
            ? statusText
            : t('subscription.freeUpgrade')}
        </p>

        {isActive ? (
          <Button
            variant="outline"
            className="mt-3"
            onClick={() => window.open(manageUrl, '_blank', 'noopener,noreferrer')}
          >
            {t('subscription.manageSubscription')}
          </Button>
        ) : (
          <>
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
          </>
        )}

        {note && (
          <p className="mt-3 text-sm text-brand-700" role="status">
            {note}
          </p>
        )}
      </section>
    );
  }

  // Web: existing Stripe flow (unchanged behavior).
  if (!isActive) {
    return (
      <section
        className="rounded-lg border-2 border-brand-200 bg-brand-50 px-4 py-4 sm:px-6 sm:py-6"
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
      </section>
    );
  }

  return (
    <section
      className="rounded-lg border-2 border-brand-200 bg-brand-50 px-4 py-4 sm:px-6 sm:py-6"
      aria-label={t('subscription.sectionAriaLabel')}
    >
      <p className="text-sm font-medium text-brand-900">{statusText}</p>
      <Button
        variant="outline"
        className="mt-3"
        onClick={() => portal.mutate()}
        disabled={portal.isPending}
      >
        {portal.isPending ? t('subscription.redirecting') : t('subscription.manageBilling')}
      </Button>
    </section>
  );
}
