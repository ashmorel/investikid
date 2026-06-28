import { useEffect, useRef } from 'react';
import { useQueryClient, onlineManager } from '@tanstack/react-query';
import { isOfflineDbAvailable } from '@/lib/offline/sqlite';
import { scopeFromMe } from '@/lib/offline/scope';
import { syncMarket } from '@/lib/offline/marketSync';
import type { Me } from '@/api/auth';

/**
 * Fires `syncMarket` once per app open, and again whenever the (childId, market)
 * scope changes (e.g. a market switch). Native-only; no-op on web.
 */
export function useOfflineMarketSync(): void {
  const qc = useQueryClient();
  const me = qc.getQueryData<Me | null>(['me']);
  const scope = scopeFromMe(me ?? null);

  // Track the last scope key we fired for — a ref so it survives re-renders
  // but does NOT cause re-renders itself.
  const lastFiredKey = useRef<string | null>(null);

  useEffect(() => {
    if (!isOfflineDbAvailable()) return;
    if (!onlineManager.isOnline()) return;
    if (!scope) return;

    const key = `${scope.childId}:${scope.market}`;
    if (lastFiredKey.current === key) return;

    lastFiredKey.current = key;
    void syncMarket(scope).catch(() => {});
  }, [scope?.childId, scope?.market]); // eslint-disable-line react-hooks/exhaustive-deps
}
