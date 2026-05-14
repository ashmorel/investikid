import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StockHeader } from '@/components/child/simulator/StockHeader';

describe('StockHeader', () => {
  it('renders company name, ticker, exchange, and price', () => {
    render(
      <StockHeader
        name="Apple Inc."
        ticker="AAPL"
        exchange="NASDAQ"
        price="185.42"
        currency="USD"
        existingShares={null}
        existingAvgPrice={null}
      />
    );
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('NASDAQ')).toBeInTheDocument();
    expect(screen.getByText(/\$185\.42 USD/)).toBeInTheDocument();
  });

  it('shows existing holding info when user owns shares', () => {
    render(
      <StockHeader
        name="Apple Inc."
        ticker="AAPL"
        exchange="NASDAQ"
        price="185.42"
        currency="USD"
        existingShares="5"
        existingAvgPrice="180.00"
      />
    );
    expect(screen.getByText(/You own 5 shares/)).toBeInTheDocument();
    expect(screen.getByText(/Avg buy \$180\.00/)).toBeInTheDocument();
  });

  it('does not show holding info when user has no shares', () => {
    render(
      <StockHeader
        name="Apple Inc."
        ticker="AAPL"
        exchange="NASDAQ"
        price="185.42"
        currency="USD"
        existingShares={null}
        existingAvgPrice={null}
      />
    );
    expect(screen.queryByText(/You own/)).not.toBeInTheDocument();
  });

  it('includes EduTooltip about Price', () => {
    render(
      <StockHeader
        name="Apple Inc."
        ticker="AAPL"
        exchange="NASDAQ"
        price="185.42"
        currency="USD"
        existingShares={null}
        existingAvgPrice={null}
      />
    );
    expect(screen.getByRole('button', { name: /info about Price/i })).toBeInTheDocument();
  });
});
