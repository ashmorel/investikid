import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MarketSearchBar } from '@/components/child/simulator/MarketSearchBar';

describe('MarketSearchBar', () => {
  it('renders search input with label', () => {
    render(<MarketSearchBar value="" onChange={vi.fn()} />);
    expect(screen.getByRole('searchbox', { name: /search stocks/i })).toBeInTheDocument();
  });

  it('calls onChange when user types', async () => {
    const onChange = vi.fn();
    render(<MarketSearchBar value="" onChange={onChange} />);
    const input = screen.getByRole('searchbox');
    await userEvent.type(input, 'A');
    expect(onChange).toHaveBeenCalledWith('A');
  });
});
