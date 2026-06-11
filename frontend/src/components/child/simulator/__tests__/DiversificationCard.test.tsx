import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { DiversificationCard } from '../DiversificationCard';

describe('DiversificationCard', () => {
  it.each([
    [0, 'No investments yet', 0],
    [1, 'All eggs in one basket', 1],
    [3, 'Getting spread out', 3],
    [5, 'Nicely diversified', 5],
    [7, 'Well spread', 5],
  ])('with %i holdings shows "%s" and %i filled steps', (count, label, filled) => {
    render(<DiversificationCard holdingsCount={count} />);
    expect(screen.getByText(label)).toBeInTheDocument();
    const meter = screen.getByRole('progressbar', { name: /diversification/i });
    expect(meter).toHaveAttribute('aria-valuenow', String(filled));
    expect(meter).toHaveAttribute('aria-valuemax', '5');
  });

  it('shows the nudge line', () => {
    render(<DiversificationCard holdingsCount={2} />);
    expect(
      screen.getByText('Spreading across more companies lowers the damage any one can do'),
    ).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<DiversificationCard holdingsCount={3} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
