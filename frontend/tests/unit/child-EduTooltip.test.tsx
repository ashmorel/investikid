import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EduTooltip } from '@/components/child/simulator/EduTooltip';

describe('EduTooltip', () => {
  it('renders the term and shows tooltip content on hover', async () => {
    render(
      <EduTooltip term="Unrealized P/L" explanation="This is how much you'd gain or lose if you sold now." />
    );
    expect(screen.getByText('Unrealized P/L')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /info about Unrealized P\/L/i })).toBeInTheDocument();
  });

  it('renders children when provided instead of term text', () => {
    render(
      <EduTooltip term="Price" explanation="Current price per share.">
        <span>$185.42</span>
      </EduTooltip>
    );
    expect(screen.getByText('$185.42')).toBeInTheDocument();
  });
});
