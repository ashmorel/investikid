import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { axe } from 'vitest-axe';
import { TierChip } from '../TierChip';

describe('TierChip', () => {
  it('renders an "Investor" pill labelled for screen readers', () => {
    render(<TierChip />);
    const chip = screen.getByText('Investor');
    expect(chip).toHaveAccessibleName('Investor mode');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<TierChip />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
