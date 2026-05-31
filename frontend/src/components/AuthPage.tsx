import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

type Props = {
  children: ReactNode;
  className?: string;
};

export function AuthPage({ children, className }: Props) {
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
        {children}
      </div>
    </main>
  );
}
