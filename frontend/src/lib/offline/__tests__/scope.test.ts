import { describe, it, expect } from 'vitest';
import type { Me } from '@/api/auth';
import { scopeFromMe } from '../scope';

const base = { id: 'C1' } as unknown as Me;

describe('scopeFromMe', () => {
  it('prefers active_market_code', () => {
    expect(scopeFromMe({ ...base, active_market_code: 'GB' } as Me))
      .toEqual({ childId: 'C1', market: 'GB' });
  });
  it('falls back to content_region then US', () => {
    expect(scopeFromMe({ ...base, content_region: 'HK' } as Me))
      .toEqual({ childId: 'C1', market: 'HK' });
    expect(scopeFromMe(base)).toEqual({ childId: 'C1', market: 'US' });
  });
  it('returns null without an id', () => {
    expect(scopeFromMe(null)).toBeNull();
    expect(scopeFromMe({} as Me)).toBeNull();
  });
});
