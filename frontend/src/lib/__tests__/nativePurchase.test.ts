import { describe, it, expect, vi, beforeEach } from 'vitest';

const skPurchase = vi.fn();
const pbPurchase = vi.fn();
vi.mock('@/lib/storekit', () => ({ StoreKit: { purchase: (o: unknown) => skPurchase(o) } }));
vi.mock('@/lib/playBilling', () => ({ PlayBilling: { purchase: (o: unknown) => pbPurchase(o) } }));

import { runNativePurchase } from '../nativePurchase';

const verifyApple = vi.fn(async () => {});
const verifyGoogle = vi.fn(async () => {});
const iosDeps = {
  platform: 'ios' as const,
  productId: 'premium_monthly',
  getAppleToken: vi.fn(async () => 'apple-tok'),
  verifyApple,
};
const androidDeps = {
  platform: 'android' as const,
  productId: 'premium_monthly',
  getGoogleToken: vi.fn(async () => 'google-tok'),
  verifyGoogle,
};

beforeEach(() => {
  skPurchase.mockReset(); pbPurchase.mockReset();
  verifyApple.mockClear(); verifyGoogle.mockClear();
  iosDeps.getAppleToken.mockClear(); androidDeps.getGoogleToken.mockClear();
});

describe('runNativePurchase', () => {
  it('ios success verifies and returns active', async () => {
    skPurchase.mockResolvedValue({ jws: 'JWS' });
    const r = await runNativePurchase(iosDeps);
    expect(skPurchase).toHaveBeenCalledWith({ productId: 'premium_monthly', appAccountToken: 'apple-tok' });
    expect(verifyApple).toHaveBeenCalledWith('JWS');
    expect(r.status).toBe('active');
  });
  it('ios pending returns pending without verifying', async () => {
    skPurchase.mockResolvedValue({ pending: true });
    const r = await runNativePurchase(iosDeps);
    expect(verifyApple).not.toHaveBeenCalled();
    expect(r.status).toBe('pending');
  });
  it('android success verifies and returns active', async () => {
    pbPurchase.mockResolvedValue({ purchaseToken: 'PT', productId: 'premium_monthly' });
    const r = await runNativePurchase(androidDeps);
    expect(pbPurchase).toHaveBeenCalledWith({ productId: 'premium_monthly', obfuscatedAccountId: 'google-tok' });
    expect(verifyGoogle).toHaveBeenCalledWith('PT', 'premium_monthly');
    expect(r.status).toBe('active');
  });
  it('android success falls back to the requested productId when the plugin omits it', async () => {
    pbPurchase.mockResolvedValue({ purchaseToken: 'PT' }); // no productId in the result
    const r = await runNativePurchase(androidDeps);
    expect(verifyGoogle).toHaveBeenCalledWith('PT', 'premium_monthly');
    expect(r.status).toBe('active');
  });
  it('android pending returns pending', async () => {
    pbPurchase.mockResolvedValue({ pending: true });
    const r = await runNativePurchase(androidDeps);
    expect(verifyGoogle).not.toHaveBeenCalled();
    expect(r.status).toBe('pending');
  });
  it('no token returned is cancelled', async () => {
    skPurchase.mockResolvedValue({});
    const r = await runNativePurchase(iosDeps);
    expect(r.status).toBe('cancelled');
  });
});
