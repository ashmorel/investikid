// Single source of truth for display languages (BCP-47). Keep in lockstep with
// backend/app/core/languages.py — a backend test enforces code parity.
export type SupportedLanguage = {
  code: 'en' | 'es' | 'fr' | 'de' | 'zh-Hant' | 'zh-Hans';
  endonym: string;
  available: boolean; // true once a UI catalog ships
};

export const SUPPORTED_LANGUAGES: SupportedLanguage[] = [
  { code: 'en', endonym: 'English', available: true },
  { code: 'es', endonym: 'Español', available: false },
  { code: 'fr', endonym: 'Français', available: false },
  { code: 'de', endonym: 'Deutsch', available: false },
  { code: 'zh-Hant', endonym: '繁體中文', available: false },
  { code: 'zh-Hans', endonym: '简体中文', available: false },
];

export const AVAILABLE_LANGUAGES = SUPPORTED_LANGUAGES.filter((l) => l.available);
export const SUPPORTED_CODES = SUPPORTED_LANGUAGES.map((l) => l.code);
export type LanguageCode = SupportedLanguage['code'];

export function isSupportedLanguage(code: string): code is LanguageCode {
  return (SUPPORTED_CODES as string[]).includes(code);
}
