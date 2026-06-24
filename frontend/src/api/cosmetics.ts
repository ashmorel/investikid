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

/**
 * Equipped cosmetics. Accessories STACK (a list of every equipped accessory
 * slug); background + skin are single-pick (one slug or null each).
 */
export function useEquippedCosmetics(): {
  accessories: string[];
  skin: string | null;
  background: string | null;
} {
  const { data } = useCosmetics();
  const single = (type: string) =>
    data?.items.find((i) => i.equipped && i.type === type)?.slug ?? null;
  return {
    accessories: (data?.items ?? []).filter((i) => i.equipped && i.type === 'accessory').map((i) => i.slug),
    skin: single('skin'),
    background: single('background'),
  };
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
        : apiFetch(`/cosmetics/${v.unequip}/unequip`, { method: 'POST' }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: SHOP_KEY }),
  });
}
