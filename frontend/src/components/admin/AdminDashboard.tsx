import { useTranslation } from 'react-i18next';
import { useAdminStats } from '@/api/admin';

const CARDS = [
  { key: 'modules' as const, tKey: 'dashboard.cards.modules', icon: '📖', color: 'text-success-600' },
  { key: 'lessons' as const, tKey: 'dashboard.cards.lessons', icon: '📝', color: 'text-brand-600' },
  { key: 'badges' as const, tKey: 'dashboard.cards.badges', icon: '🏆', color: 'text-accent-600' },
  { key: 'challenges' as const, tKey: 'dashboard.cards.challenges', icon: '⚡', color: 'text-accent-600' },
];

export default function AdminDashboard() {
  const { t } = useTranslation('admin');
  const { data: stats, isLoading } = useAdminStats();

  return (
    <div>
      <h2 className="mb-2 text-xl font-semibold text-ink">{t('dashboard.heading')}</h2>
      <p className="mb-6 text-sm text-muted-foreground">{t('dashboard.contentOverview')}</p>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {CARDS.map((card) => (
          <div key={card.key} className="rounded-2xl border border-line bg-card p-5 shadow-sm">
            <div className="text-sm text-muted-foreground">{card.icon} {t(card.tKey)}</div>
            <div className="mt-1 text-3xl font-bold text-ink">
              {isLoading ? '—' : stats?.[card.key] ?? 0}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
