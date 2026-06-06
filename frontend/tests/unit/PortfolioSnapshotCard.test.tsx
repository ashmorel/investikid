import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PortfolioSnapshotCard } from '@/components/child/home/PortfolioSnapshotCard';

describe('PortfolioSnapshotCard', () => {
  it('shows value and an up indicator with a text label (not colour alone)', () => {
    render(
      <MemoryRouter>
        <PortfolioSnapshotCard totalValue="1234.50" currencyCode="GBP" changePct={2.3} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/£1,234.50/)).toBeInTheDocument();
    expect(screen.getByText(/up/i)).toBeInTheDocument(); // textual label
    expect(screen.getByText('▲')).toBeInTheDocument(); // glyph
    expect(screen.getByRole('link', { name: /trade/i })).toBeInTheDocument();
  });

  it('shows a down indicator for negative change', () => {
    render(
      <MemoryRouter>
        <PortfolioSnapshotCard totalValue="900.00" currencyCode="GBP" changePct={-1.1} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/down/i)).toBeInTheDocument();
    expect(screen.getByText('▼')).toBeInTheDocument();
  });

  it('hides the change line when no change value is provided', () => {
    render(
      <MemoryRouter>
        <PortfolioSnapshotCard totalValue="1000.00" currencyCode="GBP" changePct={null} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/£1,000.00/)).toBeInTheDocument();
    expect(screen.queryByText(/today/i)).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /trade/i })).toBeInTheDocument();
  });
});
