import { Link } from 'react-router-dom';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { EduTooltip } from './EduTooltip';
import { formatCurrency } from '@/lib/currency';
import type { HoldingOut } from '@/api/simulator';

const EXCHANGE_CURRENCY: Record<string, string> = {
  NASDAQ: 'USD', LSE: 'GBP', HKEX: 'HKD',
};

type Props = { holdings: HoldingOut[] };

export function HoldingsTable({ holdings }: Props) {
  if (holdings.length === 0) {
    return (
      <div className="rounded-2xl border-2 border-amber-200 bg-white p-8 text-center space-y-3">
        <span className="text-5xl">📈</span>
        <p className="font-bold text-gray-900">No stocks yet!</p>
        <p className="text-sm text-gray-500">Start by browsing the market and making your first trade.</p>
        <Link
          to="/simulator/market"
          className="inline-block rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-5 py-2 text-sm font-bold text-white hover:from-amber-500 hover:to-orange-600 transition-colors"
        >
          Browse Market →
        </Link>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="border-b bg-muted/50">
          <tr>
            <th className="px-3 py-2 text-left font-medium">Ticker</th>
            <th className="px-3 py-2 text-right font-medium">Shares</th>
            <th className="px-3 py-2 text-right font-medium">Avg Buy</th>
            <th className="px-3 py-2 text-right font-medium">Current</th>
            <th className="px-3 py-2 text-right font-medium">Value</th>
            <th className="px-3 py-2 text-right font-medium">
              <EduTooltip
                term="Unrealized P/L"
                explanation="This is how much you'd gain or lose if you sold now. It's 'unrealized' because you haven't sold yet."
              />
            </th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => {
            const pl = parseFloat(h.unrealized_pl);
            const plSign = pl > 0 ? 'positive' : pl < 0 ? 'negative' : 'neutral';
            const currency = EXCHANGE_CURRENCY[h.exchange] ?? 'USD';
            return (
              <tr key={`${h.exchange}-${h.ticker}`} className="border-b last:border-0 hover:bg-muted/30">
                <td colSpan={6} className="p-0">
                  <Link
                    to={`/simulator/stock/${h.exchange}/${h.ticker}`}
                    className="flex items-center justify-between gap-2 px-3 py-2"
                  >
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{h.ticker}</span>
                      <span className="rounded bg-muted px-1.5 py-0.5 text-xs">{h.exchange}</span>
                    </span>
                    <span className="flex items-center gap-4 text-right">
                      <span>{h.shares}</span>
                      <span>{formatCurrency(h.avg_buy_price, currency)}</span>
                      <span>{formatCurrency(h.current_price, currency)}</span>
                      <span>{formatCurrency(h.market_value, currency)}</span>
                      <span className={`flex items-center gap-1 ${plSign === 'positive' ? 'text-green-600' : plSign === 'negative' ? 'text-red-600' : ''}`}>
                        {plSign === 'positive' && <TrendingUp className="h-3.5 w-3.5" data-pl="positive" />}
                        {plSign === 'negative' && <TrendingDown className="h-3.5 w-3.5" data-pl="negative" />}
                        {plSign === 'neutral' && <Minus className="h-3.5 w-3.5" data-pl="neutral" />}
                        {h.unrealized_pl}
                      </span>
                    </span>
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
