import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import { gamificationApi } from '@/api/gamification';

vi.mock('@/lib/platform', () => ({ isNativeApp: () => false }));
vi.mock('@/lib/biometric', () => ({
  biometric: {
    isAvailable: vi.fn(async () => false),
    verify: vi.fn(async () => false),
    enroll: vi.fn(async () => {}),
    clear: vi.fn(async () => {}),
  },
  getDeviceId: vi.fn(() => 'dev-1'),
  getBioAccounts: vi.fn(() => []),
  addBioAccount: vi.fn(),
  removeBioAccount: vi.fn(),
}));
vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({
    data: { id: '7', username: 'Sam', is_premium: false, biometric_allowed: false },
  }),
}));
vi.mock('@/api/auth', () => ({
  authApi: {
    logout: vi.fn().mockResolvedValue({}),
    updatePreferences: vi.fn().mockResolvedValue({}),
    biometricEnroll: vi.fn().mockResolvedValue({ secret: 'srv-secret' }),
    biometricUnenroll: vi.fn().mockResolvedValue({}),
  },
}));
vi.mock('@/api/content', () => ({ TOPIC_OPTIONS: [{ value: '', label: 'All topics' }] }));
vi.mock('@/components/child/FeedbackDialog', () => ({ FeedbackDialog: () => null }));
vi.mock('@/components/child/RegionSwitcher', () => ({ RegionSwitcher: () => null }));
vi.mock('@/components/child/CurrencySelector', () => ({ CurrencySelector: () => null }));
vi.mock('@/hooks/useMediaQuery', () => ({ useMediaQuery: () => true }));
vi.mock('@/api/gamification', () => ({
  gamificationApi: {
    getHandle: vi.fn(async () => ({ handle: 'CoolBadger42', hidden: false })),
    rerollHandle: vi.fn(async () => ({ handle: 'SwiftFox99' })),
    setLeaderboardVisibility: vi.fn(async () => ({ hidden: true })),
    getAllBadges: vi.fn(async () => []),
    getEarnedBadges: vi.fn(async () => []),
    getChallenges: vi.fn(async () => []),
    getLeaderboard: vi.fn(async () => []),
  },
}));

import { ProfileMenu } from '../ProfileMenu';

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>;
}

/** Open the account menu → Profile editor panel. */
async function openProfileEditor() {
  render(wrap(<ProfileMenu username="Sam" />));
  await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
  await userEvent.click(await screen.findByRole('menuitem', { name: /profile/i }));
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(gamificationApi.getHandle).mockResolvedValue({ handle: 'CoolBadger42', hidden: false });
  vi.mocked(gamificationApi.rerollHandle).mockResolvedValue({ handle: 'SwiftFox99' });
  vi.mocked(gamificationApi.setLeaderboardVisibility).mockResolvedValue({ hidden: true });
});

describe('ProfileMenu handle row', () => {
  it('shows the handle after loading', async () => {
    await openProfileEditor();
    expect(await screen.findByText('CoolBadger42')).toBeInTheDocument();
  });

  it('clicking "New name" calls rerollHandle and shows the new handle', async () => {
    await openProfileEditor();
    await screen.findByText('CoolBadger42');

    await userEvent.click(screen.getByRole('button', { name: /new name/i }));

    expect(gamificationApi.rerollHandle).toHaveBeenCalledTimes(1);
    expect(await screen.findByText('SwiftFox99')).toBeInTheDocument();
  });
});

describe('ProfileMenu hide-from-leaderboard toggle', () => {
  it('renders the hide-from-leaderboard checkbox', async () => {
    await openProfileEditor();
    const cb = await screen.findByRole('checkbox', { name: /hide me from public leaderboards/i });
    expect(cb).toBeInTheDocument();
  });

  it('seeds the hide checkbox as unchecked when API returns hidden: false', async () => {
    vi.mocked(gamificationApi.getHandle).mockResolvedValue({ handle: 'CoolBadger42', hidden: false });
    await openProfileEditor();
    const cb = await screen.findByRole('checkbox', { name: /hide me from public leaderboards/i });
    expect(cb).not.toBeChecked();
  });

  it('seeds the hide checkbox as checked when API returns hidden: true', async () => {
    vi.mocked(gamificationApi.getHandle).mockResolvedValue({ handle: 'CoolBadger42', hidden: true });
    await openProfileEditor();
    const cb = await screen.findByRole('checkbox', { name: /hide me from public leaderboards/i });
    expect(cb).toBeChecked();
  });

  it('toggling calls setLeaderboardVisibility(true)', async () => {
    await openProfileEditor();
    const cb = await screen.findByRole('checkbox', { name: /hide me from public leaderboards/i });
    await userEvent.click(cb);
    expect(gamificationApi.setLeaderboardVisibility).toHaveBeenCalledWith(true);
  });

  it('has no axe violations in the profile editor', async () => {
    const { container } = render(wrap(<ProfileMenu username="Sam" />));
    // open the profile editor to get full DOM
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    await userEvent.click(await screen.findByRole('menuitem', { name: /profile/i }));
    // wait for async handle fetch
    await screen.findByText('CoolBadger42');
    expect(await axe(container)).toHaveNoViolations();
  });
});
