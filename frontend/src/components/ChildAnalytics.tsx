import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ProgressBar } from './ProgressBar';
import type { ChildAnalytics as ChildAnalyticsType } from '@/api/parent';

function formatScore(type: string, score: number | null): string {
  if (type === 'card' || type === 'video') return '✓';
  if (score === null) return '—';
  return `${Math.round(score * 100)}%`;
}

function TypeBadge({ type }: { type: string }) {
  const label = type.charAt(0).toUpperCase() + type.slice(1);
  return (
    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
      {label}
    </span>
  );
}

export function ChildAnalytics({ analytics }: { analytics: ChildAnalyticsType }) {
  const [expanded, setExpanded] = useState(false);
  const hasActivity = analytics.lessons_completed > 0 || analytics.badges.length > 0;

  if (!hasActivity) {
    return (
      <p className="mt-2 text-xs text-muted-foreground">No activity yet</p>
    );
  }

  return (
    <div className="mt-2">
      <p className="text-[13px] text-muted-foreground">
        Lvl {analytics.level}
        <span className="mx-1.5">&middot;</span>
        {analytics.xp} XP
        <span className="mx-1.5">&middot;</span>
        {analytics.streak_count}-day streak
        {analytics.streak_count > 0 && ' 🔥'}
      </p>

      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        className="mt-1 text-[13px] font-medium text-brand-700 hover:text-brand-800"
      >
        {expanded ? 'Hide progress' : 'Show progress'}
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="analytics-detail"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-3 border-t pt-2">
              <ProgressBar
                value={analytics.lessons_completed}
                max={analytics.lessons_total}
                label={`${analytics.lessons_completed} of ${analytics.lessons_total} lessons completed`}
              />

              {analytics.recent_lessons.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground">Recent:</p>
                  <ul className="mt-1 divide-y divide-muted">
                    {analytics.recent_lessons.map((lesson) => (
                      <li
                        key={`${lesson.title}-${lesson.completed_at}`}
                        className="flex items-center justify-between py-1 text-xs"
                      >
                        <span className="flex items-center gap-1.5">
                          {lesson.title}
                          <TypeBadge type={lesson.type} />
                        </span>
                        <span
                          className={
                            lesson.score !== null && lesson.score < 0.7
                              ? 'font-medium text-accent-600'
                              : 'font-medium text-success-600'
                          }
                        >
                          {formatScore(lesson.type, lesson.score)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {analytics.badges.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Badges:{' '}
                  {analytics.badges.map((b, i) => (
                    <span key={b.name}>
                      {i > 0 && <span className="mx-1">&middot;</span>}
                      {b.name}
                    </span>
                  ))}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
