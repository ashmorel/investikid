import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { LevelProgressCard } from '../LevelProgressCard';

describe('LevelProgressCard', () => {
  it('shows the level and XP-in-level fraction', () => {
    render(<LevelProgressCard level={4} xp={340} />);
    expect(screen.getByText('Level 4 Investor')).toBeInTheDocument();
    expect(screen.getByText('40 / 100 XP')).toBeInTheDocument();
    expect(screen.getByText(/60 XP to level 5/)).toBeInTheDocument();
  });

  it('exposes an accessible progressbar with the XP-in-level value', () => {
    render(<LevelProgressCard level={4} xp={340} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '40');
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
  });

  it('has no axe violations', async () => {
    const { container } = render(<LevelProgressCard level={1} xp={0} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
