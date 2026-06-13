import { Capacitor } from '@capacitor/core';

/**
 * True when running inside the native Capacitor shell (iOS/Android).
 *
 * Used to suppress external-payment UI (Stripe checkout / billing portal)
 * in native builds, which would violate App Store Guideline 3.1.1.
 * The web/PWA build is unaffected.
 */
export function isNativeApp(): boolean {
  return Capacitor.isNativePlatform();
}

/** The runtime platform: 'web' | 'ios' | 'android'. */
export function getPlatform(): string {
  return Capacitor.getPlatform();
}

/** True when running in the native Android shell. */
export function isAndroid(): boolean {
  return Capacitor.getPlatform() === 'android';
}

/** True when running in the native iOS shell. */
export function isIOS(): boolean {
  return Capacitor.getPlatform() === 'ios';
}
