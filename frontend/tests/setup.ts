import '@testing-library/jest-dom/vitest';
import { expect, vi } from 'vitest';
import * as matchers from 'vitest-axe/matchers';

// Auto-load all English catalogs so extraction tasks never need to edit this
// file — the mock in __mocks__/react-i18next.ts discovers new namespaces via
// Vite glob. Tests that need the real i18next stack add vi.unmock('react-i18next').
vi.mock('react-i18next');

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
