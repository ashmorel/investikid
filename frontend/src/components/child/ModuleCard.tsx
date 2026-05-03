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

  if (module.locked) {
    return (
      <button
        type="button"
        onClick={onLockedClick}
        aria-label={`${module.title} (locked)`}
        className={cn(
          'flex w-full flex-col gap-2 rounded-lg border bg-card p-4 text-left opacity-60',
          'cursor-not-allowed',
        )}
      >
        <span className="text-xs uppercase text-muted-foreground">{module.topic}</span>
        <h3 className="font-medium">{module.title}</h3>
        <span className="mt-2 inline-flex items-center gap-1 text-sm text-muted-foreground">
          <Lock className="h-4 w-4" /> Premium
        </span>
      </button>
    );
  }

  return (
    <Link
      to={`/lessons/${module.id}`}
      className="flex flex-col gap-2 rounded-lg border bg-card p-4 transition hover:bg-muted"
    >
      <span className="text-xs uppercase text-muted-foreground">{module.topic}</span>
      <h3 className="font-medium">{module.title}</h3>
      <p className="text-sm text-muted-foreground">{completedCount} / {totalCount} lessons</p>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div className="h-full bg-primary transition-all" style={{ width: `${pct}%` }} />
      </div>
    </Link>
  );
}
