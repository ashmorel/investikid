import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { PremiumPaywall } from '@/components/child/PremiumPaywall';
import type { PremiumRequestKind } from '@/api/premium';
import { track } from '@/lib/analytics';

export type PaywallContext = { kind: PremiumRequestKind; label: string; id?: string };
type Ctx = { open: (c: PaywallContext) => void };
const PaywallCtx = createContext<Ctx | null>(null);

export function PremiumPaywallProvider({ children }: { children: ReactNode }) {
  const [ctx, setCtx] = useState<PaywallContext | null>(null);
  const open = useCallback((c: PaywallContext) => {
    track('paywall_view', { surface: c.kind });
    setCtx(c);
  }, []);
  const value = useMemo(() => ({ open }), [open]);
  return (
    <PaywallCtx.Provider value={value}>
      {children}
      <PremiumPaywall context={ctx} onClose={() => setCtx(null)} />
    </PaywallCtx.Provider>
  );
}

export function usePremiumPaywall(): Ctx {
  const c = useContext(PaywallCtx);
  if (!c) throw new Error('usePremiumPaywall must be used within PremiumPaywallProvider');
  return c;
}
