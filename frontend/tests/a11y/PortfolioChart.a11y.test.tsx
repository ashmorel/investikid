import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { PortfolioChart } from '@/components/child/simulator/PortfolioChart';

describe('PortfolioChart a11y', () => {
  const history = [
    { date: '2026-05-01', value: 100 },
    { date: '2026-05-02', value: 110 },
    { date: '2026-05-03', value: 120 },
  ];

  it('container is role=img with summary label', () => {
    render(<PortfolioChart history={history as never} />);
    const region = screen.getByRole('img', { name: /portfolio/i });
    expect(region).toBeInTheDocument();
  });

  it('exposes a data table via ChartDescription', () => {
    render(<PortfolioChart history={history as never} />);
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('is axe-clean', async () => {
    const { container } = render(<PortfolioChart history={history as never} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
