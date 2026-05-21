import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProgressBar } from './ProgressBar';

describe('ProgressBar', () => {
  it('renders label text', () => {
    render(<ProgressBar value={5} max={10} label="5 of 10 lessons" />);
    expect(screen.getByText('5 of 10 lessons')).toBeInTheDocument();
  });

  it('has correct ARIA attributes', () => {
    render(<ProgressBar value={3} max={10} label="3 of 10" />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '3');
    expect(bar).toHaveAttribute('aria-valuemax', '10');
    expect(bar).toHaveAttribute('aria-valuemin', '0');
  });

  it('renders correct fill width', () => {
    const { container } = render(<ProgressBar value={4} max={10} label="4 of 10" />);
    const fill = container.querySelector('[data-testid="progress-fill"]');
    expect(fill).toHaveStyle({ width: '40%' });
  });

  it('handles zero max gracefully', () => {
    render(<ProgressBar value={0} max={0} label="No lessons" />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '0');
  });

  it('clamps fill to 100%', () => {
    const { container } = render(<ProgressBar value={15} max={10} label="15 of 10" />);
    const fill = container.querySelector('[data-testid="progress-fill"]');
    expect(fill).toHaveStyle({ width: '100%' });
  });
});
