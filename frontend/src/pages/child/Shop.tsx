import { useState } from 'react';
import { useBuyCosmetic, useCosmetics, useEquipCosmetic, type CosmeticItem } from '@/api/cosmetics';
import { BackButton } from '@/components/child/BackButton';
import { Penny } from '@/components/child/ui/Penny';
import ConfirmDialog from '@/components/admin/ConfirmDialog';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { tierConfig, useAgeTier } from '@/lib/ageTier';

export default function Shop() {
  const { data, isLoading, isError } = useCosmetics();
  const buy = useBuyCosmetic();
  const equip = useEquipCosmetic();
  const { open: openPaywall } = usePremiumPaywall();
  const tier = useAgeTier();
  const playful = tierConfig[tier].chipEmoji;
  const [confirmItem, setConfirmItem] = useState<CosmeticItem | null>(null);

  const equipped = data?.items.find((i) => i.equipped)?.slug ?? null;

  function onAction(item: CosmeticItem) {
    if (item.owned) {
      equip.mutate(item.equipped ? null : item.id);
      return;
    }
    if (item.is_premium && !item.can_buy && (data?.coins ?? 0) >= item.coin_cost) {
      openPaywall({ kind: 'module', label: item.name });
      return;
    }
    if (item.can_buy) setConfirmItem(item);
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <BackButton to="/home" label="Home" />
      <div className="mt-2 flex items-center justify-between">
        <h1 className="flex items-center gap-2 text-xl font-extrabold text-gray-900">
          <Penny size={36} accessory={equipped} />
          {playful ? "Penny's Shop" : 'Shop'}
        </h1>
        <span
          className="rounded-full bg-accent-100 px-3 py-1.5 text-sm font-extrabold text-accent-700"
          aria-label={`${data?.coins ?? 0} coins`}
        >
          <span aria-hidden="true">🪙 </span>{data?.coins ?? 0}
        </span>
      </div>
      <p className="mt-1 text-sm text-gray-600">
        Earn coins by learning — 1 coin for every XP. Spend them on looks for Penny.
      </p>

      {isLoading && <p className="mt-6 text-sm text-muted-foreground">Loading the shop…</p>}
      {isError && (
        <p role="alert" className="mt-6 text-sm font-semibold text-red-700">
          The shop is closed right now — try again shortly.
        </p>
      )}

      {data && (
        <ul className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {data.items.map((item) => {
            const affordable = data.coins >= item.coin_cost;
            const label = item.owned
              ? item.equipped ? 'Take off' : 'Wear it'
              : item.is_premium && !item.can_buy && affordable
                ? 'Premium'
                : affordable ? 'Buy' : 'Keep saving';
            return (
              <li
                key={item.id}
                className="flex flex-col items-center gap-1.5 rounded-2xl border border-brand-200 bg-white p-4 text-center"
              >
                <span className="text-3xl" aria-hidden="true">{item.emoji}</span>
                <p className="text-sm font-bold text-gray-900">
                  {item.name}
                  {item.is_premium && <span aria-hidden="true"> ✨</span>}
                </p>
                <p className="text-xs font-semibold text-gray-600">
                  <span aria-hidden="true">🪙 </span>{item.coin_cost}
                  {item.is_premium && <span className="sr-only"> — Premium item</span>}
                </p>
                <button
                  type="button"
                  onClick={() => onAction(item)}
                  disabled={(!item.owned && !item.can_buy && !(item.is_premium && affordable)) || buy.isPending || equip.isPending}
                  className={`mt-1 min-h-[44px] w-full rounded-xl px-2 text-sm font-bold focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 ${
                    item.equipped
                      ? 'border border-brand-600 bg-brand-50 text-brand-800'
                      : item.owned || item.can_buy
                        ? 'bg-brand-600 text-white hover:bg-brand-700'
                        : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {label}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <ConfirmDialog
        open={confirmItem !== null}
        title={confirmItem ? `Buy ${confirmItem.name}?` : ''}
        message={confirmItem ? `This costs ${confirmItem.coin_cost} coins. You have ${data?.coins ?? 0}.` : ''}
        onConfirm={() => {
          if (confirmItem) buy.mutate(confirmItem.id);
          setConfirmItem(null);
        }}
        onCancel={() => setConfirmItem(null)}
      />
    </div>
  );
}
