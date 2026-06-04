import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CashCard } from '@/components/child/simulator/CashCard';

function renderCard(props: Partial<Parameters<typeof CashCard>[0]> = {}) {
  const defaults = {
    virtualCash: '10000.00',
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
  it('renders available cash', () => {
    renderCard();
    expect(screen.getByText(/Available Cash/i)).toBeInTheDocument();
    expect(screen.getByText(/\$10,000\.00 USD/)).toBeInTheDocument();
  });

  it('renders week change when provided', () => {
    renderCard({ weekChange: { value: '+$130.00 USD', up: true } });
    expect(screen.getByText(/This Week/i)).toBeInTheDocument();
    expect(screen.getByText(/\+\$130\.00 USD/)).toBeInTheDocument();
  });

  it('renders dash when no weekChange', () => {
    renderCard();
    expect(screen.getByText('—')).toBeInTheDocument();
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
