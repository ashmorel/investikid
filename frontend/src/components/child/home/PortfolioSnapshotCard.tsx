import { Link } from 'react-router-dom';
import { formatCurrency } from '@/lib/currency';

type Props = {
  totalValue: string;
  currencyCode: string;
  changePct?: number | null;
};

export function PortfolioSnapshotCard({ totalValue, currencyCode, changePct }: Props) {
  // Only show the daily-change line when we actually have a change value; otherwise
  // a permanent "up 0.0% today" would read as misleading telemetry.
  const hasChange = changePct != null;
  const up = (changePct ?? 0) >= 0;
  const glyph = up ? '▲' : '▼';
  const label = up ? 'up' : 'down';
  return (
    <section
      aria-label="Your practice portfolio"
      className="rounded-2xl border border-line bg-card p-4 shadow-sm"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Practice portfolio
          </p>
          <p className="mt-1 text-2xl font-extrabold text-ink">
            {formatCurrency(totalValue, currencyCode)}
          </p>
          {hasChange && (
            <p className={`mt-0.5 text-sm font-semibold ${up ? 'text-success-700' : 'text-accent-700'}`}>
              <span aria-hidden="true">{glyph}</span>{' '}
              <span>
                {label} {Math.abs(changePct).toFixed(1)}% today
              </span>
            </p>
          )}
        </div>
        <Link
          to="/simulator"
          className="rounded-full bg-brand-gradient px-4 py-2 text-sm font-bold text-white shadow"
        >
          Trade
        </Link>
      </div>
    </section>
  );
}
