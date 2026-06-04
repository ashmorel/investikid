import { Lock } from 'lucide-react';
import type { LevelOut } from '@/api/content';

type Props = {
  level: LevelOut;
  onOpen: () => void;
  onLockedClick: () => void;
};

export function LevelCard({ level, onOpen, onLockedClick }: Props) {
  const locked = level.state === 'locked';
  const premium = level.locked_reason === 'premium';
  const handle = locked ? onLockedClick : onOpen;
  return (
    <button
      type="button"
      onClick={handle}
      aria-label={`${level.title}${locked ? (premium ? ' (premium)' : ' (locked)') : ''}`}
      className="flex w-full flex-col items-start gap-1 rounded-2xl border-2 border-brand-200 bg-white p-4 text-left"
    >
      <span className="text-2xl" aria-hidden="true">{level.icon}</span>
      <h2 className="text-sm font-bold text-gray-900">{level.title}</h2>
      {level.state === 'completed' && (
        <span className="text-xs font-medium text-success-600">✓ Completed</span>
      )}
      {level.state === 'in_progress' && (
        <span className="text-xs text-gray-500">{level.lessons_completed}/{level.lessons_total} lessons</span>
      )}
      {locked && premium && (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-accent-600">
          <Lock className="h-3.5 w-3.5" aria-hidden="true" /> Premium
        </span>
      )}
      {locked && !premium && (
        <span className="inline-flex items-center gap-1 text-xs text-gray-400">
          <Lock className="h-3.5 w-3.5" aria-hidden="true" /> Finish the previous level to unlock
        </span>
      )}
    </button>
  );
}
