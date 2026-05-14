import { Link } from 'react-router-dom';
import { formatCurrency } from '@/lib/currency';

type CashCardProps = {
  virtualCash: string;
  totalValue: string;
  currencyCode: string;
  hasMultiCurrency: boolean;
  showTotalValue?: boolean;
};

export function CashCard({ virtualCash, totalValue, currencyCode, hasMultiCurrency, showTotalValue = true }: CashCardProps) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">Virtual Cash</p>
          <p className="text-xl font-semibold">{formatCurrency(virtualCash, currencyCode)}</p>
        </div>
        {showTotalValue && (
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Total Portfolio Value</p>
            <p className="text-xl font-semibold">{formatCurrency(totalValue, currencyCode)}</p>
          </div>
        )}
      </div>
      {hasMultiCurrency && (
        <p className="mt-2 text-xs text-muted-foreground italic">
          Total is approximate — converted at today's rates
        </p>
      )}
      <div className="mt-3">
        <Link
          to="/simulator/market"
          className="text-sm font-medium text-primary hover:underline"
        >
          Browse stocks →
        </Link>
      </div>
    </div>
  );
}
