import type { Mutation, Query } from '@tanstack/react-query';
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';
import { isOfflineDbAvailable } from './offline/sqlite';

/** How long persisted queries stay valid on disk (and the matching gcTime). */
export const PERSIST_MAX_AGE = 24 * 60 * 60 * 1000; // 24h

/**
 * Content query-key heads that SQLite owns on native. Excluded from the
 * localStorage persist blob when `isOfflineDbAvailable()` is true.
 */
const CONTENT_QUERY_KEYS: readonly string[] = ['modules', 'module-levels', 'level-lessons', 'lesson', 'module'];

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
  'trade-config',
  // Simulator data the child has already seen — kept readable offline.
  // `market-movers` was removed (dead after Goal 5; the Simulator now reads
  // `market-snapshot`). `market-search` / news / coach stay excluded.
  'market-snapshot',
  'quote',
  'trades',
  'stock-history',
];

/** Persist only successfully-fetched queries whose key head is allowlisted. */
export function shouldDehydrateQuery(query: Query): boolean {
  if (query.state.status !== 'success') return false;
  const head = query.queryKey[0];
  if (typeof head !== 'string' || !PERSISTED_QUERY_KEYS.includes(head)) return false;
  // On native, content lives in SQLite — keep it out of the localStorage blob.
  if (isOfflineDbAvailable() && CONTENT_QUERY_KEYS.includes(head)) return false;
  return true;
}

/** Persist only paused lesson-completion mutations — the offline outbox.
 * Settled mutations and other keys are not persisted. */
export function shouldDehydrateMutation(mutation: Mutation): boolean {
  return (
    mutation.state.isPaused === true &&
    Array.isArray(mutation.options.mutationKey) &&
    mutation.options.mutationKey[0] === 'completeLesson'
  );
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
