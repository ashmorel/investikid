import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import type { UseQueryResult } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import FeaturedDropCard, { pickFeatured } from '../FeaturedDropCard';
import type { CollectableDrop, CollectablesState } from '@/api/collectables';

// i18n is globally mocked in tests/setup.ts (returns the key).
vi.mock('@/api/collectables', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/collectables')>();
  return { ...actual, useCollectables: vi.fn() };
});

import { useCollectables } from '@/api/collectables';

function drop(over: Partial<CollectableDrop>): CollectableDrop {
  return {
    slug: 's', name: 'Drop', emoji: '👑', type: 'accessory', rarity: 'rare',
    ends_at: '2099-01-01T00:00:00Z', goal: { type: 'streak_days', threshold: 7, current: 5 },
    earned: false, ...over,
  };
}

function mockState(state: CollectablesState | undefined) {
  vi.mocked(useCollectables).mockReturnValue(
    { data: state, isLoading: false } as unknown as UseQueryResult<CollectablesState | null, Error>,
  );
}

function renderCard() {
  return render(<MemoryRouter><FeaturedDropCard /></MemoryRouter>);
}

describe('pickFeatured', () => {
  it('ignores earned drops and picks the soonest-ending', () => {
    const a = drop({ slug: 'a', name: 'A', ends_at: '2099-03-01T00:00:00Z' });
    const b = drop({ slug: 'b', name: 'B', ends_at: '2099-01-01T00:00:00Z' });
    const earned = drop({ slug: 'c', name: 'C', ends_at: '2098-01-01T00:00:00Z', earned: true });
    expect(pickFeatured([a, b, earned])?.slug).toBe('b');
  });

  it('sorts a null ends_at last', () => {
    const dated = drop({ slug: 'd', ends_at: '2099-05-01T00:00:00Z' });
    const undated = drop({ slug: 'u', ends_at: null });
    expect(pickFeatured([undated, dated])?.slug).toBe('d');
  });

  it('returns undefined when all are earned', () => {
    expect(pickFeatured([drop({ earned: true })])).toBeUndefined();
  });
});

describe('FeaturedDropCard', () => {
  it('renders the featured drop name and progress', () => {
    mockState({ active: [drop({ name: 'Streak Legend', goal: { type: 'streak_days', threshold: 7, current: 5 } })], owned: [] });
    renderCard();
    expect(screen.getByText('Streak Legend')).toBeInTheDocument();
    expect(screen.getByText('5 / 7')).toBeInTheDocument();
    expect(screen.getByRole('link')).toBeInTheDocument();
  });

  it('features the soonest-ending of several live drops', () => {
    mockState({ active: [
      drop({ slug: 'late', name: 'Later', ends_at: '2099-09-01T00:00:00Z' }),
      drop({ slug: 'soon', name: 'Sooner', ends_at: '2099-02-01T00:00:00Z' }),
    ], owned: [] });
    renderCard();
    expect(screen.getByText('Sooner')).toBeInTheDocument();
    expect(screen.queryByText('Later')).toBeNull();
  });

  it('renders nothing when there are no active drops', () => {
    mockState({ active: [], owned: [] });
    const { container } = renderCard();
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when every live drop is earned', () => {
    mockState({ active: [drop({ earned: true })], owned: [] });
    const { container } = renderCard();
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when data is undefined', () => {
    mockState(undefined);
    const { container } = renderCard();
    expect(container).toBeEmptyDOMElement();
  });

  it('has no axe violations', async () => {
    mockState({ active: [drop({ name: 'Streak Legend' })], owned: [] });
    const { container } = renderCard();
    expect(await axe(container)).toHaveNoViolations();
  });
});
