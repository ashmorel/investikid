import { describe, it, expect, beforeEach, vi } from 'vitest';

// Tracks whether the @capacitor/haptics module factory was ever evaluated,
// i.e. whether the dynamic import inside haptics.ts actually ran.
const hapticsModuleImported = vi.fn();
const notificationSpy = vi.fn(async () => {});
const impactSpy = vi.fn(async () => {});

vi.mock('@capacitor/haptics', () => {
  hapticsModuleImported();
  return {
    Haptics: { notification: notificationSpy, impact: impactSpy },
    NotificationType: { Success: 'SUCCESS', Warning: 'WARNING' },
    ImpactStyle: { Medium: 'MEDIUM', Heavy: 'HEAVY' },
  };
});

let native = false;
vi.mock('@/lib/platform', () => ({ isNativeApp: () => native }));

async function freshHaptics() {
  vi.resetModules();
  return await import('../haptics');
}

beforeEach(() => {
  native = false;
  hapticsModuleImported.mockClear();
  notificationSpy.mockClear();
  impactSpy.mockClear();
});

describe('haptic', () => {
  it('never imports @capacitor/haptics on web (isNativeApp false)', async () => {
    const { haptic } = await freshHaptics();
    await haptic('success');
    await haptic('heavy');
    expect(hapticsModuleImported).not.toHaveBeenCalled();
    expect(notificationSpy).not.toHaveBeenCalled();
    expect(impactSpy).not.toHaveBeenCalled();
  });

  it('maps kinds to notification/impact on native', async () => {
    native = true;
    const { haptic } = await freshHaptics();
    await haptic('success');
    expect(notificationSpy).toHaveBeenCalledWith({ type: 'SUCCESS' });
    await haptic('warning');
    expect(notificationSpy).toHaveBeenCalledWith({ type: 'WARNING' });
    await haptic('medium');
    expect(impactSpy).toHaveBeenCalledWith({ style: 'MEDIUM' });
    await haptic('heavy');
    expect(impactSpy).toHaveBeenCalledWith({ style: 'HEAVY' });
  });

  it('swallows errors from the native plugin', async () => {
    native = true;
    notificationSpy.mockRejectedValueOnce(new Error('boom'));
    const { haptic } = await freshHaptics();
    await expect(haptic('success')).resolves.toBeUndefined();
  });
});
