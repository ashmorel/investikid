import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { QuickStatCard } from '../QuickStatCard';

describe('QuickStatCard', () => {
  it('renders label and value', () => {
    render(<QuickStatCard label="Available Cash" value="$250.00" />);
    expect(screen.getByText('Available Cash')).toBeInTheDocument();
    expect(screen.getByText('$250.00')).toBeInTheDocument();
  });
  it('applies the success tone class to the value', () => {
    render(<QuickStatCard label="This Week" value="+$130" tone="success" />);
    expect(screen.getByText('+$130')).toHaveClass('text-success-700');
  });
  it('has no axe violations', async () => {
    const { container } = render(<QuickStatCard label="Available Cash" value="$250.00" emoji="💵" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
