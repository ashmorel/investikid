import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Web (non-native) — the Sounds toggle must show everywhere.
vi.mock('@/lib/platform', () => ({ isNativeApp: () => false }));
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
import { isSoundEnabled } from '@/lib/sound';

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>;
}

async function openSoundsToggle() {
  const view = render(wrap(<ProfileMenu username="Sam" />));
  await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
  await userEvent.click(await screen.findByRole('menuitem', { name: /profile/i }));
  const toggle = await screen.findByRole('checkbox', { name: /sounds/i });
  return { toggle, view };
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe('ProfileMenu sounds toggle', () => {
  it('renders checked by default (sounds on)', async () => {
    const { toggle } = await openSoundsToggle();
    expect(toggle).toBeChecked();
  });

  it('reflects a persisted muted state', async () => {
    localStorage.setItem('investikid-sound', '0');
    const { toggle } = await openSoundsToggle();
    expect(toggle).not.toBeChecked();
  });

  it('click flips the state and persists it', async () => {
    const { toggle } = await openSoundsToggle();
    await userEvent.click(toggle);
    expect(toggle).not.toBeChecked();
    expect(localStorage.getItem('investikid-sound')).toBe('0');
    expect(isSoundEnabled()).toBe(false);

    await userEvent.click(toggle);
    expect(toggle).toBeChecked();
    expect(isSoundEnabled()).toBe(true);
  });

  it('has no axe violations with the editor open', async () => {
    const { view } = await openSoundsToggle();
    const results = await axe(view.container);
    expect(results).toHaveNoViolations();
  });
});
