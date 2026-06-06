import type { GroupLeaderboard as Board } from '@/api/groups';
import { GROUP } from '@/lib/groupConfig';
import { cn } from '@/lib/utils';

export function GroupLeaderboard({ boards }: { boards: Board[] }) {
  if (boards.length === 0) {
    return (
      <p className="rounded-2xl border border-brand-100 bg-card p-4 text-sm text-muted-foreground">
        {GROUP.noGroupPrompt}
      </p>
    );
  }
  return (
    <div className="space-y-4">
      {boards.map((b) => (
        <section
          key={b.group_id}
          aria-label={`${b.group_name} leaderboard`}
          className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm"
        >
          <h3 className="mb-2 text-sm font-extrabold text-gray-900">{b.group_name}</h3>
          <ol className="space-y-1">
            {b.entries.map((e, i) => (
              <li
                key={e.username}
                className={cn(
                  'flex items-center justify-between rounded-lg px-3 py-1.5 text-sm',
                  e.is_me ? 'bg-brand-100 font-bold text-brand-800' : 'text-gray-700',
                )}
              >
                <span>
                  <span className="mr-2 text-muted-foreground">{i + 1}.</span>
                  {e.username}
                  {e.is_me && <span className="ml-2 text-xs text-brand-700">(you)</span>}
                </span>
                <span className="font-semibold">{e.xp_this_week} XP</span>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
