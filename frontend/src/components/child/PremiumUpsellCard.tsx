import { useState } from 'react';
import { Sparkles, X } from 'lucide-react';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { isNudgeDismissed, dismissNudge } from '@/lib/premiumNudge';
import { PREMIUM_BENEFITS } from '@/lib/premiumConfig';

const KEY = 'home-upsell';

export function PremiumUpsellCard({ isPremium }: { isPremium: boolean }) {
  const { open } = usePremiumPaywall();
  const [hidden, setHidden] = useState(() => isNudgeDismissed(KEY));
  if (isPremium || hidden) return null;
  return (
    <div className="relative rounded-2xl border-2 border-accent-200 bg-accent-50 p-4">
      <button
        type="button"
        onClick={() => { dismissNudge(KEY); setHidden(true); }}
        aria-label="Dismiss"
        className="absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-full text-accent-700 hover:bg-accent-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-500"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-accent-700" aria-hidden="true" />
        <h2 className="text-base font-bold text-gray-900">Unlock Premium 🌟</h2>
      </div>
      <ul className="mt-2 space-y-1 text-sm text-gray-700">
        {PREMIUM_BENEFITS.slice(0, 2).map((b) => (
          <li key={b} className="flex items-center gap-1.5"><span aria-hidden="true">✨</span>{b}</li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => open({ kind: 'home', label: 'Premium' })}
        className="mt-3 inline-flex min-h-[44px] items-center rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
      >
        Ask my grown-up
      </button>
    </div>
  );
}
