import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PennyFAB } from '../PennyFAB';

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('PennyFAB', () => {
  it('renders with accessible label', () => {
    wrap(<PennyFAB dueCount={0} />);
    expect(screen.getByRole('button', { name: /open coach penny/i })).toBeInTheDocument();
  });

  it('shows badge dot when dueCount > 0', () => {
    wrap(<PennyFAB dueCount={3} />);
    expect(screen.getByTestId('penny-badge')).toBeInTheDocument();
  });

  it('hides badge dot when dueCount is 0', () => {
    wrap(<PennyFAB dueCount={0} />);
    expect(screen.queryByTestId('penny-badge')).not.toBeInTheDocument();
  });

  it('calls onOpen on click', async () => {
    const onOpen = vi.fn();
    wrap(<PennyFAB dueCount={0} onOpen={onOpen} />);
    await userEvent.click(screen.getByRole('button', { name: /open coach penny/i }));
    expect(onOpen).toHaveBeenCalledTimes(1);
  });
});
