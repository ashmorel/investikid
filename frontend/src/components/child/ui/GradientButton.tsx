import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & { to?: string; full?: boolean };

const BASE =
  'inline-flex items-center justify-center gap-1 rounded-2xl bg-brand-gradient px-5 py-3.5 text-sm font-extrabold text-white shadow-lg shadow-brand-600/30 transition-transform hover:brightness-110 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2';

export function GradientButton({ to, full, className, children, disabled, ...rest }: Props) {
  const cls = cn(BASE, full && 'w-full', disabled ? 'opacity-50 pointer-events-none active:scale-100' : '', className);
  if (to) {
    return (
      <Link
        to={to}
        className={cls}
        aria-disabled={disabled || undefined}
        onClick={rest.onClick as React.MouseEventHandler | undefined}
      >
        {children}
      </Link>
    );
  }
  return <button className={cls} disabled={disabled} {...rest}>{children}</button>;
}
