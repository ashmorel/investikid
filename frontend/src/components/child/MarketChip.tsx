import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useMarkets } from '../../hooks/useMarkets';
import { flagFor } from '../../lib/marketFlags';

export function MarketChip({ activeCode }: { activeCode: string }) {
  const { t } = useTranslation('markets');
  const { data: markets } = useMarkets();
  const active = markets?.find((m) => m.code === activeCode);
  const name = active?.name ?? activeCode;
  return (
    <Link
      to="/markets"
      aria-label={`${name} — ${t('chip.label')}`}
      className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-brand-100 bg-card px-3 py-2 text-sm font-semibold text-brand-700 transition-colors hover:bg-brand-50"
    >
      <span aria-hidden="true">{flagFor(activeCode)}</span>
      <span>{name}</span>
      {/* eslint-disable-next-line i18next/no-literal-string -- decorative chevron glyph, aria-hidden */}
      <span aria-hidden="true" className="text-brand-400">⌄</span>
    </Link>
  );
}
