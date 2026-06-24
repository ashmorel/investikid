import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import type { UseQueryResult } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import LimitedShelf from '../LimitedShelf';
import type { CollectableDrop, CollectablesState, OwnedCollectable } from '@/api/collectables';

// i18n is globally mocked in tests/setup.ts via vi.mock('react-i18next')
// The mock returns the key so we assert on i18n key substrings.

vi.mock('@/api/collectables', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/collectables')>();
  return { ...actual, useCollectables: vi.fn() };
});

vi.mock('@/api/cosmetics', () => ({
  useEquipCosmetic: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { useCollectables } from '@/api/collectables';

function mockQuery(data: CollectablesState) {
  vi.mocked(useCollectables).mockReturnValue(
    { data, isLoading: false } as unknown as UseQueryResult<CollectablesState | null, Error>,
  );
}

const legendaryDrop: CollectableDrop = {
  slug: 'streak-legend',
  name: 'Streak Legend',
  emoji: '🔥',
  type: 'accessory',
  rarity: 'legendary',
  ends_at: '2099-07-01T00:00:00Z',
  goal: { type: 'streak_days', threshold: 7, current: 3 },
  earned: false,
};

const earnedDrop: CollectableDrop = {
  ...legendaryDrop,
  earned: true,
};

const ownedCollectable: OwnedCollectable = {
  slug: 'streak-legend',
  name: 'Streak Legend',
  emoji: '🔥',
  type: 'accessory',
  rarity: 'legendary',
  equipped: false,
};

describe('LimitedShelf', () => {
  it('renders the drop name, rarity badge, and progress when not earned', () => {
    mockQuery({ active: [legendaryDrop], owned: [] });

    render(<LimitedShelf />);

    expect(screen.getByText('Streak Legend')).toBeInTheDocument();
    // rarity badge — checks for "legendary" text (i18n key or literal)
    expect(screen.getByText(/legendary/i)).toBeInTheDocument();
    // progress "3 / 7"
    expect(screen.getByText(/3\s*\/\s*7/i)).toBeInTheDocument();
  });

  it('shows an Earned state when drop.earned is true', () => {
    mockQuery({ active: [earnedDrop], owned: [] });

    render(<LimitedShelf />);

    // i18n mock returns the key; we look for the "earned" substring from the key
    expect(screen.getByText(/earned/i)).toBeInTheDocument();
    // progress bar should NOT appear
    expect(screen.queryByText(/3\s*\/\s*7/i)).not.toBeInTheDocument();
  });

  it('shows the owned collection when the user owns collectables', () => {
    mockQuery({ active: [], owned: [ownedCollectable] });

    render(<LimitedShelf />);

    expect(screen.getByText('Streak Legend')).toBeInTheDocument();
  });

  it('renders nothing when both active and owned are empty', () => {
    mockQuery({ active: [], owned: [] });

    const { container } = render(<LimitedShelf />);
    expect(container.firstChild).toBeNull();
  });

  it('has no accessibility violations with active drop', async () => {
    mockQuery({ active: [legendaryDrop], owned: [] });

    const { container } = render(<LimitedShelf />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
