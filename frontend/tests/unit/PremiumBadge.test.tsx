import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PremiumBadge } from '@/components/child/PremiumBadge';

describe('PremiumBadge', () => {
  it('shows the word Premium + a glyph (not colour-only)', () => {
    render(<PremiumBadge />);
    expect(screen.getByText(/premium/i)).toBeInTheDocument();
    expect(screen.getByText('✨')).toBeInTheDocument();
  });
});
