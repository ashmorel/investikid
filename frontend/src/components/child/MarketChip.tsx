import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useMarkets } from '../../hooks/useMarkets';
import { flagFor } from '../../lib/marketFlags';

export function MarketChip({ activeCode, xp }: { activeCode: string; xp?: number | null }) {
  const { t } = useTranslation('markets');
  const { data: markets } = useMarkets();
  const active = markets?.find((m) => m.code === activeCode);
  const name = active?.name ?? activeCode;
  const showXp = typeof xp === 'number';
  return (
    <Link
      to="/markets"
      aria-label={`${name} — ${t('chip.label')}`}
      className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-brand-100 bg-card px-3 py-2 text-sm font-semibold text-brand-700 transition-colors hover:bg-brand-50"
    >
      <span aria-hidden="true">{flagFor(activeCode)}</span>
      <span>{name}</span>
      {showXp && (
        <span aria-hidden="true" className="ml-0.5 flex items-center gap-1 border-l border-brand-100 pl-2">
          <span className="font-bold">{xp}</span>
          {/* eslint-disable-next-line i18next/no-literal-string -- decorative unit, aria-hidden */}
          <span className="text-brand-400">XP</span>
        </span>
      )}
      {/* eslint-disable-next-line i18next/no-literal-string -- decorative chevron glyph, aria-hidden */}
      <span aria-hidden="true" className="text-brand-400">⌄</span>
    </Link>
  );
}
