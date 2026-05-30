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
