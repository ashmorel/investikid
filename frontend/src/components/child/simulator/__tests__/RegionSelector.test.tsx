import { useState } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { RegionSelector } from '../RegionSelector';
import type { RegionCode } from '@/lib/region';

describe('RegionSelector', () => {
  it('renders three options and marks the value selected', () => {
    render(<RegionSelector value="GB" onChange={vi.fn()} />);
    expect(screen.getByRole('radiogroup', { name: /market region/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /UK/i })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('radio', { name: /US/i })).toHaveAttribute('aria-checked', 'false');
  });

  it('roves tabindex: only the selected radio is tabbable', () => {
    render(<RegionSelector value="GB" onChange={vi.fn()} />);
    expect(screen.getByRole('radio', { name: /UK/i })).toHaveAttribute('tabindex', '0');
    expect(screen.getByRole('radio', { name: /US/i })).toHaveAttribute('tabindex', '-1');
    expect(screen.getByRole('radio', { name: /HK/i })).toHaveAttribute('tabindex', '-1');
  });

  it('fires onChange when an option is clicked', async () => {
    const onChange = vi.fn();
    render(<RegionSelector value="US" onChange={onChange} />);
    await userEvent.click(screen.getByRole('radio', { name: /HK/i }));
    expect(onChange).toHaveBeenCalledWith('HK');
  });

  it('moves selection with arrow keys', async () => {
    const onChange = vi.fn();
    render(<RegionSelector value="US" onChange={onChange} />);
    const us = screen.getByRole('radio', { name: /US/i });
    us.focus();
    await userEvent.keyboard('{ArrowRight}');
    expect(onChange).toHaveBeenCalledWith('GB');
  });

  it('wraps with ArrowLeft from the first option to the last', async () => {
    const onChange = vi.fn();
    render(<RegionSelector value="US" onChange={onChange} />);
    const us = screen.getByRole('radio', { name: /US/i });
    us.focus();
    await userEvent.keyboard('{ArrowLeft}');
    expect(onChange).toHaveBeenCalledWith('HK');
  });

  it('moves focus to the newly-selected radio on arrow navigation', async () => {
    function Controlled() {
      const [value, setValue] = useState<RegionCode>('US');
      return <RegionSelector value={value} onChange={setValue} />;
    }
    render(<Controlled />);
    const us = screen.getByRole('radio', { name: /US/i });
    us.focus();
    await userEvent.keyboard('{ArrowRight}');
    expect(screen.getByRole('radio', { name: /UK/i })).toHaveFocus();
  });

  it('has no axe violations', async () => {
    const { container } = render(<RegionSelector value="US" onChange={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
