import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { REMINDER } from '@/lib/reminderConfig';
import { requestReminderPermission, syncStreakReminder } from '@/lib/streakReminder';

vi.mock('@/lib/platform', () => ({ isNativeApp: () => true }));
vi.mock('@/lib/streakReminder', () => ({
  requestReminderPermission: vi.fn(async () => true),
  applyStreakReminder: vi.fn(async () => {}),
  syncStreakReminder: vi.fn(async () => {}),
  decideStreakReminder: () => ({ action: 'cancel' }),
  ymdLocal: () => '2026-01-15',
}));
vi.mock('@/hooks/useChildSession', () => ({ useChildSession: () => ({ data: { username: 'Sam', is_premium: false } }) }));
vi.mock('@/api/auth', () => ({
  authApi: { logout: vi.fn().mockResolvedValue({}), updatePreferences: vi.fn().mockResolvedValue({}) },
}));
vi.mock('@/api/content', () => ({ TOPIC_OPTIONS: [{ value: '', label: 'All topics' }] }));
vi.mock('@/components/child/FeedbackDialog', () => ({ FeedbackDialog: () => null }));
vi.mock('@/components/child/RegionSwitcher', () => ({ RegionSwitcher: () => null }));
vi.mock('@/components/child/CurrencySelector', () => ({ CurrencySelector: () => null }));
// Desktop path renders the editor content inline inside a Dialog.
vi.mock('@/hooks/useMediaQuery', () => ({ useMediaQuery: () => true }));

import { ProfileMenu } from '../ProfileMenu';

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>;
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  vi.mocked(requestReminderPermission).mockResolvedValue(true);
});

/** Open the account menu → Profile editor and return the reminder checkbox. */
async function openReminderToggle() {
  render(wrap(<ProfileMenu username="Sam" />));
  await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
  await userEvent.click(await screen.findByRole('menuitem', { name: /profile/i }));
  await screen.findByText(/daily streak reminder/i);
  return screen.getByRole('checkbox');
}

describe('ProfileMenu daily reminder toggle (native)', () => {
  it('renders the reminder toggle on native', async () => {
    render(wrap(<ProfileMenu username="Sam" />));
    // Settings live behind the account menu → Profile editor; open it first.
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    await userEvent.click(await screen.findByRole('menuitem', { name: /profile/i }));
    expect(await screen.findByText(/daily streak reminder/i)).toBeInTheDocument();
  });

  it('enables the reminder immediately when permission is granted', async () => {
    const checkbox = await openReminderToggle();
    await userEvent.click(checkbox);

    expect(requestReminderPermission).toHaveBeenCalled();
    expect(localStorage.getItem(REMINDER.storageKey)).toBe('1');
    expect(syncStreakReminder).toHaveBeenCalled();
  });

  it('shows the denied hint and does not persist when permission is refused', async () => {
    vi.mocked(requestReminderPermission).mockResolvedValueOnce(false);
    const checkbox = await openReminderToggle();
    await userEvent.click(checkbox);

    expect(
      await screen.findByText(/turn on notifications for investikid/i),
    ).toBeInTheDocument();
    expect(localStorage.getItem(REMINDER.storageKey)).toBeNull();
  });
});
