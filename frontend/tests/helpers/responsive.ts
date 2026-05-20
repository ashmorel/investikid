import { render, type RenderOptions } from '@testing-library/react';
import { vi } from 'vitest';
import type { ReactElement } from 'react';

type Viewport = 'mobile' | 'tablet' | 'desktop';

const WIDTHS: Record<Viewport, number> = {
  mobile: 375,
  tablet: 768,
  desktop: 1024,
};

function setupViewport(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  });

  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => {
      // Parse "(min-width: Xpx)" patterns
      const minMatch = query.match(/\(min-width:\s*(\d+)px\)/);
      const matches = minMatch ? width >= parseInt(minMatch[1], 10) : false;
      return {
        matches,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      };
    }),
  );
}

function renderAt(viewport: Viewport, ui: ReactElement, options?: RenderOptions) {
  setupViewport(WIDTHS[viewport]);
  return render(ui, options);
}

export function renderMobile(ui: ReactElement, options?: RenderOptions) {
  return renderAt('mobile', ui, options);
}

export function renderTablet(ui: ReactElement, options?: RenderOptions) {
  return renderAt('tablet', ui, options);
}

export function renderDesktop(ui: ReactElement, options?: RenderOptions) {
  return renderAt('desktop', ui, options);
}

/**
 * Simulate a touch-capable device. Returns a cleanup function.
 */
export function mockTouchDevice(): () => void {
  const had = 'ontouchstart' in window;
  Object.defineProperty(window, 'ontouchstart', {
    writable: true,
    configurable: true,
    value: () => {},
  });
  return () => {
    if (!had) {
      delete (window as unknown as Record<string, unknown>).ontouchstart;
    }
  };
}
