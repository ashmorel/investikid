import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

type Props = { emoji: string; title: string; subtitle: string; accent: string; tint: string; to?: string; locked?: boolean; recommended?: boolean };

export function ModuleTile({ emoji, title, subtitle, accent, tint, to, locked, recommended }: Props) {
  const inner = (
    <>
      {recommended && <span className="absolute right-3 top-3 rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-extrabold text-amber-700"><span aria-hidden="true">★ </span>Next</span>}
      <span className="flex h-10 w-10 items-center justify-center rounded-xl text-xl" style={{ backgroundColor: accent }} aria-hidden="true">{emoji}</span>
      <span className="mt-2 block text-[15px] font-extrabold text-gray-900">{title}</span>
      <span className="text-[11px] font-bold text-gray-500">{subtitle}</span>
    </>
  );
  const cls = cn('relative block rounded-2xl p-3.5', locked && 'opacity-60');
  if (to && !locked) return <Link to={to} className={cn(cls, 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500')} style={{ backgroundColor: tint }}>{inner}</Link>;
  return <div className={cls} style={{ backgroundColor: tint }} aria-disabled={locked || undefined}>{inner}</div>;
}
