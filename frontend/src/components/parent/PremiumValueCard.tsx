import { useQuery } from '@tanstack/react-query';
import { billingApi, type SubscriptionStatus } from '@/api/billing';
import { premiumApi } from '@/api/premium';
import { PREMIUM_BENEFITS } from '@/lib/premiumConfig';
import { Button } from '@/components/ui/button';

const STATUS_QUERY_KEY = ['subscription-status'] as const;
const REQUESTS_KEY = ['premium-requests'];

/**
 * Non-subscribed parent upsell: a concise "Premium gives your child…" value
 * block + a prominent Subscribe CTA. When a child has a pending premium
 * request, it is highlighted by name. Subscribed parents see nothing here
 * (they manage their subscription via SubscriptionCard). Billing itself is
 * NOT reimplemented — onSubscribe routes to the existing subscribe action.
 */
export function PremiumValueCard({ onSubscribe }: { onSubscribe?: () => void }) {
  const { data: sub, isLoading } = useQuery<SubscriptionStatus | null>({
    queryKey: STATUS_QUERY_KEY,
    queryFn: billingApi.getStatus,
  });
  const requestsQuery = useQuery({
    queryKey: REQUESTS_KEY,
    queryFn: premiumApi.parentRequests,
    retry: false,
  });

  if (isLoading || !sub) return null;

  const isActive = sub.has_subscription && sub.status !== 'canceled';
  if (isActive) return null;

  const reqs = requestsQuery.data ?? [];
  const pendingNames = Array.from(new Set(reqs.map((r) => r.child_username)));

  return (
    <section
      aria-label="Premium upgrade"
      className="mb-4 rounded-2xl border-2 border-brand-200 bg-brand-50 p-4 sm:p-6"
    >
      <h2 className="text-base font-extrabold text-brand-900">
        Premium gives your child…
      </h2>
      <ul className="mt-3 space-y-2">
        {PREMIUM_BENEFITS.map((benefit) => (
          <li key={benefit} className="flex items-start gap-2 text-sm text-ink">
            <span aria-hidden="true" className="text-brand-600">✓</span>
            <span>{benefit}</span>
          </li>
        ))}
      </ul>

      {pendingNames.length > 0 && (
        <p className="mt-4 rounded-xl bg-accent-50 px-3 py-2 text-sm font-medium text-accent-700">
          <strong>{pendingNames.join(' and ')}</strong> asked to unlock Premium —
          subscribe to say yes.
        </p>
      )}

      <Button
        className="mt-4 min-h-[44px] bg-brand-600 text-white hover:bg-brand-700"
        onClick={() => onSubscribe?.()}
      >
        Subscribe to Premium
      </Button>
    </section>
  );
}
