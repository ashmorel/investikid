import { useAdminStats } from '@/api/admin';

const CARDS = [
  { key: 'modules' as const, label: 'Modules', icon: '📖', color: 'text-success-600' },
  { key: 'lessons' as const, label: 'Lessons', icon: '📝', color: 'text-brand-600' },
  { key: 'badges' as const, label: 'Badges', icon: '🏆', color: 'text-accent-600' },
  { key: 'challenges' as const, label: 'Challenges', icon: '⚡', color: 'text-accent-600' },
];

export default function AdminDashboard() {
  const { data: stats, isLoading } = useAdminStats();

  return (
    <div>
      <h2 className="mb-2 text-xl font-semibold text-ink">Dashboard</h2>
      <p className="mb-6 text-sm text-muted-foreground">Content overview</p>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {CARDS.map((card) => (
          <div key={card.key} className="rounded-2xl border border-line bg-card p-5 shadow-sm">
            <div className="text-sm text-muted-foreground">{card.icon} {card.label}</div>
            <div className="mt-1 text-3xl font-bold text-ink">
              {isLoading ? '—' : stats?.[card.key] ?? 0}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
