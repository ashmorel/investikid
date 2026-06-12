import { Link } from 'react-router-dom';
import { formatCurrency } from '@/lib/currency';
import { tierConfig, useAgeTier } from '@/lib/ageTier';

type Props = {
  portfolioValue: string | number | null;
  currencyCode: string;
  reviewDue: number;
  badgesEarned: number | null;
  badgesTotal: number | null;
};

const chipBase =
  'inline-flex min-h-[44px] items-center gap-1.5 rounded-2xl px-3.5 py-2 text-xs font-bold shadow-sm ' +
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500';

export function QuickLinksRow({ portfolioValue, currencyCode, reviewDue, badgesEarned, badgesTotal }: Props) {
  const tier = useAgeTier();
  const emoji = tierConfig[tier].chipEmoji;

  const chips: Array<{ key: string; to: string; label: string; text: string; className: string; icon: string }> = [];

  if (portfolioValue != null) {
    chips.push({
      key: 'portfolio',
      to: '/simulator',
      label: 'Portfolio',
      text: formatCurrency(portfolioValue, currencyCode),
      className: 'bg-white text-gray-700',
      icon: '📊',
    });
  }

  if (reviewDue > 0) {
    chips.push({
      key: 'review',
      to: '/progress',
      label: `${reviewDue} to review`,
      text: '',
      className: 'bg-accent-100 text-accent-700',
      icon: '🔁',
    });
  }

  if (badgesEarned != null && badgesTotal != null) {
    chips.push({
      key: 'badges',
      to: '/stats',
      label: 'Badges',
      text: `${badgesEarned} of ${badgesTotal}`,
      className: 'bg-white text-gray-700',
      icon: '🏅',
    });
  }

  if (chips.length === 0) return null;

  return (
    <nav aria-label="Shortcuts">
      <p className="text-[10px] font-bold uppercase tracking-widest text-gray-600">While you're here</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {chips.map((c) => (
          <Link key={c.key} to={c.to} aria-label={c.text ? `${c.label} ${c.text}` : c.label} className={`${chipBase} ${c.className}`}>
            {emoji && <span aria-hidden="true">{c.icon}</span>}
            <span>{c.label}</span>
            {c.text && <span className="font-extrabold">{c.text}</span>}
          </Link>
        ))}
      </div>
    </nav>
  );
}
