/**
 * Global manual mock for react-i18next.
 *
 * Vitest uses this file automatically when vi.mock('react-i18next') is called
 * (node_module mocks live in <root>/__mocks__/).
 *
 * The mock auto-discovers ALL English catalogs via Vite glob so extraction
 * tasks never need to edit setup.ts or this file — adding a new
 * src/locales/en/<ns>.json is sufficient.
 *
 * Tests that exercise the REAL initI18n stack add `vi.unmock('react-i18next')`
 * at the top of their file (it hoists above the import) to bypass this mock.
 */

import type { ReactNode } from 'react';

// Load every catalog under src/locales/en/ at build time via Vite glob.
const rawModules = import.meta.glob('../src/locales/en/*.json', { eager: true }) as Record<
  string,
  Record<string, unknown>
>;

// Build a map: namespace name (e.g. "common", "settings") → JSON object.
const CATALOGS: Record<string, Record<string, unknown>> = {};
for (const [path, mod] of Object.entries(rawModules)) {
  // Extract filename without extension: "../src/locales/en/settings.json" → "settings"
  const ns = path.replace(/^.*\/([^/]+)\.json$/, '$1');
  CATALOGS[ns] = (mod as { default?: Record<string, unknown> }).default ?? mod;
}

/** Walk a dotted key path through a nested object. Returns undefined if missing. */
function resolve(obj: Record<string, unknown>, key: string): unknown {
  const parts = key.split('.');
  let cur: unknown = obj;
  for (const part of parts) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  return cur;
}

/** Apply {{var}} interpolation from opts. */
function interpolate(value: string, opts?: Record<string, unknown>): string {
  if (!opts) return value;
  return value.replace(/\{\{(\w+)\}\}/g, (_, k) =>
    opts[k] !== undefined ? String(opts[k]) : `{{${k}}}`,
  );
}

export function useTranslation(ns: string = 'common') {
  const catalog = CATALOGS[ns] ?? CATALOGS['common'] ?? {};

  function t(key: string, opts?: Record<string, unknown>): string {
    const raw = resolve(catalog, key);
    if (typeof raw === 'string') return interpolate(raw, opts);
    return key;
  }

  return {
    t,
    i18n: {
      language: 'en',
      changeLanguage: async () => {},
    },
  };
}

/** Passthrough — renders children (or i18nKey) as-is. */
export function Trans({
  children,
  i18nKey,
}: {
  children?: ReactNode;
  i18nKey?: string;
}): ReactNode {
  return (children ?? i18nKey ?? null) as ReactNode;
}

/** Passthrough provider — no real i18next context needed in unit tests. */
export function I18nextProvider({ children }: { children: ReactNode }): ReactNode {
  return children as ReactNode;
}

/** Stub for initReactI18next (used in src/i18n/index.ts i18next.use() call). */
export const initReactI18next = {
  type: '3rdParty' as const,
  init: () => {},
};
