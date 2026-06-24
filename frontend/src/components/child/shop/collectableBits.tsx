// Shared presentation bits for limited-edition collectables, used by both the
// shop's LimitedShelf and the Home FeaturedDropCard. Behaviour is identical to
// the original inline copies in LimitedShelf.

export const RARITY_STYLE: Record<string, string> = {
  legendary: 'bg-amber-100 text-amber-800',
  epic:      'bg-purple-100 text-purple-800',
  rare:      'bg-sky-100 text-sky-800',
  common:    'bg-muted text-muted-foreground',
};

export function rarityClass(rarity: string | null): string {
  return rarity ? (RARITY_STYLE[rarity] ?? RARITY_STYLE.common) : RARITY_STYLE.common;
}

// Rarity-forward card border accent (same conventional ramp as RARITY_STYLE).
export const RARITY_BORDER: Record<string, string> = {
  legendary: 'border-amber-300',
  epic:      'border-purple-300',
  rare:      'border-sky-300',
  common:    'border-brand-200',
};

export function rarityBorder(rarity: string | null): string {
  return rarity ? (RARITY_BORDER[rarity] ?? RARITY_BORDER.common) : RARITY_BORDER.common;
}

// Pure: no side-effects, `now` passed in so it is stable across renders.
export function formatCountdown(
  endsAt: string | null,
  now: number,
  t: (key: string, opts?: Record<string, unknown>) => string,
): string {
  if (!endsAt) return '';
  const ms = new Date(endsAt).getTime() - now;
  if (ms <= 0) return '';
  const days = Math.floor(ms / 86_400_000);
  const hours = Math.floor((ms % 86_400_000) / 3_600_000);
  if (days > 0) return t('limited.endsInDays', { count: days });
  if (hours > 0) return t('limited.endsInHours', { count: hours });
  return t('limited.endsInLessThanHour');
}

export function ProgressBar({ current, threshold }: { current: number; threshold: number }) {
  const pct = threshold > 0 ? Math.min(100, (current / threshold) * 100) : 0;
  return (
    <div
      className="h-2 overflow-hidden rounded-full bg-muted"
      role="progressbar"
      aria-label={`${current} / ${threshold}`}
      aria-valuenow={current}
      aria-valuemin={0}
      aria-valuemax={threshold}
    >
      <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: `${pct}%` }} />
    </div>
  );
}
