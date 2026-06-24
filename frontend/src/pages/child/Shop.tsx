import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useBuyCosmetic, useCosmetics, useEquipCosmetic, useEquippedCosmetics, type CosmeticItem } from '@/api/cosmetics';
import { BackButton } from '@/components/child/BackButton';
import { Penny } from '@/components/child/ui/Penny';
import { AvatarStage } from '@/components/child/ui/AvatarStage';
import ConfirmDialog from '@/components/admin/ConfirmDialog';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { tierConfig, useAgeTier } from '@/lib/ageTier';
import LimitedShelf from '@/components/child/shop/LimitedShelf';

type TabType = 'accessory' | 'background' | 'skin';

export default function Shop() {
  const { t } = useTranslation('child');
  const { data, isLoading, isError } = useCosmetics();
  const buy = useBuyCosmetic();
  const equip = useEquipCosmetic();
  const { open: openPaywall } = usePremiumPaywall();
  const tier = useAgeTier();
  const playful = tierConfig[tier].chipEmoji;
  const [confirmItem, setConfirmItem] = useState<CosmeticItem | null>(null);
  const [tab, setTab] = useState<TabType>('accessory');

  const eq = useEquippedCosmetics();

  function onAction(item: CosmeticItem) {
    if (item.owned) {
      if (item.equipped) {
        equip.mutate({ unequip: item.id });
      } else {
        equip.mutate({ equip: item.id });
      }
      return;
    }
    if (item.is_premium && !item.can_buy && (data?.coins ?? 0) >= item.coin_cost) {
      openPaywall({ kind: 'module', label: item.name });
      return;
    }
    if (item.can_buy) setConfirmItem(item);
  }

  const tabs: { key: TabType; label: string }[] = [
    { key: 'accessory', label: t('shop.tabs.accessory') },
    { key: 'background', label: t('shop.tabs.background') },
    { key: 'skin', label: t('shop.tabs.skin') },
  ];

  const visibleItems = data?.items.filter((i) => i.type === tab) ?? [];
  const wearingNames = (data?.items ?? [])
    .filter((i) => i.equipped && i.type === 'accessory')
    .map((i) => i.name);

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <BackButton to="/home" label={t('nav.home')} />
      <div className="mt-2 flex items-center justify-between">
        <h1 className="flex items-center gap-2 text-xl font-extrabold text-ink">
          <Penny size={36} accessories={eq.accessories} skin={eq.skin} />
          {playful ? t('shop.pageTitle') : t('shop.pageTitleSimple')}
        </h1>
        <span
          className="rounded-full bg-accent-100 px-2.5 py-1 text-sm font-extrabold text-accent-700"
          aria-label={t('shop.coinsAriaLabel', { count: data?.coins ?? 0 })}
        >
          <span aria-hidden="true">🪙 </span>{data?.coins ?? 0}
        </span>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        {t('shop.description')}
      </p>

      <div className="relative mt-4">
        <AvatarStage
          hero
          background={eq.background}
          skin={eq.skin}
          accessories={eq.accessories}
          label={t('shop.avatarLabel')}
        />
        <div className="absolute inset-x-0 bottom-3 flex justify-center px-4">
          <span className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-brand-200 bg-white/95 px-3 py-1.5 text-xs shadow-sm backdrop-blur">
            {wearingNames.length > 0 ? (
              <>
                <span className="font-bold uppercase tracking-wide text-muted-foreground">{t('shop.wearing')}</span>
                <span className="truncate font-extrabold text-brand-800">{wearingNames.join(' · ')}</span>
              </>
            ) : (
              <span className="font-semibold text-muted-foreground">{t('shop.wearingEmpty')}</span>
            )}
          </span>
        </div>
      </div>

      {isLoading && <p className="mt-6 text-sm text-muted-foreground">{t('shop.loading')}</p>}
      {isError && (
        <p role="alert" className="mt-6 text-sm font-semibold text-danger-700">
          {t('shop.error')}
        </p>
      )}

      {data && (
        <>
          <div role="tablist" className="mt-5 flex gap-1 rounded-2xl border border-brand-200 bg-brand-50 p-1">
            {tabs.map(({ key, label }) => (
              <button
                key={key}
                role="tab"
                type="button"
                aria-selected={tab === key}
                onClick={() => setTab(key)}
                className={`min-h-[44px] flex-1 rounded-xl px-3 text-sm font-bold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 ${
                  tab === key
                    ? 'bg-white text-brand-800 shadow-sm'
                    : 'text-brand-600 hover:bg-brand-100'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {visibleItems.map((item) => {
              const affordable = data.coins >= item.coin_cost;
              const label = item.owned
                ? item.equipped ? t('shop.itemLabel.takeOff') : t('shop.itemLabel.wearIt')
                : item.is_premium && !item.can_buy && affordable
                  ? t('shop.itemLabel.premium')
                  : affordable ? t('shop.itemLabel.buy') : t('shop.itemLabel.keepSaving');
              return (
                <li
                  key={item.id}
                  className={`relative flex flex-col items-center gap-2 rounded-2xl bg-white p-4 text-center ${
                    item.equipped ? 'border-2 border-brand-600' : 'border border-brand-200'
                  }`}
                >
                  {item.equipped && (
                    <span className="absolute right-2 top-2 rounded-full bg-brand-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                      {t('shop.wearing')}
                    </span>
                  )}
                  <span className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-50 text-3xl" aria-hidden="true">{item.emoji}</span>
                  <p className="text-sm font-bold text-ink">
                    {item.name}
                    {item.is_premium && <span aria-hidden="true"> ✨</span>}
                  </p>
                  {item.owned ? (
                    <span className="text-xs font-semibold text-muted-foreground">{t('shop.owned')}</span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-accent-100 px-2 py-0.5 text-xs font-extrabold text-accent-700">
                      <span aria-hidden="true">🪙</span>{item.coin_cost}
                      {item.is_premium && <span className="sr-only">{t('shop.itemPremiumSr')}</span>}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => onAction(item)}
                    disabled={(!item.owned && !item.can_buy && !(item.is_premium && affordable)) || buy.isPending || equip.isPending}
                    className={`mt-1 min-h-[44px] w-full rounded-xl px-2 text-sm font-bold focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 ${
                      item.equipped
                        ? 'border border-brand-600 bg-brand-50 text-brand-800'
                        : item.owned || item.can_buy
                          ? 'bg-brand-600 text-white hover:bg-brand-700'
                          : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    {label}
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}

      <LimitedShelf />

      {buy.isError && (
        <p className="mt-3 text-sm text-danger-500" role="alert">
          {t('shop.buyError')}
        </p>
      )}
      {equip.isError && (
        <p className="mt-3 text-sm text-danger-500" role="alert">
          {t('shop.equipError')}
        </p>
      )}

      <ConfirmDialog
        open={confirmItem !== null}
        title={confirmItem ? t('shop.confirmTitle', { name: confirmItem.name }) : ''}
        message={confirmItem ? t('shop.confirmMessage', { cost: confirmItem.coin_cost, balance: data?.coins ?? 0 }) : ''}
        onConfirm={() => {
          if (confirmItem) buy.mutate(confirmItem.id);
          setConfirmItem(null);
        }}
        onCancel={() => setConfirmItem(null)}
      />
    </div>
  );
}
