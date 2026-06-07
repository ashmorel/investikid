import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@capacitor/core', () => ({
  Capacitor: { getPlatform: vi.fn(), isNativePlatform: vi.fn() },
}));
import { Capacitor } from '@capacitor/core';
import { getPlatform, isAndroid, isNativeApp } from '../platform';

describe('platform helpers', () => {
  beforeEach(() => vi.clearAllMocks());
  it('getPlatform returns the Capacitor platform', () => {
    (Capacitor.getPlatform as ReturnType<typeof vi.fn>).mockReturnValue('android');
    expect(getPlatform()).toBe('android');
  });
  it('isAndroid true only on android', () => {
    (Capacitor.getPlatform as ReturnType<typeof vi.fn>).mockReturnValue('android');
    expect(isAndroid()).toBe(true);
    (Capacitor.getPlatform as ReturnType<typeof vi.fn>).mockReturnValue('ios');
    expect(isAndroid()).toBe(false);
  });
  it('isNativeApp delegates to Capacitor.isNativePlatform', () => {
    (Capacitor.isNativePlatform as ReturnType<typeof vi.fn>).mockReturnValue(true);
    expect(isNativeApp()).toBe(true);
  });
});
