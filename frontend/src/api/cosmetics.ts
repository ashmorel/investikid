import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

export type CosmeticItem = {
  id: string;
  slug: string;
  name: string;
  emoji: string;
  type: string;
  coin_cost: number;
  is_premium: boolean;
  owned: boolean;
  equipped: boolean;
  can_buy: boolean;
};

export type ShopState = { coins: number; items: CosmeticItem[] };

const SHOP_KEY = ['cosmetics'] as const;

export function useCosmetics() {
  return useQuery<ShopState | null>({
    queryKey: SHOP_KEY,
    queryFn: () => apiFetch<ShopState>('/cosmetics'),
    staleTime: 5 * 60_000,
  });
}

/** Equipped slug per category (accessory / skin / background). */
export function useEquippedCosmetics(): {
  accessory: string | null;
  skin: string | null;
  background: string | null;
} {
  const { data } = useCosmetics();
  const bySlug = (type: string) =>
    data?.items.find((i) => i.equipped && i.type === type)?.slug ?? null;
  return {
    accessory: bySlug('accessory'),
    skin: bySlug('skin'),
    background: bySlug('background'),
  };
}

/** Slug of the currently equipped accessory (back-compat for PennyFAB/CoachPanel). */
export function useEquippedAccessory(): string | null {
  return useEquippedCosmetics().accessory;
}

export function useBuyCosmetic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) =>
      apiFetch<{ status: string; coins: number }>(`/cosmetics/${itemId}/buy`, { method: 'POST' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SHOP_KEY });
      void qc.invalidateQueries({ queryKey: ['progress'] });
    },
  });
}

export function useEquipCosmetic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { equip: string } | { unequip: string }) =>
      'equip' in v
        ? apiFetch(`/cosmetics/${v.equip}/equip`, { method: 'POST' })
        : apiFetch(`/cosmetics/unequip?type=${encodeURIComponent(v.unequip)}`, { method: 'POST' }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: SHOP_KEY }),
  });
}
