import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { simulatorApi } from '@/api/simulator';
import { currencyOptions } from '@/lib/region';
import { getCurrencySymbol } from '@/lib/currency';

export function CurrencySelector({ currentCurrency }: { currentCurrency: string }) {
  const { t } = useTranslation('child');
  const qc = useQueryClient();
  const options = currencyOptions(currentCurrency);

  const save = useMutation({
    mutationFn: (currency_code: string) => simulatorApi.setCurrency(currency_code),
    onSuccess: () => {
      // Independent of region: holdings persist, totals re-display converted.
      for (const key of [['me'], ['portfolio'], ['portfolio-history']]) {
        qc.invalidateQueries({ queryKey: key });
      }
    },
  });

  return (
    <div className="space-y-1.5">
      <label htmlFor="practice-currency" className="text-sm font-medium">
        {t('currencySelector.label')}
      </label>
      <select
        id="practice-currency"
        aria-label={t('currencySelector.label')}
        className="h-11 w-full rounded-md border border-input bg-background px-3 text-base"
        value={currentCurrency}
        disabled={save.isPending}
        onChange={(e) => save.mutate(e.target.value)}
      >
        {options.map((c) => (
          <option key={c} value={c}>
            {getCurrencySymbol(c)} {c}
          </option>
        ))}
      </select>
    </div>
  );
}
