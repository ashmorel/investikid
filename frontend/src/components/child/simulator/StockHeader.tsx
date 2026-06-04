import { EduTooltip } from './EduTooltip';
import { formatCurrency } from '@/lib/currency';

type StockHeaderProps = {
  name: string;
  ticker: string;
  exchange: string;
  price: string;
  currency: string;
  existingShares: string | null;
  existingAvgPrice: string | null;
};

export function StockHeader({
  name, ticker, exchange, price, currency, existingShares, existingAvgPrice,
}: StockHeaderProps) {
  return (
    <div className="mb-6 rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">{name}</h1>
        <span className="rounded bg-brand-100 px-2 py-0.5 text-sm font-semibold text-brand-800">{ticker}</span>
        <span className="rounded bg-brand-100 px-2 py-0.5 text-sm font-semibold text-brand-800">{exchange}</span>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <p className="text-3xl font-bold">{formatCurrency(price, currency)}</p>
        <EduTooltip
          term="Price"
          explanation="This is the current price for one share. In practice mode, prices stay the same so you can learn without surprises."
        />
      </div>
      {existingShares && existingAvgPrice && (
        <p className="mt-2 text-sm text-muted-foreground">
          You own {existingShares} shares · Avg buy {formatCurrency(existingAvgPrice, currency)}
        </p>
      )}
    </div>
  );
}
