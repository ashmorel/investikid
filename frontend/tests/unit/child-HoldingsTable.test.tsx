import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { HoldingsTable } from '@/components/child/simulator/HoldingsTable';
import type { HoldingOut } from '@/api/simulator';

const holdings: HoldingOut[] = [
  { ticker: 'AAPL', exchange: 'NASDAQ', shares: '5', avg_buy_price: '180.00', current_price: '185.42', market_value: '927.10', unrealized_pl: '27.10' },
  { ticker: 'VOD', exchange: 'LSE', shares: '10', avg_buy_price: '13.00', current_price: '12.34', market_value: '123.40', unrealized_pl: '-6.60' },
];

function renderTable(h: HoldingOut[] = holdings) {
  return render(
    <MemoryRouter>
      <HoldingsTable holdings={h} />
    </MemoryRouter>,
  );
}

describe('HoldingsTable totals row', () => {
  it('renders the Total row with holdings value and overall unrealized P/L', () => {
    render(
      <MemoryRouter>
        <HoldingsTable
          holdings={holdings}
          holdingsValue="1050.50"
          totalUnrealizedPl="20.50"
          currencyCode="GBP"
        />
      </MemoryRouter>,
    );
    const totals = screen.getByTestId('holdings-totals');
    expect(totals).toHaveTextContent('Total');
    expect(totals).toHaveTextContent('£1,050.50');
    expect(totals).toHaveTextContent('+£20.50');
    expect(totals.querySelector('[data-pl="positive"]')).toBeInTheDocument();
  });

  it('shows a negative overall P/L in red with minus icon', () => {
    render(
      <MemoryRouter>
        <HoldingsTable
          holdings={holdings}
          holdingsValue="900.00"
          totalUnrealizedPl="-12.34"
          currencyCode="GBP"
        />
      </MemoryRouter>,
    );
    const totals = screen.getByTestId('holdings-totals');
    expect(totals.querySelector('[data-pl="negative"]')).toBeInTheDocument();
  });

  it('omits the totals row when totals props are absent', () => {
    render(
      <MemoryRouter>
        <HoldingsTable holdings={holdings} />
      </MemoryRouter>,
    );
    expect(screen.queryByTestId('holdings-totals')).not.toBeInTheDocument();
  });

  it('omits the totals row when there are no holdings', () => {
    render(
      <MemoryRouter>
        <HoldingsTable holdings={[]} holdingsValue="0.00" totalUnrealizedPl="0.00" currencyCode="GBP" />
      </MemoryRouter>,
    );
    expect(screen.queryByTestId('holdings-totals')).not.toBeInTheDocument();
  });
});

describe('HoldingsTable', () => {
  it('renders a row per holding with ticker and exchange badge', () => {
    renderTable();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('NASDAQ')).toBeInTheDocument();
    expect(screen.getByText('VOD')).toBeInTheDocument();
    expect(screen.getByText('LSE')).toBeInTheDocument();
  });

  it('shows signed currency P/L with green icon for gains and red for losses', () => {
    renderTable();
    const positiveRow = screen.getByText('+$27.10 USD').closest('tr')!;
    expect(positiveRow.querySelector('[data-pl="positive"]')).toBeInTheDocument();
    const negativeRow = screen.getByText('−£6.60 GBP').closest('tr')!;
    expect(negativeRow.querySelector('[data-pl="negative"]')).toBeInTheDocument();
  });

  it('renders rows as links to stock detail page', () => {
    renderTable();
    const links = screen.getAllByRole('link');
    expect(links[0]).toHaveAttribute('href', '/simulator/stock/NASDAQ/AAPL');
    expect(links[1]).toHaveAttribute('href', '/simulator/stock/LSE/VOD');
  });

  it('renders empty state when no holdings', () => {
    renderTable([]);
    expect(screen.getByText(/No stocks yet!/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Browse Market/i })).toHaveAttribute('href', '/simulator/market');
  });

  it('includes EduTooltip for Unrealized P/L column header', () => {
    renderTable();
    expect(screen.getByRole('button', { name: /info about Unrealized P\/L/i })).toBeInTheDocument();
  });
});
