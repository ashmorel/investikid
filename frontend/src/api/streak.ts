import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';
import type { Progress } from './content';

/**
 * Spend earned coins to repair a just-lapsed streak. The backend is
 * authoritative: it validates the repair window + coin balance and returns the
 * updated progress (409 on `streak_not_repairable` / `not_enough_coins`).
 * On success we invalidate the progress query so coins + streak refresh.
 */
export function useRepairStreak() {
  const qc = useQueryClient();
  return useMutation<Progress | null, Error, void>({
    mutationFn: () => apiFetch<Progress>('/streak/repair', { method: 'POST' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['progress'] });
    },
  });
}
