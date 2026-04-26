import { describe, it, expect, beforeEach } from 'vitest';
import { readCookie } from '@/lib/cookies';

describe('readCookie', () => {
  beforeEach(() => { document.cookie = ''; });

  it('returns null when cookie absent', () => {
    expect(readCookie('csrf_token')).toBeNull();
  });

  it('reads a single cookie value', () => {
    document.cookie = 'csrf_token=abc123';
    expect(readCookie('csrf_token')).toBe('abc123');
  });

  it('reads value among multiple cookies', () => {
    document.cookie = 'other=xyz';
    document.cookie = 'csrf_token=abc123';
    expect(readCookie('csrf_token')).toBe('abc123');
  });

  it('decodes percent-encoded values', () => {
    document.cookie = 'csrf_token=' + encodeURIComponent('a/b=c');
    expect(readCookie('csrf_token')).toBe('a/b=c');
  });
});
