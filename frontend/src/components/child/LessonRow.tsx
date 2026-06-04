import { Link } from 'react-router-dom';
import { Check, Play, Circle } from 'lucide-react';
import type { LessonSummary } from '@/api/content';

type Status = 'done' | 'next' | 'later';

export function LessonRow({ moduleId, levelId, lesson, status }: { moduleId: string; levelId?: string; lesson: LessonSummary; status: Status }) {
  const to = levelId
    ? `/lessons/${moduleId}/${levelId}/${lesson.id}`
    : `/lessons/${moduleId}/${lesson.id}`;
  return (
    <Link
      to={to}
      className="flex items-center gap-3 border-b border-brand-100 px-4 py-3.5 last:border-b-0 hover:bg-brand-50 transition-colors"
    >
      <StatusIcon status={status} />
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-gray-900 truncate">{lesson.order_index + 1}. {lesson.title}</p>
      </div>
      <div className="flex items-center gap-2 text-xs shrink-0">
        <span className="rounded-lg bg-brand-100 px-2 py-0.5 font-semibold text-brand-800 capitalize">{lesson.type}</span>
        <span className="text-gray-500">{lesson.xp_reward} XP</span>
      </div>
    </Link>
  );
}

function StatusIcon({ status }: { status: Status }) {
  if (status === 'done') return <Check aria-label="completed" className="h-5 w-5 text-success-600" />;
  if (status === 'next') return (
    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-gradient">
      <Play aria-label="next up" className="h-3.5 w-3.5 text-white" fill="white" />
    </span>
  );
  return <Circle aria-label="not started" className="h-5 w-5 text-gray-300" />;
}
