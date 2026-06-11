import { describe, it, expect, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useOnline } from '../useOnline';

function setNavigatorOnline(value: boolean) {
  Object.defineProperty(window.navigator, 'onLine', {
    configurable: true,
    get: () => value,
  });
}

describe('useOnline', () => {
  afterEach(() => setNavigatorOnline(true));

  it('reports the initial navigator.onLine value', () => {
    setNavigatorOnline(false);
    const { result } = renderHook(() => useOnline());
    expect(result.current).toBe(false);
  });

  it('toggles with offline/online events', () => {
    setNavigatorOnline(true);
    const { result } = renderHook(() => useOnline());
    expect(result.current).toBe(true);

    act(() => {
      setNavigatorOnline(false);
      window.dispatchEvent(new Event('offline'));
    });
    expect(result.current).toBe(false);

    act(() => {
      setNavigatorOnline(true);
      window.dispatchEvent(new Event('online'));
    });
    expect(result.current).toBe(true);
  });
});
