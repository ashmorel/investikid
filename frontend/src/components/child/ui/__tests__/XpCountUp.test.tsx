import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { XpCountUp } from '../XpCountUp';

// Toggle framer's reduced-motion hook per test.
let reducedMotion = false;
vi.mock('framer-motion', async (importOriginal) => ({
  ...(await importOriginal<typeof import('framer-motion')>()),
  useReducedMotion: () => reducedMotion,
}));

afterEach(() => {
  reducedMotion = false;
});

describe('XpCountUp', () => {
  it('counts up to the final value', async () => {
    render(<XpCountUp value={30} />);
    await waitFor(() => expect(screen.getByText('+30')).toBeInTheDocument(), {
      timeout: 3000,
    });
  });

  it('exposes the final value to screen readers immediately (no live spam)', () => {
    render(<XpCountUp value={30} />);
    expect(screen.getByText('+30 XP')).toBeInTheDocument();
  });

  it('renders the final value immediately under reduced motion', () => {
    reducedMotion = true;
    render(<XpCountUp value={45} />);
    expect(screen.getByText('+45')).toBeInTheDocument();
  });

  it('has no a11y violations', async () => {
    const { container } = render(<XpCountUp value={10} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
