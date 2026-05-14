import type { LeaderboardEntry } from '@/api/gamification';
import { countryFlag } from '@/lib/country';
import { cn } from '@/lib/utils';

type Props = {
  entries: LeaderboardEntry[];
  currentUsername: string;
};

export function LeaderboardTable({ entries, currentUsername }: Props) {
  if (entries.length === 0) {
    return (
      <p className="py-8 text-center text-muted-foreground">
        No activity this week yet. Complete a lesson to get on the board!
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium">#</th>
            <th className="px-4 py-3 text-left font-medium">Username</th>
            <th className="px-4 py-3 text-left font-medium">Country</th>
            <th className="px-4 py-3 text-right font-medium">XP This Week</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, i) => {
            const isCurrentUser = entry.username === currentUsername;
            return (
              <tr
                key={entry.username}
                className={cn(
                  'border-b last:border-b-0',
                  isCurrentUser && 'bg-primary/5 font-medium',
                )}
              >
                <td className="px-4 py-3">{i + 1}</td>
                <td className="px-4 py-3">
                  <span className="flex items-center gap-2">
                    {entry.username}
                    {isCurrentUser && (
                      <span className="rounded-full bg-primary px-2 py-0.5 text-xs text-primary-foreground">
                        You
                      </span>
                    )}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span aria-label={entry.country_code}>
                    {countryFlag(entry.country_code)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">{entry.xp_this_week}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
