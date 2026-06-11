const BANDS: { max: number; label: string }[] = [
  { max: 0, label: 'No investments yet' },
  { max: 1, label: 'All eggs in one basket' },
  { max: 3, label: 'Getting spread out' },
  { max: 5, label: 'Nicely diversified' },
  { max: Infinity, label: 'Well spread' },
];

export function DiversificationCard({ holdingsCount }: { holdingsCount: number }) {
  const label = BANDS.find((b) => holdingsCount <= b.max)!.label;
  const filled = Math.min(holdingsCount, 5);

  return (
    <div className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold text-muted-foreground">Diversification</p>
        <span className="text-xl" aria-hidden="true">🧺</span>
      </div>
      <p className="mt-0.5 text-lg font-extrabold text-ink">{label}</p>
      <div
        role="progressbar"
        aria-label="Diversification level"
        aria-valuemin={0}
        aria-valuemax={5}
        aria-valuenow={filled}
        aria-valuetext={`${filled} of 5`}
        className="mt-2 flex gap-1"
      >
        {Array.from({ length: 5 }, (_, i) => (
          <div
            key={i}
            className={`h-2 flex-1 rounded-full ${i < filled ? 'bg-brand-500' : 'bg-brand-100'}`}
          />
        ))}
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        Spreading across more companies lowers the damage any one can do
      </p>
    </div>
  );
}
