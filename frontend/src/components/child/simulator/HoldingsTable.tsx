import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { EduTooltip } from './EduTooltip';
import { formatCurrency } from '@/lib/currency';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import type { HoldingOut } from '@/api/simulator';

const EXCHANGE_CURRENCY: Record<string, string> = {
  NASDAQ: 'USD', LSE: 'GBP', HKEX: 'HKD',
};

type Props = {
  holdings: HoldingOut[];
  /** Portfolio-level totals from the API; the row is omitted when absent. */
  holdingsValue?: string;
  totalUnrealizedPl?: string;
  currencyCode?: string;
};

/** "+£27.10 GBP" / "−£6.60 GBP" — sign first, then symbol, so negatives read cleanly. */
function formatSignedCurrency(value: string, currencyCode: string): string {
  const num = parseFloat(value);
  const sign = num > 0 ? '+' : num < 0 ? '−' : '';
  return `${sign}${formatCurrency(Math.abs(num), currencyCode)}`;
}

function TotalPl({ value, currencyCode }: { value: string; currencyCode: string }) {
  const pl = parseFloat(value);
  const sign = pl > 0 ? 'positive' : pl < 0 ? 'negative' : 'neutral';
  return (
    <span
      className={`flex items-center gap-1 font-bold ${sign === 'positive' ? 'text-success-600' : sign === 'negative' ? 'text-danger-600' : ''}`}
    >
      {sign === 'positive' && <TrendingUp className="h-3.5 w-3.5" data-pl="positive" />}
      {sign === 'negative' && <TrendingDown className="h-3.5 w-3.5" data-pl="negative" />}
      {sign === 'neutral' && <Minus className="h-3.5 w-3.5" data-pl="neutral" />}
      {formatSignedCurrency(value, currencyCode)}
    </span>
  );
}

