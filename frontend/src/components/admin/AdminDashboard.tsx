import { useAdminStats } from '@/api/admin';

const CARDS = [
  { key: 'modules' as const, label: 'Modules', icon: '📖', color: 'text-success-500' },
  { key: 'lessons' as const, label: 'Lessons', icon: '📝', color: 'text-blue-400' },
  { key: 'badges' as const, label: 'Badges', icon: '🏆', color: 'text-accent-500' },
  { key: 'challenges' as const, label: 'Challenges', icon: '⚡', color: 'text-accent-500' },
];

export default function AdminDashboard() {
  const { data: stats, isLoading } = useAdminStats();

  return (
    <div>
      <h2 className="mb-2 text-xl font-semibold text-slate-50">Dashboard</h2>
      <p className="mb-6 text-sm text-slate-400">Content overview</p>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {CARDS.map((card) => (
          <div key={card.key} className="rounded-lg border border-slate-700 bg-slate-900 p-5">
            <div className="text-sm text-slate-500">{card.icon} {card.label}</div>
            <div className="mt-1 text-3xl font-bold text-slate-50">
              {isLoading ? '—' : stats?.[card.key] ?? 0}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
