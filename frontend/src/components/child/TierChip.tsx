/** Small pill marking the investor (14–18) experience. Rendered only when tierConfig.showTierChip. */
export function TierChip() {
  return (
    <span
      aria-label="Investor mode"
      className="inline-flex items-center rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700"
    >
      Investor
    </span>
  );
}
