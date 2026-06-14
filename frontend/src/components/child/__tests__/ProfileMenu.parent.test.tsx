import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

const navigate = vi.fn();
vi.mock('react-router-dom', async (orig) => ({ ...(await orig() as object), useNavigate: () => navigate }));
vi.mock('@/hooks/useChildSession', () => ({ useChildSession: vi.fn() }));

// Use vi.hoisted so parentFromSession is available inside the factory
const { parentFromSession } = vi.hoisted(() => ({
  parentFromSession: vi.fn().mockResolvedValue({ status: 'ok' }),
}));
vi.mock('@/api/auth', () => ({ authApi: { logout: vi.fn(), updatePreferences: vi.fn(), parentFromSession }, TOPIC_OPTIONS: [] }));
vi.mock('@/api/content', () => ({ TOPIC_OPTIONS: [] }));
vi.mock('@/components/mobile/BottomSheet', () => ({ BottomSheet: () => null }));
vi.mock('@/components/child/FeedbackDialog', () => ({ FeedbackDialog: () => null }));
vi.mock('@/hooks/useMediaQuery', () => ({ useMediaQuery: () => true }));

import { useChildSession } from '@/hooks/useChildSession';
import { ProfileMenu } from '../ProfileMenu';
const mockSession = vi.mocked(useChildSession);

function wrap(ui: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>);
}

describe('ProfileMenu parent entry', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows Parent area when is_parent and navigates via the bridge', async () => {
    mockSession.mockReturnValue({ data: { id: '1', username: 'sam', is_admin: false, is_parent: true } } as ReturnType<typeof useChildSession>);
    wrap(<ProfileMenu username="sam" />);
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    const item = await screen.findByRole('menuitem', { name: /parent area/i });
    await userEvent.click(item);
    expect(parentFromSession).toHaveBeenCalled();
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/parent'));
  });

  it('hides Parent area when not a parent', async () => {
    mockSession.mockReturnValue({ data: { id: '2', username: 'kid', is_admin: false, is_parent: false } } as ReturnType<typeof useChildSession>);
    wrap(<ProfileMenu username="kid" />);
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    expect(screen.queryByRole('menuitem', { name: /parent area/i })).toBeNull();
  });
});
