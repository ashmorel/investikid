import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { formatCurrency } from '@/lib/currency';
import { tierConfig, useAgeTier } from '@/lib/ageTier';
import { track } from '@/lib/analytics';

type Props = {
  portfolioValue: string | number | null;
  currencyCode: string;
  reviewDue: number;
  badgesEarned: number | null;
  badgesTotal: number | null;
  coins: number;
};

const chipBase =
  'inline-flex min-h-[44px] items-center gap-1.5 rounded-2xl px-3.5 py-2 text-xs font-bold shadow-sm ' +
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500';

export function QuickLinksRow({ portfolioValue, currencyCode, reviewDue, badgesEarned, badgesTotal, coins }: Props) {
  const { t } = useTranslation('home');
  const tier = useAgeTier();
  const emoji = tierConfig[tier].chipEmoji;

  const chips: Array<{ key: string; to: string; label: string; text: string; className: string; icon: string; ariaLabel?: string }> = [];

  // Penny's Shop & Avatar — always shown so it's easy to find (it was
  // previously buried in the account menu). Shows the spendable coin balance.
  chips.push({
    key: 'shop',
    to: '/shop',
    label: t('quickLinks.shop'),
    text: String(coins),
    className: 'bg-brand-100 text-brand-800',
    icon: '🐷',
    ariaLabel: t('quickLinks.shopAria', { count: coins }),
  });

  if (portfolioValue != null) {
    chips.push({
      key: 'portfolio',
      to: '/simulator',
      label: t('quickLinks.portfolio'),
      text: formatCurrency(portfolioValue, currencyCode),
      className: 'bg-white text-gray-700',
      icon: '📊',
    });
  }

  if (reviewDue > 0) {
    chips.push({
      key: 'review',
      to: '/progress',
      label: t('quickLinks.review', { count: reviewDue }),
      text: '',
      className: 'bg-accent-100 text-accent-700',
      icon: '🔁',
    });
  }

  if (badgesEarned != null && badgesTotal != null) {
    chips.push({
      key: 'badges',
      to: '/stats',
      label: t('quickLinks.badges'),
      text: t('quickLinks.badgesCount', { earned: badgesEarned, total: badgesTotal }),
      className: 'bg-white text-gray-700',
      icon: '🏅',
    });
  }

  if (chips.length === 0) return null;

  return (
    <nav aria-label="Shortcuts">
      <p className="text-[10px] font-bold uppercase tracking-widest text-gray-600">{t('quickLinks.heading')}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {chips.map((c) => (
          <Link
            key={c.key}
            to={c.to}
            aria-label={c.ariaLabel ?? (c.text ? `${c.label} ${c.text}` : c.label)}
            className={`${chipBase} ${c.className}`}
            onClick={() => track('quicklink_tap', { surface: c.key })}
          >
            {emoji && <span aria-hidden="true">{c.icon}</span>}
            <span>{c.label}</span>
            {c.text && <span className="font-extrabold">{c.text}</span>}
          </Link>
        ))}
      </div>
    </nav>
  );
}
