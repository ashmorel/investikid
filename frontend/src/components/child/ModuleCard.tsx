import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';
import type { ModuleOut } from '@/api/content';
import { cn } from '@/lib/utils';

type Props = {
  module: ModuleOut;
  completedCount: number;
  totalCount: number;
  onLockedClick: () => void;
};

export function ModuleCard({ module, completedCount, totalCount, onLockedClick }: Props) {
  const pct = totalCount === 0 ? 0 : Math.round((completedCount / totalCount) * 100);
  const isDone = pct === 100;

  if (module.locked) {
    return (
      <button
        type="button"
        onClick={onLockedClick}
        aria-label={`${module.title} (locked)`}
        className="flex w-full flex-col items-center gap-2 rounded-2xl border-2 border-amber-200 bg-white p-4 text-center opacity-60 cursor-not-allowed"
      >
        <span className="text-3xl">{module.icon}</span>
        <h3 className="font-bold text-sm text-gray-900">{module.title}</h3>
        <span className="inline-flex items-center gap-1 text-xs text-gray-500">
          <Lock className="h-3.5 w-3.5" /> Premium
        </span>
      </button>
    );
  }

  return (
    <Link
      to={`/lessons/${module.id}`}
      className="flex flex-col items-center gap-2 rounded-2xl border-2 border-amber-200 bg-white p-4 text-center transition hover:border-amber-400 hover:shadow-md"
    >
      <span className="text-4xl">{module.icon}</span>
      <h3 className="font-bold text-sm text-gray-900">{module.title}</h3>
      <p className="text-xs text-gray-500">{completedCount} / {totalCount} quests</p>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-amber-100">
        <div
          className={cn(
            'h-full rounded-full transition-all',
            isDone ? 'bg-gradient-to-r from-green-400 to-green-500' : 'bg-gradient-to-r from-amber-400 to-orange-500',
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      {isDone && (
        <span className="text-xs font-semibold text-green-600">✓ Complete</span>
      )}
    </Link>
  );
}
