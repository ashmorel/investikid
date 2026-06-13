import { useQuery } from '@tanstack/react-query';
import { groupsApi, type GroupChallenges } from '@/api/groups';
import { tierConfig, useAgeTier } from '@/lib/ageTier';

/** Co-op group challenge progress (M9) — shown on Stats near the group boards. */
export function GroupGoals() {
  const tier = useAgeTier();
  const emoji = tierConfig[tier].chipEmoji;
  const { data } = useQuery<GroupChallenges[] | null>({
    queryKey: ['group-challenges'],
    queryFn: groupsApi.myChallenges,
    staleTime: 60_000,
  });

  const blocks = (data ?? []).filter((b) => b.challenges.length > 0);
  if (blocks.length === 0) return null;

  return (
    <section aria-label="Group goals" className="mt-4 space-y-3">
      {blocks.map((block) => (
        <div key={block.group_id} className="rounded-2xl border border-brand-200 bg-white p-4">
          <h3 className="text-sm font-extrabold text-gray-900">
            {emoji && <span aria-hidden="true">🎯 </span>}{block.group_name} — group goals
          </h3>
          <ul className="mt-2 space-y-3">
            {block.challenges.map((ch) => {
              const pct = Math.min(100, Math.round((ch.group_progress / ch.target_value) * 100));
              return (
                <li key={ch.id}>
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-bold text-gray-800">{ch.title}</p>
                    <p className="text-xs font-semibold text-gray-600">
                      {ch.completed
                        ? emoji ? 'Completed! 🎉' : 'Completed'
                        : `${ch.group_progress} / ${ch.target_value}`}
                    </p>
                  </div>
                  <div
                    className="mt-1 h-2 w-full overflow-hidden rounded-full bg-brand-100"
                    role="progressbar"
                    aria-valuenow={ch.group_progress}
                    aria-valuemin={0}
                    aria-valuemax={ch.target_value}
                    aria-label={`${ch.title} group progress`}
                  >
                    <div
                      className={`h-full rounded-full ${ch.completed ? 'bg-success-500' : 'bg-brand-gradient'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <p className="mt-0.5 text-[11px] text-gray-500">{ch.description}</p>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </section>
  );
}
