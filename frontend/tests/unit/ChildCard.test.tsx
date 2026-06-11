import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChildCard } from '@/components/ChildCard';
import type { Child } from '@/api/parent';

const baseChild: Child = {
  user_id: 'u1', username: 'kid', country_code: 'GB',
  is_active: true, is_premium: false,
  parent_consent_given_at: '2026-01-01T00:00:00Z',
  consent_declined_at: null, deleted_at: null, deletion_requested_at: null,
  age_tier: 'explorer' as const, tier_override: null,
  analytics: null,
};

function wrap(child: Child) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><ChildCard child={child} /></QueryClientProvider>,
  );
}

beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });

describe('ChildCard', () => {
  it('shows Active chip when consent given and is_active', () => {
    wrap(baseChild);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('shows Frozen chip when not active but consent given', () => {
    wrap({ ...baseChild, is_active: false });
    expect(screen.getByText('Frozen')).toBeInTheDocument();
  });

  it('disables erasure button when already deleted', () => {
    wrap({ ...baseChild, is_active: false, deleted_at: '2026-02-01T00:00:00Z' });
    expect(screen.getByRole('button', { name: /delete account/i })).toBeDisabled();
  });

  it('shows Premium badge when child is premium', () => {
    wrap({ ...baseChild, is_premium: true });
    expect(screen.getByText(/Premium ✨/)).toBeInTheDocument();
  });

  it('does not show premium toggle button', () => {
    wrap(baseChild);
    expect(screen.queryByTestId('premium-toggle')).not.toBeInTheDocument();
  });

  it('erasure button only enabled when typed username matches', async () => {
    wrap(baseChild);
    await userEvent.click(screen.getByRole('button', { name: /delete account/i }));
    const dialogConfirm = screen.getByRole('button', { name: /^delete account$/i });
    expect(dialogConfirm).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/Type child username/i), 'kid');
    expect(dialogConfirm).toBeEnabled();
  });
});
