import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { PennyFAB } from '../PennyFAB';

describe('PennyFAB', () => {
  it('renders with accessible label', () => {
    render(<MemoryRouter><PennyFAB dueCount={0} /></MemoryRouter>);
    expect(screen.getByRole('button', { name: /open coach penny/i })).toBeInTheDocument();
  });

  it('shows badge dot when dueCount > 0', () => {
    render(<MemoryRouter><PennyFAB dueCount={3} /></MemoryRouter>);
    expect(screen.getByTestId('penny-badge')).toBeInTheDocument();
  });

  it('hides badge dot when dueCount is 0', () => {
    render(<MemoryRouter><PennyFAB dueCount={0} /></MemoryRouter>);
    expect(screen.queryByTestId('penny-badge')).not.toBeInTheDocument();
  });

  it('calls onOpen on click', async () => {
    const onOpen = vi.fn();
    render(<MemoryRouter><PennyFAB dueCount={0} onOpen={onOpen} /></MemoryRouter>);
    await userEvent.click(screen.getByRole('button', { name: /open coach penny/i }));
    expect(onOpen).toHaveBeenCalledTimes(1);
  });
});
