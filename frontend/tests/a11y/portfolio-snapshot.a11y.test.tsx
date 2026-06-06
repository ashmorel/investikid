import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { PortfolioSnapshotCard } from '@/components/child/home/PortfolioSnapshotCard';

describe('a11y: PortfolioSnapshotCard', () => {
  it('has no axe violations', async () => {
    const { container } = render(
      <MemoryRouter>
        <PortfolioSnapshotCard totalValue="1000.00" currencyCode="GBP" changePct={-1.1} />
      </MemoryRouter>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
