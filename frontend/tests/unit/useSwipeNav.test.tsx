import { render, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useRef } from 'react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { useSwipeNav } from '@/hooks/useSwipeNav';

const navigateMock = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

function TestHarness() {
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();
  useSwipeNav({ ref });
  return (
    <div ref={ref} data-testid="swipe-area" style={{ width: 375, height: 600 }}>
      <p data-testid="path">{location.pathname}</p>
    </div>
  );
}

function setupMobile() {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => {
      const minMatch = query.match(/\(min-width:\s*(\d+)px\)/);
      const matches = minMatch ? 375 >= parseInt(minMatch[1], 10) : false;
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
  Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 375 });
}

describe('useSwipeNav', () => {
  beforeEach(() => {
    navigateMock.mockClear();
    setupMobile();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('navigates right (next tab) on left swipe from /home', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <TestHarness />
      </MemoryRouter>,
    );
    const area = document.querySelector('[data-testid="swipe-area"]')!;
    const now = Date.now();

    act(() => {
      fireEvent.touchStart(area, {
        touches: [{ clientX: 300, clientY: 300 }],
        timeStamp: now,
      });
      fireEvent.touchEnd(area, {
        changedTouches: [{ clientX: 100, clientY: 305 }],
        timeStamp: now + 100,
      });
    });

    expect(navigateMock).toHaveBeenCalledWith('/lessons');
  });

  it('navigates left (prev tab) on right swipe from /lessons', () => {
    render(
      <MemoryRouter initialEntries={['/lessons']}>
        <TestHarness />
      </MemoryRouter>,
    );
    const area = document.querySelector('[data-testid="swipe-area"]')!;
    const now = Date.now();

    act(() => {
      fireEvent.touchStart(area, {
        touches: [{ clientX: 100, clientY: 300 }],
        timeStamp: now,
      });
      fireEvent.touchEnd(area, {
        changedTouches: [{ clientX: 300, clientY: 305 }],
        timeStamp: now + 100,
      });
    });

    expect(navigateMock).toHaveBeenCalledWith('/home');
  });

  it('does NOT navigate on vertical swipe', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <TestHarness />
      </MemoryRouter>,
    );
    const area = document.querySelector('[data-testid="swipe-area"]')!;
    const now = Date.now();

    act(() => {
      fireEvent.touchStart(area, {
        touches: [{ clientX: 200, clientY: 100 }],
        timeStamp: now,
      });
      fireEvent.touchEnd(area, {
        changedTouches: [{ clientX: 205, clientY: 400 }],
        timeStamp: now + 100,
      });
    });

    expect(navigateMock).not.toHaveBeenCalled();
  });

  it('does NOT navigate when swipe distance is too small', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <TestHarness />
      </MemoryRouter>,
    );
    const area = document.querySelector('[data-testid="swipe-area"]')!;
    const now = Date.now();

    act(() => {
      fireEvent.touchStart(area, {
        touches: [{ clientX: 200, clientY: 300 }],
        timeStamp: now,
      });
      fireEvent.touchEnd(area, {
        changedTouches: [{ clientX: 175, clientY: 305 }],
        timeStamp: now + 100,
      });
    });

    expect(navigateMock).not.toHaveBeenCalled();
  });
});
