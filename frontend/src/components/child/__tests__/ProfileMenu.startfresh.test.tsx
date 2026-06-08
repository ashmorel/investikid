import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { simulatorApi } from '@/api/simulator';

vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({ data: { username: 'Sam', is_premium: false } }),
}));
vi.mock('@/api/auth', () => ({
  authApi: { logout: vi.fn().mockResolvedValue({}), updatePreferences: vi.fn().mockResolvedValue({}) },
}));
vi.mock('@/api/content', () => ({ TOPIC_OPTIONS: [{ value: '', label: 'All topics' }] }));
vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    resetPortfolio: vi.fn(() => Promise.resolve({ id: '1', virtual_cash: '1000.00', currency_code: 'USD' })),
    setCurrency: vi.fn(() => Promise.resolve({ id: '1', virtual_cash: '1000.00', currency_code: 'USD' })),
  },
}));
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

/** Open the account menu → Profile editor and return the "Start fresh" trigger button. */
async function openEditor() {
  render(wrap(<ProfileMenu username="Sam" />));
  await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
  await userEvent.click(await screen.findByRole('menuitem', { name: /profile/i }));
  return screen.findByRole('button', { name: /start fresh/i });
}

describe('ProfileMenu Start fresh', () => {
  beforeEach(() => vi.clearAllMocks());

  it('resets the portfolio when the dialog is confirmed', async () => {
    const trigger = await openEditor();
    await userEvent.click(trigger);
    const dialog = await screen.findByRole('dialog', { name: /start fresh/i });
    await userEvent.click(within(dialog).getByRole('button', { name: /confirm/i }));
    expect(simulatorApi.resetPortfolio).toHaveBeenCalledTimes(1);
  });

  it('does not reset when the dialog is cancelled', async () => {
    const trigger = await openEditor();
    await userEvent.click(trigger);
    const dialog = await screen.findByRole('dialog', { name: /start fresh/i });
    await userEvent.click(within(dialog).getByRole('button', { name: /cancel/i }));
    expect(simulatorApi.resetPortfolio).not.toHaveBeenCalled();
  });

  it('has no axe violations with the confirm dialog open', async () => {
    const trigger = await openEditor();
    await userEvent.click(trigger);
    await screen.findByRole('dialog', { name: /start fresh/i });
    expect(await axe(document.body)).toHaveNoViolations();
  });
});
