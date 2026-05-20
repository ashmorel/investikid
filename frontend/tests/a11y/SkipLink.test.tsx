import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { SkipLink } from '@/components/a11y/SkipLink';

describe('SkipLink', () => {
  it('renders an anchor targeting #main with the right label', () => {
    render(<><SkipLink /><main id="main" tabIndex={-1}>x</main></>);
    const link = screen.getByRole('link', { name: /skip to main content/i });
    expect(link).toHaveAttribute('href', '#main');
  });

  it('is visually-hidden until focused', async () => {
    render(<SkipLink />);
    const link = screen.getByRole('link', { name: /skip to main content/i });
    expect(link.className).toMatch(/sr-only/);
    expect(link.className).toMatch(/focus:not-sr-only|focus-visible:not-sr-only/);
  });

  it('has no axe violations', async () => {
    const { container } = render(<><SkipLink /><main id="main" tabIndex={-1}>x</main></>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
