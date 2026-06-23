import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../client';
import { useEquippedCosmetics, useEquipCosmetic } from '../cosmetics';

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
  useMutation: vi.fn(),
  useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
}));

import { useQuery, useMutation } from '@tanstack/react-query';

// ---------------------------------------------------------------------------
// useEquipCosmetic – mutationFn routing
// ---------------------------------------------------------------------------

describe('useEquipCosmetic mutationFn', () => {
  // Capture the mutationFn via useMutation mock before each test
  let equipFn: (v: { equip: string } | { unequip: string }) => unknown;

  beforeEach(() => {
    vi.restoreAllMocks();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useMutation).mockImplementation((opts: any) => {
      equipFn = opts.mutationFn as typeof equipFn;
      return {} as ReturnType<typeof useMutation>;
    });
    // Call in beforeEach — still outside React tree but eslint is satisfied
    // by not calling it inside a non-hook/non-component helper function.
    useEquipCosmetic();
  });

  it('{ equip: id } posts /cosmetics/{id}/equip', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(null);
    await equipFn({ equip: 'abc123' });
    expect(spy).toHaveBeenCalledWith('/cosmetics/abc123/equip', { method: 'POST' });
  });

  it('{ unequip: type } posts /cosmetics/unequip?type=background', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(null);
    await equipFn({ unequip: 'background' });
    expect(spy).toHaveBeenCalledWith('/cosmetics/unequip?type=background', { method: 'POST' });
  });

  it('{ unequip: type } url-encodes the type', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(null);
    await equipFn({ unequip: 'some type' });
    expect(spy).toHaveBeenCalledWith('/cosmetics/unequip?type=some%20type', { method: 'POST' });
  });
});

// ---------------------------------------------------------------------------
// useEquippedCosmetics – mapping equipped items by type
// ---------------------------------------------------------------------------

function mockItems(items: {
  id: string; slug: string; name: string; emoji: string; type: string;
  owned: boolean; equipped: boolean;
}[]) {
  vi.mocked(useQuery).mockReturnValue({
    data: {
      coins: 100,
      items: items.map((i) => ({
        ...i,
        coin_cost: 0,
        is_premium: false,
        can_buy: false,
      })),
    },
  } as ReturnType<typeof useQuery>);
}

describe('useEquippedCosmetics', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('maps equipped items by type, returns slug or null', () => {
    mockItems([
      { id: '1', slug: 'hat', name: 'Hat', emoji: '🎩', type: 'accessory', owned: true, equipped: true },
      { id: '2', slug: 'blue-bg', name: 'Blue BG', emoji: '🟦', type: 'background', owned: true, equipped: false },
      { id: '3', slug: 'skin-a', name: 'Skin A', emoji: '😀', type: 'skin', owned: true, equipped: false },
    ]);

    const result = useEquippedCosmetics();
    expect(result.accessory).toBe('hat');
    expect(result.background).toBeNull();
    expect(result.skin).toBeNull();
  });

  it('returns all nulls when nothing is equipped', () => {
    mockItems([
      { id: '1', slug: 'hat', name: 'Hat', emoji: '🎩', type: 'accessory', owned: false, equipped: false },
    ]);

    const result = useEquippedCosmetics();
    expect(result).toEqual({ accessory: null, skin: null, background: null });
  });

  it('returns all three when all categories are equipped', () => {
    mockItems([
      { id: '1', slug: 'hat', name: 'Hat', emoji: '🎩', type: 'accessory', owned: true, equipped: true },
      { id: '2', slug: 'blue-bg', name: 'Blue BG', emoji: '🟦', type: 'background', owned: true, equipped: true },
      { id: '3', slug: 'skin-a', name: 'Skin A', emoji: '😀', type: 'skin', owned: true, equipped: true },
    ]);

    const result = useEquippedCosmetics();
    expect(result).toEqual({ accessory: 'hat', skin: 'skin-a', background: 'blue-bg' });
  });

  it('returns null for all when data is undefined', () => {
    vi.mocked(useQuery).mockReturnValue({ data: undefined } as ReturnType<typeof useQuery>);

    const result = useEquippedCosmetics();
    expect(result).toEqual({ accessory: null, skin: null, background: null });
  });
});
