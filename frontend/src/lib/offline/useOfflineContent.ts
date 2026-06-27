import type { CacheScope } from './scope';
import { isOfflineDbAvailable } from './sqlite';

export function cacheFirst<T>(opts: {
  scope: CacheScope | null;
  fetch: () => Promise<T>;
  read: (scope: CacheScope) => Promise<T | null>;
  write: (scope: CacheScope, data: T) => Promise<void>;
}): () => Promise<T> {
  const { scope, fetch, read, write } = opts;
  return async () => {
    const useStore = scope != null && isOfflineDbAvailable();
    try {
      const data = await fetch();
      if (useStore) void write(scope, data);
      return data;
    } catch (err) {
      if (useStore) {
        const cached = await read(scope);
        if (cached != null) return cached;
      }
      throw err;
    }
  };
}
