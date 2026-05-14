import { EduTooltip } from './EduTooltip';
import type { TradeOut } from '@/api/simulator';

type Props = { trades: TradeOut[] };

export function TradeHistoryTab({ trades }: Props) {
  return (
    <div>
      <div className="mb-2">
        <EduTooltip
          term="Trade"
          explanation="A trade is when you buy or sell shares of a stock."
        />
      </div>
      {trades.length === 0 ? (
        <p className="py-4 text-center text-sm text-muted-foreground">No trades yet.</p>
      ) : (
        <div className="space-y-2">
          {trades.map((t) => (
            <div key={t.id} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium">{t.ticker}</span>
                <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                  t.type === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {t.type === 'buy' ? 'Buy' : 'Sell'}
                </span>
              </div>
              <div className="flex items-center gap-4 text-muted-foreground">
                <span>{t.shares} shares</span>
                <span>@ {t.price}</span>
                <span>{new Date(t.executed_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
