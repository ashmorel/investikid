import { describe, it, expect } from 'vitest';
import { orderModulesForTier } from '../tierModuleOrder';

const mods = [
  { id: 'a', topic: 'budgeting', order_index: 0 },
  { id: 'b', topic: 'stocks', order_index: 1 },
  { id: 'c', topic: 'crypto', order_index: 2 },
  { id: 'd', topic: 'taxes', order_index: 3 },
];

describe('orderModulesForTier', () => {
  it('investor surfaces investing topics first', () => {
    const ids = orderModulesForTier(mods, 'investor').map((m) => m.id);
    expect(ids.indexOf('b')).toBeLessThan(ids.indexOf('a'));
    expect(ids.indexOf('c')).toBeLessThan(ids.indexOf('a'));
  });
  it('explorer surfaces foundations first', () => {
    const ids = orderModulesForTier(mods, 'explorer').map((m) => m.id);
    expect(ids.indexOf('a')).toBeLessThan(ids.indexOf('b'));
  });
  it('falls back to order_index for unmapped/tied topics', () => {
    const ids = orderModulesForTier(mods, 'investor').map((m) => m.id);
    expect(ids[ids.length - 1]).toBe('d');
  });
  it('does not mutate the input array', () => {
    const copy = [...mods];
    orderModulesForTier(mods, 'investor');
    expect(mods).toEqual(copy);
  });
});
