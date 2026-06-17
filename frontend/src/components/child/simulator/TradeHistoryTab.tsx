import { useTranslation } from 'react-i18next';
import { EduTooltip } from './EduTooltip';
import type { TradeOut } from '@/api/simulator';

type Props = { trades: TradeOut[] };

export function TradeHistoryTab({ trades }: Props) {
  const { t } = useTranslation('simulator');
  return (
    <div>
      <div className="mb-2">
        <EduTooltip
          term={t('tradeHistory.tradeTooltipTerm')}
          explanation={t('tradeHistory.tradeTooltipExplanation')}
        />
      </div>
      {trades.length === 0 ? (
        <p className="py-4 text-center text-sm text-muted-foreground">{t('tradeHistory.noTrades')}</p>
      ) : (
        <div className="space-y-2">
          {trades.map((trade) => (
            <div key={trade.id} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium">{trade.ticker}</span>
                <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                  trade.type === 'buy' ? 'bg-success-100 text-success-700' : 'bg-danger-100 text-danger-700'
                }`}>
                  {trade.type === 'buy' ? t('tradeHistory.buy') : t('tradeHistory.sell')}
                </span>
              </div>
              <div className="flex items-center gap-4 text-muted-foreground">
                <span>{t('tradeHistory.sharesCount', { count: trade.shares })}</span>
                <span>@ {trade.price}</span>
                <span>{new Date(trade.executed_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
