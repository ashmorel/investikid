import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & { to?: string; full?: boolean };

const BASE =
  'inline-flex items-center justify-center gap-1 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 px-5 py-3.5 text-sm font-extrabold text-white shadow-lg shadow-orange-500/30 transition-transform hover:from-amber-500 hover:to-orange-600 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-offset-2 disabled:opacity-50 disabled:active:scale-100';

export function GradientButton({ to, full, className, children, ...rest }: Props) {
  const cls = cn(BASE, full && 'w-full', className);
  if (to) return <Link to={to} className={cls}>{children}</Link>;
  return <button className={cls} {...rest}>{children}</button>;
}
