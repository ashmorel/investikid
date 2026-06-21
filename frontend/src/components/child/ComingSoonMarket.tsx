import { useTranslation } from 'react-i18next';
import { Penny } from './ui/Penny';
import { useMarkets, useSwitchMarket } from '../../hooks/useMarkets';

export function ComingSoonMarket({ marketName }: { marketName: string }) {
  const { t } = useTranslation('markets');
  const { data: markets } = useMarkets();
  const switchMarket = useSwitchMarket();
  // The content-ready market to fall back to (GB by default).
  const home = markets?.find((m) => m.has_content);

  return (
    <div className="flex flex-col items-center gap-3 rounded-3xl border border-brand-100 bg-card p-7 text-center shadow-sm">
      <Penny size={72} mood="thinking" />
      <p className="text-base font-bold text-foreground">{t('comingSoon.title', { market: marketName })}</p>
      <p className="text-sm text-muted-foreground">{t('comingSoon.body', { home: home?.name ?? marketName })}</p>
      {home && (
        <button
          type="button"
          onClick={() => switchMarket.mutate(home.code)}
          disabled={switchMarket.isPending}
          className="min-h-[44px] rounded-xl bg-brand-gradient px-5 py-2.5 text-sm font-bold text-white shadow-sm transition-[filter] hover:brightness-110 disabled:opacity-60"
        >
          {t('comingSoon.switchBack', { home: home.name })}
        </button>
      )}
      {switchMarket.isError && (
        <p className="mt-2 text-sm text-danger-500" role="alert">
          {t('picker.switchError')}
        </p>
      )}
    </div>
  );
}
