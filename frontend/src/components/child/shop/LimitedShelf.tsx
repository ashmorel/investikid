import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useCollectables, type CollectableDrop, type OwnedCollectable } from '@/api/collectables';
import { useEquipCosmetic } from '@/api/cosmetics';
import { rarityClass, formatCountdown, ProgressBar } from './collectableBits';

// ---------------------------------------------------------------------------
// Active drop card
// ---------------------------------------------------------------------------
function ActiveDrop({ drop, now }: { drop: CollectableDrop; now: number }) {
  const { t } = useTranslation('child');
  const countdown = formatCountdown(drop.ends_at, now, t as Parameters<typeof formatCountdown>[2]);
  const rarity = drop.rarity ?? 'common';
  const goalLabel = t(`limited.goal.${drop.goal.type}`, { defaultValue: drop.goal.type });

  return (
    <li className="flex flex-col gap-2 rounded-2xl border border-brand-200 bg-white p-4">
      <div className="flex items-center gap-3">
        <span className="text-3xl" aria-hidden="true">{drop.emoji}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-ink">{drop.name}</p>
          <span
            className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${rarityClass(drop.rarity)}`}
          >
            {rarity}
          </span>
        </div>
        {countdown && (
          <span className="shrink-0 text-xs text-muted-foreground">{countdown}</span>
        )}
      </div>

      {drop.earned ? (
        <p className="text-sm font-bold text-brand-700">{t('limited.earned')}</p>
      ) : (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{goalLabel}</span>
            <span>{drop.goal.current} / {drop.goal.threshold}</span>
          </div>
          <ProgressBar current={drop.goal.current} threshold={drop.goal.threshold} />
        </div>
      )}
    </li>
  );
}

// ---------------------------------------------------------------------------
// Owned collectable card
// ---------------------------------------------------------------------------
function OwnedCard({ item }: { item: OwnedCollectable }) {
  const { t } = useTranslation('child');
  const equip = useEquipCosmetic();
  const rarity = item.rarity ?? 'common';

  function onEquip() {
    if (item.equipped) {
      equip.mutate({ unequip: item.slug });
    } else {
      equip.mutate({ equip: item.slug });
    }
  }

  return (
    <li className="flex flex-col items-center gap-1.5 rounded-2xl border border-brand-200 bg-white p-4 text-center">
      <span className="text-3xl" aria-hidden="true">{item.emoji}</span>
      <p className="text-sm font-bold text-ink">{item.name}</p>
      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${rarityClass(item.rarity)}`}>
        {rarity}
      </span>
      <button
        type="button"
        onClick={onEquip}
        disabled={equip.isPending}
        className={`mt-1 min-h-[44px] w-full rounded-xl px-2 text-sm font-bold focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 ${
          item.equipped
            ? 'border border-brand-600 bg-brand-50 text-brand-800'
            : 'bg-brand-600 text-white hover:bg-brand-700'
        }`}
      >
        {item.equipped ? t('shop.itemLabel.takeOff') : t('shop.itemLabel.wearIt')}
      </button>
    </li>
  );
}

// ---------------------------------------------------------------------------
// LimitedShelf
// ---------------------------------------------------------------------------
export default function LimitedShelf() {
  const { t } = useTranslation('child');
  const { data, isLoading } = useCollectables();
  // Capture the current time once per mount via useState initializer so the
  // countdown is stable across re-renders and Date.now() is not called during
  // subsequent renders (satisfying react-hooks/purity).
  const [now] = useState(() => Date.now());

  if (isLoading) {
    return (
      <div className="mt-6" aria-busy="true" aria-label={t('shop.loading')}>
        <span className="text-sm text-muted-foreground">{t('shop.loading')}</span>
      </div>
    );
  }

  const active = data?.active ?? [];
  const owned = data?.owned ?? [];
  if (active.length === 0 && owned.length === 0) {
    return null;
  }

  return (
    <section className="mt-8" aria-labelledby="limited-shelf-heading">
      <h2
        id="limited-shelf-heading"
        className="mb-1 px-1 text-xs font-bold uppercase tracking-wider text-muted-foreground"
      >
        {t('limited.title')}
      </h2>

      {active.length === 0 && (
        <p className="mt-2 text-sm text-muted-foreground">{t('limited.emptyActive')}</p>
      )}

      {active.length > 0 && (
        <ul className="mt-3 space-y-3">
          {active.map((drop) => (
            <ActiveDrop key={drop.slug} drop={drop} now={now} />
          ))}
        </ul>
      )}

      {owned.length > 0 && (
        <>
          <h3 className="mb-1 mt-5 px-1 text-xs font-bold uppercase tracking-wider text-muted-foreground">
            {t('limited.ownedTitle')}
          </h3>
          <ul className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {owned.map((item) => (
              <OwnedCard key={item.slug} item={item} />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
