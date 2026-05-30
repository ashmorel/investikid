import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChildCard } from '../ChildCard';
import { parentApi, type Child } from '@/api/parent';

const BASE_CHILD: Child = {
  user_id: 'child-1',
  username: 'alex',
  country_code: 'GB',
  is_active: true,
  is_premium: false,
  parent_consent_given_at: '2026-05-01T10:00:00Z',
  consent_declined_at: null,
  deleted_at: null,
  deletion_requested_at: null,
  analytics: null,
};

function renderCard(child: Child = BASE_CHILD) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['children'], [child]);
  return render(
    <QueryClientProvider client={qc}>
      <ChildCard child={child} />
    </QueryClientProvider>,
  );
}

describe('ChildCard premium toggle', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders an unchecked premium switch for a free child', () => {
    renderCard();
    const sw = screen.getByLabelText('Premium');
    expect(sw).toBeInTheDocument();
    expect(sw).not.toBeChecked();
  });

  it('renders a checked premium switch for a premium child', () => {
    renderCard({ ...BASE_CHILD, is_premium: true });
    expect(screen.getByLabelText('Premium ✨')).toBeChecked();
  });

  it('grants premium when toggled on', async () => {
    const spy = vi
      .spyOn(parentApi, 'setChildPremium')
      .mockResolvedValue({ status: 'ok', premium: true });
    renderCard();
    fireEvent.click(screen.getByLabelText('Premium'));
    await waitFor(() => expect(spy).toHaveBeenCalledWith('child-1', true));
  });
});
