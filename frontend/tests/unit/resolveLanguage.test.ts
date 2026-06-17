import { describe, expect, it } from 'vitest';
import { mapToSupported } from '../../src/i18n/resolveLanguage';

describe('mapToSupported', () => {
  it('maps exact codes', () => {
    expect(mapToSupported('en')).toBe('en');
    expect(mapToSupported('de')).toBe('de');
  });
  it('maps regioned locales to the base language', () => {
    expect(mapToSupported('es-ES')).toBe('es');
    expect(mapToSupported('fr-CA')).toBe('fr');
  });
  it('maps Chinese scripts correctly', () => {
    expect(mapToSupported('zh-Hant-HK')).toBe('zh-Hant');
    expect(mapToSupported('zh-TW')).toBe('zh-Hant');
    expect(mapToSupported('zh-MO')).toBe('zh-Hant');
    expect(mapToSupported('zh-CN')).toBe('zh-Hans');
    expect(mapToSupported('zh')).toBe('zh-Hans');
  });
  it('falls back to English for unsupported', () => {
    expect(mapToSupported('ja')).toBe('en');
    expect(mapToSupported('')).toBe('en');
  });
});
