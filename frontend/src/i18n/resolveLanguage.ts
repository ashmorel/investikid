import { type LanguageCode, isSupportedLanguage } from './languages';
import { LANGUAGE_STORAGE_KEY } from '../hooks/useLanguage';
import { isNativeApp } from '../lib/platform';

// Map an arbitrary BCP-47 locale to one of our supported codes.
export function mapToSupported(locale: string): LanguageCode {
  const lc = (locale || '').toLowerCase();
  if (lc.startsWith('zh')) {
    // Traditional: Hant, TW, HK, MO; everything else Chinese → Simplified.
    if (lc.includes('hant') || lc.includes('-tw') || lc.includes('-hk') || lc.includes('-mo')) {
      return 'zh-Hant';
    }
    return 'zh-Hans';
  }
  const base = lc.split('-')[0];
  return isSupportedLanguage(base) ? (base as LanguageCode) : 'en';
}

async function deviceLocale(): Promise<string> {
  if (isNativeApp()) {
    try {
      const { Device } = await import('@capacitor/device');
      const { value } = await Device.getLanguageTag();
      return value;
    } catch {
      /* fall through to navigator */
    }
  }
  return navigator.language || 'en';
}

// Boot order: localStorage cache → device locale → en. (The authenticated
// server value overrides this once /me loads; see useLanguage.)
export async function resolveBootLanguage(): Promise<LanguageCode> {
  const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored && isSupportedLanguage(stored)) return stored;
  return mapToSupported(await deviceLocale());
}
