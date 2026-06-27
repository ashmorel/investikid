// frontend/src/hooks/useOfflineAvailability.ts
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { Me } from '@/api/auth';
import { scopeFromMe } from '@/lib/offline/scope';
import { isOfflineDbAvailable } from '@/lib/offline/sqlite';
import { listAvailableOffline } from '@/lib/offline/contentStore';

export type OfflineAvailabilityResult = {
  levelIds: Set<string>;
  lessonCount: number;
};

const EMPTY: OfflineAvailabilityResult = { levelIds: new Set<string>(), lessonCount: 0 };

export function useOfflineAvailability(): OfflineAvailabilityResult {
  const qc = useQueryClient();
  const scope = scopeFromMe(qc.getQueryData<Me>(['me']));

  const { data } = useQuery({
    queryKey: ['offline-availability', scope?.childId, scope?.market],
    queryFn: async () => {
      const result = await listAvailableOffline(scope!);
      return {
        levelIds: new Set(result.levelIds),
        lessonCount: result.lessonCount,
      };
    },
    enabled: isOfflineDbAvailable() && !!scope,
    staleTime: 60_000,
  });

  return data ?? EMPTY;
}
