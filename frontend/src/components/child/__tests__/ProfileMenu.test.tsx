import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ProfileMenu } from '../ProfileMenu';

vi.mock('@/hooks/useChildSession', () => ({ useChildSession: vi.fn() }));
vi.mock('@/api/auth', () => ({
  authApi: { logout: vi.fn().mockResolvedValue({}), updatePreferences: vi.fn().mockResolvedValue({}) },
  TOPIC_OPTIONS: [{ value: '', label: 'All topics' }],
}));
vi.mock('@/api/content', () => ({ TOPIC_OPTIONS: [{ value: '', label: 'All topics' }] }));
vi.mock('@/components/mobile/BottomSheet', () => ({ BottomSheet: () => null }));
vi.mock('@/components/child/FeedbackDialog', () => ({ FeedbackDialog: () => null }));
vi.mock('@/hooks/useMediaQuery', () => ({ useMediaQuery: () => true }));

import { useChildSession } from '@/hooks/useChildSession';
const mockUseChildSession = vi.mocked(useChildSession);

function wrap(ui: React.ReactNode) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProfileMenu', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows Admin link when is_admin is true', async () => {
    mockUseChildSession.mockReturnValue({
      data: { id: '1', email: 'a@b.com', username: 'admin', dob: '', country_code: 'GB',
               currency_code: 'GBP', topic_path: null, is_premium: false, is_admin: true,
               parent_email: null, created_at: '', email_verified_at: null },
      isLoading: false,
    } as ReturnType<typeof useChildSession>);

    wrap(<ProfileMenu username="admin" />);
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    expect(screen.getByRole('menuitem', { name: /admin/i })).toBeInTheDocument();
  });

  it('does not show Admin link when is_admin is false', async () => {
    mockUseChildSession.mockReturnValue({
      data: { id: '2', email: 'k@b.com', username: 'kid', dob: '', country_code: 'GB',
               currency_code: 'GBP', topic_path: null, is_premium: false, is_admin: false,
               parent_email: null, created_at: '', email_verified_at: null },
      isLoading: false,
    } as ReturnType<typeof useChildSession>);

    wrap(<ProfileMenu username="kid" />);
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    expect(screen.queryByRole('menuitem', { name: /^admin$/i })).not.toBeInTheDocument();
  });

  it('does not show Admin link when session is undefined', async () => {
    mockUseChildSession.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<typeof useChildSession>);

    wrap(<ProfileMenu username="guest" />);
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    expect(screen.queryByRole('menuitem', { name: /^admin$/i })).not.toBeInTheDocument();
  });
});
