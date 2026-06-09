import { describe, it, expect } from 'vitest';
import { toRegionCode } from '@/lib/region';

describe('toRegionCode', () => {
  it('passes through supported region codes', () => {
    expect(toRegionCode('US')).toBe('US');
    expect(toRegionCode('GB')).toBe('GB');
    expect(toRegionCode('HK')).toBe('HK');
  });

  it('clamps unsupported country codes to US', () => {
    expect(toRegionCode('FR')).toBe('US');
    expect(toRegionCode('de')).toBe('US');
    expect(toRegionCode('')).toBe('US');
  });

  it('clamps null/undefined to US', () => {
    expect(toRegionCode(null)).toBe('US');
    expect(toRegionCode(undefined)).toBe('US');
  });
});
