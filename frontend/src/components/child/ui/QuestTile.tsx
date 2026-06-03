import { Link } from 'react-router-dom';
import { ArrowRight, Lock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ModuleOut } from '@/api/content';

type QuestTileProps = {
  module: ModuleOut;
  href?: string;
  eyebrow?: string;
  reason?: string;
  className?: string;
};

const TOPIC_GRADIENTS: Record<ModuleOut['topic'], string> = {
  stocks: 'from-emerald-400 to-teal-500',
  savings: 'from-sky-400 to-blue-500',
  real_estate: 'from-pink-400 to-rose-500',
  budgeting: 'from-amber-400 to-orange-500',
  risk: 'from-violet-400 to-fuchsia-500',
  crypto: 'from-cyan-400 to-indigo-500',
  taxes: 'from-lime-400 to-green-500',
  debt: 'from-red-400 to-orange-500',
  entrepreneurship: 'from-yellow-400 to-amber-500',
};

export function QuestTile({ module, href = `/lessons/${module.id}`, eyebrow, reason, className }: QuestTileProps) {
  return (
    <Link
      to={href}
      className={cn(
        'group relative block min-h-[150px] overflow-hidden rounded-3xl border border-white/80 bg-white p-4 text-left shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:ring-offset-2',
        className,
      )}
      aria-label={module.title}
    >
      <div
        className={cn(
          'absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r',
          TOPIC_GRADIENTS[module.topic] ?? 'from-amber-400 to-orange-500',
        )}
        aria-hidden="true"
      />
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-orange-50 text-2xl shadow-inner">
          <span aria-hidden="true">{module.icon}</span>
        </div>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-gray-50 text-gray-500 transition group-hover:bg-orange-50 group-hover:text-orange-600">
          {module.locked ? <Lock className="h-4 w-4" aria-hidden="true" /> : <ArrowRight className="h-4 w-4" aria-hidden="true" />}
        </span>
      </div>
      {eyebrow && <p className="mt-4 text-xs font-extrabold uppercase text-orange-600">{eyebrow}</p>}
      <h3 className="mt-1 text-base font-extrabold leading-tight text-gray-950">{module.title}</h3>
      {reason && <p className="mt-2 line-clamp-2 text-sm leading-snug text-gray-600">{reason}</p>}
    </Link>
  );
}
