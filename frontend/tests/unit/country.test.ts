import { describe, it, expect } from 'vitest';
import { countryFlag } from '@/lib/country';

describe('countryFlag', () => {
  it('converts GB to flag emoji', () => {
    expect(countryFlag('GB')).toBe('\u{1F1EC}\u{1F1E7}');
  });

  it('converts US to flag emoji', () => {
    expect(countryFlag('US')).toBe('\u{1F1FA}\u{1F1F8}');
  });

  it('handles lowercase input', () => {
    expect(countryFlag('gb')).toBe('\u{1F1EC}\u{1F1E7}');
  });

  it('returns empty string for empty input', () => {
    expect(countryFlag('')).toBe('');
  });
});
