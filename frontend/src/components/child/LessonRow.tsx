import { Link } from 'react-router-dom';
import { Check, Play, Circle } from 'lucide-react';
import type { LessonSummary } from '@/api/content';

type Status = 'done' | 'next' | 'later';

export function LessonRow({ moduleId, lesson, status }: { moduleId: string; lesson: LessonSummary; status: Status }) {
  return (
    <Link
      to={`/lessons/${moduleId}/${lesson.id}`}
      className="flex items-center gap-3 border-b border-amber-100 px-4 py-3.5 last:border-b-0 hover:bg-amber-50 transition-colors"
    >
      <StatusIcon status={status} />
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-gray-900 truncate">{lesson.order_index + 1}. {lesson.title}</p>
      </div>
      <div className="flex items-center gap-2 text-xs shrink-0">
        <span className="rounded-lg bg-amber-100 px-2 py-0.5 font-semibold text-amber-800 capitalize">{lesson.type}</span>
        <span className="text-gray-500">{lesson.xp_reward} XP</span>
      </div>
    </Link>
  );
}

function StatusIcon({ status }: { status: Status }) {
  if (status === 'done') return <Check aria-label="completed" className="h-5 w-5 text-green-500" />;
  if (status === 'next') return (
    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500">
      <Play aria-label="next up" className="h-3.5 w-3.5 text-white" fill="white" />
    </span>
  );
  return <Circle aria-label="not started" className="h-5 w-5 text-gray-300" />;
}
