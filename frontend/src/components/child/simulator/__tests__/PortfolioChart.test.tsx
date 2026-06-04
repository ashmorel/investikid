import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PortfolioChart } from '../PortfolioChart';

const history = [
  { date: 'Mon', value: 950 },
  { date: 'Tue', value: 1080 },
];

describe('PortfolioChart variant', () => {
  it('card variant keeps the heading + role=img summary', () => {
    render(<PortfolioChart history={history} />);
    expect(screen.getByText('Portfolio Value')).toBeInTheDocument();
    expect(screen.getByRole('img')).toHaveAttribute('aria-label', expect.stringContaining('Portfolio'));
  });
  it('onGradient variant drops the heading but keeps the role=img summary', () => {
    render(<PortfolioChart history={history} variant="onGradient" />);
    expect(screen.queryByText('Portfolio Value')).not.toBeInTheDocument();
    expect(screen.getByRole('img')).toHaveAttribute('aria-label', expect.stringContaining('Portfolio'));
  });
  it('renders nothing for <2 points', () => {
    const { container } = render(<PortfolioChart history={[{ date: 'Mon', value: 1 }]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
