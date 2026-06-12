import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

export type CosmeticItem = {
  id: string;
  slug: string;
  name: string;
  emoji: string;
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

/** Slug of the currently equipped accessory (for Penny renders). */
export function useEquippedAccessory(): string | null {
  const { data } = useCosmetics();
  return data?.items.find((i) => i.equipped)?.slug ?? null;
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
    mutationFn: (itemId: string | null) =>
      itemId
        ? apiFetch(`/cosmetics/${itemId}/equip`, { method: 'POST' })
        : apiFetch('/cosmetics/unequip', { method: 'POST' }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: SHOP_KEY }),
  });
}
