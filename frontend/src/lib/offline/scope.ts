import type { Me } from '@/api/auth';

export type CacheScope = { childId: string; market: string };

/** Derive the (child, market) cache scope from the `me` payload, or null. */
export function scopeFromMe(me: Me | null | undefined): CacheScope | null {
  if (!me || !me.id) return null;
  return { childId: me.id, market: me.active_market_code ?? me.content_region ?? 'US' };
}