export function HoldingsTable({ holdings, holdingsValue, totalUnrealizedPl, currencyCode }: Props) {
  const { t } = useTranslation('simulator');
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const navigate = useNavigate();
  const showTotals =
    holdings.length > 0 && !!holdingsValue && !!totalUnrealizedPl && !!currencyCode;

  if (holdings.length === 0) {
    return (
      <div className="rounded-2xl border border-brand-100 shadow-sm bg-white p-8 text-center space-y-3">
        <span className="text-5xl">📈</span>
        <p className="font-bold text-gray-900">{t('holdings.noStocksTitle')}</p>
        <p className="text-sm text-gray-500">{t('holdings.noStocksBody')}</p>
        <Link
          to="/simulator/market"
          className="inline-block rounded-xl bg-brand-gradient px-5 py-2 text-sm font-bold text-white hover:opacity-90 transition-opacity"
        >
          {t('holdings.browseMarket')}
        </Link>
      </div>
    );
  }

  if (!isDesktop) {
    return (
      <div className="space-y-2">
        {holdings.map((h) => {
          const pl = parseFloat(h.unrealized_pl);
          const plSign = pl > 0 ? 'positive' : pl < 0 ? 'negative' : 'neutral';
          const currency = EXCHANGE_CURRENCY[h.exchange] ?? 'USD';
          return (
            <Link
              key={`${h.exchange}-${h.ticker}`}
              to={`/simulator/stock/${h.exchange}/${h.ticker}`}
              className="block rounded-xl border border-brand-100 shadow-sm bg-white p-3 transition-shadow hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-100 text-xs font-extrabold text-brand-700" aria-hidden="true">{h.ticker.slice(0, 2)}</span>
                  <span className="font-bold">{h.ticker}</span>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-xs">{h.exchange}</span>
                </span>
                <span className={`flex items-center gap-1 text-sm ${plSign === 'positive' ? 'text-success-600' : plSign === 'negative' ? 'text-danger-600' : ''}`}>
                  {plSign === 'positive' && <TrendingUp className="h-3.5 w-3.5" data-pl="positive" />}
                  {plSign === 'negative' && <TrendingDown className="h-3.5 w-3.5" data-pl="negative" />}
                  {plSign === 'neutral' && <Minus className="h-3.5 w-3.5" data-pl="neutral" />}
                  {formatSignedCurrency(h.unrealized_pl, currency)}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                <span>{t('holdings.sharesCount', { count: h.shares })}</span>
                <span>{t('holdings.avgBuy', { value: formatCurrency(h.avg_buy_price, currency) })}</span>
                <span>{t('holdings.marketValue', { value: formatCurrency(h.market_value, currency) })}</span>
              </div>
            </Link>
          );
        })}
        {showTotals && (
          <div className="rounded-xl border border-brand-200 bg-brand-50 p-3" data-testid="holdings-totals">
            <div className="flex items-center justify-between">
              <span className="font-bold text-gray-900">{t('holdings.total')}</span>
              <TotalPl value={totalUnrealizedPl!} currencyCode={currencyCode!} />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {t('holdings.portfolioValue', { value: formatCurrency(holdingsValue!, currencyCode!) })}
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-brand-100 shadow-sm">
      <table className="w-full text-sm">
        <thead className="border-b bg-muted/50">
          <tr>
            <th className="px-3 py-2 text-left font-medium">{t('holdings.col.ticker')}</th>
            <th className="px-3 py-2 text-left font-medium">{t('holdings.col.shares')}</th>
            <th className="px-3 py-2 text-left font-medium">{t('holdings.col.avgBuy')}</th>
            <th className="px-3 py-2 text-left font-medium">{t('holdings.col.current')}</th>
            <th className="px-3 py-2 text-left font-medium">{t('holdings.col.value')}</th>
            <th className="px-3 py-2 text-left font-medium">
              <EduTooltip
                term={t('holdings.col.unrealizedPl')}
                explanation={t('holdings.col.unrealizedPlTooltip')}
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
              <tr
                key={`${h.exchange}-${h.ticker}`}
                className="cursor-pointer border-b last:border-0 hover:bg-muted/30"
                onClick={() => navigate(`/simulator/stock/${h.exchange}/${h.ticker}`)}
              >
                <td className="px-3 py-2">
                  <Link
                    to={`/simulator/stock/${h.exchange}/${h.ticker}`}
                    onClick={(e) => e.stopPropagation()}
                    className="flex items-center gap-2"
                  >
                    <span className="font-medium">{h.ticker}</span>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-xs">{h.exchange}</span>
                  </Link>
                </td>
                <td className="px-3 py-2 text-left">{h.shares}</td>
                <td className="px-3 py-2 text-left">{formatCurrency(h.avg_buy_price, currency)}</td>
                <td className="px-3 py-2 text-left">{formatCurrency(h.current_price, currency)}</td>
                <td className="px-3 py-2 text-left">{formatCurrency(h.market_value, currency)}</td>
                <td className="px-3 py-2 text-left">
                  <span className={`flex items-center gap-1 ${plSign === 'positive' ? 'text-success-600' : plSign === 'negative' ? 'text-danger-600' : ''}`}>
                    {plSign === 'positive' && <TrendingUp className="h-3.5 w-3.5" data-pl="positive" />}
                    {plSign === 'negative' && <TrendingDown className="h-3.5 w-3.5" data-pl="negative" />}
                    {plSign === 'neutral' && <Minus className="h-3.5 w-3.5" data-pl="neutral" />}
                    {formatSignedCurrency(h.unrealized_pl, currency)}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
        {showTotals && (
          <tfoot className="border-t bg-brand-50" data-testid="holdings-totals">
            <tr>
              <td className="px-3 py-2 font-bold text-gray-900" colSpan={4}>{t('holdings.total')}</td>
              <td className="px-3 py-2 font-bold">{formatCurrency(holdingsValue!, currencyCode!)}</td>
              <td className="px-3 py-2"><TotalPl value={totalUnrealizedPl!} currencyCode={currencyCode!} /></td>
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );
}
