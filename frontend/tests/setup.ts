import '@testing-library/jest-dom/vitest';
import { expect, vi } from 'vitest';
import * as matchers from 'vitest-axe/matchers';

// ---------------------------------------------------------------------------
// Global react-i18next mock
// ---------------------------------------------------------------------------
// Resolves dotted keys against the English locale catalogs so components that
// call useTranslation() return the real English text in tests, without needing
// a full i18n initialisation cycle.
import commonEn from '../src/locales/en/common.json';
import settingsEn from '../src/locales/en/settings.json';

type JsonObj = Record<string, unknown>;

const CATALOGS: Record<string, JsonObj> = {
  common: commonEn as JsonObj,
  settings: settingsEn as JsonObj,
};

function resolveKey(catalog: JsonObj, key: string): string {
  const parts = key.split('.');
  let node: JsonObj | string = catalog;
  for (const part of parts) {
    if (node && typeof node === 'object' && part in node) {
      const next = (node as JsonObj)[part];
      node = next as JsonObj | string;
    } else {
      return key; // fallback to key
    }
  }
  return typeof node === 'string' ? node : key;
}

vi.mock('react-i18next', () => ({
  useTranslation: (ns?: string) => {
    const nsKey = ns ?? 'common';
    const catalog = CATALOGS[nsKey] ?? CATALOGS.common;
    return {
      t: (key: string, opts?: Record<string, unknown>) => {
        let value = resolveKey(catalog, key);
        // Simple interpolation: replace {{varName}} with opts[varName]
        if (opts) {
          value = value.replace(/\{\{(\w+)\}\}/g, (_: string, k: string) =>
            opts[k] !== undefined ? String(opts[k]) : `{{${k}}}`,
          );
        }
        return value;
      },
      i18n: { changeLanguage: vi.fn(), language: 'en' },
    };
  },
  Trans: ({ children }: { children: React.ReactNode }) => children,
  initReactI18next: { type: '3rdParty', init: vi.fn() },
}));

// Matcher TS typing lives in `tests/vitest-axe.d.ts` (vitest-axe's
// bundled extend-expect.d.ts only augments the legacy `Vi.Assertion`
// global). Runtime registration happens here.
expect.extend(matchers);

// jsdom does not implement matchMedia; provide a desktop-width default so
// components that call useMediaQuery still work in tests that don't use the
// renderMobile / renderDesktop helpers.
if (typeof window !== 'undefined' && !window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string) => {
      const minMatch = query.match(/\(min-width:\s*(\d+)px\)/);
      const matches = minMatch ? 1024 >= parseInt(minMatch[1], 10) : false;
      return {
        matches,
        media: query,
        addEventListener: () => {},
        removeEventListener: () => {},
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
      };
    },
  });
}
