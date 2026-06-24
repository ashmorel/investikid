import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useCollectables, type CollectableDrop } from '@/api/collectables';
import { rarityClass, formatCountdown, ProgressBar } from '@/components/child/shop/collectableBits';

// Pure: soonest-ending, not-yet-earned live drop; a null ends_at sorts last.
export function pickFeatured(active: CollectableDrop[]): CollectableDrop | undefined {
  return active
    .filter((d) => !d.earned)
    .sort((a, b) => {
      if (a.ends_at === b.ends_at) return 0;
      if (a.ends_at === null) return 1;
      if (b.ends_at === null) return -1;
      return new Date(a.ends_at).getTime() - new Date(b.ends_at).getTime();
    })[0];
}

export default function FeaturedDropCard() {
  const { t } = useTranslation('home');
  const { t: tChild } = useTranslation('child');
  const { data } = useCollectables();
  // Capture now once per mount so the countdown is stable across re-renders
  // (and Date.now() is not called during render — satisfies react-hooks/purity).
  const [now] = useState(() => Date.now());

  const featured = pickFeatured(data?.active ?? []);
  if (!featured) return null;

  const countdown = formatCountdown(
    featured.ends_at, now, tChild as Parameters<typeof formatCountdown>[2],
  );
  const rarity = featured.rarity ?? 'common';

  return (
    <Link
      to="/shop"
      aria-label={t('featuredDrop.ariaLabel', {
        name: featured.name, current: featured.goal.current, threshold: featured.goal.threshold,
      })}
      className="block rounded-xl border border-line bg-card p-4 min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
    >
      <div className="flex items-center gap-2">
        <span className="text-2xl" aria-hidden="true">{featured.emoji}</span>
        <div className="min-w-0 flex-1">
          <div className="text-base font-extrabold text-ink">{featured.name}</div>
          <span className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${rarityClass(featured.rarity)}`}>
            {rarity}
          </span>
        </div>
        {countdown && <span className="shrink-0 text-xs text-muted-foreground">{countdown}</span>}
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
        <span>{t('featuredDrop.title')}</span>
        <span>{featured.goal.current} / {featured.goal.threshold}</span>
      </div>
      <div className="mt-1">
        <ProgressBar current={featured.goal.current} threshold={featured.goal.threshold} />
      </div>
    </Link>
  );
}
