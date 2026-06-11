import { formatCurrency } from '@/lib/currency';

const YEARS = [10, 20, 30];
const ANNUAL_GROWTH = 1.07;

export function GrowthProjectionCard({
  totalValue,
  currencyCode,
}: {
  totalValue: string;
  currencyCode: string;
}) {
  const value = parseFloat(totalValue);
  if (!Number.isFinite(value) || value <= 0) return null;

  return (
    <div className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold text-muted-foreground">
          If your portfolio kept growing ~7% a year…
        </p>
        <span className="text-xl" aria-hidden="true">🌱</span>
      </div>
      <dl className="mt-2 space-y-1">
        {YEARS.map((n) => (
          <div key={n} className="flex items-baseline justify-between">
            <dt className="text-sm text-muted-foreground">In {n} years</dt>
            <dd className="text-sm font-extrabold text-ink">
              {formatCurrency((value * Math.pow(ANNUAL_GROWTH, n)).toFixed(2), currencyCode)}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-xs italic text-muted-foreground">
        An illustration of compounding — not a prediction or a promise.
      </p>
    </div>
  );
}
