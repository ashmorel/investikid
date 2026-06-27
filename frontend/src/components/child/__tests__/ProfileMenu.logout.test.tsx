import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

// Mock offline modules BEFORE importing ProfileMenu so the hoisting works.
vi.mock('@/lib/offline/contentStore', () => ({
  clearForChild: vi.fn(async () => {}),
}));
vi.mock('@/lib/offline/scope', () => ({
  scopeFromMe: vi.fn((me) => (me?.id ? { childId: me.id, market: me.active_market_code ?? 'US' } : null)),
}));

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
import { clearForChild } from '@/lib/offline/contentStore';
import type { Me } from '@/api/auth';
import { ProfileMenu } from '../ProfileMenu';

const mockUseChildSession = vi.mocked(useChildSession);
const mockClearForChild = vi.mocked(clearForChild);

function makeQc(me: Me | undefined) {
  const qc = new QueryClient();
  if (me) qc.setQueryData<Me>(['me'], me);
  return qc;
}

function wrap(ui: React.ReactNode, qc: QueryClient) {
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProfileMenu logout — clearForChild wiring', () => {
  const me: Me = {
    id: 'child-42',
    email: 'kid@test.com',
    username: 'kid',
    dob: '',
    country_code: 'GB',
    currency_code: 'GBP',
    topic_path: null,
    is_premium: false,
    is_admin: false,
    parent_email: null,
    created_at: '',
    email_verified_at: null,
    active_market_code: 'GB',
  } as unknown as Me;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseChildSession.mockReturnValue({ data: undefined, isLoading: false } as ReturnType<typeof useChildSession>);
  });

  it('calls clearForChild with the scoped childId+market before removing me from cache', async () => {
    const qc = makeQc(me);
    const removeSpy = vi.spyOn(qc, 'removeQueries');

    wrap(<ProfileMenu username="kid" />, qc);
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    await userEvent.click(screen.getByRole('menuitem', { name: /log out/i }));

    // Give the async onSettled a tick to run
    await new Promise((r) => setTimeout(r, 0));

    expect(mockClearForChild).toHaveBeenCalledWith({ childId: 'child-42', market: 'GB' });
    expect(removeSpy).toHaveBeenCalledWith({ queryKey: ['me'] });
    // clearForChild must be called before removeQueries
    const clearOrder = mockClearForChild.mock.invocationCallOrder[0];
    const removeOrder = removeSpy.mock.invocationCallOrder[0];
    expect(clearOrder).toBeLessThan(removeOrder ?? Infinity);
  });

  it('skips clearForChild when me is absent from cache (guest logout)', async () => {
    const qc = makeQc(undefined);

    wrap(<ProfileMenu username="guest" />, qc);
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    await userEvent.click(screen.getByRole('menuitem', { name: /log out/i }));

    await new Promise((r) => setTimeout(r, 0));

    expect(mockClearForChild).not.toHaveBeenCalled();
  });
});
