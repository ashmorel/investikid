import { describe, it, expect, vi } from 'vitest';
import type { Query } from '@tanstack/react-query';
import {
  shouldDehydrateQuery,
  createAppPersister,
  PERSISTED_QUERY_KEYS,
  PERSIST_MAX_AGE,
} from '../queryPersistence';

function fakeQuery(queryKey: unknown[], status: 'success' | 'error' | 'pending' = 'success') {
  return { queryKey, state: { status } } as unknown as Query;
}

describe('shouldDehydrateQuery', () => {
  it.each([
    ['modules'],
    ['module-levels', 3],
    ['level-lessons', 7],
    ['lesson', 12],
    ['module', 3, 'lessons'],
    ['me'],
    ['progress'],
    ['portfolio'],
    ['trade-config'],
    ['market-snapshot', 'GB'],
    ['quote', 'AAPL'],
    ['trades'],
    ['stock-history', 'NVDA'],
  ])('persists allowlisted key %j', (...key) => {
    expect(shouldDehydrateQuery(fakeQuery(key))).toBe(true);
  });

  it.each([
    [['admin', 'modules']],
    [['admin', 'stats']],
    [['admin-modules']],
    [['children']],
    [['parent-identities']],
    [['market-search', 'NVDA']],
    [['market-featured']],
    [['coach-chat']],
    [['chart-guide', 'NASDAQ', 'NVDA', '1mo']],
    [['news-summary']],
    [['home-greeting', 'morning']],
  ])('excludes admin/parent/search/coach key %j', (key) => {
    expect(shouldDehydrateQuery(fakeQuery(key))).toBe(false);
  });

  it('never persists non-success queries, even allowlisted ones', () => {
    expect(shouldDehydrateQuery(fakeQuery(['modules'], 'error'))).toBe(false);
    expect(shouldDehydrateQuery(fakeQuery(['modules'], 'pending'))).toBe(false);
  });

  it('ignores non-string key heads', () => {
    expect(shouldDehydrateQuery(fakeQuery([{ scope: 'modules' }]))).toBe(false);
  });

  it('exposes the exact allowlist', () => {
    expect(PERSISTED_QUERY_KEYS).toEqual([
      'modules',
      'module-levels',
      'level-lessons',
      'lesson',
      'module',
      'me',
      'progress',
      'portfolio',
      'trade-config',
      'market-snapshot',
      'quote',
      'trades',
      'stock-history',
    ]);
  });

  it('persists the current simulator + content keys, drops dead/excluded ones', () => {
    for (const head of ['market-snapshot', 'quote', 'trades', 'stock-history', 'portfolio', 'lesson', 'me']) {
      expect(shouldDehydrateQuery(fakeQuery([head, 'x']))).toBe(true);
    }
    expect(shouldDehydrateQuery(fakeQuery(['market-movers', 'US']))).toBe(false); // dead key removed
    expect(shouldDehydrateQuery(fakeQuery(['market-search', 'aapl']))).toBe(false); // excluded
    expect(shouldDehydrateQuery(fakeQuery(['coach']))).toBe(false); // excluded
    expect(shouldDehydrateQuery(fakeQuery(['quote', 'x'], 'error'))).toBe(false); // non-success
    expect(PERSISTED_QUERY_KEYS).not.toContain('market-movers');
  });
});

describe('createAppPersister', () => {
  it('returns a persister when localStorage works', () => {
    expect(createAppPersister()).not.toBeNull();
  });

  it('returns null when localStorage is unavailable (private mode)', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('QuotaExceededError');
    });
    try {
      expect(createAppPersister()).toBeNull();
    } finally {
      spy.mockRestore();
    }
  });

  it('uses a 24h maxAge constant', () => {
    expect(PERSIST_MAX_AGE).toBe(24 * 60 * 60 * 1000);
  });
});
