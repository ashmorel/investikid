import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { billingApi, type SubscriptionStatus } from '@/api/billing';
import { Button } from '@/components/ui/button';
import { isNativeApp } from '@/lib/platform';
import { StoreKit } from '@/lib/storekit';

const PREMIUM_PRODUCT_ID = 'premium_monthly';
const APPLE_MANAGE_URL = 'https://apps.apple.com/account/subscriptions';
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

export function SubscriptionCard() {
  const qc = useQueryClient();
  const [note, setNote] = useState<string | null>(null);

  const { data: sub, isLoading } = useQuery<SubscriptionStatus | null>({
    queryKey: STATUS_QUERY_KEY,
    queryFn: billingApi.getStatus,
  });

  // --- Web (Stripe) ---
  const checkout = useMutation({
    mutationFn: billingApi.createCheckout,
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
        productId: PREMIUM_PRODUCT_ID,
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
        setNote('Your purchase is pending — it can take a moment to confirm.');
      }
    },
    onError: (err) => {
      if (isUserCancelled(err)) return;
      setNote('Something went wrong. Please try again.');
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
        setNote('Nothing to restore on this Apple ID.');
      }
    },
    onError: (err) => {
      if (isUserCancelled(err)) return;
      setNote('Something went wrong. Please try again.');
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

  // Native (iOS): StoreKit Subscribe / Restore / Manage — no Stripe UI.
  if (native) {
    return (
      <section
        className="rounded-lg border-2 border-brand-200 bg-brand-50 px-4 py-4 sm:px-6 sm:py-6"
        aria-label="Subscription status"
      >
        <p className="text-sm font-medium text-brand-900">
          {isActive
            ? statusText
            : 'Free plan — upgrade for AI coach, advanced scenarios, and more'}
        </p>

        {isActive ? (
          <Button
            variant="outline"
            className="mt-3"
            onClick={() => window.open(APPLE_MANAGE_URL, '_blank', 'noopener,noreferrer')}
          >
            Manage subscription
          </Button>
        ) : (
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              className="bg-brand-600 text-white hover:bg-brand-700"
              onClick={() => subscribe.mutate()}
              disabled={subscribe.isPending}
            >
              {subscribe.isPending ? 'Subscribing…' : 'Subscribe'}
            </Button>
            <Button
              variant="outline"
              onClick={() => restore.mutate()}
              disabled={restore.isPending}
            >
              {restore.isPending ? 'Restoring…' : 'Restore Purchases'}
            </Button>
          </div>
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
        aria-label="Subscription status"
      >
        <p className="text-sm font-medium text-brand-900">
          Free plan — upgrade for AI coach, advanced scenarios, and more
        </p>
        <Button
          className="mt-3 bg-brand-600 text-white hover:bg-brand-700"
          onClick={() => checkout.mutate()}
          disabled={checkout.isPending}
        >
          {checkout.isPending ? 'Redirecting…' : 'Subscribe to Premium'}
        </Button>
      </section>
    );
  }

  return (
    <section
      className="rounded-lg border-2 border-brand-200 bg-brand-50 px-4 py-4 sm:px-6 sm:py-6"
      aria-label="Subscription status"
    >
      <p className="text-sm font-medium text-brand-900">{statusText}</p>
      <Button
        variant="outline"
        className="mt-3"
        onClick={() => portal.mutate()}
        disabled={portal.isPending}
      >
        {portal.isPending ? 'Redirecting…' : 'Manage Billing'}
      </Button>
    </section>
  );
}
