import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { authApi } from '@/api/auth';
import { addBioAccount, biometric, removeBioAccount } from '@/lib/biometric';

vi.mock('@/lib/platform', () => ({ isNativeApp: () => true }));
vi.mock('@/lib/biometric', () => ({
  biometric: {
    isAvailable: vi.fn(async () => true),
    verify: vi.fn(async () => true),
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
    data: { id: '7', username: 'Sam', is_premium: false, biometric_allowed: true },
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

import { ProfileMenu } from '../ProfileMenu';

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>;
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  vi.mocked(biometric.isAvailable).mockResolvedValue(true);
  vi.mocked(biometric.verify).mockResolvedValue(true);
  vi.mocked(authApi.biometricEnroll).mockResolvedValue({ secret: 'srv-secret' });
});

/** Open the account menu → Profile editor and return the Face ID checkbox. */
async function openBiometricToggle() {
  render(wrap(<ProfileMenu username="Sam" />));
  await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
  await userEvent.click(await screen.findByRole('menuitem', { name: /profile/i }));
  return screen.findByRole('checkbox', { name: /sign in with face id/i });
}

describe('ProfileMenu Face ID toggle (native)', () => {
  it('enrolls — verify, server enroll, keychain write, registry add', async () => {
    const checkbox = await openBiometricToggle();
    await userEvent.click(checkbox);

    expect(biometric.verify).toHaveBeenCalled();
    expect(authApi.biometricEnroll).toHaveBeenCalledWith('dev-1', 'Sam');
    expect(biometric.enroll).toHaveBeenCalledWith('child:7', 'Sam', 'srv-secret');
    expect(addBioAccount).toHaveBeenCalledWith({ key: 'child:7', label: 'Sam', kind: 'child' });
  });

  it('does not enroll when biometric verify is cancelled', async () => {
    vi.mocked(biometric.verify).mockResolvedValueOnce(false);
    const checkbox = await openBiometricToggle();
    await userEvent.click(checkbox);

    expect(authApi.biometricEnroll).not.toHaveBeenCalled();
    expect(addBioAccount).not.toHaveBeenCalled();
  });

  it('unenrolls — server unenroll, keychain clear, registry remove', async () => {
    const { getBioAccounts } = await import('@/lib/biometric');
    vi.mocked(getBioAccounts).mockReturnValue([{ key: 'child:7', label: 'Sam', kind: 'child' }]);
    const checkbox = await openBiometricToggle();
    expect(checkbox).toBeChecked();
    await userEvent.click(checkbox);

    expect(authApi.biometricUnenroll).toHaveBeenCalledWith('dev-1');
    expect(biometric.clear).toHaveBeenCalledWith('child:7');
    expect(removeBioAccount).toHaveBeenCalledWith('child:7');
  });
});

describe('ProfileMenu Face ID toggle gating', () => {
  it('hides the toggle when biometric hardware is unavailable', async () => {
    vi.mocked(biometric.isAvailable).mockResolvedValue(false);
    render(wrap(<ProfileMenu username="Sam" />));
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    await userEvent.click(await screen.findByRole('menuitem', { name: /profile/i }));
    expect(screen.queryByRole('checkbox', { name: /sign in with face id/i })).toBeNull();
  });
});
