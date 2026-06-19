import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { BackButton } from '@/components/child/BackButton';
import { useToast } from '@/hooks/use-toast';
import { useMarkets, useSwitchMarket } from '@/hooks/useMarkets';
import { flagFor } from '@/lib/marketFlags';
import { formatRewardToast } from '@/lib/marketReward';

export function Markets() {
  const { t } = useTranslation('markets');
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: markets } = useMarkets();
  const switchMarket = useSwitchMarket();

  function choose(code: string, isSelected: boolean) {
    if (isSelected) return; // already learning here — nothing to switch
    const marketName = (markets ?? []).find((m) => m.code === code)?.name ?? code;
    switchMarket.mutate(code, {
      // The hook already invalidates the market-scoped content queries on success;
      // celebrate any enroll reward, then drop the child back to Home for the new market.
      onSuccess: (data) => {
        const msg = formatRewardToast(t, data?.reward, marketName);
        if (msg) toast({ description: msg });
        navigate('/');
      },
    });
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <BackButton to="/" label={t('picker.back')} />
      <header className="mt-2">
        <h1 className="text-xl font-extrabold text-gray-900">{t('picker.title')}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t('picker.subtitle')}</p>
      </header>

      <ul className="mt-6 flex flex-col gap-3">
        {(markets ?? []).map((m) => (
          <li key={m.code}>
            <button
              type="button"
              aria-pressed={m.is_selected}
              disabled={switchMarket.isPending}
              onClick={() => choose(m.code, m.is_selected)}
              className={`flex w-full min-h-[44px] items-center gap-3 rounded-2xl border bg-card p-4 text-left shadow-sm transition-colors hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 disabled:opacity-60 ${
                m.is_selected ? 'border-brand-500 ring-1 ring-brand-200' : 'border-brand-100'
              }`}
            >
              <span className="text-2xl" aria-hidden="true">{flagFor(m.code)}</span>
              <span className="flex flex-col">
                <span className="font-semibold text-gray-900">{m.name}</span>
                <span className="text-sm text-muted-foreground">{m.currency_code}</span>
              </span>
              {m.is_selected ? (
                <span className="ml-auto rounded-full bg-brand-100 px-2.5 py-0.5 text-sm font-semibold text-brand-700">
                  {t('picker.learning')}
                </span>
              ) : m.locked ? (
                <span className="ml-auto rounded-full bg-brand-500 px-2.5 py-0.5 text-sm font-semibold text-white">
                  {t('picker.premium')}
                </span>
              ) : !m.has_content ? (
                <span className="ml-auto rounded-full bg-gray-100 px-2.5 py-0.5 text-sm font-semibold text-muted-foreground">
                  {t('picker.comingSoon')}
                </span>
              ) : null}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
