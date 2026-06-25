import { BookOpen, Flame, Lock, Star, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import type { BadgeDefinition, EarnedBadge } from '@/api/gamification';
import { cn } from '@/lib/utils';

type Props = {
  allBadges: BadgeDefinition[];
  earnedBadges: EarnedBadge[];
};

const CONDITION_ICONS: Record<string, React.ElementType> = {
  lesson_count: BookOpen,
  streak_days: Flame,
  trade_count: TrendingUp,
  total_xp: Star,
};

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, scale: 0.9 },
  show: { opacity: 1, scale: 1 },
};

export function BadgeGrid({ allBadges, earnedBadges }: Props) {
  const { t } = useTranslation('child');
  const earnedById = new Map(earnedBadges.map((b) => [b.id, b]));

  function formatEarnedDate(iso: string): string {
    const date = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / 86_400_000);

    if (diffDays === 0) return t('badges.earnedToday');
    if (diffDays === 1) return t('badges.earnedYesterday');
    if (diffDays < 30) return t('badges.earnedDaysAgo', { count: diffDays });
    return t('badges.earnedOn', { date: date.toLocaleDateString() });
  }

  return (
    <motion.div
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {allBadges.map((badge) => {
        const earned = earnedById.get(badge.id);
        const Icon = CONDITION_ICONS[badge.condition_type] ?? Star;
        const isNewlyEarned = earned && formatEarnedDate(earned.earned_at) === t('badges.earnedToday');

        return (
          <motion.div
            key={badge.id}
            variants={item}
            className={cn(
              'relative rounded-xl border-brand-200 p-4',
              earned ? 'bg-card' : 'bg-muted/50 opacity-60',
            )}
          >
            <div className="flex items-start gap-3">
              <motion.div
                className={cn(
                  'flex h-10 w-10 shrink-0 items-center justify-center rounded-full',
                  earned ? 'bg-brand-100 text-brand-700' : 'bg-muted text-muted-foreground',
                )}
                {...(isNewlyEarned
                  ? {
                      initial: { scale: 0, rotate: -180 },
                      animate: { scale: 1, rotate: 0 },
                      transition: { type: 'spring', stiffness: 200, damping: 12 },
                    }
                  : {})}
              >
                <Icon className="h-5 w-5" />
              </motion.div>
              <div className="min-w-0 flex-1">
                <p className="font-medium">{badge.name}</p>
                <p className="text-sm text-muted-foreground">{badge.description}</p>
                {earned ? (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatEarnedDate(earned.earned_at)}
                  </p>
                ) : (
                  <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground" aria-label={t('badges.locked')}>
                    <Lock className="h-3 w-3" />
                    {t('badges.locked')}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        );
      })}
    </motion.div>
  );
}
