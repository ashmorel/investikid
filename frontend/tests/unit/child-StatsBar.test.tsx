import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatsBar } from '@/components/child/StatsBar';

describe('StatsBar', () => {
  it('renders level, xp, and streak values', () => {
    render(<StatsBar xp={320} level={4} streakCount={5} streakFreezes={0} lastActivityDate="2026-05-02" today={new Date('2026-05-02T12:00:00Z')} />);
    expect(screen.getByText(/Level 4/i)).toBeInTheDocument();
    expect(screen.getByText(/320 XP/i)).toBeInTheDocument();
    expect(screen.getByText(/5-day/i)).toBeInTheDocument();
  });

  it('streak chip has aria-label including "streak active" when active', () => {
    render(<StatsBar xp={1} level={1} streakCount={1} streakFreezes={0} lastActivityDate="2026-05-02" today={new Date('2026-05-02T00:00:00Z')} />);
    expect(screen.getByLabelText(/streak active/i)).toBeInTheDocument();
  });

  it('streak chip has aria-label "streak inactive" when last activity > 1 day ago', () => {
    render(<StatsBar xp={1} level={1} streakCount={5} streakFreezes={0} lastActivityDate="2026-04-29" today={new Date('2026-05-02T00:00:00Z')} />);
    expect(screen.getByLabelText(/streak inactive/i)).toBeInTheDocument();
  });

  it('renders zeros for fresh user', () => {
    render(<StatsBar xp={0} level={1} streakCount={0} streakFreezes={0} lastActivityDate={null} today={new Date('2026-05-02T00:00:00Z')} />);
    expect(screen.getByText(/0 XP/i)).toBeInTheDocument();
    expect(screen.getByText(/Level 1/i)).toBeInTheDocument();
  });
});
