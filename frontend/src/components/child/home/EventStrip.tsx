import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/api/client';
import { tierConfig, useAgeTier } from '@/lib/ageTier';

type SeasonalEvent = {
  title: string;
  emoji: string;
  ends_at: string;
  xp_bonus_pct: number;
};

/** Slim seasonal-event banner (M9). Renders ONLY while an event is active, so
 * it never competes with the Home hero outside event weeks. */
export function EventStrip() {
  const tier = useAgeTier();
  const emoji = tierConfig[tier].chipEmoji;
  const { data } = useQuery<{ event: SeasonalEvent | null } | null>({
    queryKey: ['active-event'],
    queryFn: () => apiFetch<{ event: SeasonalEvent | null }>('/events/active'),
    staleTime: 5 * 60_000,
  });

  const event = data?.event;
  if (!event) return null;

  return (
    <p
      role="status"
      aria-label={`Seasonal event: ${event.title}${event.xp_bonus_pct ? `, ${event.xp_bonus_pct} percent bonus XP` : ''}`}
      className="mb-3 flex min-h-[36px] items-center justify-center gap-1.5 rounded-xl bg-accent-100 px-3 py-1.5 text-center text-xs font-extrabold text-accent-700"
    >
      {emoji && event.emoji && <span aria-hidden="true">{event.emoji} </span>}
      {event.title}
      {event.xp_bonus_pct > 0 && <span> — +{event.xp_bonus_pct}% XP!</span>}
    </p>
  );
}
