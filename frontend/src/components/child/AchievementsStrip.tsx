import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { badgeIcon } from '@/api/admin';
import type { BadgeDefinition, EarnedBadge } from '@/api/gamification';

export function AchievementsStrip({
  allBadges,
  earnedBadges,
}: {
  allBadges: BadgeDefinition[];
  earnedBadges: EarnedBadge[];
}) {
  if (!allBadges.length) return null;
  const earnedIds = new Set(earnedBadges.map((b) => b.id));
  return (
    <section aria-label="Achievements">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-extrabold uppercase tracking-wider text-gray-700">Achievements</h2>
        <Link to="/stats" className="text-xs font-bold text-brand-700 hover:underline">
          See all <span aria-hidden="true">→</span>
        </Link>
      </div>
      <ul className="flex gap-3 overflow-x-auto pb-1">
        {allBadges.map((b) => {
          const earned = earnedIds.has(b.id);
          return (
            <li key={b.id} className="flex w-16 shrink-0 flex-col items-center gap-1 text-center">
              <span
                className={cn(
                  'flex h-12 w-12 items-center justify-center rounded-2xl text-2xl',
                  earned ? 'bg-brand-gradient shadow' : 'bg-muted',
                )}
                aria-hidden="true"
              >
                {earned ? badgeIcon(b) : <Lock className="h-5 w-5 text-gray-400" />}
              </span>
              <span className={cn('text-[10px] font-semibold leading-tight', earned ? 'text-gray-700' : 'text-gray-400')}>
                {b.name}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
