import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { Disclosure } from '@/components/a11y/Disclosure';

describe('Disclosure', () => {
  it('is collapsed by default and toggles on click', async () => {
    const u = userEvent.setup();
    render(<Disclosure label="Transcript">Hello world</Disclosure>);
    const btn = screen.getByRole('button', { name: /transcript/i });
    expect(btn).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Hello world')).not.toBeVisible();
    await u.click(btn);
    expect(btn).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Hello world')).toBeVisible();
  });

  it('button controls the panel by aria-controls/id', () => {
    render(<Disclosure label="X">body</Disclosure>);
    const btn = screen.getByRole('button');
    const controlsId = btn.getAttribute('aria-controls')!;
    expect(document.getElementById(controlsId)).toBeTruthy();
  });

  it('has no axe violations open or closed', async () => {
    const u = userEvent.setup();
    const { container } = render(<Disclosure label="X">body</Disclosure>);
    expect(await axe(container)).toHaveNoViolations();
    await u.click(screen.getByRole('button'));
    expect(await axe(container)).toHaveNoViolations();
  });
});
