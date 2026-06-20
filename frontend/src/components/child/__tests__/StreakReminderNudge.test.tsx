import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import StreakReminderNudge from '../StreakReminderNudge';

const isNative = vi.fn(() => true);
const requestPerm = vi.fn(async () => true);
const sync = vi.fn(async (_a?: unknown) => {});
vi.mock('@/lib/platform', () => ({ isNativeApp: () => isNative() }));
vi.mock('@/lib/streakReminder', () => ({
  requestReminderPermission: () => requestPerm(),
  syncStreakReminder: (a: unknown) => sync(a),
}));
vi.mock('@/hooks/useProgress', () => ({
  useProgress: () => ({ data: { streak_count: 3, last_activity_date: '2020-01-01' } }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

const NUDGE_KEY = 'notif_streak_nudge_seen';
const ENABLED_KEY = 'notif_streak_reminder';

beforeEach(() => {
  localStorage.clear();
  isNative.mockReturnValue(true);
  requestPerm.mockReset().mockResolvedValue(true);
  sync.mockReset();
});

describe('StreakReminderNudge', () => {
  it('renders for a native user with a streak and no prior decision', () => {
    render(<StreakReminderNudge />);
    expect(screen.getByRole('button', { name: /enable/i })).toBeInTheDocument();
  });

  it('enabling requests permission, sets the flag, and syncs', async () => {
    render(<StreakReminderNudge />);
    fireEvent.click(screen.getByRole('button', { name: /enable/i }));
    await waitFor(() => expect(requestPerm).toHaveBeenCalled());
    expect(localStorage.getItem(ENABLED_KEY)).toBe('1');
    expect(localStorage.getItem(NUDGE_KEY)).toBe('1');
    expect(sync).toHaveBeenCalled();
  });

  it('when permission is DENIED, suppresses but does not enable or sync', async () => {
    requestPerm.mockResolvedValue(false);
    render(<StreakReminderNudge />);
    fireEvent.click(screen.getByRole('button', { name: /enable/i }));
    await waitFor(() => expect(requestPerm).toHaveBeenCalled());
    expect(localStorage.getItem(NUDGE_KEY)).toBe('1'); // never nag again
    expect(localStorage.getItem(ENABLED_KEY)).toBeNull(); // reminder stays off
    expect(sync).not.toHaveBeenCalled();
  });

  it('dismiss sets the seen flag and hides without enabling', () => {
    render(<StreakReminderNudge />);
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));
    expect(localStorage.getItem(NUDGE_KEY)).toBe('1');
    expect(localStorage.getItem(ENABLED_KEY)).toBeNull();
  });

  it('renders nothing on web', () => {
    isNative.mockReturnValue(false);
    const { container } = render(<StreakReminderNudge />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing once already seen', () => {
    localStorage.setItem(NUDGE_KEY, '1');
    const { container } = render(<StreakReminderNudge />);
    expect(container).toBeEmptyDOMElement();
  });
});
