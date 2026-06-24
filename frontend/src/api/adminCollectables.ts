import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

export const UNLOCK_TYPES = ['streak_days', 'window_xp', 'window_lessons', 'window_arcade'] as const;
export const RARITIES = ['common', 'rare', 'epic', 'legendary'] as const;
export type UnlockType = (typeof UNLOCK_TYPES)[number];
export type Rarity = (typeof RARITIES)[number];
export type DropStatus = 'scheduled' | 'live' | 'ended';

export interface PoolItem {
  item_id: string;
  slug: string;
  name: string;
  emoji: string;
  type: string;
}

export interface Drop extends PoolItem {
  rarity: Rarity | null;
  unlock_type: UnlockType | null;
  unlock_threshold: number | null;
  available_from: string | null;
  available_until: string | null;
  status: DropStatus;
  owned_count: number;
}

export interface ScheduleBody {
  item_id: string;
  rarity: Rarity;
  unlock_type: UnlockType;
  unlock_threshold: number;
  available_from: string;
  available_until: string;
}

const POOL_KEY = ['admin', 'collectables', 'pool'];
const DROPS_KEY = ['admin', 'collectables', 'drops'];

export function usePool() {
  return useQuery({ queryKey: POOL_KEY, queryFn: () => apiFetch<PoolItem[]>('/admin/collectables/pool') as Promise<PoolItem[]> });
}

export function useDrops() {
  return useQuery({ queryKey: DROPS_KEY, queryFn: () => apiFetch<Drop[]>('/admin/collectables') as Promise<Drop[]> });
}

function useInvalidate() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: POOL_KEY });
    qc.invalidateQueries({ queryKey: DROPS_KEY });
  };
}

export function useScheduleDrop() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: ScheduleBody) =>
      apiFetch<Drop>('/admin/collectables', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export function useEditDrop() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ itemId, body }: { itemId: string; body: Partial<ScheduleBody> }) =>
      apiFetch<Drop>(`/admin/collectables/${itemId}`, { method: 'PATCH', body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export function useUnscheduleDrop() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (itemId: string) =>
      apiFetch<PoolItem>(`/admin/collectables/${itemId}/unschedule`, { method: 'POST' }),
    onSuccess: invalidate,
  });
}
