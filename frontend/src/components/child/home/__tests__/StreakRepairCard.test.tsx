import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import type { UseQueryResult } from '@tanstack/react-query';

// ── Mocks ────────────────────────────────────────────────────────────
vi.mock('@/hooks/useProgress', () => ({ useProgress: vi.fn() }));
vi.mock('@/api/streak', () => ({ useRepairStreak: vi.fn() }));
const toast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ toast }) }));

import { useProgress } from '@/hooks/useProgress';
import { useRepairStreak } from '@/api/streak';
import type { Progress } from '@/api/content';
import { ApiError } from '@/api/client';
import StreakRepairCard from '../StreakRepairCard';

const mockUseProgress = useProgress as unknown as ReturnType<typeof vi.fn>;
const mockUseRepairStreak = useRepairStreak as unknown as ReturnType<typeof vi.fn>;

const baseProgress: Progress = {
  xp: 100,
  level: 2,
  streak_count: 5,
  streak_freezes: 0,
  last_activity_date: '2026-06-27',
  daily_goal_xp: 30,
  xp_today: 0,
  goal_met: false,
  virtual_coins: 200,
  next_freeze_in: 5,
  streak_repair_available: true,
  streak_repair_cost: 50,
};

function mockProgress(data: Progress | undefined, opts?: { isLoading?: boolean; isError?: boolean }) {
  mockUseProgress.mockReturnValue({
    data,
    isLoading: opts?.isLoading ?? false,
    isError: opts?.isError ?? false,
  } as unknown as UseQueryResult<Progress | null, Error>);
}

const mutate = vi.fn();
function mockMutation(overrides?: Partial<ReturnType<typeof useRepairStreak>>) {
  mockUseRepairStreak.mockReturnValue({
    mutate,
    isPending: false,
    ...overrides,
  } as unknown as ReturnType<typeof useRepairStreak>);
}

beforeEach(() => {
  vi.clearAllMocks();
  mockMutation();
});

describe('StreakRepairCard — available', () => {
  beforeEach(() => mockProgress(baseProgress));

  it('renders title and confirm/dismiss buttons when repair is available', () => {
    render(<StreakRepairCard />);
    expect(screen.getByRole('button', { name: /restore my streak/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /no thanks/i })).toBeInTheDocument();
  });

  it('confirm click calls the repair mutation', () => {
    render(<StreakRepairCard />);
    fireEvent.click(screen.getByRole('button', { name: /restore my streak/i }));
    expect(mutate).toHaveBeenCalledTimes(1);
  });

  it('dismiss hides the card', () => {
    const { container } = render(<StreakRepairCard />);
    fireEvent.click(screen.getByRole('button', { name: /no thanks/i }));
    expect(container).toBeEmptyDOMElement();
  });

  it('buttons are at least 44px tall', () => {
    render(<StreakRepairCard />);
    for (const name of [/restore my streak/i, /no thanks/i]) {
      const cls = screen.getByRole('button', { name }).getAttribute('class') ?? '';
      expect(cls).toMatch(/min-h-\[44px\]/);
    }
  });

  it('has no axe violations', async () => {
    const { container } = render(<StreakRepairCard />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('fires a success toast on a successful repair', async () => {
    mockMutation({
      mutate: ((_: void, opts?: { onSuccess?: () => void }) => opts?.onSuccess?.()) as never,
    });
    render(<StreakRepairCard />);
    fireEvent.click(screen.getByRole('button', { name: /restore my streak/i }));
    await waitFor(() =>
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({ title: expect.stringMatching(/restored/i) }),
      ),
    );
  });

  it('shows the not-enough-coins message when the repair errors with that code', async () => {
    mockMutation({
      mutate: ((_: void, opts?: { onError?: (e: unknown) => void }) =>
        opts?.onError?.(new ApiError(409, 'not_enough_coins', 'not_enough_coins'))) as never,
    });
    render(<StreakRepairCard />);
    fireEvent.click(screen.getByRole('button', { name: /restore my streak/i }));
    await waitFor(() =>
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({ description: expect.stringMatching(/enough coins/i) }),
      ),
    );
  });

  it('shows the generic error message on a non-coin error', async () => {
    mockMutation({
      mutate: ((_: void, opts?: { onError?: (e: unknown) => void }) =>
        opts?.onError?.(new ApiError(500, 'boom'))) as never,
    });
    render(<StreakRepairCard />);
    fireEvent.click(screen.getByRole('button', { name: /restore my streak/i }));
    await waitFor(() =>
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({ description: expect.stringMatching(/couldn't restore/i) }),
      ),
    );
  });
});

describe('StreakRepairCard — hidden states', () => {
  it('renders nothing when repair is not available', () => {
    mockProgress({ ...baseProgress, streak_repair_available: false });
    const { container } = render(<StreakRepairCard />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing while loading', () => {
    mockProgress(undefined, { isLoading: true });
    const { container } = render(<StreakRepairCard />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing on error', () => {
    mockProgress(undefined, { isError: true });
    const { container } = render(<StreakRepairCard />);
    expect(container).toBeEmptyDOMElement();
  });
});
