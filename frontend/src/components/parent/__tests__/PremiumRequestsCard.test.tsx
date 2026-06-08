import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PremiumRequestsCard } from '../PremiumRequestsCard';

vi.mock('@/api/premium', () => ({
  premiumApi: {
    parentRequests: vi.fn(async () => [
      {
        id: 'req-1',
        child_username: 'Yasmin',
        context_kind: 'module',
        context_label: 'Investing Basics',
        created_at: '2026-06-07T10:00:00Z',
      },
    ]),
    declineRequest: vi.fn(async () => ({ status: 'ok' })),
  },
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

describe('PremiumRequestsCard', () => {
  it('renders the pending request', async () => {
    render(wrap(<PremiumRequestsCard />));
    expect(await screen.findByText('Yasmin')).toBeInTheDocument();
    expect(screen.getByText(/Investing Basics/)).toBeInTheDocument();
  });

  it('calls declineRequest when Decline is clicked', async () => {
    const { premiumApi } = await import('@/api/premium');
    const user = userEvent.setup();
    render(wrap(<PremiumRequestsCard />));
    await user.click(await screen.findByRole('button', { name: /decline/i }));
    expect(premiumApi.declineRequest).toHaveBeenCalledWith('req-1');
  });

  it('calls onApprove when Approve is clicked', async () => {
    const onApprove = vi.fn();
    const user = userEvent.setup();
    render(wrap(<PremiumRequestsCard onApprove={onApprove} />));
    await user.click(await screen.findByRole('button', { name: /approve/i }));
    expect(onApprove).toHaveBeenCalled();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(wrap(<PremiumRequestsCard />));
    await screen.findByText('Yasmin');
    expect(await axe(container)).toHaveNoViolations();
  });
});
