import type { Query } from '@tanstack/react-query';
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';

/** How long persisted queries stay valid on disk (and the matching gcTime). */
export const PERSIST_MAX_AGE = 24 * 60 * 60 * 1000; // 24h

/**
 * Allowlist of query-key first segments that are safe + useful to persist:
 * child learning content and the child's own simulator data. Admin, parent,
 * search, news and coach/AI queries are deliberately excluded.
 */
export const PERSISTED_QUERY_KEYS: readonly string[] = [
  'modules',
  'module-levels',
  'level-lessons',
  'lesson',
  'module',
  'me',
  'progress',
  'portfolio',
  'market-movers',
  'trade-config',
];

/** Persist only successfully-fetched queries whose key head is allowlisted. */
export function shouldDehydrateQuery(query: Query): boolean {
  if (query.state.status !== 'success') return false;
  const head = query.queryKey[0];
  return typeof head === 'string' && PERSISTED_QUERY_KEYS.includes(head);
}

/**
 * Create the localStorage persister, or null when localStorage is unusable
 * (e.g. private browsing) so the app silently degrades to in-memory caching.
 */
export function createAppPersister() {
  try {
    const storage = window.localStorage;
    const probeKey = '__investikid-persist-probe__';
    storage.setItem(probeKey, '1');
    storage.removeItem(probeKey);
    return createSyncStoragePersister({ storage, key: 'investikid-query-cache' });
  } catch {
    return null;
  }
}
