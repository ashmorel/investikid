import { GradientButton } from '@/components/child/ui/GradientButton';
import { QuickStatCard } from './QuickStatCard';
import { formatCurrency } from '@/lib/currency';

type CashCardProps = {
  virtualCash: string;
  currencyCode: string;
  hasMultiCurrency: boolean;
  weekChange?: { value: string; up: boolean } | null;
};

export function CashCard({ virtualCash, currencyCode, hasMultiCurrency, weekChange }: CashCardProps) {
  return (
    <div>
      <div className="grid grid-cols-2 gap-3">
        <QuickStatCard label="Available Cash" value={formatCurrency(virtualCash, currencyCode)} emoji="💵" />
        {weekChange ? (
          <QuickStatCard label="This Week" value={weekChange.value} emoji="📈" tone={weekChange.up ? 'success' : 'danger'} />
        ) : (
          <QuickStatCard label="This Week" value="—" />
        )}
      </div>
      {hasMultiCurrency && (
        <p className="mt-2 text-xs italic text-muted-foreground">Total is approximate — converted at today's rates</p>
      )}
      <GradientButton to="/simulator/market" full className="mt-3">Browse stocks <span aria-hidden="true">→</span></GradientButton>
    </div>
  );
}
