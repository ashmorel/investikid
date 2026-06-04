import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { PortfolioHero } from '../PortfolioHero';

const history = [
  { date: 'Mon', value: 950 },
  { date: 'Fri', value: 1080 },
];

describe('PortfolioHero', () => {
  it('shows the Practice Portfolio label and total value', () => {
    render(<PortfolioHero totalValue="1080.00" currencyCode="USD" history={history} />);
    expect(screen.getByText(/Practice Portfolio/i)).toBeInTheDocument();
    expect(screen.getByText('$1,080.00 USD')).toBeInTheDocument();
  });
  it('shows an up change pill from history first→last', () => {
    render(<PortfolioHero totalValue="1080.00" currencyCode="USD" history={history} />);
    expect(screen.getAllByText(/13\.7%/)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/this week/i)[0]).toBeInTheDocument();
  });
  it('hides the change pill when history has <2 points', () => {
    render(<PortfolioHero totalValue="1080.00" currencyCode="USD" history={[{ date: 'Mon', value: 1080 }]} />);
    expect(screen.queryByText(/this week/i)).not.toBeInTheDocument();
    expect(screen.getByText('$1,080.00 USD')).toBeInTheDocument();
  });
  it('has no axe violations', async () => {
    const { container } = render(<PortfolioHero totalValue="1080.00" currencyCode="USD" history={history} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
