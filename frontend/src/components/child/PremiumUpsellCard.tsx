import { useState } from 'react';
import { Sparkles, X } from 'lucide-react';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { isNudgeDismissed, dismissNudge } from '@/lib/premiumNudge';

const KEY = 'home-upsell';

export function PremiumUpsellCard({ isPremium }: { isPremium: boolean }) {
  const { open } = usePremiumPaywall();
  const [hidden, setHidden] = useState(() => isNudgeDismissed(KEY));
  if (isPremium || hidden) return null;
  return (
    <div className="flex min-h-[44px] items-center gap-2 rounded-2xl border border-accent-200 bg-accent-50 px-3.5 py-2">
      <Sparkles className="h-4 w-4 shrink-0 text-accent-700" aria-hidden="true" />
      <p className="min-w-0 flex-1 truncate text-xs font-bold text-gray-800">Unlock all levels & the AI coach</p>
      <button
        type="button"
        onClick={() => open({ kind: 'home', label: 'Premium' })}
        className="shrink-0 min-h-[44px] rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
      >
        Ask my grown-up
      </button>
      <button
        type="button"
        onClick={() => { dismissNudge(KEY); setHidden(true); }}
        aria-label="Dismiss"
        className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-accent-700 hover:bg-accent-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-500"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}
