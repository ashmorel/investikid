import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TierBadge } from '@/components/child/TierBadge';

describe('TierBadge', () => {
  it('renders Premium text and amber class when premium=true', () => {
    render(<TierBadge premium={true} />);
    const badge = screen.getByTestId('tier-badge');
    expect(badge.textContent).toContain('Premium');
    expect(badge.className).toContain('bg-amber-100');
  });

  it('renders Free text and slate class when premium=false', () => {
    render(<TierBadge premium={false} />);
    const badge = screen.getByTestId('tier-badge');
    expect(badge.textContent).toContain('Free');
    expect(badge.className).toContain('bg-slate-100');
  });
});
