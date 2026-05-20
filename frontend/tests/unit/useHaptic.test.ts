import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useHaptic } from '@/hooks/useHaptic';

describe('useHaptic', () => {
  let vibrateSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vibrateSpy = vi.fn();
    Object.defineProperty(navigator, 'vibrate', {
      writable: true,
      configurable: true,
      value: vibrateSpy,
    });
    // Default: no reduced motion
    vi.stubGlobal(
      'matchMedia',
      vi.fn((query: string) => ({
        matches: false,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('vibrates with light intensity (10ms)', () => {
    const { result } = renderHook(() => useHaptic());
    result.current('light');
    expect(vibrateSpy).toHaveBeenCalledWith(10);
  });

  it('vibrates with medium intensity (25ms)', () => {
    const { result } = renderHook(() => useHaptic());
    result.current('medium');
    expect(vibrateSpy).toHaveBeenCalledWith(25);
  });

  it('vibrates with heavy intensity (50ms)', () => {
    const { result } = renderHook(() => useHaptic());
    result.current('heavy');
    expect(vibrateSpy).toHaveBeenCalledWith(50);
  });

  it('no-ops when navigator.vibrate is unavailable', () => {
    Object.defineProperty(navigator, 'vibrate', {
      writable: true,
      configurable: true,
      value: undefined,
    });
    const { result } = renderHook(() => useHaptic());
    // Should not throw
    expect(() => result.current('medium')).not.toThrow();
  });

  it('no-ops when prefers-reduced-motion is active', () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn((query: string) => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );
    const { result } = renderHook(() => useHaptic());
    result.current('heavy');
    expect(vibrateSpy).not.toHaveBeenCalled();
  });
});
