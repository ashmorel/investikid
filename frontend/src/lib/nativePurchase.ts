import { StoreKit } from '@/lib/storekit';
import { PlayBilling } from '@/lib/playBilling';

export type PurchaseStatus = 'active' | 'pending' | 'cancelled';
export type PurchaseResult = { status: PurchaseStatus };

// Per-platform deps as a discriminated union: an iOS caller can't forget
// verifyApple, an Android caller can't forget verifyGoogle, and neither has to
// pass a no-op stub for the other platform.
export type IosPurchaseDeps = {
  platform: 'ios';
  productId: string;
  getAppleToken: () => Promise<string>;
  verifyApple: (jws: string) => Promise<void>;
};
export type AndroidPurchaseDeps = {
  platform: 'android';
  productId: string;
  getGoogleToken: () => Promise<string>;
  verifyGoogle: (purchaseToken: string, productId: string) => Promise<void>;
};
export type NativePurchaseDeps = IosPurchaseDeps | AndroidPurchaseDeps;

/** Run a native subscription purchase and verify it. `pending` means the OS is
 *  awaiting parental approval (Ask-to-Buy) — entitlement flips later via webhook
 *  + reconcile, so we do NOT verify/unlock here. */
export async function runNativePurchase(deps: NativePurchaseDeps): Promise<PurchaseResult> {
  if (deps.platform === 'android') {
    const token = await deps.getGoogleToken();
    const res = await PlayBilling.purchase({ productId: deps.productId, obfuscatedAccountId: token });
    if (res.pending) return { status: 'pending' };
    if (!res.purchaseToken) return { status: 'cancelled' };
    await deps.verifyGoogle(res.purchaseToken, res.productId ?? deps.productId);
    return { status: 'active' };
  }
  const token = await deps.getAppleToken();
  const res = await StoreKit.purchase({ productId: deps.productId, appAccountToken: token });
  if (res.pending) return { status: 'pending' };
  if (!res.jws) return { status: 'cancelled' };
  await deps.verifyApple(res.jws);
  return { status: 'active' };
}
