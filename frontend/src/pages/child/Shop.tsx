import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useBuyCosmetic, useCosmetics, useEquipCosmetic, useEquippedCosmetics, type CosmeticItem } from '@/api/cosmetics';
import { BackButton } from '@/components/child/BackButton';
import { Penny } from '@/components/child/ui/Penny';
import { AvatarStage } from '@/components/child/ui/AvatarStage';
import ConfirmDialog from '@/components/admin/ConfirmDialog';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { tierConfig, useAgeTier } from '@/lib/ageTier';

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
        equip.mutate({ unequip: item.type });
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

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <BackButton to="/home" label={t('nav.home')} />
      <div className="mt-2 flex items-center justify-between">
        <h1 className="flex items-center gap-2 text-xl font-extrabold text-gray-900">
          <Penny size={36} accessory={eq.accessory} skin={eq.skin} />
          {playful ? t('shop.pageTitle') : t('shop.pageTitleSimple')}
        </h1>
        <span
          className="rounded-full bg-accent-100 px-3 py-1.5 text-sm font-extrabold text-accent-700"
          aria-label={t('shop.coinsAriaLabel', { count: data?.coins ?? 0 })}
        >
          <span aria-hidden="true">🪙 </span>{data?.coins ?? 0}
        </span>
      </div>
      <p className="mt-1 text-sm text-gray-600">
        {t('shop.description')}
      </p>

      <div className="mt-4">
        <AvatarStage
          background={eq.background}
          skin={eq.skin}
          accessory={eq.accessory}
          label={t('shop.avatarLabel')}
        />
      </div>

      {isLoading && <p className="mt-6 text-sm text-muted-foreground">{t('shop.loading')}</p>}
      {isError && (
        <p role="alert" className="mt-6 text-sm font-semibold text-red-700">
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
                  className="flex flex-col items-center gap-1.5 rounded-2xl border border-brand-200 bg-white p-4 text-center"
                >
                  <span className="text-3xl" aria-hidden="true">{item.emoji}</span>
                  <p className="text-sm font-bold text-gray-900">
                    {item.name}
                    {item.is_premium && <span aria-hidden="true"> ✨</span>}
                  </p>
                  <p className="text-xs font-semibold text-gray-600">
                    <span aria-hidden="true">🪙 </span>{item.coin_cost}
                    {item.is_premium && <span className="sr-only">{t('shop.itemPremiumSr')}</span>}
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
        </>
      )}

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
