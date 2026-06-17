import { useTranslation } from 'react-i18next';
import { GradientButton } from '@/components/child/ui/GradientButton';
import { QuickStatCard } from './QuickStatCard';
import { formatCurrency } from '@/lib/currency';

type CashCardProps = {
  virtualCash: string;
  currencyCode: string;
  hasMultiCurrency: boolean;
  weekChange?: { value: string; up: boolean } | null;
};

export function CashCard({ virtualCash, currencyCode, hasMultiCurrency, weekChange }: CashCardProps) {
  const { t } = useTranslation('simulator');
  return (
    <div>
      <div className="grid grid-cols-2 gap-3">
        <QuickStatCard label={t('cashCard.availableCash')} value={formatCurrency(virtualCash, currencyCode)} emoji="💵" />
        {weekChange ? (
          <QuickStatCard label={t('cashCard.thisWeek')} value={weekChange.value} emoji="📈" tone={weekChange.up ? 'success' : 'danger'} />
        ) : (
          <QuickStatCard label={t('cashCard.thisWeek')} value="—" />
        )}
      </div>
      {hasMultiCurrency && (
        <p className="mt-2 text-xs italic text-muted-foreground">{t('cashCard.multiCurrencyNote')}</p>
      )}
      <GradientButton to="/simulator/market" full className="mt-3">{t('cashCard.browseStocks')} <span aria-hidden="true">→</span></GradientButton>
    </div>
  );
}
