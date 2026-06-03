import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { GradientButton } from '../GradientButton';

describe('GradientButton', () => {
  it('renders a button and fires onClick', () => {
    const onClick = vi.fn();
    render(<GradientButton onClick={onClick}>Start</GradientButton>);
    screen.getByRole('button', { name: 'Start' }).click();
    expect(onClick).toHaveBeenCalled();
  });
  it('renders a link when `to` is set', () => {
    render(<MemoryRouter><GradientButton to="/x">Go</GradientButton></MemoryRouter>);
    expect(screen.getByRole('link', { name: 'Go' })).toHaveAttribute('href', '/x');
  });
  it('no a11y violations', async () => {
    const { container } = render(<GradientButton>Check</GradientButton>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
