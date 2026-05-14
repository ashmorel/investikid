import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CashCard } from '@/components/child/simulator/CashCard';

function renderCard(props: Partial<Parameters<typeof CashCard>[0]> = {}) {
  const defaults = {
    virtualCash: '10000.00',
    totalValue: '12500.00',
    currencyCode: 'USD',
    hasMultiCurrency: false,
  };
  return render(
    <MemoryRouter>
      <CashCard {...defaults} {...props} />
    </MemoryRouter>,
  );
}

describe('CashCard', () => {
  it('renders virtual cash and total value', () => {
    renderCard();
    expect(screen.getByText(/\$10,000\.00 USD/)).toBeInTheDocument();
    expect(screen.getByText(/\$12,500\.00 USD/)).toBeInTheDocument();
  });

  it('shows multi-currency footnote when hasMultiCurrency is true', () => {
    renderCard({ hasMultiCurrency: true });
    expect(screen.getByText(/approximate/i)).toBeInTheDocument();
  });

  it('hides multi-currency footnote when hasMultiCurrency is false', () => {
    renderCard({ hasMultiCurrency: false });
    expect(screen.queryByText(/approximate/i)).not.toBeInTheDocument();
  });

  it('renders Browse stocks link to /simulator/market', () => {
    renderCard();
    const link = screen.getByRole('link', { name: /browse stocks/i });
    expect(link).toHaveAttribute('href', '/simulator/market');
  });
});
