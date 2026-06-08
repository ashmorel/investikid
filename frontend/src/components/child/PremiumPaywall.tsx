import { useState } from 'react';
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from '@/components/ui/sheet';
import { Penny } from '@/components/child/ui/Penny';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { premiumApi } from '@/api/premium';
import { PAYWALL_CTA, PAYWALL_REQUEST_DECLINED, PAYWALL_TITLE, PREMIUM_BENEFITS } from '@/lib/premiumConfig';
import type { PaywallContext } from '@/hooks/usePremiumPaywall';

export function PremiumPaywall({ context, onClose }: { context: PaywallContext | null; onClose: () => void }) {
  const isDesktop = useMediaQuery('(min-width: 640px)');
  const [sentStatus, setSentStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const open = context !== null;

  async function ask() {
    if (!context) return;
    setBusy(true);
    try {
      const res = await premiumApi.requestUnlock({ kind: context.kind, label: context.label });
      setSentStatus(res?.status ?? 'sent');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={(o) => { if (!o) { onClose(); setSentStatus(null); } }}>
      <SheetContent
        side={isDesktop ? 'right' : 'bottom'}
        className={
          isDesktop
            ? 'flex h-full w-full max-w-md flex-col gap-0 border-brand-100 bg-white p-0 sm:max-w-md'
            : 'flex max-h-[85svh] flex-col gap-0 rounded-t-2xl border-brand-100 bg-white p-0'
        }
      >
        <SheetHeader className="flex-row items-center gap-2 border-b border-brand-100 px-4 py-3 text-left">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100" aria-hidden="true">
            <Penny size={28} mood="happy" />
          </span>
          <div>
            <SheetTitle>{PAYWALL_TITLE}</SheetTitle>
            <SheetDescription>
              {context ? `"${context.label}" is a Premium treat.` : 'Premium unlocks more.'}
            </SheetDescription>
          </div>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-auto px-4 py-3 pb-[calc(0.75rem+var(--safe-bottom))]">
          {sentStatus ? (
            <p className="py-6 text-center text-base font-semibold text-ink">
              {sentStatus === 'no_parent'
                ? 'Ask a grown-up to set up Premium for you. 💛'
                : sentStatus === 'declined'
                  ? PAYWALL_REQUEST_DECLINED
                  : sentStatus === 'already_sent'
                    ? 'We already told your grown-up today 👍'
                    : "We've let your grown-up know! 🎉"}
            </p>
          ) : (
            <>
              <ul className="space-y-2">
                {PREMIUM_BENEFITS.map((b) => (
                  <li key={b} className="flex items-start gap-2 text-sm text-ink">
                    <span aria-hidden="true">✨</span><span>{b}</span>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={ask}
                disabled={busy}
                className="mt-4 w-full rounded-full bg-brand-gradient px-5 py-3 text-sm font-bold text-white shadow disabled:opacity-60"
              >
                {busy ? 'Sending…' : PAYWALL_CTA}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="mt-2 w-full rounded-full px-5 py-2 text-sm font-semibold text-muted-foreground"
              >
                Maybe later
              </button>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
