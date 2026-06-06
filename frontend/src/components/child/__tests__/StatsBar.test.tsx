import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { axe } from 'vitest-axe';
import { StatsBar } from '../StatsBar';

describe('StatsBar freeze indicator', () => {
  it('shows the shield with count when freezes > 0', () => {
    render(<StatsBar xp={10} level={1} streakCount={5} streakFreezes={2} lastActivityDate={null} />);
    expect(screen.getByLabelText(/2 streak freeze/i)).toBeInTheDocument();
  });
  it('hides the shield when freezes is 0', () => {
    render(<StatsBar xp={10} level={1} streakCount={5} streakFreezes={0} lastActivityDate={null} />);
    expect(screen.queryByLabelText(/streak freeze/i)).toBeNull();
  });
  it('has no accessibility violations', async () => {
    const { container } = render(<StatsBar xp={10} level={1} streakCount={5} streakFreezes={1} lastActivityDate={null} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
