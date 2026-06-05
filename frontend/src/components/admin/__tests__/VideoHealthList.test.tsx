import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import VideoHealthList from '../VideoHealthList';

const check = vi.fn().mockResolvedValue({ summary: {}, items: [] });
vi.mock('@/api/admin', () => ({
  useVideoHealth: () => ({
    data: [
      { lesson_id: 'l1', module_id: 'm1', module_title: 'Savings', lesson_title: 'Compound', youtube_id: 'deadID', status: 'dead', http_status: 404, checked_at: '2026-06-05T00:00:00Z' },
      { lesson_id: 'l2', module_id: 'm2', module_title: 'Stocks', lesson_title: 'What is a stock', youtube_id: 'liveID', status: 'ok', http_status: 200, checked_at: '2026-06-05T00:00:00Z' },
    ],
    isLoading: false, isError: false,
  }),
  useCheckVideoHealth: () => ({ mutate: check, isPending: false }),
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>);
}

describe('VideoHealthList', () => {
  it('renders statuses and flags the dead video', () => {
    wrap(<VideoHealthList />);
    expect(screen.getByText('Compound')).toBeInTheDocument();
    expect(screen.getByText(/^dead$/i)).toBeInTheDocument();
    expect(screen.getByText(/^ok$/i)).toBeInTheDocument();
  });

  it('Check now triggers a re-check', async () => {
    wrap(<VideoHealthList />);
    await userEvent.click(screen.getByRole('button', { name: /check now/i }));
    expect(check).toHaveBeenCalled();
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<VideoHealthList />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
