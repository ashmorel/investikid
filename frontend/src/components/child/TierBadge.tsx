type Props = { premium: boolean };

export function TierBadge({ premium }: Props) {
  return (
    <span
      data-testid="tier-badge"
      className={
        premium
          ? 'rounded-full bg-accent-100 px-2 py-0.5 text-xs font-semibold text-accent-700'
          : 'rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600'
      }
    >
      {premium ? 'Premium ✨' : 'Free'}
    </span>
  );
}
