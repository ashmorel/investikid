import { describe, it, expect } from 'vitest';
import { decideBackAction, ROOT_PATHS } from '../backButton';

describe('decideBackAction', () => {
  it('exits at a root path with no history to pop', () => {
    expect(decideBackAction({ path: '/home', canGoBack: false })).toBe('exit');
  });
  it('goes back when there is web history', () => {
    expect(decideBackAction({ path: '/home', canGoBack: true })).toBe('back');
  });
  it('goes back on a non-root path even without canGoBack', () => {
    expect(decideBackAction({ path: '/lesson/42', canGoBack: false })).toBe('back');
  });
  it('treats every declared root path as an exit point', () => {
    for (const p of ROOT_PATHS) {
      expect(decideBackAction({ path: p, canGoBack: false })).toBe('exit');
    }
  });
});
