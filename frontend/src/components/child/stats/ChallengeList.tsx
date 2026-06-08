import { CheckCircle2 } from 'lucide-react';
import type { ChallengeOut } from '@/api/gamification';
import { cn } from '@/lib/utils';
import { PremiumBadge } from '@/components/child/PremiumBadge';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';

type Props = {
  challenges: ChallengeOut[];
  isPremium?: boolean;
};

export function ChallengeList({ challenges, isPremium = false }: Props) {
  const { open: openPaywall } = usePremiumPaywall();

  if (challenges.length === 0) {
    return (
      <p className="py-8 text-center text-muted-foreground">
        No active challenges this week.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {challenges.map((c) => {
        const completed = c.completed_at !== null;
        const pct = Math.min(Math.round((c.progress / c.target_value) * 100), 100);
        const locked = c.is_premium && !isPremium;

        const card = (
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  {completed && <CheckCircle2 className="h-4 w-4 shrink-0 text-success-600" />}
                  <p className="font-medium">{c.title}</p>
                  {c.is_premium && <PremiumBadge />}
                </div>
                <p className="text-sm text-muted-foreground">{c.description}</p>
              </div>
              <span className="shrink-0 text-sm font-medium text-primary">+{c.xp_reward} XP</span>
            </div>

            <div className="mt-3 flex items-center gap-2">
              <div
                role="progressbar"
                aria-valuenow={c.progress}
                aria-valuemin={0}
                aria-valuemax={c.target_value}
                aria-label={`${c.title} progress`}
                className="h-2 flex-1 rounded-full bg-muted"
              >
                <div
                  className={cn(
                    'h-full rounded-full transition-all',
                    completed ? 'bg-success-600' : 'bg-brand-600',
                  )}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs font-medium text-muted-foreground">
                {completed ? 'Completed!' : `${pct}%`}
              </span>
            </div>
          </div>
        );

        if (locked) {
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => openPaywall({ kind: 'challenge', label: c.title })}
              className="block w-full text-left"
            >
              {card}
            </button>
          );
        }

        return <div key={c.id}>{card}</div>;
      })}
    </div>
  );
}
