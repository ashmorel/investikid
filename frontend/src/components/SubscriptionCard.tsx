import { useMutation, useQuery } from '@tanstack/react-query';
import { billingApi, type SubscriptionStatus } from '@/api/billing';
import { Button } from '@/components/ui/button';

function daysUntil(dateStr: string): number {
  const diff = new Date(dateStr).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

export function SubscriptionCard() {
  const { data: sub, isLoading } = useQuery<SubscriptionStatus | null>({
    queryKey: ['subscription-status'],
    queryFn: billingApi.getStatus,
  });

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

  if (isLoading || !sub) return null;

  const isActive = sub.has_subscription && sub.status !== 'canceled';

  // No subscription or canceled — show upgrade CTA
  if (!isActive) {
    return (
      <section
        className="rounded-lg border-2 border-amber-200 bg-amber-50 px-4 py-4 sm:px-6 sm:py-6"
        aria-label="Subscription status"
      >
        <p className="text-sm font-medium text-amber-900">
          Free plan — upgrade for AI coach, advanced scenarios, and more
        </p>
        <Button
          className="mt-3 bg-amber-500 text-white hover:bg-amber-600"
          onClick={() => checkout.mutate()}
          disabled={checkout.isPending}
        >
          {checkout.isPending ? 'Redirecting…' : 'Subscribe to Premium'}
        </Button>
      </section>
    );
  }

  // Active subscription states
  let statusText = '';
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

  return (
    <section
      className="rounded-lg border-2 border-amber-200 bg-amber-50 px-4 py-4 sm:px-6 sm:py-6"
      aria-label="Subscription status"
    >
      <p className="text-sm font-medium text-amber-900">{statusText}</p>
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
