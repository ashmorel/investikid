import { describe, it, expect } from 'vitest';
import { makeNonce } from '@/lib/nonce';

describe('makeNonce', () => {
  it('returns a 32-char lowercase hex string', () => {
    const nonce = makeNonce();
    expect(nonce).toMatch(/^[0-9a-f]{32}$/);
  });

  it('two consecutive calls produce different values', () => {
    expect(makeNonce()).not.toBe(makeNonce());
  });
});
