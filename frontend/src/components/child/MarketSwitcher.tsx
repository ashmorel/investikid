import { useTranslation } from 'react-i18next';
import { useToast } from '@/hooks/use-toast';
import { useMarkets, useSwitchMarket } from '@/hooks/useMarkets';
import { flagFor } from '@/lib/marketFlags';
import { formatRewardToast } from '@/lib/marketReward';
import type { MarketSummary } from '@/api/market';

/**
 * Compact, in-place market switcher for the Learn tab. Drives the child's
 * ACTIVE MARKET (`active_market_code`) — the axis lessons are actually filtered
 * by — so tapping a flag changes the lessons shown without leaving the page.
 *
 * Only markets that have published content are offered (a toggle to an empty
 * market would just blank the list). A locked (premium-gated) market routes to
 * the paywall via `onLockedClick` instead of switching, since a free learner
 * could otherwise switch into a market whose lessons they cannot complete.
 *
 * NOTE: this is distinct from `RegionSwitcher`, which sets the legacy
 * `content_region` preference (simulator featured exchange + parent analytics)
 * and still lives in the profile menu.
 */
export function MarketSwitcher({ onLockedClick }: { onLockedClick?: (market: MarketSummary) => void }) {
  const { t } = useTranslation('markets');
  const { toast } = useToast();
  const { data: markets } = useMarkets();
  const switchMarket = useSwitchMarket();

  const choices = (markets ?? []).filter((m) => m.has_content);
  if (choices.length < 2) return null; // nothing meaningful to switch between

  function choose(m: MarketSummary) {
    if (m.is_selected || switchMarket.isPending) return;
    if (m.locked) {
      onLockedClick?.(m);
      return;
    }
    switchMarket.mutate(m.code, {
      // useSwitchMarket already invalidates the market-scoped content queries, so
      // the lesson list re-fetches for the new market right here on the Learn tab.
      onSuccess: (data) => {
        const msg = formatRewardToast(t, data?.reward, m.name);
        if (msg) toast({ description: msg });
      },
      onError: () => {
        toast({ description: t('picker.switchError'), variant: 'destructive' });
      },
    });
  }

  return (
    <div
      role="group"
      aria-label={t('switcher.label')}
      className="inline-flex flex-wrap rounded-xl border border-brand-100 bg-card p-1"
    >
      {choices.map((m) => {
        const active = m.is_selected;
        return (
          <button
            key={m.code}
            type="button"
            aria-pressed={active}
            disabled={switchMarket.isPending}
            onClick={() => choose(m)}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-base font-semibold transition-colors min-h-[44px] disabled:opacity-60 ${
              active ? 'bg-brand-gradient text-white' : 'text-brand-700 hover:bg-brand-50'
            }`}
          >
            <span aria-hidden="true">{flagFor(m.code)}</span>
            <span>{m.name}</span>
            {m.locked && !active ? <span aria-hidden="true">🔒</span> : null}
          </button>
        );
      })}
    </div>
  );
}
