import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { GrowthProjectionCard } from '../GrowthProjectionCard';

describe('GrowthProjectionCard', () => {
  it('projects 7% compound growth at 10/20/30 years', () => {
    render(<GrowthProjectionCard totalValue="1000.00" currencyCode="GBP" />);
    // 1000 × 1.07^10 = 1967.151…, ^20 = 3869.684…, ^30 = 7612.255…
    expect(screen.getByText('£1,967.15 GBP')).toBeInTheDocument();
    expect(screen.getByText('£3,869.68 GBP')).toBeInTheDocument();
    expect(screen.getByText('£7,612.26 GBP')).toBeInTheDocument();
    expect(screen.getByText('In 10 years')).toBeInTheDocument();
    expect(screen.getByText('In 20 years')).toBeInTheDocument();
    expect(screen.getByText('In 30 years')).toBeInTheDocument();
  });

  it('renders nothing when the portfolio value is zero', () => {
    const { container } = render(<GrowthProjectionCard totalValue="0.00" currencyCode="GBP" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the disclaimer', () => {
    render(<GrowthProjectionCard totalValue="500.00" currencyCode="USD" />);
    expect(
      screen.getByText('An illustration of compounding — not a prediction or a promise.'),
    ).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<GrowthProjectionCard totalValue="1000.00" currencyCode="USD" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
