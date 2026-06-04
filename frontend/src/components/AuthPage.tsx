import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Penny } from '@/components/child/ui/Penny';

type Props = {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  className?: string;
};

export function AuthPage({ children, title, subtitle, className }: Props) {
  return (
    <main
      className="box-border flex min-h-[100svh] w-full max-w-full items-center justify-center overflow-x-hidden px-4 py-8 sm:px-6"
      style={{
        paddingTop: 'max(2rem, calc(env(safe-area-inset-top, 0px) + 1.5rem))',
        paddingBottom: 'max(2rem, calc(env(safe-area-inset-bottom, 0px) + 1.5rem))',
        paddingLeft: 'max(1rem, env(safe-area-inset-left, 0px))',
        paddingRight: 'max(1rem, env(safe-area-inset-right, 0px))',
      }}
    >
      <div className={cn('w-full max-w-md min-w-0 break-words', className)}>
        <div className="mb-5 flex flex-col items-center text-center">
          <div className="flex items-center gap-2">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-100" aria-hidden="true">
              <Penny size={36} mood="happy" />
            </span>
            <span className="text-xl font-extrabold tracking-tight text-ink">InvestiKid</span>
          </div>
          {title && <h1 className="mt-4 text-2xl font-extrabold text-ink">{title}</h1>}
          {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
        </div>
        <div className="rounded-2xl border border-brand-100 bg-card p-6 shadow-sm">
          {children}
        </div>
      </div>
    </main>
  );
}
