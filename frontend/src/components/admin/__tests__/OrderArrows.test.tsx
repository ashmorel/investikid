import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import OrderArrows from '../OrderArrows';

describe('OrderArrows', () => {
  it('renders up and down buttons', () => {
    render(<OrderArrows onMoveUp={vi.fn()} onMoveDown={vi.fn()} />);
    expect(screen.getByRole('button', { name: /move up/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /move down/i })).toBeInTheDocument();
  });

  it('calls onMoveUp when up button clicked', () => {
    const onUp = vi.fn();
    render(<OrderArrows onMoveUp={onUp} onMoveDown={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /move up/i }));
    expect(onUp).toHaveBeenCalledTimes(1);
  });

  it('calls onMoveDown when down button clicked', () => {
    const onDown = vi.fn();
    render(<OrderArrows onMoveUp={vi.fn()} onMoveDown={onDown} />);
    fireEvent.click(screen.getByRole('button', { name: /move down/i }));
    expect(onDown).toHaveBeenCalledTimes(1);
  });

  it('disables up button when isFirst', () => {
    render(<OrderArrows onMoveUp={vi.fn()} onMoveDown={vi.fn()} isFirst />);
    expect(screen.getByRole('button', { name: /move up/i })).toBeDisabled();
  });

  it('disables down button when isLast', () => {
    render(<OrderArrows onMoveUp={vi.fn()} onMoveDown={vi.fn()} isLast />);
    expect(screen.getByRole('button', { name: /move down/i })).toBeDisabled();
  });
});
