import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { OptionCard } from '../OptionCard';

describe('OptionCard', () => {
  it('is a radio that reports checked when selected/correct and fires onSelect', () => {
    const onSelect = vi.fn();
    render(<OptionCard letter="A" state="selected" onSelect={onSelect}>£10</OptionCard>);
    const r = screen.getByRole('radio', { name: /£10/ });
    expect(r).toHaveAttribute('aria-checked', 'true');
    r.click();
    expect(onSelect).toHaveBeenCalled();
  });
  it('no a11y violations inside a radiogroup', async () => {
    const { container } = render(
      <div role="radiogroup" aria-label="answers">
        <OptionCard letter="A" state="default" onSelect={() => {}}>One</OptionCard>
        <OptionCard letter="B" state="correct" onSelect={() => {}}>Two</OptionCard>
      </div>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
