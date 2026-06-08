import { registerPlugin } from '@capacitor/core';

export interface PlayProduct { id: string; displayPrice: string; displayName: string }
export interface PlayBillingPlugin {
  getProducts(o: { productIds: string[] }): Promise<{ products: PlayProduct[] }>;
  purchase(o: { productId: string; obfuscatedAccountId: string }): Promise<{ purchaseToken?: string; productId?: string; pending?: boolean }>;
  restore(): Promise<{ purchaseTokens: string[] }>;
}
export const PlayBilling = registerPlugin<PlayBillingPlugin>('PlayBilling');
