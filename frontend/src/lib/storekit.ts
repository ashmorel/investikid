import { registerPlugin } from '@capacitor/core';

export interface StoreKitProduct { id: string; displayPrice: string; displayName: string }
export interface StoreKitPlugin {
  getProducts(o: { productIds: string[] }): Promise<{ products: StoreKitProduct[] }>;
  purchase(o: { productId: string; appAccountToken: string }): Promise<{ jws?: string; pending?: boolean }>;
  restore(): Promise<{ jws: string[] }>;
}
export const StoreKit = registerPlugin<StoreKitPlugin>('StoreKitPlugin');
